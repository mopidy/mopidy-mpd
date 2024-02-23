from __future__ import annotations

from typing import TypeAlias, TypedDict


class MpdConfig(TypedDict):
    hostname: str
    port: int
    password: str | None
    max_connections: int
    connection_timeout: int
    zeroconf: str
    command_blacklist: list[str]
    default_playlist_scheme: str


SocketAddress: TypeAlias = tuple[str, int | None]
