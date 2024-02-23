import unittest

import pytest
from mopidy_mpd.exceptions import (
    MpdAckError,
    MpdNoCommandError,
    MpdNoExistError,
    MpdNotImplementedError,
    MpdPermissionError,
    MpdSystemError,
    MpdUnknownCommandError,
)


class MpdExceptionsTest(unittest.TestCase):
    def test_mpd_not_implemented_is_a_mpd_ack_error(self):
        with pytest.raises(MpdAckError) as exc_info:
            raise MpdNotImplementedError

        assert exc_info.value.message == "Not implemented"

    def test_get_mpd_ack_with_default_values(self):
        e = MpdAckError("A description")

        assert e.get_mpd_ack() == "ACK [0@0] {None} A description"

    def test_get_mpd_ack_with_values(self):
        with pytest.raises(MpdAckError) as exc_info:
            raise MpdAckError("A description", index=7, command="foo")

        assert exc_info.value.get_mpd_ack() == "ACK [0@7] {foo} A description"

    def test_mpd_unknown_command(self):
        with pytest.raises(MpdAckError) as exc_info:
            raise MpdUnknownCommandError(command="play")

        assert exc_info.value.get_mpd_ack() == 'ACK [5@0] {} unknown command "play"'

    def test_mpd_no_command(self):
        with pytest.raises(MpdAckError) as exc_info:
            raise MpdNoCommandError

        assert exc_info.value.get_mpd_ack() == "ACK [5@0] {} No command given"

    def test_mpd_system_error(self):
        with pytest.raises(MpdSystemError) as exc_info:
            raise MpdSystemError("foo")

        assert exc_info.value.get_mpd_ack() == "ACK [52@0] {None} foo"

    def test_mpd_permission_error(self):
        with pytest.raises(MpdPermissionError) as exc_info:
            raise MpdPermissionError(command="foo")

        assert (
            exc_info.value.get_mpd_ack()
            == 'ACK [4@0] {foo} you don\'t have permission for "foo"'
        )

    def test_mpd_noexist_error(self):
        with pytest.raises(MpdNoExistError) as exc_info:
            raise MpdNoExistError(command="foo")

        assert exc_info.value.get_mpd_ack() == "ACK [50@0] {foo} "
