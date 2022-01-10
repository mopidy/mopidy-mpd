from unittest.mock import patch

from tests import protocol


class ConnectionHandlerTest(protocol.BaseTestCase):
    def test_close_closes_the_client_connection(self):
        with patch.object(self.session, "close") as close_mock:
            self.send_request("close")
            close_mock.assert_called_once_with()
        self.assertEqualResponse("OK")

    def test_empty_request(self):
        self.send_request("")
        self.assertEqualResponse("ACK [5@0] {} No command given")

        self.send_request("  ")
        self.assertEqualResponse("ACK [5@0] {} No command given")

    def test_kill(self):
        self.send_request("kill")
        self.assertEqualResponse(
            'ACK [4@0] {kill} you don\'t have permission for "kill"'
        )

    def test_ping(self):
        self.send_request("ping")
        self.assertEqualResponse("OK")

    def test_tagtypes(self):
        self.send_request("tagtypes")
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: ArtistSort")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: AlbumArtist")
        self.assertInResponse("tagtype: AlbumArtistSort")
        self.assertInResponse("tagtype: Title")
        self.assertInResponse("tagtype: Track")
        self.assertInResponse("tagtype: Name")
        self.assertInResponse("tagtype: Genre")
        self.assertInResponse("tagtype: Date")
        self.assertInResponse("tagtype: Composer")
        self.assertInResponse("tagtype: Performer")
        self.assertInResponse("tagtype: Disc")
        self.assertInResponse("tagtype: MUSICBRAINZ_ARTISTID")
        self.assertInResponse("tagtype: MUSICBRAINZ_ALBUMID")
        self.assertInResponse("tagtype: MUSICBRAINZ_ALBUMARTISTID")
        self.assertInResponse("tagtype: MUSICBRAINZ_TRACKID")
        self.assertInResponse("OK")

    def test_tagtypes_clear(self):
        self.send_request("tagtypes clear")
        self.assertEqualResponse("OK")

    def test_tagtypes_all(self):
        self.send_request("tagtypes all")
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: ArtistSort")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: AlbumArtist")
        self.assertInResponse("tagtype: AlbumArtistSort")
        self.assertInResponse("tagtype: Title")
        self.assertInResponse("tagtype: Track")
        self.assertInResponse("tagtype: Name")
        self.assertInResponse("tagtype: Genre")
        self.assertInResponse("tagtype: Date")
        self.assertInResponse("tagtype: Composer")
        self.assertInResponse("tagtype: Performer")
        self.assertInResponse("tagtype: Disc")
        self.assertInResponse("tagtype: MUSICBRAINZ_ARTISTID")
        self.assertInResponse("tagtype: MUSICBRAINZ_ALBUMID")
        self.assertInResponse("tagtype: MUSICBRAINZ_ALBUMARTISTID")
        self.assertInResponse("tagtype: MUSICBRAINZ_TRACKID")
        self.assertInResponse("OK")

    def test_tagtypes_disable(self):
        self.send_request("tagtypes all")
        self.send_request(
            "tagtypes disable MUSICBRAINZ_ARTISTID MUSICBRAINZ_ALBUMID "
            "MUSICBRAINZ_ALBUMARTISTID MUSICBRAINZ_TRACKID"
        )
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: ArtistSort")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: AlbumArtist")
        self.assertInResponse("tagtype: AlbumArtistSort")
        self.assertInResponse("tagtype: Title")
        self.assertInResponse("tagtype: Track")
        self.assertInResponse("tagtype: Name")
        self.assertInResponse("tagtype: Genre")
        self.assertInResponse("tagtype: Date")
        self.assertInResponse("tagtype: Composer")
        self.assertInResponse("tagtype: Performer")
        self.assertInResponse("tagtype: Disc")
        self.assertInResponse("OK")

    def test_tagtypes_enable(self):
        self.send_request("tagtypes clear")
        self.send_request("tagtypes enable Artist Album Title Track Name Genre")
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: Title")
        self.assertInResponse("tagtype: Track")
        self.assertInResponse("tagtype: Name")
        self.assertInResponse("tagtype: Genre")
        self.assertInResponse("OK")
