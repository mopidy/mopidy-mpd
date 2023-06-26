from io import BytesIO
from mopidy_mpd.protocol import album_art
from unittest import mock
from mopidy.models import Album, Track, Image

from tests import protocol


def mock_get_images(self, uris):
    result = {}
    for uri in uris:
        result[uri] = [Image(uri="dummy:/albumart.jpg", width=128, height=128)]
    return result


class AlbumArtTest(protocol.BaseTestCase):
    def test_albumart_for_track_without_art(self):
        track = Track(
            uri="dummy:/à",
            name="a nàme",
            album=Album(uri="something:àlbum:12345"),
        )
        self.backend.library.dummy_library = [track]
        self.core.tracklist.add(uris=[track.uri]).get()

        self.core.playback.play().get()

        self.send_request("albumart file:///home/test/music.flac 0")
        self.assertInResponse("ACK [50@0] {albumart} No art file exists")

    @mock.patch.object(
        protocol.core.library.LibraryController, "get_images", mock_get_images
    )
    def test_albumart(self):
        track = Track(
            uri="dummy:/à",
            name="a nàme",
            album=Album(uri="something:àlbum:12345"),
        )
        self.backend.library.dummy_library = [track]
        self.core.tracklist.add(uris=[track.uri]).get()

        self.core.playback.play().get()

        ##
        expected = b"result"

        with mock.patch.object(
            album_art, "urlopen", return_value=BytesIO(expected)
        ):
            self.send_request("albumart file:///home/test/music.flac 0")

        self.assertInResponse("binary: " + str(len(expected)))
