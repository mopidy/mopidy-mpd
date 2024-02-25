from __future__ import annotations

from typing import TYPE_CHECKING, Never

from mopidy_mpd import exceptions, protocol
from mopidy_mpd.protocol import tagtype_list

if TYPE_CHECKING:
    from mopidy_mpd.context import MpdContext


@protocol.commands.add("close", auth_required=False)
def close(context: MpdContext) -> None:
    """
    *musicpd.org, connection section:*

        ``close``

        Closes the connection to MPD.
    """
    context.session.close()


@protocol.commands.add("kill", list_command=False)
def kill(context: MpdContext) -> Never:
    """
    *musicpd.org, connection section:*

        ``kill``

        Kills MPD.
    """
    raise exceptions.MpdPermissionError(command="kill")


@protocol.commands.add("password", auth_required=False)
def password(context: MpdContext, password: str) -> None:
    """
    *musicpd.org, connection section:*

        ``password {PASSWORD}``

        This is used for authentication with the server. ``PASSWORD`` is
        simply the plaintext password.
    """
    if password == context.config["mpd"]["password"]:
        context.dispatcher.authenticated = True
    else:
        raise exceptions.MpdPasswordError("incorrect password")


@protocol.commands.add("ping", auth_required=False)
def ping(context: MpdContext) -> None:
    """
    *musicpd.org, connection section:*

        ``ping``

        Does nothing but return ``OK``.
    """


@protocol.commands.add("tagtypes")
def tagtypes(context: MpdContext, *args: str) -> protocol.Result:
    """
    *mpd.readthedocs.io, connection settings section:*

        ``tagtypes``

        Shows a list of available song metadata.

        ``tagtypes disable {NAME...}``

        Remove one or more tags from the list of tag types the client is interested in.

        ``tagtypes enable {NAME...}``

        Re-enable one or more tags from the list of tag types for this client.

        ``tagtypes clear``

        Clear the list of tag types this client is interested in.

        ``tagtypes all``

        Announce that this client is interested in all tag types.
    """
    parameters = list(args)
    if parameters:
        subcommand = parameters.pop(0).lower()
        match subcommand:
            case "all":
                context.session.tagtypes.update(tagtype_list.TAGTYPE_LIST)
            case "clear":
                context.session.tagtypes.clear()
            case "disable":
                _validate_tagtypes(parameters)
                context.session.tagtypes.difference_update(parameters)
            case "enable":
                _validate_tagtypes(parameters)
                context.session.tagtypes.update(parameters)
            case _:
                raise exceptions.MpdArgError("Unknown sub command")
        return None
    return [("tagtype", tagtype) for tagtype in context.session.tagtypes]


def _validate_tagtypes(parameters: list[str]) -> None:
    param_set = set(parameters)
    if not param_set:
        raise exceptions.MpdArgError("Not enough arguments")
    if not param_set.issubset(tagtype_list.TAGTYPE_LIST):
        raise exceptions.MpdArgError("Unknown tag type")
