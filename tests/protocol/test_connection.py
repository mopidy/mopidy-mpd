from unittest.mock import patch

from tests import protocol
from mopidy_mpd.protocol import tagtype_list


class ConnectionHandlerTest(protocol.BaseTestCase):
    def test_close_closes_the_client_connection(self):
        with patch.object(self.session, "close") as close_mock:
            self.send_request("close")
            close_mock.assert_called_once_with()
        self.assertEqualResponse("OK")

    def test_empty_request(self):
        self.send_request("")
        self.assertNoResponse()

        self.send_request("  ")
        self.assertNoResponse()

    def test_kill(self):
        self.send_request("kill")
        self.assertEqualResponse(
            'ACK [4@0] {kill} you don\'t have permission for "kill"'
        )

    def test_ping(self):
        self.send_request("ping")
        self.assertEqualResponse("OK")

    def test_malformed_comamnd(self):
        self.send_request("GET / HTTP/1.1")
        self.assertNoResponse()
        self.connection.stop.assert_called_once_with("Malformed command")

    def test_tagtypes(self):
        self.send_request("tagtypes")
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: ArtistSort")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: AlbumArtist")
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
        self.send_request("tagtypes")
        self.assertEqualResponse("OK")

    def test_tagtypes_all(self):
        self.send_request("tagtypes all")
        self.assertEqualResponse("OK")
        self.send_request("tagtypes")
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: AlbumArtist")
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
        self.assertResponseLength(len(tagtype_list.TAGTYPE_LIST) + 1)

    def test_tagtypes_disable(self):
        self.send_request("tagtypes all")
        self.send_request(
            "tagtypes disable MUSICBRAINZ_ARTISTID MUSICBRAINZ_ALBUMID "
            "MUSICBRAINZ_ALBUMARTISTID MUSICBRAINZ_TRACKID"
        )
        self.assertEqualResponse("OK")
        self.send_request("tagtypes")
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: AlbumArtist")
        self.assertInResponse("tagtype: Title")
        self.assertInResponse("tagtype: Track")
        self.assertInResponse("tagtype: Name")
        self.assertInResponse("tagtype: Genre")
        self.assertInResponse("tagtype: Date")
        self.assertInResponse("tagtype: Composer")
        self.assertInResponse("tagtype: Performer")
        self.assertInResponse("tagtype: Disc")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_ARTISTID")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_ALBUMID")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_ALBUMARTISTID")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_TRACKID")
        self.assertInResponse("OK")

    def test_tagtypes_enable(self):
        self.send_request("tagtypes clear")
        self.send_request("tagtypes enable Artist Album Title Track Name Genre")
        self.assertEqualResponse("OK")
        self.send_request("tagtypes")
        self.assertInResponse("tagtype: Artist")
        self.assertInResponse("tagtype: Album")
        self.assertInResponse("tagtype: Title")
        self.assertInResponse("tagtype: Track")
        self.assertInResponse("tagtype: Name")
        self.assertInResponse("tagtype: Genre")
        self.assertNotInResponse("tagtype: ArtistSort")
        self.assertNotInResponse("tagtype: AlbumArtist")
        self.assertNotInResponse("tagtype: AlbumArtistSort")
        self.assertNotInResponse("tagtype: Date")
        self.assertNotInResponse("tagtype: Composer")
        self.assertNotInResponse("tagtype: Performer")
        self.assertNotInResponse("tagtype: Disc")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_ARTISTID")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_ALBUMID")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_ALBUMARTISTID")
        self.assertNotInResponse("tagtype: MUSICBRAINZ_TRACKID")
        self.assertInResponse("OK")

    def test_tagtypes_disable_x(self):
        self.send_request("tagtypes disable x")
        self.assertEqualResponse("ACK [2@0] {tagtypes} Unknown tag type")

    def test_tagtypes_enable_x(self):
        self.send_request("tagtypes enable x")
        self.assertEqualResponse("ACK [2@0] {tagtypes} Unknown tag type")

    def test_tagtypes_disable_empty(self):
        self.send_request("tagtypes disable")
        self.assertEqualResponse("ACK [2@0] {tagtypes} Not enough arguments")

    def test_tagtypes_enable_empty(self):
        self.send_request("tagtypes enable")
        self.assertEqualResponse("ACK [2@0] {tagtypes} Not enough arguments")

    def test_tagtypes_bogus(self):
        self.send_request("tagtypes bogus")
        self.assertEqualResponse("ACK [2@0] {tagtypes} Unknown sub command")
