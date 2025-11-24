from __future__ import annotations

import logging
import re
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    overload,
)

from mopidy_mpd import exceptions, types

if TYPE_CHECKING:
    from collections.abc import Generator

    import pykka
    from mopidy.core import CoreProxy
    from mopidy.models import Ref, Track
    from mopidy.types import Uri

    from mopidy_mpd.dispatcher import MpdDispatcher
    from mopidy_mpd.session import MpdSession
    from mopidy_mpd.uri_mapper import MpdUriMapper


logger = logging.getLogger(__name__)


class MpdContext:
    """
    This object is passed as the first argument to all MPD command handlers to
    give the command handlers access to important parts of Mopidy.
    """

    #: The Mopidy config.
    config: types.Config

    #: The Mopidy core API.
    core: CoreProxy

    #: The current session instance.
    session: MpdSession

    #: The current dispatcher instance.
    dispatcher: MpdDispatcher

    #: Mapping of URIs to MPD names.
    uri_map: MpdUriMapper

    def __init__(
        self,
        config: types.Config,
        core: CoreProxy,
        uri_map: MpdUriMapper,
        session: MpdSession,
        dispatcher: MpdDispatcher,
    ) -> None:
        self.config = config
        self.core = core
        self.uri_map = uri_map
        self.session = session
        self.dispatcher = dispatcher

    @overload
    def browse(
        self, path: str | None, *, recursive: bool, lookup: Literal[True]
    ) -> Generator[tuple[str, pykka.Future[dict[Uri, list[Track]]] | None], Any]: ...

    @overload
    def browse(
        self, path: str | None, *, recursive: bool, lookup: Literal[False]
    ) -> Generator[tuple[str, Ref | None], Any]: ...

    def browse(  # noqa: C901, PLR0912
        self,
        path: str | None,
        *,
        recursive: bool = True,
        lookup: bool = True,
    ) -> Generator[Any, Any]:
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

        uri = self.uri_map.uri_from_name(root_path)
        if uri is None:
            for part in path_parts:
                for ref in self.core.library.browse(uri).get():
                    if ref.type != ref.TRACK and ref.name == part:
                        uri = ref.uri
                        break
                else:
                    raise exceptions.MpdNoExistError("Not found")
            root_path = self.uri_map.insert(root_path, uri)

        if recursive:
            yield (root_path, None)

        path_and_futures = [(root_path, self.core.library.browse(uri))]
        while path_and_futures:
            base_path, future = path_and_futures.pop()
            for ref in future.get():
                if ref.name is None or ref.uri is None:
                    continue

                path = "/".join([base_path, ref.name.replace("/", "")])
                path = self.uri_map.insert(path, ref.uri)

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
