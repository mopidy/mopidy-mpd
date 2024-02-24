from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    NewType,
    TypeAlias,
    TypeVar,
    cast,
)

import pykka

from mopidy_mpd import context, exceptions, protocol, tokenize, types

if TYPE_CHECKING:
    from mopidy.core import CoreProxy
    from mopidy.ext import Config

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
        self.context = context.MpdContext(
            config=config,
            core=core,
            session=session,
            dispatcher=self,
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
