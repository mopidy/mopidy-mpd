import logging
from unittest.mock import Mock, sentinel

from mopidy_mpd import dispatcher, network, session


def test_on_start_logged(caplog):
    caplog.set_level(logging.INFO)
    connection = Mock(spec=network.Connection)

    session.MpdSession(
        config=None,
        core=None,
        connection=connection,
    ).on_start()

    assert f"New MPD connection from {connection}" in caplog.text


def test_on_line_received_logged(caplog):
    caplog.set_level(logging.DEBUG)
    connection = Mock(spec=network.Connection)
    mpd_session = session.MpdSession(
        config=None,
        core=None,
        connection=connection,
    )
    mpd_session.dispatcher = Mock(spec=dispatcher.MpdDispatcher)
    mpd_session.dispatcher.handle_request.return_value = [str(sentinel.resp)]

    mpd_session.on_line_received("foobar")

    assert f"Request from {connection}: foobar" in caplog.text
    assert f"Response to {connection}:" in caplog.text
