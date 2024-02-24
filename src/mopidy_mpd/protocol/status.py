from __future__ import annotations

from typing import TYPE_CHECKING, Never

from mopidy.core import PlaybackState

from mopidy_mpd import exceptions, protocol, translator

if TYPE_CHECKING:
    from mopidy.models import Track
    from mopidy.types import DurationMs

    from mopidy_mpd.context import MpdContext


#: Subsystems that can be registered with idle command.
SUBSYSTEMS = [
    "database",
    "mixer",
    "options",
    "output",
    "player",
    "playlist",
    "stored_playlist",
    "update",
]


@protocol.commands.add("clearerror")
def clearerror(context: MpdContext) -> Never:
    """
    *musicpd.org, status section:*

        ``clearerror``

        Clears the current error message in status (this is also
        accomplished by any command that starts playback).
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("currentsong")
def currentsong(context: MpdContext) -> protocol.Result:
    """
    *musicpd.org, status section:*

        ``currentsong``

        Displays the song info of the current song (same song that is
        identified in status).
    """
    tl_track = context.core.playback.get_current_tl_track().get()
    stream_title = context.core.playback.get_stream_title().get()
    if tl_track is not None:
        position = context.core.tracklist.index(tl_track).get()
        return translator.track_to_mpd_format(
            tl_track,
            position=position,
            stream_title=stream_title,
            tagtypes=context.session.tagtypes,
        )
    return None


@protocol.commands.add("idle")
def idle(context: MpdContext, *args: str) -> protocol.Result:
    """
    *musicpd.org, status section:*

        ``idle [SUBSYSTEMS...]``

        Waits until there is a noteworthy change in one or more of MPD's
        subsystems. As soon as there is one, it lists all changed systems
        in a line in the format ``changed: SUBSYSTEM``, where ``SUBSYSTEM``
        is one of the following:

        - ``database``: the song database has been modified after update.
        - ``update``: a database update has started or finished. If the
          database was modified during the update, the database event is
          also emitted.
        - ``stored_playlist``: a stored playlist has been modified,
          renamed, created or deleted
        - ``playlist``: the current playlist has been modified
        - ``player``: the player has been started, stopped or seeked
        - ``mixer``: the volume has been changed
        - ``output``: an audio output has been enabled or disabled
        - ``options``: options like repeat, random, crossfade, replay gain

        While a client is waiting for idle results, the server disables
        timeouts, allowing a client to wait for events as long as MPD runs.
        The idle command can be canceled by sending the command ``noidle``
        (no other commands are allowed). MPD will then leave idle mode and
        print results immediately; might be empty at this time.

        If the optional ``SUBSYSTEMS`` argument is used, MPD will only send
        notifications when something changed in one of the specified
        subsystems.
    """
    # TODO: test against valid subsystems

    subsystems = list(args) if args else SUBSYSTEMS

    for subsystem in subsystems:
        context.subscriptions.add(subsystem)

    active = context.subscriptions.intersection(context.events)
    if not active:
        context.session.prevent_timeout = True
        return None

    response = []
    context.events = set()
    context.subscriptions = set()

    for subsystem in active:
        response.append(f"changed: {subsystem}")
    return response


@protocol.commands.add("noidle", list_command=False)
def noidle(context: MpdContext) -> None:
    """See :meth:`_status_idle`."""
    if not context.subscriptions:
        return
    context.subscriptions = set()
    context.events = set()
    context.session.prevent_timeout = False


@protocol.commands.add("stats")
def stats(context: MpdContext) -> protocol.Result:
    """
    *musicpd.org, status section:*

        ``stats``

        Displays statistics.

        - ``artists``: number of artists
        - ``songs``: number of albums
        - ``uptime``: daemon uptime in seconds
        - ``db_playtime``: sum of all song times in the db
        - ``db_update``: last db update in UNIX time
        - ``playtime``: time length of music played
    """
    return {
        "artists": 0,  # TODO
        "albums": 0,  # TODO
        "songs": 0,  # TODO
        "uptime": 0,  # TODO
        "db_playtime": 0,  # TODO
        "db_update": 0,  # TODO
        "playtime": 0,  # TODO
    }


@protocol.commands.add("status")
def status(context: MpdContext) -> protocol.Result:
    """
    *musicpd.org, status section:*

        ``status``

        Reports the current status of the player and the volume level.

        - ``volume``: 0-100 or -1
        - ``repeat``: 0 or 1
        - ``single``: 0 or 1
        - ``consume``: 0 or 1
        - ``playlist``: 31-bit unsigned integer, the playlist version
          number
        - ``playlistlength``: integer, the length of the playlist
        - ``state``: play, stop, or pause
        - ``song``: playlist song number of the current song stopped on or
          playing
        - ``songid``: playlist songid of the current song stopped on or
          playing
        - ``nextsong``: playlist song number of the next song to be played
        - ``nextsongid``: playlist songid of the next song to be played
        - ``time``: total time elapsed (of current playing/paused song)
        - ``elapsed``: Total time elapsed within the current song, but with
          higher resolution.
        - ``bitrate``: instantaneous bitrate in kbps
        - ``xfade``: crossfade in seconds
        - ``audio``: sampleRate``:bits``:channels
        - ``updatings_db``: job id
        - ``error``: if there is an error, returns message here

    *Clarifications based on experience implementing*
        - ``volume``: can also be -1 if no output is set.
        - ``elapsed``: Higher resolution means time in seconds with three
          decimal places for millisecond precision.
    """
    # Fire these off first, as other futures depends on them
    f_current_tl_track = context.core.playback.get_current_tl_track()
    f_next_tlid = context.core.tracklist.get_next_tlid()

    # ...and wait for them to complete
    current_tl_track = f_current_tl_track.get()
    current_tlid = current_tl_track.tlid if current_tl_track else None
    current_track = current_tl_track.track if current_tl_track else None
    next_tlid = f_next_tlid.get()

    # Then fire off the rest...
    f_current_index = context.core.tracklist.index(tlid=current_tlid)
    f_mixer_volume = context.core.mixer.get_volume()
    f_next_index = context.core.tracklist.index(tlid=next_tlid)
    f_playback_state = context.core.playback.get_state()
    f_playback_time_position = context.core.playback.get_time_position()
    f_tracklist_consume = context.core.tracklist.get_consume()
    f_tracklist_length = context.core.tracklist.get_length()
    f_tracklist_random = context.core.tracklist.get_random()
    f_tracklist_repeat = context.core.tracklist.get_repeat()
    f_tracklist_single = context.core.tracklist.get_single()
    f_tracklist_version = context.core.tracklist.get_version()

    # ...and wait for them to complete
    current_index = f_current_index.get()
    mixer_volume = f_mixer_volume.get()
    next_index = f_next_index.get()
    playback_state = f_playback_state.get()
    playback_time_position = f_playback_time_position.get()
    tracklist_consume = f_tracklist_consume.get()
    tracklist_length = f_tracklist_length.get()
    tracklist_random = f_tracklist_random.get()
    tracklist_repeat = f_tracklist_repeat.get()
    tracklist_single = f_tracklist_single.get()
    tracklist_version = f_tracklist_version.get()

    result = [
        ("volume", mixer_volume if mixer_volume is not None else -1),
        ("repeat", int(tracklist_repeat)),
        ("random", int(tracklist_random)),
        ("single", int(tracklist_single)),
        ("consume", int(tracklist_consume)),
        ("playlist", tracklist_version),
        ("playlistlength", tracklist_length),
        ("xfade", 0),  # Not supported
        ("state", _status_state(playback_state)),
    ]
    if current_tlid is not None and current_index is not None:
        result.append(("song", current_index))
        result.append(("songid", current_tlid))
    if next_tlid is not None and next_index is not None:
        result.append(("nextsong", next_index))
        result.append(("nextsongid", next_tlid))
    if (
        playback_state in (PlaybackState.PLAYING, PlaybackState.PAUSED)
        and current_track is not None
    ):
        result.append(("time", _status_time(playback_time_position, current_track)))
        result.append(("elapsed", _status_time_elapsed(playback_time_position)))
        result.append(("bitrate", current_track.bitrate or 0))
    return result


def _status_state(playback_state: PlaybackState) -> str:
    match playback_state:
        case PlaybackState.PLAYING:
            return "play"
        case PlaybackState.STOPPED:
            return "stop"
        case PlaybackState.PAUSED:
            return "pause"


def _status_time(playback_time_position: DurationMs, current_track: Track) -> str:
    position = playback_time_position // 1000
    total = (current_track.length or 0) // 1000
    return f"{position:d}:{total:d}"


def _status_time_elapsed(playback_time_position: DurationMs) -> str:
    elapsed = playback_time_position / 1000.0
    return f"{elapsed:.3f}"
