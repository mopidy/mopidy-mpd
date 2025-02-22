from mopidy_mpd import Extension


def test_get_default_config() -> None:
    ext = Extension()

    config = ext.get_default_config()

    assert "[mpd]" in config
    assert "enabled = true" in config


def test_get_config_schema() -> None:
    ext = Extension()

    schema = ext.get_config_schema()

    assert "hostname" in schema
    assert "port" in schema
    assert "password" in schema
    assert "max_connections" in schema
    assert "connection_timeout" in schema
    assert "zeroconf" in schema
    assert "command_blacklist" in schema
    assert "default_playlist_scheme" in schema
