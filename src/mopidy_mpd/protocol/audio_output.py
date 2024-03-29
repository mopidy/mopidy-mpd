from __future__ import annotations

from typing import TYPE_CHECKING

from mopidy_mpd import exceptions, protocol

if TYPE_CHECKING:
    from mopidy_mpd.context import MpdContext


@protocol.commands.add("disableoutput", outputid=protocol.UINT)
def disableoutput(context: MpdContext, outputid: int) -> None:
    """
    *musicpd.org, audio output section:*

        ``disableoutput {ID}``

        Turns an output off.
    """
    if outputid == 0:
        success = context.core.mixer.set_mute(False).get()
        if not success:
            raise exceptions.MpdSystemError("problems disabling output")
    else:
        raise exceptions.MpdNoExistError("No such audio output")


@protocol.commands.add("enableoutput", outputid=protocol.UINT)
def enableoutput(context: MpdContext, outputid: int) -> None:
    """
    *musicpd.org, audio output section:*

        ``enableoutput {ID}``

        Turns an output on.
    """
    if outputid == 0:
        success = context.core.mixer.set_mute(True).get()
        if not success:
            raise exceptions.MpdSystemError("problems enabling output")
    else:
        raise exceptions.MpdNoExistError("No such audio output")


@protocol.commands.add("toggleoutput", outputid=protocol.UINT)
def toggleoutput(context: MpdContext, outputid: int) -> None:
    """
    *musicpd.org, audio output section:*

        ``toggleoutput {ID}``

        Turns an output on or off, depending on the current state.
    """
    if outputid == 0:
        mute_status = context.core.mixer.get_mute().get()
        success = context.core.mixer.set_mute(not mute_status)
        if not success:
            raise exceptions.MpdSystemError("problems toggling output")
    else:
        raise exceptions.MpdNoExistError("No such audio output")


@protocol.commands.add("outputs")
def outputs(context: MpdContext) -> protocol.Result:
    """
    *musicpd.org, audio output section:*

        ``outputs``

        Shows information about all outputs.
    """
    muted = 1 if context.core.mixer.get_mute().get() else 0
    return [
        ("outputid", 0),
        ("outputname", "Mute"),
        ("outputenabled", muted),
    ]
