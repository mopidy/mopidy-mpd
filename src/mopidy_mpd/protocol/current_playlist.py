from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from mopidy_mpd import exceptions, protocol, translator

if TYPE_CHECKING:
    from mopidy.types import Uri

    from mopidy_mpd.context import MpdContext


@protocol.commands.add("add")
def add(context: MpdContext, uri: Uri) -> None:
    """
    *musicpd.org, current playlist section:*

        ``add {URI}``

        Adds the file ``URI`` to the playlist (directories add recursively).
        ``URI`` can also be a single file.

    *Clarifications:*

    - ``add ""`` should add all tracks in the library to the current playlist.
    """
    if not uri.strip("/"):
        return

    # If we have an URI just try and add it directly without bothering with
    # jumping through browse...
    if urlparse(uri).scheme != "" and context.core.tracklist.add(uris=[uri]).get():
        return

    try:
        uris = []
        for _path, ref in context.browse(uri, recursive=True, lookup=False):
            if ref:
                uris.append(ref.uri)
    except exceptions.MpdNoExistError as exc:
        exc.message = "directory or file not found"
        raise

    if not uris:
        raise exceptions.MpdNoExistError("directory or file not found")
    context.core.tracklist.add(uris=uris).get()


@protocol.commands.add("addid", songpos=protocol.UINT)
def addid(context: MpdContext, uri: Uri, songpos: int | None = None) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``addid {URI} [POSITION]``

        Adds a song to the playlist (non-recursive) and returns the song id.

        ``URI`` is always a single file or URL. For example::

            addid "foo.mp3"
            Id: 999
            OK

    *Clarifications:*

    - ``addid ""`` should return an error.
    """
    if not uri:
        raise exceptions.MpdNoExistError("No such song")

    length = context.core.tracklist.get_length()
    if songpos is not None and songpos > length.get():
        raise exceptions.MpdArgError("Bad song index")

    tl_tracks = context.core.tracklist.add(uris=[uri], at_position=songpos).get()

    if not tl_tracks:
        raise exceptions.MpdNoExistError("No such song")
    return ("Id", tl_tracks[0].tlid)


@protocol.commands.add("delete", songrange=protocol.RANGE)
def delete(context: MpdContext, songrange: slice) -> None:
    """
    *musicpd.org, current playlist section:*

        ``delete [{POS} | {START:END}]``

        Deletes a song from the playlist.
    """
    start = songrange.start
    end = songrange.stop
    if end is None:
        end = context.core.tracklist.get_length().get()
    tl_tracks = context.core.tracklist.slice(start, end).get()
    if not tl_tracks:
        raise exceptions.MpdArgError("Bad song index", command="delete")
    context.core.tracklist.remove({"tlid": [tl_track.tlid for tl_track in tl_tracks]})


@protocol.commands.add("deleteid", tlid=protocol.UINT)
def deleteid(context: MpdContext, tlid: int) -> None:
    """
    *musicpd.org, current playlist section:*

        ``deleteid {SONGID}``

        Deletes the song ``SONGID`` from the playlist
    """
    tl_tracks = context.core.tracklist.remove({"tlid": [tlid]}).get()
    if not tl_tracks:
        raise exceptions.MpdNoExistError("No such song")


@protocol.commands.add("clear")
def clear(context: MpdContext) -> None:
    """
    *musicpd.org, current playlist section:*

        ``clear``

        Clears the current playlist.
    """
    context.core.tracklist.clear()


@protocol.commands.add("move", songrange=protocol.RANGE, to=protocol.UINT)
def move_range(context: MpdContext, songrange: slice, to: int) -> None:
    """
    *musicpd.org, current playlist section:*

        ``move [{FROM} | {START:END}] {TO}``

        Moves the song at ``FROM`` or range of songs at ``START:END`` to
        ``TO`` in the playlist.
    """
    start = songrange.start
    end = songrange.stop
    if end is None:
        end = context.core.tracklist.get_length().get()
    context.core.tracklist.move(start, end, to)


@protocol.commands.add("moveid", tlid=protocol.UINT, to=protocol.UINT)
def moveid(context: MpdContext, tlid: int, to: int) -> None:
    """
    *musicpd.org, current playlist section:*

        ``moveid {FROM} {TO}``

        Moves the song with ``FROM`` (songid) to ``TO`` (playlist index) in
        the playlist. If ``TO`` is negative, it is relative to the current
        song in the playlist (if there is one).
    """
    position = context.core.tracklist.index(tlid=tlid).get()
    if position is None:
        raise exceptions.MpdNoExistError("No such song")
    context.core.tracklist.move(position, position + 1, to)


@protocol.commands.add("playlist")
def playlist(context: MpdContext) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``playlist``

        Displays the current playlist.

        .. note::

            Do not use this, instead use ``playlistinfo``.
    """
    return playlistinfo(context)


@protocol.commands.add("playlistfind")
def playlistfind(context: MpdContext, tag: str, needle: str) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``playlistfind {TAG} {NEEDLE}``

        Finds songs in the current playlist with strict matching.
    """
    if tag == "filename":
        tl_tracks = context.core.tracklist.filter({"uri": [needle]}).get()
        if not tl_tracks:
            return None
        position = context.core.tracklist.index(tl_tracks[0]).get()
        return translator.track_to_mpd_format(
            tl_tracks[0], context.session.tagtypes, position=position
        )
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("playlistid", tlid=protocol.UINT)
def playlistid(context: MpdContext, tlid: int | None = None) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``playlistid {SONGID}``

        Displays a list of songs in the playlist. ``SONGID`` is optional
        and specifies a single song to display info for.
    """
    if tlid is not None:
        tl_tracks = context.core.tracklist.filter({"tlid": [tlid]}).get()
        if not tl_tracks:
            raise exceptions.MpdNoExistError("No such song")
        position = context.core.tracklist.index(tl_tracks[0]).get()
        return translator.track_to_mpd_format(
            tl_tracks[0], context.session.tagtypes, position=position
        )

    return translator.tracks_to_mpd_format(
        context.core.tracklist.get_tl_tracks().get(),
        context.session.tagtypes,
    )


@protocol.commands.add("playlistinfo")
def playlistinfo(context: MpdContext, parameter: str | None = None) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``playlistinfo [[SONGPOS] | [START:END]]``

        Displays a list of all songs in the playlist, or if the optional
        argument is given, displays information only for the song
        ``SONGPOS`` or the range of songs ``START:END``.

    *ncmpc and mpc:*

    - uses negative indexes, like ``playlistinfo "-1"``, to request
      the entire playlist
    """
    if parameter is None or parameter == "-1":
        start, end = 0, None
    else:
        tracklist_slice = protocol.RANGE(parameter)
        start, end = tracklist_slice.start, tracklist_slice.stop

    tl_tracks = context.core.tracklist.get_tl_tracks().get()
    if start and start > len(tl_tracks):
        raise exceptions.MpdArgError("Bad song index")
    if end and end > len(tl_tracks):
        end = None
    return translator.tracks_to_mpd_format(
        tl_tracks, context.session.tagtypes, start=start, end=end
    )


@protocol.commands.add("playlistsearch")
def playlistsearch(context: MpdContext, tag: str, needle: str) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``playlistsearch {TAG} {NEEDLE}``

        Searches case-sensitively for partial matches in the current
        playlist.

    *GMPC:*

    - uses ``filename`` and ``any`` as tags
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("plchanges", version=protocol.INT)
def plchanges(context: MpdContext, version: int) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``plchanges {VERSION}``

        Displays changed songs currently in the playlist since ``VERSION``.

        To detect songs that were deleted at the end of the playlist, use
        ``playlistlength`` returned by status command.

    *MPDroid:*

    - Calls ``plchanges "-1"`` two times per second to get the entire playlist.
    """
    # TODO: Naive implementation that returns all tracks as changed
    tracklist_version = context.core.tracklist.get_version().get()

    if version < tracklist_version:
        return translator.tracks_to_mpd_format(
            context.core.tracklist.get_tl_tracks().get(),
            context.session.tagtypes,
        )

    if version == tracklist_version:
        # A version match could indicate this is just a metadata update, so
        # check for a stream ref and let the client know about the change.
        stream_title = context.core.playback.get_stream_title().get()
        if stream_title is None:
            return None

        tl_track = context.core.playback.get_current_tl_track().get()
        position = context.core.tracklist.index(tl_track).get()
        if tl_track is not None and position is not None:
            return translator.track_to_mpd_format(
                tl_track,
                context.session.tagtypes,
                position=position,
                stream_title=stream_title,
            )

    return None


@protocol.commands.add("plchangesposid", version=protocol.INT)
def plchangesposid(context: MpdContext, version: int) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``plchangesposid {VERSION}``

        Displays changed songs currently in the playlist since ``VERSION``.
        This function only returns the position and the id of the changed
        song, not the complete metadata. This is more bandwidth efficient.

        To detect songs that were deleted at the end of the playlist, use
        ``playlistlength`` returned by status command.
    """
    # TODO: Naive implementation that returns all tracks as changed
    if int(version) != context.core.tracklist.get_version().get():
        result = []
        for position, (tlid, _) in enumerate(
            context.core.tracklist.get_tl_tracks().get()
        ):
            result.append(("cpos", position))
            result.append(("Id", tlid))
        return result
    return None


@protocol.commands.add("prio", priority=protocol.UINT, position=protocol.RANGE)
def prio(context: MpdContext, priority: int, position: slice) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``prio {PRIORITY} {START:END...}``

        Set the priority of the specified songs. A higher priority means that
        it will be played first when "random" mode is enabled.

        A priority is an integer between 0 and 255. The default priority of new
        songs is 0.
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("prioid")
def prioid(context: MpdContext, *args: str) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``prioid {PRIORITY} {ID...}``

        Same as prio, but address the songs with their id.
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("rangeid", tlid=protocol.UINT, songrange=protocol.RANGE)
def rangeid(context: MpdContext, tlid: int, songrange: slice) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``rangeid {ID} {START:END}``

        Specifies the portion of the song that shall be played. START and END
        are offsets in seconds (fractional seconds allowed); both are optional.
        Omitting both (i.e. sending just ":") means "remove the range, play
        everything". A song that is currently playing cannot be manipulated
        this way.

    .. versionadded:: 0.19
        New in MPD protocol version 0.19
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("shuffle", songrange=protocol.RANGE)
def shuffle(context: MpdContext, songrange: slice | None = None) -> None:
    """
    *musicpd.org, current playlist section:*

        ``shuffle [START:END]``

        Shuffles the current playlist. ``START:END`` is optional and
        specifies a range of songs.
    """
    if songrange is None:
        start, end = None, None
    else:
        start, end = songrange.start, songrange.stop
    context.core.tracklist.shuffle(start, end)


@protocol.commands.add("swap", songpos1=protocol.UINT, songpos2=protocol.UINT)
def swap(context: MpdContext, songpos1: int, songpos2: int) -> None:
    """
    *musicpd.org, current playlist section:*

        ``swap {SONG1} {SONG2}``

        Swaps the positions of ``SONG1`` and ``SONG2``.
    """
    if songpos2 < songpos1:
        songpos1, songpos2 = songpos2, songpos1
    context.core.tracklist.move(songpos1, songpos1 + 1, songpos2)
    context.core.tracklist.move(songpos2 - 1, songpos2, songpos1)


@protocol.commands.add("swapid", tlid1=protocol.UINT, tlid2=protocol.UINT)
def swapid(context: MpdContext, tlid1: int, tlid2: int) -> None:
    """
    *musicpd.org, current playlist section:*

        ``swapid {SONG1} {SONG2}``

        Swaps the positions of ``SONG1`` and ``SONG2`` (both song ids).
    """
    position1 = context.core.tracklist.index(tlid=tlid1).get()
    position2 = context.core.tracklist.index(tlid=tlid2).get()
    if position1 is None or position2 is None:
        raise exceptions.MpdNoExistError("No such song")
    swap(context, position1, position2)


@protocol.commands.add("addtagid", tlid=protocol.UINT)
def addtagid(context: MpdContext, tlid: int, tag: str, value: str) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``addtagid {SONGID} {TAG} {VALUE}``

        Adds a tag to the specified song. Editing song tags is only possible
        for remote songs. This change is volatile: it may be overwritten by
        tags received from the server, and the data is gone when the song gets
        removed from the queue.

    .. versionadded:: 0.19
        New in MPD protocol version 0.19
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("cleartagid", tlid=protocol.UINT)
def cleartagid(context: MpdContext, tlid: int, tag: str) -> protocol.Result:
    """
    *musicpd.org, current playlist section:*

        ``cleartagid {SONGID} [TAG]``

        Removes tags from the specified song. If TAG is not specified, then all
        tag values will be removed. Editing song tags is only possible for
        remote songs.

    .. versionadded:: 0.19
        New in MPD protocol version 0.19
    """
    raise exceptions.MpdNotImplementedError  # TODO
