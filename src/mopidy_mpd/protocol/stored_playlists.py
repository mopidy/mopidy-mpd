from __future__ import annotations

import datetime
import logging
import re
from typing import TYPE_CHECKING, Literal, overload
from urllib.parse import urlparse

from mopidy.types import Uri, UriScheme

from mopidy_mpd import exceptions, protocol, translator

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mopidy.models import Playlist, Track

    from mopidy_mpd.context import MpdContext

logger = logging.getLogger(__name__)


def _check_playlist_name(name: str) -> None:
    if re.search("[/\n\r]", name):
        raise exceptions.MpdInvalidPlaylistNameError


@overload
def _get_playlist(
    context: MpdContext, name: str, *, must_exist: Literal[True]
) -> Playlist:
    ...


@overload
def _get_playlist(
    context: MpdContext, name: str, *, must_exist: Literal[False]
) -> Playlist | None:
    ...


def _get_playlist(
    context: MpdContext, name: str, *, must_exist: bool
) -> Playlist | None:
    playlist = None
    uri = context.uri_map.playlist_uri_from_name(name)
    if uri:
        playlist = context.core.playlists.lookup(uri).get()
    if must_exist and playlist is None:
        raise exceptions.MpdNoExistError("No such playlist")
    return playlist


@protocol.commands.add("listplaylist")
def listplaylist(context: MpdContext, name: str) -> protocol.Result:
    """
    *musicpd.org, stored playlists section:*

        ``listplaylist {NAME}``

        Lists the files in the playlist ``NAME.m3u``.

    Output format::

        file: relative/path/to/file1.flac
        file: relative/path/to/file2.ogg
        file: relative/path/to/file3.mp3
    """
    playlist = _get_playlist(context, name, must_exist=True)
    return [("file", track.uri) for track in playlist.tracks]


@protocol.commands.add("listplaylistinfo")
def listplaylistinfo(context: MpdContext, name: str) -> protocol.Result:
    """
    *musicpd.org, stored playlists section:*

        ``listplaylistinfo {NAME}``

        Lists songs in the playlist ``NAME.m3u``.

    Output format:

        Standard track listing, with fields: file, Time, Title, Date,
        Album, Artist, Track
    """
    playlist = _get_playlist(context, name, must_exist=True)
    track_uris = [track.uri for track in playlist.tracks]
    tracks_map = context.core.library.lookup(uris=track_uris).get()
    tracks = []
    for uri in track_uris:
        tracks.extend(tracks_map[uri])
    playlist = playlist.replace(tracks=tracks)
    return translator.playlist_to_mpd_format(playlist, context.session.tagtypes)


@protocol.commands.add("listplaylists")
def listplaylists(context: MpdContext) -> protocol.ResultList:
    """
    *musicpd.org, stored playlists section:*

        ``listplaylists``

        Prints a list of the playlist directory.

        After each playlist name the server sends its last modification
        time as attribute ``Last-Modified`` in ISO 8601 format. To avoid
        problems due to clock differences between clients and the server,
        clients should not compare this value with their local clock.

    Output format::

        playlist: a
        Last-Modified: 2010-02-06T02:10:25Z
        playlist: b
        Last-Modified: 2010-02-06T02:11:08Z

    *Clarifications:*

    - ncmpcpp 0.5.10 segfaults if we return 'playlist: ' on a line, so we must
      ignore playlists without names, which isn't very useful anyway.
    """
    last_modified = _get_last_modified()
    result: protocol.ResultList = []
    for playlist_ref in context.core.playlists.as_list().get():
        if not playlist_ref.name:
            continue
        name = context.uri_map.playlist_name_from_uri(playlist_ref.uri)
        if name is None:
            continue
        result.append(("playlist", name))
        result.append(("Last-Modified", last_modified))
    return result


# TODO: move to translators?
def _get_last_modified(last_modified: int | None = None) -> str:
    """Formats last modified timestamp of a playlist for MPD.

    Time in UTC with second precision, formatted in the ISO 8601 format, with
    the "Z" time zone marker for UTC. For example, "1970-01-01T00:00:00Z".
    """
    if last_modified is None:
        # If unknown, assume the playlist is modified
        dt = datetime.datetime.now(tz=datetime.UTC)
    else:
        dt = datetime.datetime.fromtimestamp(last_modified / 1000.0, tz=datetime.UTC)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


DEFAULT_PLAYLIST_SLICE = slice(0, None)


@protocol.commands.add("load", playlist_slice=protocol.RANGE)
def load(
    context: MpdContext,
    name: str,
    playlist_slice: slice = DEFAULT_PLAYLIST_SLICE,
) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``load {NAME} [START:END]``

        Loads the playlist into the current queue. Playlist plugins are
        supported. A range may be specified to load only a part of the
        playlist.

    *Clarifications:*

    - ``load`` appends the given playlist to the current playlist.

    - MPD 0.17.1 does not support open-ended ranges, i.e. without end
      specified, for the ``load`` command, even though MPD's general range docs
      allows open-ended ranges.

    - MPD 0.17.1 does not fail if the specified range is outside the playlist,
      in either or both ends.
    """
    playlist = _get_playlist(context, name, must_exist=True)
    track_uris = [track.uri for track in playlist.tracks[playlist_slice]]
    context.core.tracklist.add(uris=track_uris).get()


@protocol.commands.add("playlistadd")
def playlistadd(context: MpdContext, name: str, track_uri: Uri) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``playlistadd {NAME} {URI}``

        Adds ``URI`` to the playlist ``NAME.m3u``.

        ``NAME.m3u`` will be created if it does not exist.
    """
    _check_playlist_name(name)
    old_playlist = _get_playlist(context, name, must_exist=False)
    if not old_playlist:
        # Create new playlist with this single track
        lookup_res = context.core.library.lookup(uris=[track_uri]).get()
        tracks = [track for uri_tracks in lookup_res.values() for track in uri_tracks]
        _create_playlist(context, name, tracks)
    else:
        # Add track to existing playlist
        lookup_res = context.core.library.lookup(uris=[track_uri]).get()
        new_tracks = [
            track for uri_tracks in lookup_res.values() for track in uri_tracks
        ]
        new_playlist = old_playlist.replace(
            tracks=list(old_playlist.tracks) + new_tracks
        )
        saved_playlist = context.core.playlists.save(new_playlist).get()
        if saved_playlist is None:
            playlist_scheme = UriScheme(urlparse(old_playlist.uri).scheme)
            uri_scheme = UriScheme(urlparse(track_uri).scheme)
            raise exceptions.MpdInvalidTrackForPlaylistError(
                playlist_scheme, uri_scheme
            )


def _create_playlist(context: MpdContext, name: str, tracks: Iterable[Track]) -> None:
    """
    Creates new playlist using backend appropriate for the given tracks
    """
    uri_schemes = {UriScheme(urlparse(t.uri).scheme) for t in tracks}
    for scheme in uri_schemes:
        new_playlist = context.core.playlists.create(name, scheme).get()
        if new_playlist is None:
            logger.debug("Backend for scheme %s can't create playlists", scheme)
            continue  # Backend can't create playlists at all
        new_playlist = new_playlist.replace(tracks=tracks)
        saved_playlist = context.core.playlists.save(new_playlist).get()
        if saved_playlist is not None:
            return  # Created and saved
        continue  # Failed to save using this backend
    # Can't use backend appropriate for passed URI schemes, use default one
    default_scheme = context.config["mpd"]["default_playlist_scheme"]
    new_playlist = context.core.playlists.create(name, default_scheme).get()
    if new_playlist is None:
        # If even MPD's default backend can't save playlist, everything is lost
        logger.warning("MPD's default backend can't create playlists")
        raise exceptions.MpdFailedToSavePlaylistError(default_scheme)
    new_playlist = new_playlist.replace(tracks=tracks)
    saved_playlist = context.core.playlists.save(new_playlist).get()
    if saved_playlist is None:
        uri_scheme = UriScheme(urlparse(new_playlist.uri).scheme)
        raise exceptions.MpdFailedToSavePlaylistError(uri_scheme)


@protocol.commands.add("playlistclear")
def playlistclear(context: MpdContext, name: str) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``playlistclear {NAME}``

        Clears the playlist ``NAME.m3u``.

    The playlist will be created if it does not exist.
    """
    _check_playlist_name(name)
    playlist = _get_playlist(context, name, must_exist=False)
    if not playlist:
        playlist = context.core.playlists.create(name).get()

    # TODO(type): Handle the failure to create a playlist
    assert playlist

    # Just replace tracks with empty list and save
    playlist = playlist.replace(tracks=[])
    if context.core.playlists.save(playlist).get() is None:
        raise exceptions.MpdFailedToSavePlaylistError(
            UriScheme(urlparse(playlist.uri).scheme)
        )


@protocol.commands.add("playlistdelete", songpos=protocol.UINT)
def playlistdelete(context: MpdContext, name: str, songpos: int) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``playlistdelete {NAME} {SONGPOS}``

        Deletes ``SONGPOS`` from the playlist ``NAME.m3u``.
    """
    _check_playlist_name(name)
    playlist = _get_playlist(context, name, must_exist=True)

    try:
        # Convert tracks to list and remove requested
        tracks = list(playlist.tracks)
        tracks.pop(songpos)
    except IndexError as exc:
        raise exceptions.MpdArgError("Bad song index") from exc

    # Replace tracks and save playlist
    playlist = playlist.replace(tracks=tracks)
    saved_playlist = context.core.playlists.save(playlist).get()
    if saved_playlist is None:
        raise exceptions.MpdFailedToSavePlaylistError(
            UriScheme(urlparse(playlist.uri).scheme)
        )


@protocol.commands.add("playlistmove", from_pos=protocol.UINT, to_pos=protocol.UINT)
def playlistmove(context: MpdContext, name: str, from_pos: int, to_pos: int) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``playlistmove {NAME} {SONGID} {SONGPOS}``

        Moves ``SONGID`` in the playlist ``NAME.m3u`` to the position
        ``SONGPOS``.

    *Clarifications:*

    - The second argument is not a ``SONGID`` as used elsewhere in the protocol
      documentation, but just the ``SONGPOS`` to move *from*, i.e.
      ``playlistmove {NAME} {FROM_SONGPOS} {TO_SONGPOS}``.
    """
    if from_pos == to_pos:
        return

    _check_playlist_name(name)
    playlist = _get_playlist(context, name, must_exist=True)
    if from_pos == to_pos:
        return  # Nothing to do

    try:
        # Convert tracks to list and perform move
        tracks = list(playlist.tracks)
        track = tracks.pop(from_pos)
        tracks.insert(to_pos, track)
    except IndexError as exc:
        raise exceptions.MpdArgError("Bad song index") from exc

    # Replace tracks and save playlist
    playlist = playlist.replace(tracks=tracks)
    saved_playlist = context.core.playlists.save(playlist).get()
    if saved_playlist is None:
        raise exceptions.MpdFailedToSavePlaylistError(
            UriScheme(urlparse(playlist.uri).scheme)
        )


@protocol.commands.add("rename")
def rename(context: MpdContext, old_name: str, new_name: str) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``rename {NAME} {NEW_NAME}``

        Renames the playlist ``NAME.m3u`` to ``NEW_NAME.m3u``.
    """
    _check_playlist_name(old_name)
    _check_playlist_name(new_name)

    old_playlist = _get_playlist(context, old_name, must_exist=True)

    if _get_playlist(context, new_name, must_exist=False):
        raise exceptions.MpdExistError("Playlist already exists")
    # TODO: should we purge the mapping in an else?

    # Create copy of the playlist and remove original
    uri_scheme = UriScheme(urlparse(old_playlist.uri).scheme)
    empty_playlist = context.core.playlists.create(new_name, uri_scheme).get()
    if empty_playlist is None:
        raise exceptions.MpdFailedToSavePlaylistError(uri_scheme)
    filled_playlist = empty_playlist.replace(tracks=old_playlist.tracks)
    saved_playlist = context.core.playlists.save(filled_playlist).get()
    if saved_playlist is None:
        raise exceptions.MpdFailedToSavePlaylistError(uri_scheme)
    context.core.playlists.delete(old_playlist.uri).get()


@protocol.commands.add("rm")
def rm(context: MpdContext, name: str) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``rm {NAME}``

        Removes the playlist ``NAME.m3u`` from the playlist directory.
    """
    _check_playlist_name(name)
    uri = context.uri_map.playlist_uri_from_name(name)
    if not uri:
        raise exceptions.MpdNoExistError("No such playlist")
    context.core.playlists.delete(uri).get()


@protocol.commands.add("save")
def save(context: MpdContext, name: str) -> None:
    """
    *musicpd.org, stored playlists section:*

        ``save {NAME}``

        Saves the current playlist to ``NAME.m3u`` in the playlist
        directory.
    """
    _check_playlist_name(name)
    tracks = context.core.tracklist.get_tracks().get()
    playlist = _get_playlist(context, name, must_exist=False)
    if not playlist:
        # Create new playlist
        _create_playlist(context, name, tracks)
    else:
        # Overwrite existing playlist
        new_playlist = playlist.replace(tracks=tracks)
        saved_playlist = context.core.playlists.save(new_playlist).get()
        if saved_playlist is None:
            raise exceptions.MpdFailedToSavePlaylistError(
                UriScheme(urlparse(playlist.uri).scheme)
            )
