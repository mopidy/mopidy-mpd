import logging
import pathlib

import pkg_resources

from mopidy import config, ext

__version__ = pkg_resources.get_distribution("Mopidy-MPD").version

# TODO: If you need to log, use loggers named after the current Python module
logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = "Mopidy-MPD"
    ext_name = "mpd"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()
        # TODO: Comment in and edit, or remove entirely
        #schema["username"] = config.String()
        #schema["password"] = config.Secret()
        return schema

    def setup(self, registry):
        # You will typically only implement one of the following things
        # in a single extension.

        # TODO: Edit or remove entirely
        from .frontend import FoobarFrontend
        registry.add("frontend", FoobarFrontend)

        # TODO: Edit or remove entirely
        from .backend import FoobarBackend
        registry.add("backend", FoobarBackend)

        # TODO: Edit or remove entirely
        registry.add("http:static", {
            "name": self.ext_name,
            "path": str(pathlib.Path(__file__) / "static")),
        })
