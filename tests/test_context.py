from typing import cast

import pykka
import pytest
from mopidy.backend import BackendProxy
from mopidy.core import Core, CoreProxy
from mopidy.models import Ref

from mopidy_mpd import uri_mapper
from mopidy_mpd.context import MpdContext
from tests import dummy_backend


@pytest.fixture
def a_track() -> Ref:
    return Ref.track(uri="dummy:/a", name="a")


@pytest.fixture
def b_track() -> Ref:
    return Ref.track(uri="dummy:/foo/b", name="b")


@pytest.fixture
def backend_to_browse(a_track: Ref, b_track: Ref) -> BackendProxy:
    backend = cast(BackendProxy, dummy_backend.create_proxy())
    backend.library.dummy_browse_result = {
        "dummy:/": [
            a_track,
            Ref.directory(uri="dummy:/foo", name="foo"),
        ],
        "dummy:/foo": [
            b_track,
        ],
    }
    return backend


@pytest.fixture
def mpd_context(backend_to_browse: BackendProxy) -> MpdContext:
    core = cast(
        CoreProxy,
        Core.start(config=None, backends=[backend_to_browse]).proxy(),
    )
    return MpdContext(
        config=None,
        core=core,
        uri_map=uri_mapper.MpdUriMapper(core),
        dispatcher=None,
        session=None,
    )


class TestMpdContext:
    @classmethod
    def teardown_class(cls):
        pykka.ActorRegistry.stop_all()

    def test_browse_root(self, mpd_context, a_track):
        results = mpd_context.browse("dummy", recursive=False, lookup=False)

        assert [("/dummy/a", a_track), ("/dummy/foo", None)] == list(results)

    def test_browse_root_recursive(self, mpd_context, a_track, b_track):
        results = mpd_context.browse("dummy", recursive=True, lookup=False)

        assert [
            ("/dummy", None),
            ("/dummy/a", a_track),
            ("/dummy/foo", None),
            ("/dummy/foo/b", b_track),
        ] == list(results)

    @pytest.mark.parametrize(
        "bad_ref",
        [
            Ref.track(uri="dummy:/x"),
            Ref.directory(uri="dummy:/y"),
        ],
    )
    def test_browse_skips_bad_refs(
        self, backend_to_browse, a_track, bad_ref, mpd_context
    ):
        backend_to_browse.library.dummy_browse_result = {
            "dummy:/": [bad_ref, a_track],
        }

        results = mpd_context.browse("dummy", recursive=False, lookup=False)

        assert [("/dummy/a", a_track)] == list(results)
