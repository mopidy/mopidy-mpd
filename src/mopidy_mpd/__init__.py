import pathlib
from importlib.metadata import version

from mopidy import config, ext

__version__ = version("Mopidy-MPD")


class Extension(ext.Extension):
    dist_name = "Mopidy-MPD"
    ext_name = "mpd"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()
        schema["hostname"] = config.Hostname()
        schema["port"] = config.Port(optional=True)
        schema["password"] = config.Secret(optional=True)
        schema["max_connections"] = config.Integer(minimum=1)
        schema["connection_timeout"] = config.Integer(minimum=1)
        schema["zeroconf"] = config.String(optional=True)
        schema["command_blacklist"] = config.List(optional=True)
        schema["default_playlist_scheme"] = config.String()
        return schema

    def setup(self, registry):
        from .actor import MpdFrontend

        registry.add("frontend", MpdFrontend)
