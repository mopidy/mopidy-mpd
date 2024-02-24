from __future__ import annotations

import logging
import re
from collections.abc import Callable, Generator
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NewType,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

import pykka

from mopidy_mpd import exceptions, protocol, tokenize, types
from mopidy_mpd.uri_mapper import MpdUriMapper

if TYPE_CHECKING:
    from mopidy.core import CoreProxy
    from mopidy.ext import Config
    from mopidy.models import Ref, Track
    from mopidy.types import Uri

    from mopidy_mpd.session import MpdSession


logger = logging.getLogger(__name__)

protocol.load_protocol_modules()

T = TypeVar("T")
Request: TypeAlias = str
Response = NewType("Response", list[str])
Filter: TypeAlias = Callable[[Request, Response, list["Filter"]], Response]


class MpdDispatcher:
    """
    The MPD session feeds the MPD dispatcher with requests. The dispatcher
    finds the correct handler, processes the request, and sends the response
    back to the MPD session.
    """

    _noidle = re.compile(r"^noidle$")

    def __init__(
        self,
        config: Config,
        core: CoreProxy,
        session: MpdSession,
    ) -> None:
        self.config = config
        self.mpd_config = cast(types.MpdConfig, config.get("mpd", {}) if config else {})
        self.authenticated = False
        self.command_list_receiving = False
        self.command_list_ok = False
        self.command_list = []
        self.command_list_index = None
        self.context = MpdContext(
            core=core,
            dispatcher=self,
            session=session,
            config=config,
        )

    def handle_request(
        self,
        request: Request,
        current_command_list_index: int | None = None,
    ) -> Response:
        """Dispatch incoming requests to the correct handler."""
        self.command_list_index = current_command_list_index
        response: Response = Response([])
        filter_chain: list[Filter] = [
            self._catch_mpd_ack_errors_filter,
            self._authenticate_filter,
            self._command_list_filter,
            self._idle_filter,
            self._add_ok_filter,
            self._call_handler_filter,
        ]
        return self._call_next_filter(request, response, filter_chain)

    def handle_idle(self, subsystem: str) -> None:
        # TODO: validate against mopidy_mpd/protocol/status.SUBSYSTEMS
        self.context.events.add(subsystem)

        subsystems = self.context.subscriptions.intersection(self.context.events)
        if not subsystems:
            return

        response: list[str] = []
        for subsystem in subsystems:
            response.append(f"changed: {subsystem}")
        response.append("OK")
        self.context.subscriptions = set()
        self.context.events = set()
        self.context.session.send_lines(response)

    def _call_next_filter(
        self, request: str, response: Response, filter_chain: list[Filter]
    ) -> Response:
        if filter_chain:
            next_filter = filter_chain.pop(0)
            return next_filter(request, response, filter_chain)
        return response

    # --- Filter: catch MPD ACK errors

    def _catch_mpd_ack_errors_filter(
        self,
        request: Request,
        response: Response,
        filter_chain: list[Filter],
    ) -> Response:
        try:
            return self._call_next_filter(request, response, filter_chain)
        except exceptions.MpdAckError as mpd_ack_error:
            if self.command_list_index is not None:
                mpd_ack_error.index = self.command_list_index
            return Response([mpd_ack_error.get_mpd_ack()])

    # --- Filter: authenticate

    def _authenticate_filter(
        self,
        request: Request,
        response: Response,
        filter_chain: list[Filter],
    ) -> Response:
        if self.authenticated:
            return self._call_next_filter(request, response, filter_chain)

        if self.config["mpd"]["password"] is None:
            self.authenticated = True
            return self._call_next_filter(request, response, filter_chain)

        command_name = request.split(" ")[0]
        command = protocol.commands.handlers.get(command_name)

        if command and not command.auth_required:
            return self._call_next_filter(request, response, filter_chain)

        raise exceptions.MpdPermissionError(command=command_name)

    # --- Filter: command list

    def _command_list_filter(
        self,
        request: Request,
        response: Response,
        filter_chain: list[Filter],
    ) -> Response:
        if self._is_receiving_command_list(request):
            self.command_list.append(request)
            return Response([])

        response = self._call_next_filter(request, response, filter_chain)
        if (
            (
                self._is_receiving_command_list(request)
                or self._is_processing_command_list(request)
            )
            and response
            and response[-1] == "OK"
        ):
            response = Response(response[:-1])
        return response

    def _is_receiving_command_list(self, request: str) -> bool:
        return self.command_list_receiving and request != "command_list_end"

    def _is_processing_command_list(self, request: str) -> bool:
        return self.command_list_index is not None and request != "command_list_end"

    # --- Filter: idle

    def _idle_filter(
        self,
        request: Request,
        response: Response,
        filter_chain: list[Filter],
    ) -> Response:
        if self._is_currently_idle() and not self._noidle.match(request):
            logger.debug(
                "Client sent us %s, only %s is allowed while in " "the idle state",
                repr(request),
                repr("noidle"),
            )
            self.context.session.close()
            return Response([])

        if not self._is_currently_idle() and self._noidle.match(request):
            return Response([])  # noidle was called before idle

        response = self._call_next_filter(request, response, filter_chain)

        if self._is_currently_idle():
            return Response([])

        return response

    def _is_currently_idle(self) -> bool:
        return bool(self.context.subscriptions)

    # --- Filter: add OK

    def _add_ok_filter(
        self,
        request: Request,
        response: Response,
        filter_chain: list[Filter],
    ) -> Response:
        response = self._call_next_filter(request, response, filter_chain)
        if not self._has_error(response):
            response.append("OK")
        return response

    def _has_error(self, response: Response) -> bool:
        return bool(response) and response[-1].startswith("ACK")

    # --- Filter: call handler

    def _call_handler_filter(
        self,
        request: Request,
        response: Response,
        filter_chain: list[Filter],
    ) -> Response:
        try:
            result = self._call_handler(request)
            response = self._format_response(result)
            return self._call_next_filter(request, response, filter_chain)
        except pykka.ActorDeadError as exc:
            logger.warning("Tried to communicate with dead actor.")
            raise exceptions.MpdSystemError(str(exc)) from exc

    def _call_handler(self, request: str) -> protocol.Result:
        tokens = tokenize.split(request)
        # TODO: check that blacklist items are valid commands?
        blacklist = self.mpd_config.get("command_blacklist", [])
        if tokens and tokens[0] in blacklist:
            logger.warning("MPD client used blacklisted command: %s", tokens[0])
            raise exceptions.MpdDisabledError(command=tokens[0])
        try:
            return protocol.commands.call(
                context=self.context,
                tokens=tokens,
            )
        except exceptions.MpdAckError as exc:
            if exc.command is None:
                exc.command = tokens[0]
            raise

    def _format_response(self, result: protocol.Result) -> Response:
        response = Response([])
        for element in self._listify_result(result):
            response.extend(self._format_lines(element))
        return response

    def _listify_result(self, result: protocol.Result) -> protocol.ResultList:
        match result:
            case None:
                return []
            case list():
                return self._flatten(result)
            case _:
                return [result]

    def _flatten(self, lst: protocol.ResultList) -> protocol.ResultList:
        result: protocol.ResultList = []
        for element in lst:
            if isinstance(element, list):
                result.extend(self._flatten(element))
            else:
                result.append(element)
        return result

    def _format_lines(
        self, element: protocol.ResultDict | protocol.ResultTuple | str
    ) -> Response:
        if isinstance(element, dict):
            return Response([f"{key}: {value}" for (key, value) in element.items()])
        if isinstance(element, tuple):
            (key, value) = element
            return Response([f"{key}: {value}"])
        return Response([element])


class MpdContext:
    """
    This object is passed as the first argument to all MPD command handlers to
    give the command handlers access to important parts of Mopidy.
    """

    #: The Mopidy core API.
    core: CoreProxy

    #: The current dispatcher instance.
    dispatcher: MpdDispatcher

    #: The current session instance.
    session: MpdSession

    #: The MPD password.
    password: str | None = None

    #: The active subsystems that have pending events.
    events: set[str]

    #: The subsystems that we want to be notified about in idle mode.
    subscriptions: set[str]

    _uri_map: MpdUriMapper

    def __init__(
        self,
        config: Config,
        core: CoreProxy,
        dispatcher: MpdDispatcher,
        session: MpdSession,
    ) -> None:
        self.core = core
        self.dispatcher = dispatcher
        self.session = session
        if config is not None:
            mpd_config = cast(types.MpdConfig, config["mpd"])
            self.password = mpd_config["password"]
        self.events = set()
        self.subscriptions = set()
        self._uri_map = MpdUriMapper(core)

    def lookup_playlist_uri_from_name(self, name: str) -> Uri | None:
        """
        Helper function to retrieve a playlist from its unique MPD name.
        """
        return self._uri_map.playlist_uri_from_name(name)

    def lookup_playlist_name_from_uri(self, uri: Uri) -> str | None:
        """
        Helper function to retrieve the unique MPD playlist name from its uri.
        """
        return self._uri_map.playlist_name_from_uri(uri)

    @overload
    def browse(
        self, path: str | None, *, recursive: bool, lookup: Literal[True]
    ) -> Generator[tuple[str, pykka.Future[dict[Uri, list[Track]]] | None], Any, None]:
        ...

    @overload
    def browse(
        self, path: str | None, *, recursive: bool, lookup: Literal[False]
    ) -> Generator[tuple[str, Ref | None], Any, None]:
        ...

    def browse(  # noqa: C901, PLR0912
        self,
        path: str | None,
        *,
        recursive: bool = True,
        lookup: bool = True,
    ) -> Generator[Any, Any, None]:
        """
        Browse the contents of a given directory path.

        Returns a sequence of two-tuples ``(path, data)``.

        If ``recursive`` is true, it returns results for all entries in the
        given path.

        If ``lookup`` is true and the ``path`` is to a track, the returned
        ``data`` is a future which will contain the results from looking up
        the URI with :meth:`mopidy.core.LibraryController.lookup`. If
        ``lookup`` is false and the ``path`` is to a track, the returned
        ``data`` will be a :class:`mopidy.models.Ref` for the track.

        For all entries that are not tracks, the returned ``data`` will be
        :class:`None`.
        """

        path_parts: list[str] = re.findall(r"[^/]+", path or "")
        root_path: str = "/".join(["", *path_parts])

        uri = self._uri_map.uri_from_name(root_path)
        if uri is None:
            for part in path_parts:
                for ref in self.core.library.browse(uri).get():
                    if ref.type != ref.TRACK and ref.name == part:
                        uri = ref.uri
                        break
                else:
                    raise exceptions.MpdNoExistError("Not found")
            root_path = self._uri_map.insert(root_path, uri)

        if recursive:
            yield (root_path, None)

        path_and_futures = [(root_path, self.core.library.browse(uri))]
        while path_and_futures:
            base_path, future = path_and_futures.pop()
            for ref in future.get():
                if ref.name is None or ref.uri is None:
                    continue

                path = "/".join([base_path, ref.name.replace("/", "")])
                path = self._uri_map.insert(path, ref.uri)

                if ref.type == ref.TRACK:
                    if lookup:
                        # TODO: can we lookup all the refs at once now?
                        yield (path, self.core.library.lookup(uris=[ref.uri]))
                    else:
                        yield (path, ref)
                else:
                    yield (path, None)
                    if recursive:
                        path_and_futures.append(
                            (path, self.core.library.browse(ref.uri))
                        )
