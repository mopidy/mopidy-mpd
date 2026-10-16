from unittest.mock import patch

from mopidy_mpd.protocol import tagtype_list
from mopidy_mpd.protocol.connection import MAX_BINARY_LIMIT, MIN_BINARY_LIMIT
from tests import protocol


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

    def test_binarylimit_default(self):
        assert self.session._binarylimit == 8192

    def test_binarylimit(self):
        self.send_request("binarylimit 16384")
        self.assertEqualResponse("OK")
        assert self.session._binarylimit == 16384

    def test_binarylimit_min(self):
        self.send_request(f"binarylimit {MIN_BINARY_LIMIT}")
        self.assertEqualResponse("OK")
        assert self.session._binarylimit == MIN_BINARY_LIMIT

    def test_binarylimit_max(self):
        self.send_request(f"binarylimit {MAX_BINARY_LIMIT}")
        self.assertEqualResponse("OK")
        assert self.session._binarylimit == MAX_BINARY_LIMIT

    def test_binarylimit_too_small(self):
        self.send_request(f"binarylimit {MIN_BINARY_LIMIT - 1}")
        self.assertEqualResponse(
            f"ACK [2@0] {{binarylimit}} 'size' must be at least {MIN_BINARY_LIMIT}"
        )
        assert self.session._binarylimit == 8192

    def test_binarylimit_too_large(self):
        self.send_request(f"binarylimit {MAX_BINARY_LIMIT + 1}")
        self.assertEqualResponse(
            f"ACK [2@0] {{binarylimit}} 'size' must be at most {MAX_BINARY_LIMIT}"
        )
        assert self.session._binarylimit == 8192

    def test_binarylimit_not_a_number(self):
        self.send_request("binarylimit abc")
        self.assertEqualResponse("ACK [2@0] {binarylimit} incorrect arguments")

        self.send_request("binarylimit -1")
        self.assertEqualResponse("ACK [2@0] {binarylimit} incorrect arguments")
        assert self.session._binarylimit == 8192
