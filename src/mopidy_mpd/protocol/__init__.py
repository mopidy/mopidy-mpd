"""
This is Mopidy's MPD protocol implementation.

This is partly based upon the `MPD protocol documentation
<http://www.musicpd.org/doc/protocol/>`_, which is a useful resource, but it is
rather incomplete with regards to data formats, both for requests and
responses. Thus, we have had to talk a great deal with the the original `MPD
server <https://mpd.fandom.com/>`_ using telnet to get the details we need to
implement our own MPD server which is compatible with the numerous existing
`MPD clients <https://mpd.fandom.com/wiki/Clients>`_.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from mopidy_mpd import exceptions

if TYPE_CHECKING:
    from mopidy_mpd.context import MpdContext

#: The MPD protocol uses UTF-8 for encoding all data.
ENCODING = "utf-8"

#: The MPD protocol uses ``\n`` as line terminator.
LINE_TERMINATOR = b"\n"

#: The MPD protocol version is 0.19.0.
VERSION = "0.19.0"


type ResultValue = str | int
type ResultDict = dict[str, ResultValue]
type ResultTuple = tuple[str, ResultValue]
type ResultList = list[ResultTuple | ResultDict]
type Result = None | ResultDict | ResultTuple | ResultList
type HandlerFunc = Callable[..., Result]


def load_protocol_modules() -> None:
    """
    The protocol modules must be imported to get them registered in
    :attr:`commands`.
    """
    from . import (  # noqa: F401, PLC0415
        audio_output,
        channels,
        command_list,
        connection,
        current_playlist,
        mount,
        music_db,
        playback,
        reflection,
        status,
        stickers,
        stored_playlists,
    )


def INT(value: str) -> int:  # noqa: N802
    r"""Converts a value that matches [+-]?\d+ into an integer."""
    if value is None:
        raise ValueError("None is not a valid integer")
    # TODO: check for whitespace via value != value.strip()?
    return int(value)


def UINT(value: str) -> int:  # noqa: N802
    r"""Converts a value that matches \d+ into an integer."""
    if value is None:
        raise ValueError("None is not a valid integer")
    if not value.isdigit():
        raise ValueError("Only positive numbers are allowed")
    return int(value)


def FLOAT(value: str) -> float:  # noqa: N802
    r"""Converts a value that matches [+-]\d+(.\d+)? into a float."""
    if value is None:
        raise ValueError("None is not a valid float")
    return float(value)


def UFLOAT(value: str) -> float:  # noqa: N802
    r"""Converts a value that matches \d+(.\d+)? into a float."""
    if value is None:
        raise ValueError("None is not a valid float")
    result = float(value)
    if result < 0:
        raise ValueError("Only positive numbers are allowed")
    return result


def BOOL(value: str) -> bool:  # noqa: N802
    """Convert the values 0 and 1 into booleans."""
    if value in ("1", "0"):
        return bool(int(value))
    raise ValueError(f"{value!r} is not 0 or 1")


def RANGE(value: str) -> slice:  # noqa: N802
    """Convert a single integer or range spec into a slice

    ``n`` should become ``slice(n, n+1)``
    ``n:`` should become ``slice(n, None)``
    ``n:m`` should become ``slice(n, m)`` and ``m > n`` must hold
    """
    if ":" in value:
        start, stop = value.split(":", 1)
        start = UINT(start)
        if stop.strip():
            stop = UINT(stop)
            if start >= stop:
                raise ValueError("End must be larger than start")
        else:
            stop = None
    else:
        start = UINT(value)
        stop = start + 1
    return slice(start, stop)


class Commands:
    """Collection of MPD commands to expose to users.

    Normally used through the global instance which command handlers have been
    installed into.
    """

    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}

    # TODO: consider removing auth_required and list_command in favour of
    # additional command instances to register in?
    def add(
        self,
        name: str,
        *,
        auth_required: bool = True,
        list_command: bool = True,
        **validators: Callable[[str], Any],
    ) -> Callable[[HandlerFunc], HandlerFunc]:
        """Create a decorator that registers a handler and validation rules.

        Additional keyword arguments are treated as converters/validators to
        apply to tokens converting them to proper Python types.

        Requirements for valid handlers:

        - must accept a context argument as the first arg.
        - may not use variable keyword arguments, ``**kwargs``.
        - may use variable arguments ``*args`` *or* a mix of required and
          optional arguments.

        Decorator returns the unwrapped function so that tests etc can use the
        functions with values with correct python types instead of strings.

        :param name: Name of the command being registered.
        :param auth_required: If authorization is required.
        :param list_command: If command should be listed in reflection.
        """

        def wrapper(func: HandlerFunc) -> HandlerFunc:
            if name in self.handlers:
                raise ValueError(f"{name} already registered")
            self.handlers[name] = Handler(
                name=name,
                func=func,
                auth_required=auth_required,
                list_command=list_command,
                validators=validators,
            )
            return func

        return wrapper

    def call(
        self,
        *,
        context: MpdContext,
        tokens: list[str],
    ) -> Result:
        """Find and run the handler registered for the given command.

        If the handler was registered with any converters/validators they will
        be run before calling the real handler.

        :param context: MPD context
        :param tokens: List of tokens to process
        """
        if not tokens:
            raise exceptions.MpdNoCommandError
        command, tokens = tokens[0], tokens[1:]
        if command not in self.handlers:
            raise exceptions.MpdUnknownCommandError(command=command)
        return self.handlers[command](context, *tokens)


#: Global instance to install commands into
commands = Commands()


class Handler:
    def __init__(
        self,
        *,
        name: str,
        func: HandlerFunc,
        auth_required: bool,
        list_command: bool,
        validators: dict[str, Callable[[str], Any]],
    ) -> None:
        self.name = name
        self.func = func
        self.auth_required = auth_required
        self.list_command = list_command
        self.validators = validators

        self.spec = inspect.getfullargspec(func)

        if not self.spec.args and not self.spec.varargs:
            raise TypeError("Handler must accept at least one argument.")

        if len(self.spec.args) > 1 and self.spec.varargs:
            raise TypeError("*args may not be combined with regular arguments")

        if not set(self.validators.keys()).issubset(self.spec.args):
            raise TypeError("Validator for non-existent arg passed")

        if self.spec.varkw or self.spec.kwonlyargs:
            raise TypeError("Keyword arguments are not permitted")

        self.defaults = dict(
            zip(
                self.spec.args[-len(self.spec.defaults or []) :],
                self.spec.defaults or [],
                strict=False,
            )
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Result:
        if self.spec.varargs:
            return self.func(*args, **kwargs)

        try:
            ba = inspect.signature(self.func).bind(*args, **kwargs)
            ba.apply_defaults()
            callargs = ba.arguments
        except TypeError as exc:
            raise exceptions.MpdArgError(
                f'wrong number of arguments for "{self.name}"'
            ) from exc

        for key, value in callargs.items():
            if value == self.defaults.get(key, object()):
                continue
            if validator := self.validators.get(key):
                try:
                    callargs[key] = validator(value)
                except ValueError as exc:
                    raise exceptions.MpdArgError("incorrect arguments") from exc

        return self.func(**callargs)
