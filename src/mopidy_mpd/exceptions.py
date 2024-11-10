from typing import Any

from mopidy.exceptions import MopidyException
from mopidy.types import UriScheme


class MpdAckError(MopidyException):
    """See fields on this class for available MPD error codes"""

    ACK_ERROR_NOT_LIST = 1
    ACK_ERROR_ARG = 2
    ACK_ERROR_PASSWORD = 3
    ACK_ERROR_PERMISSION = 4
    ACK_ERROR_UNKNOWN = 5
    ACK_ERROR_NO_EXIST = 50
    ACK_ERROR_PLAYLIST_MAX = 51
    ACK_ERROR_SYSTEM = 52
    ACK_ERROR_PLAYLIST_LOAD = 53
    ACK_ERROR_UPDATE_ALREADY = 54
    ACK_ERROR_PLAYER_SYNC = 55
    ACK_ERROR_EXIST = 56

    error_code = 0

    def __init__(
        self,
        message: str = "",
        index: int = 0,
        command: str | None = None,
    ) -> None:
        super().__init__(message, index, command)
        self.message = message
        self.index = index
        self.command = command

    def get_mpd_ack(self) -> str:
        """
        MPD error code format::

            ACK [%(error_code)i@%(index)i] {%(command)s} description
        """
        return (
            f"ACK [{self.__class__.error_code:d}@{self.index:d}] "
            f"{{{self.command}}} {self.message}"
        )


class MpdArgError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_ARG


class MpdPasswordError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_PASSWORD


class MpdPermissionError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_PERMISSION

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        assert self.command is not None, "command must be given explicitly"
        self.message = f'you don\'t have permission for "{self.command}"'


class MpdUnknownError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_UNKNOWN


class MpdUnknownCommandError(MpdUnknownError):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        assert self.command is not None, "command must be given explicitly"
        self.message = f'unknown command "{self.command}"'
        self.command = ""


class MpdNoCommandError(MpdUnknownCommandError):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["command"] = ""
        super().__init__(*args, **kwargs)
        self.message = "No command given"


class MpdNoExistError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_NO_EXIST


class MpdExistError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_EXIST


class MpdSystemError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_SYSTEM


class MpdInvalidPlaylistNameError(MpdAckError):
    error_code = MpdAckError.ACK_ERROR_ARG

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.message = (
            "playlist name is invalid: playlist names may not "
            "contain slashes, newlines or carriage returns"
        )


class MpdNotImplementedError(MpdAckError):
    error_code = 0

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.message = "Not implemented"


class MpdInvalidTrackForPlaylistError(MpdAckError):
    # NOTE: This is a custom error for Mopidy that does not exist in MPD.
    error_code = 0

    def __init__(
        self,
        playlist_scheme: UriScheme,
        track_scheme: UriScheme,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.message = (
            f'Playlist with scheme "{playlist_scheme}" '
            f'can\'t store track scheme "{track_scheme}"'
        )


class MpdFailedToSavePlaylistError(MpdAckError):
    # NOTE: This is a custom error for Mopidy that does not exist in MPD.
    error_code = 0

    def __init__(
        self,
        backend_scheme: UriScheme,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.message = f'Backend with scheme "{backend_scheme}" failed to save playlist'


class MpdDisabledError(MpdAckError):
    # NOTE: This is a custom error for Mopidy that does not exist in MPD.
    error_code = 0

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        assert self.command is not None, "command must be given explicitly"
        self.message = f'"{self.command}" has been disabled in the server'
