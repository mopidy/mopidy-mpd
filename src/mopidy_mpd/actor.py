import asyncio
import logging
import threading
from typing import Any

import pykka
from mopidy import exceptions, listener, zeroconf
from mopidy.core import CoreListener, CoreProxy

from mopidy_mpd import network, session, types, uri_mapper

logger = logging.getLogger(__name__)

_CORE_EVENTS_TO_IDLE_SUBSYSTEMS = {
    "track_playback_paused": None,
    "track_playback_resumed": None,
    "track_playback_started": None,
    "track_playback_ended": None,
    "playback_state_changed": "player",
    "tracklist_changed": "playlist",
    "playlists_loaded": "stored_playlist",
    "playlist_changed": "stored_playlist",
    "playlist_deleted": "stored_playlist",
    "options_changed": "options",
    "volume_changed": "mixer",
    "mute_changed": "output",
    "seeked": "player",
    "stream_title_changed": "playlist",
}


class MpdFrontend(pykka.ThreadingActor, CoreListener):
    def __init__(self, config: types.Config, core: CoreProxy) -> None:
        super().__init__()

        self.hostname = network.format_hostname(config["mpd"]["hostname"])
        self.port = config["mpd"]["port"]
        self.zeroconf_name = config["mpd"]["zeroconf"]
        self.zeroconf_service = None

        self.uri_map = uri_mapper.MpdUriMapper(core)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.server = self._setup_server(config, core)
        self.server_thread = threading.Thread(target=self._run_server)

    def _setup_server(self, config: types.Config, core: CoreProxy) -> network.Server:
        try:
            server = network.Server(
                config=config,
                core=core,
                uri_map=self.uri_map,
                protocol=session.MpdSession,
                host=self.hostname,
                port=self.port,
                max_connections=config["mpd"]["max_connections"],
                timeout=config["mpd"]["connection_timeout"],
            )
        except OSError as exc:
            raise exceptions.FrontendError(f"MPD server startup failed: {exc}") from exc

        logger.info("MPD server running at %s", network.format_address(server.address))

        return server

    def _run_server(self) -> None:
        self.loop.run_until_complete(self.server.run())

    def on_start(self) -> None:
        self.server_thread.start()

        if self.zeroconf_name and not network.is_unix_socket(self.server.server_socket):
            self.zeroconf_service = zeroconf.Zeroconf(
                name=self.zeroconf_name, stype="_mpd._tcp", port=self.port
            )
            self.zeroconf_service.publish()

    def on_stop(self) -> None:
        if self.zeroconf_service:
            self.zeroconf_service.unpublish()

        session_actors = pykka.ActorRegistry.get_by_class(session.MpdSession)
        for session_actor in session_actors:
            session_actor.stop()

        if not self.server_thread.is_alive():
            logger.warning("MPD server already stopped")
            return

        self.loop.call_soon_threadsafe(self.server.stop)
        logger.debug("Waiting for MPD server thread to terminate")
        self.server_thread.join()

    def on_event(self, event: str, **kwargs: Any) -> None:
        if event not in _CORE_EVENTS_TO_IDLE_SUBSYSTEMS:
            logger.warning("Got unexpected event: %s(%s)", event, ", ".join(kwargs))
        else:
            self.send_idle(_CORE_EVENTS_TO_IDLE_SUBSYSTEMS[event])

    def send_idle(self, subsystem: str | None) -> None:
        if subsystem:
            listener.send(session.MpdSession, subsystem)
