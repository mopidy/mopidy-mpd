import logging

from mopidy_mpd import dispatcher, formatting, network, protocol
from mopidy_mpd.protocol import tagtype_list

logger = logging.getLogger(__name__)


class MpdSession(network.LineProtocol):

    """
    The MPD client session. Keeps track of a single client session. Any
    requests from the client is passed on to the MPD request dispatcher.
    """

    terminator = protocol.LINE_TERMINATOR
    encoding = protocol.ENCODING
    delimiter = rb"\r?\n"

    def __init__(self, connection, config=None, core=None, uri_map=None):
        super().__init__(connection)
        self.dispatcher = dispatcher.MpdDispatcher(
            session=self, config=config, core=core, uri_map=uri_map
        )
        self.tagtypes = tagtype_list.TAGTYPE_LIST.copy()

    def on_start(self):
        logger.info("New MPD connection from %s", self.connection)
        self.send_lines([f"OK MPD {protocol.VERSION}"])

    def on_line_received(self, line):
        logger.debug("Request from %s: %s", self.connection, line)

        # All mpd commands start with a lowercase alphabetic character
        # To prevent CSRF attacks, requests starting with an invalid
        # character are immediately dropped.
        if len(line) == 0 or not (line[0].islower() and line[0].isalpha()):
            self.connection.stop("Malformed command")
            return

        response = self.dispatcher.handle_request(line)
        if not response:
            return

        logger.debug(
            "Response to %s: %s",
            self.connection,
            formatting.indent(self.decode(self.terminator).join(response)),
        )

        self.send_lines(response)

    def on_event(self, subsystem):
        self.dispatcher.handle_idle(subsystem)

    def decode(self, line):
        try:
            return super().decode(line)
        except ValueError:
            logger.warning(
                "Stopping actor due to unescaping error, data "
                "supplied by client was not valid."
            )
            self.stop()

    def close(self):
        self.stop()
