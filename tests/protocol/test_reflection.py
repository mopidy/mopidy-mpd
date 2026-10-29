from unittest import mock

from tests import protocol

CHANNEL_REQUESTS = {
    "subscribe": 'subscribe "topic"',
    "unsubscribe": 'unsubscribe "topic"',
    "channels": "channels",
    "readmessages": "readmessages",
    "sendmessage": 'sendmessage "topic" "message"',
}


class ReflectionHandlerTest(protocol.BaseTestCase):
    def test_unimplemented_channels_are_not_advertised(self):
        for request in ("commands", "notcommands"):
            self.send_request(request)
            for name in CHANNEL_REQUESTS:
                with self.subTest(request=request, command=name):
                    self.assertNotInResponse(f"command: {name}")
            self.assertInResponse("OK")

    def test_config_is_not_allowed_across_the_network(self):
        self.send_request("config")
        self.assertEqualResponse(
            'ACK [4@0] {config} you don\'t have permission for "config"'
        )

    def test_commands_returns_list_of_all_commands(self):
        self.send_request("commands")
        # Check if some random commands are included
        self.assertInResponse("command: commands")
        self.assertInResponse("command: play")
        self.assertInResponse("command: status")
        # The dummy backend provides playlists
        self.assertInResponse("command: save")
        self.assertInResponse("command: listplaylists")
        # Check if commands you do not have access to are not present
        self.assertNotInResponse("command: config")
        self.assertNotInResponse("command: kill")
        # Check if the blacklisted commands are not present
        self.assertNotInResponse("command: command_list_begin")
        self.assertNotInResponse("command: command_list_ok_begin")
        self.assertNotInResponse("command: command_list_end")
        self.assertInResponse("command: idle")
        self.assertNotInResponse("command: noidle")
        self.assertNotInResponse("command: sticker")
        self.assertInResponse("OK")

    def test_commands_hides_playlist_commands_without_playlist_backend(self):
        with mock.patch(
            "mopidy.core.PlaylistsController.get_uri_schemes", return_value=[]
        ):
            self.send_request("commands")
        for name in (
            "listplaylists",
            "playlistadd",
            "playlistclear",
            "playlistdelete",
            "playlistmove",
            "rename",
            "rm",
            "save",
        ):
            self.assertNotInResponse(f"command: {name}")
        self.assertInResponse("command: load")
        self.assertInResponse("command: listplaylist")
        self.assertInResponse("command: play")
        self.assertInResponse("OK")

    def test_decoders(self):
        self.send_request("decoders")
        self.assertInResponse("OK")

    def test_notcommands_returns_only_config_and_kill_and_ok(self):
        response = self.send_request("notcommands")
        assert len(response) == 3
        self.assertInResponse("command: config")
        self.assertInResponse("command: kill")
        self.assertInResponse("OK")

    def test_urlhandlers(self):
        self.send_request("urlhandlers")
        self.assertInResponse("OK")
        self.assertInResponse("handler: dummy")


class ReflectionWhenNotAuthedTest(protocol.BaseTestCase):
    def get_config(self):
        config = super().get_config()
        config["mpd"]["password"] = "topsecret"  # noqa: S105
        return config

    def test_unimplemented_channels_are_not_advertised_before_or_after_login(self):
        for authenticated in (False, True):
            if authenticated:
                self.send_request('password "topsecret"')
                self.assertEqualResponse("OK")
            for request in ("commands", "notcommands"):
                self.send_request(request)
                for name in CHANNEL_REQUESTS:
                    with self.subTest(
                        authenticated=authenticated, request=request, command=name
                    ):
                        self.assertNotInResponse(f"command: {name}")
                self.assertInResponse("OK")
                if (request == "commands") == authenticated:
                    self.assertInResponse("command: play")
                    self.assertInResponse("command: status")

    def test_unlisted_channels_keep_their_authentication_and_error_responses(self):
        for authenticated in (False, True):
            if authenticated:
                self.send_request('password "topsecret"')
                self.assertEqualResponse("OK")
            for name, request in CHANNEL_REQUESTS.items():
                with self.subTest(authenticated=authenticated, command=name):
                    self.send_request(request)
                    if authenticated:
                        self.assertEqualResponse(
                            f"ACK [0@0] {{{name}}} Not implemented"
                        )
                    else:
                        self.assertEqualResponse(
                            f"ACK [4@0] {{{name}}} "
                            f'you don\'t have permission for "{name}"'
                        )

    def test_commands_show_less_if_auth_required_and_not_authed(self):
        self.send_request("commands")
        # Not requiring auth
        self.assertInResponse("command: close")
        self.assertInResponse("command: commands")
        self.assertInResponse("command: notcommands")
        self.assertInResponse("command: password")
        self.assertInResponse("command: ping")
        # Requiring auth
        self.assertNotInResponse("command: play")
        self.assertNotInResponse("command: status")

    def test_notcommands_returns_more_if_auth_required_and_not_authed(self):
        self.send_request("notcommands")
        # Not requiring auth
        self.assertNotInResponse("command: close")
        self.assertNotInResponse("command: commands")
        self.assertNotInResponse("command: notcommands")
        self.assertNotInResponse("command: password")
        self.assertNotInResponse("command: ping")
        # Requiring auth
        self.assertInResponse("command: play")
        self.assertInResponse("command: status")
