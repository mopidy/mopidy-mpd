import unittest

import pykka
import pytest

from mopidy import core
from mopidy.models import Ref
from mopidy_mpd.dispatcher import MpdContext, MpdDispatcher
from mopidy_mpd.exceptions import MpdAckError
from mopidy_mpd.uri_mapper import MpdUriMapper

from tests import dummy_backend


class MpdDispatcherTest(unittest.TestCase):
    def setUp(self):  # noqa: N802
        config = {"mpd": {"password": None, "command_blacklist": ["disabled"]}}
        self.backend = dummy_backend.create_proxy()
        self.dispatcher = MpdDispatcher(config=config)

        self.core = core.Core.start(backends=[self.backend]).proxy()

    def tearDown(self):  # noqa: N802
        pykka.ActorRegistry.stop_all()

    def test_call_handler_for_unknown_command_raises_exception(self):
        with self.assertRaises(MpdAckError) as cm:
            self.dispatcher._call_handler("an_unknown_command with args")

        assert (
            cm.exception.get_mpd_ack()
            == 'ACK [5@0] {} unknown command "an_unknown_command"'
        )

    def test_handling_unknown_request_yields_error(self):
        result = self.dispatcher.handle_request("an unhandled request")
        assert result[0] == 'ACK [5@0] {} unknown command "an"'

    def test_handling_blacklisted_command(self):
        result = self.dispatcher.handle_request("disabled")
        assert (
            result[0]
            == 'ACK [0@0] {disabled} "disabled" has been disabled in the server'
        )


@pytest.fixture
def a_track():
    return Ref.track(uri="dummy:/a", name="a")


@pytest.fixture
def b_track():
    return Ref.track(uri="dummy:/foo/b", name="b")


@pytest.fixture
def backend_to_browse(a_track, b_track):
    backend = dummy_backend.create_proxy()
    backend.library.dummy_browse_result = {
        "dummy:/": [a_track, Ref.directory(uri="dummy:/foo", name="foo")],
        "dummy:/foo": [b_track],
    }
    return backend


@pytest.fixture
def mpd_context(backend_to_browse):
    mopidy_core = core.Core.start(backends=[backend_to_browse]).proxy()
    uri_map = MpdUriMapper(mopidy_core)
    return MpdContext(None, core=mopidy_core, uri_map=uri_map)


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
            Ref.track(name="x"),
            Ref.directory(uri="dummy:/y"),
            Ref.directory(name="y"),
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
