from __future__ import annotations

from typing import TYPE_CHECKING, Never

from mopidy_mpd import exceptions, protocol

if TYPE_CHECKING:
    from mopidy_mpd.context import MpdContext


@protocol.commands.add("subscribe")
def subscribe(context: MpdContext, channel: str) -> Never:
    """
    *musicpd.org, client to client section:*

        ``subscribe {NAME}``

        Subscribe to a channel. The channel is created if it does not exist
        already. The name may consist of alphanumeric ASCII characters plus
        underscore, dash, dot and colon.
    """
    # TODO: match channel against [A-Za-z0-9:._-]+
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("unsubscribe")
def unsubscribe(context: MpdContext, channel: str) -> Never:
    """
    *musicpd.org, client to client section:*

        ``unsubscribe {NAME}``

        Unsubscribe from a channel.
    """
    # TODO: match channel against [A-Za-z0-9:._-]+
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("channels")
def channels(context: MpdContext) -> Never:
    """
    *musicpd.org, client to client section:*

        ``channels``

        Obtain a list of all channels. The response is a list of "channel:"
        lines.
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("readmessages")
def readmessages(context: MpdContext) -> Never:
    """
    *musicpd.org, client to client section:*

        ``readmessages``

        Reads messages for this client. The response is a list of "channel:"
        and "message:" lines.
    """
    raise exceptions.MpdNotImplementedError  # TODO


@protocol.commands.add("sendmessage")
def sendmessage(context: MpdContext, channel: str, text: str) -> Never:
    """
    *musicpd.org, client to client section:*

        ``sendmessage {CHANNEL} {TEXT}``

        Send a message to the specified channel.
    """
    # TODO: match channel against [A-Za-z0-9:._-]+
    raise exceptions.MpdNotImplementedError  # TODO
