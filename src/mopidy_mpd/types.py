from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, TypedDict

from mopidy.config import Config as MopidyConfig

if TYPE_CHECKING:
    from mopidy.types import UriScheme


class Config(MopidyConfig):
    mpd: MpdConfig


class MpdConfig(TypedDict):
    hostname: str
    port: int
    password: str | None
    max_connections: int
    connection_timeout: int
    zeroconf: str
    command_blacklist: list[str]
    default_playlist_scheme: UriScheme


SocketAddress: TypeAlias = tuple[str, int | None]
