from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

from mopidy.models import Album, Artist, Playlist, TlTrack, Track

from mopidy_mpd.protocol import tagtype_list

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from mopidy_mpd import protocol

logger = logging.getLogger(__name__)


def track_to_mpd_format(  # noqa: C901, PLR0912, PLR0915
    obj: Track | TlTrack,
    tagtypes: set[str],
    *,
    position: int | None = None,
    stream_title: str | None = None,
) -> protocol.ResultList:
    """
    Format track for output to MPD client.

    :param obj: the track
    :param tagtypes: the MPD tagtypes enabled by the client
    :param position: track's position in playlist
    :param stream_title: the current streams title
    """
    match obj:
        case TlTrack() as tl_track:
            tlid = tl_track.tlid
            track = tl_track.track
        case Track() as track:
            tlid = None

    if not track.uri:
        logger.warning("Ignoring track without uri")
        return []

    result: list[protocol.ResultTuple] = [
        ("file", track.uri),
        ("Time", track.length and (track.length // 1000) or 0),
        *multi_tag_list(track.artists, "name", "Artist"),
        ("Album", track.album and track.album.name or ""),
    ]

    if stream_title is not None:
        result.append(("Title", stream_title))
        if track.name:
            result.append(("Name", track.name))
    else:
        result.append(("Title", track.name or ""))

    if track.date:
        result.append(("Date", track.date))

    if track.album is not None and track.album.num_tracks is not None:
        result.append(("Track", f"{track.track_no or 0}/{track.album.num_tracks}"))
    else:
        result.append(("Track", track.track_no or 0))
    if position is not None and tlid is not None:
        result.append(("Pos", position))
        result.append(("Id", tlid))
    if track.album is not None and track.album.musicbrainz_id is not None:
        result.append(("MUSICBRAINZ_ALBUMID", track.album.musicbrainz_id))

    if track.album is not None and track.album.artists:
        result += multi_tag_list(track.album.artists, "name", "AlbumArtist")

        musicbrainz_ids = concat_multi_values(track.album.artists, "musicbrainz_id")
        if musicbrainz_ids:
            result.append(("MUSICBRAINZ_ALBUMARTISTID", musicbrainz_ids))

    if track.artists:
        musicbrainz_ids = concat_multi_values(track.artists, "musicbrainz_id")
        if musicbrainz_ids:
            result.append(("MUSICBRAINZ_ARTISTID", musicbrainz_ids))

    if track.composers:
        result += multi_tag_list(track.composers, "name", "Composer")

    if track.performers:
        result += multi_tag_list(track.performers, "name", "Performer")

    if track.genre:
        result.append(("Genre", track.genre))

    if track.disc_no:
        result.append(("Disc", track.disc_no))

    if track.last_modified:
        datestring = datetime.datetime.fromtimestamp(
            track.last_modified // 1000, tz=datetime.UTC
        ).isoformat(timespec="seconds")
        result.append(("Last-Modified", datestring.replace("+00:00", "Z")))

    if track.musicbrainz_id is not None:
        result.append(("MUSICBRAINZ_TRACKID", track.musicbrainz_id))

    if track.album and track.album.uri:
        result.append(("X-AlbumUri", track.album.uri))

    return [
        (tagtype, value)
        for (tagtype, value) in result
        if _has_value(tagtypes, tagtype, value)
    ]


def _has_value(
    tagtypes: set[str],
    tagtype: str,
    value: protocol.ResultValue,
) -> bool:
    """
    Determine whether to add the tagtype to the output or not. The tagtype must
    be in the list of tagtypes configured for the client.

    :param tagtypes: the MPD tagtypes enabled by the client
    :param tagtype: the MPD tagtype
    :param value: the tag value
    """
    if tagtype in tagtype_list.TAGTYPE_LIST:
        if tagtype not in tagtypes:
            return False
        return bool(value)
    return True


def concat_multi_values(
    models: Iterable[Artist | Album | Track],
    attribute: str,
) -> str:
    """
    Format Mopidy model values for output to MPD client.

    :param models: the models
    :param attribute: the attribute to use
    """
    # Don't sort the values. MPD doesn't appear to (or if it does it's not
    # strict alphabetical). If we just use them in the order in which they come
    # in then the musicbrainz ids have a higher chance of staying in sync
    return ";".join(
        getattr(m, attribute) for m in models if getattr(m, attribute, None) is not None
    )


def multi_tag_list(
    models: Iterable[Artist | Album | Track],
    attribute: str,
    tag: str,
) -> list[protocol.ResultTuple]:
    """
    Format multiple objects for output to MPD client in a list with one tag per
    value.

    :param models: the model objects
    :param attribute: the attribute to use
    :param tag: the name of the tag
    """

    return [
        (tag, getattr(obj, attribute))
        for obj in models
        if getattr(obj, attribute, None) is not None
    ]


def tracks_to_mpd_format(
    tracks: Sequence[Track | TlTrack],
    tagtypes: set[str],
    *,
    start: int = 0,
    end: int | None = None,
) -> protocol.ResultList:
    """
    Format list of tracks for output to MPD client.

    Optionally limit output to the slice ``[start:end]`` of the list.

    :param tracks: the tracks
    :param tagtypes: the MPD tagtypes enabled by the client
    :param start: position of first track to include in output
    :param end: position after last track to include in output, or ``None`` for
      end of list
    """
    if end is None:
        end = len(tracks)
    tracks = tracks[start:end]
    positions = range(start, end)
    assert len(tracks) == len(positions)
    result: protocol.ResultList = []
    for track, position in zip(tracks, positions, strict=True):
        formatted_track = track_to_mpd_format(track, tagtypes, position=position)
        if formatted_track:
            result.extend(formatted_track)
    return result


def playlist_to_mpd_format(
    playlist: Playlist,
    tagtypes: set[str],
    *,
    start: int = 0,
    end: int | None = None,
) -> protocol.ResultList:
    """
    Format playlist for output to MPD client.

    :param playlist: the playlist
    :param tagtypes: the MPD tagtypes enabled by the client
    :param start: position of first track to include in output
    :param end: position after last track to include in output
    """
    return tracks_to_mpd_format(list(playlist.tracks), tagtypes, start=start, end=end)
