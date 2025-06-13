import unittest
from unittest import mock

from mopidy.models import Album, Artist, Playlist, Ref, SearchResult, Track

from mopidy_mpd.protocol import music_db, stored_playlists
from tests import protocol

# TODO: split into more modules for faster parallel tests?


class QueryForSearchTest(unittest.TestCase):
    def test_dates_are_extracted(self):
        result = music_db._query_for_search(["Date", "1974-01-02", "Date", "1975"])
        assert result["date"] == ["1974-01-02", "1975"]

    def test_empty_value_is_ignored(self):
        result = music_db._query_for_search(["Date", ""])
        assert result == {}

    def test_whitespace_value_is_ignored(self):
        result = music_db._query_for_search(["Date", "  "])
        assert result == {}

    # TODO Test more mappings


class QueryFromMpdListFormatTest(unittest.TestCase):
    pass  # TODO


class TagMappingTest(unittest.TestCase):
    def test_is_list_name_mapping_for_every_field(self):
        for field in music_db._LIST_MAPPING.values():
            assert field in music_db._LIST_NAME_MAPPING

    def test_list_mapping_does_not_includes_any(self):
        assert "any" not in music_db._LIST_NAME_MAPPING

    def test_search_mapping_includes_any(self):
        assert "any" in music_db._SEARCH_MAPPING


# TODO: why isn't core.playlists.filter getting deprecation warnings?


class MusicDatabaseHandlerTest(protocol.BaseTestCase):
    def test_count(self):
        self.send_request('count "artist" "needle"')
        self.assertInResponse("songs: 0")
        self.assertInResponse("playtime: 0")
        self.assertInResponse("OK")

    def test_count_without_quotes(self):
        self.send_request('count artist "needle"')
        self.assertInResponse("songs: 0")
        self.assertInResponse("playtime: 0")
        self.assertInResponse("OK")

    def test_count_with_multiple_pairs(self):
        self.send_request('count "artist" "foo" "album" "bar"')
        self.assertInResponse("songs: 0")
        self.assertInResponse("playtime: 0")
        self.assertInResponse("OK")

    def test_count_correct_length(self):
        # Count the lone track
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(uri="dummy:a", name="foo", date="2001", length=4000)]
        )
        self.send_request('count "title" "foo"')
        self.assertInResponse("songs: 1")
        self.assertInResponse("playtime: 4")
        self.assertInResponse("OK")

        # Count multiple tracks
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[
                Track(uri="dummy:b", date="2001", length=50000),
                Track(uri="dummy:c", date="2001", length=600000),
            ]
        )
        self.send_request('count "date" "2001"')
        self.assertInResponse("songs: 2")
        self.assertInResponse("playtime: 650")
        self.assertInResponse("OK")

    def test_count_with_track_length_none(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(uri="dummy:b", date="2001", length=None)]
        )
        self.send_request('count "date" "2001"')
        self.assertInResponse("songs: 1")
        self.assertInResponse("playtime: 0")
        self.assertInResponse("OK")

    def test_findadd(self):
        track = Track(uri="dummy:a", name="A")
        self.backend.library.dummy_library = [track]
        self.backend.library.dummy_find_exact_result = SearchResult(tracks=[track])
        assert self.core.tracklist.get_length().get() == 0

        self.send_request('findadd "title" "A"')

        assert self.core.tracklist.get_length().get() == 1
        assert self.core.tracklist.get_tracks().get()[0].uri == "dummy:a"
        self.assertInResponse("OK")

    def test_searchadd(self):
        track = Track(uri="dummy:a", name="A")
        self.backend.library.dummy_library = [track]
        self.backend.library.dummy_search_result = SearchResult(tracks=[track])
        assert self.core.tracklist.get_length().get() == 0

        self.send_request('searchadd "title" "a"')

        assert self.core.tracklist.get_length().get() == 1
        assert self.core.tracklist.get_tracks().get()[0].uri == "dummy:a"
        self.assertInResponse("OK")

    def test_searchaddpl_appends_to_existing_playlist(self):
        playlist = self.core.playlists.create("my favs").get()
        playlist = playlist.replace(
            tracks=[
                Track(uri="dummy:x", name="X"),
                Track(uri="dummy:y", name="y"),
            ]
        )
        self.core.playlists.save(playlist)
        self.backend.library.dummy_search_result = SearchResult(
            tracks=[Track(uri="dummy:a", name="A")]
        )

        items = self.core.playlists.get_items(playlist.uri).get()
        assert len(items) == 2

        self.send_request('searchaddpl "my favs" "title" "a"')

        items = self.core.playlists.get_items(playlist.uri).get()
        assert len(items) == 3
        assert items[0].uri == "dummy:x"
        assert items[1].uri == "dummy:y"
        assert items[2].uri == "dummy:a"
        self.assertInResponse("OK")

    def test_searchaddpl_creates_missing_playlist(self):
        self.backend.library.dummy_search_result = SearchResult(
            tracks=[Track(uri="dummy:a", name="A")]
        )

        playlists = self.core.playlists.as_list().get()
        assert "my favs" not in {p.name for p in playlists}

        self.send_request('searchaddpl "my favs" "title" "a"')

        playlists = self.core.playlists.as_list().get()
        playlist = {p.name: p for p in playlists}["my favs"]

        items = self.core.playlists.get_items(playlist.uri).get()

        assert len(items) == 1
        assert items[0].uri == "dummy:a"
        self.assertInResponse("OK")

    def test_listall_without_uri(self):
        tracks = [
            Track(uri="dummy:/a", name="a"),
            Track(uri="dummy:/foo/b", name="b"),
        ]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
                Ref.album(uri="dummy:/album", name="album"),
                Ref.artist(uri="dummy:/artist", name="artist"),
                Ref.playlist(uri="dummy:/pl", name="pl"),
            ],
            "dummy:/foo": [Ref.track(uri="dummy:/foo/b", name="b")],
        }

        self.send_request("listall")

        self.assertInResponse("file: dummy:/a")
        self.assertInResponse("directory: dummy/foo")
        self.assertInResponse("directory: dummy/album")
        self.assertInResponse("directory: dummy/artist")
        self.assertInResponse("directory: dummy/pl")
        self.assertInResponse("file: dummy:/foo/b")
        self.assertInResponse("OK")

    def test_listall_with_uri(self):
        tracks = [
            Track(uri="dummy:/a", name="a"),
            Track(uri="dummy:/foo/b", name="b"),
        ]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ],
            "dummy:/foo": [Ref.track(uri="dummy:/foo/b", name="b")],
        }

        self.send_request('listall "/dummy/foo"')

        self.assertNotInResponse("file: dummy:/a")
        self.assertInResponse("directory: dummy/foo")
        self.assertInResponse("file: dummy:/foo/b")
        self.assertInResponse("OK")

    def test_listall_with_unknown_uri(self):
        self.send_request('listall "/unknown"')

        self.assertEqualResponse("ACK [50@0] {listall} Not found")

    def test_listall_for_dir_with_and_without_leading_slash_is_the_same(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }

        response1 = self.send_request('listall "dummy"')
        response2 = self.send_request('listall "/dummy"')
        assert response1 == response2

    def test_listall_for_dir_with_and_without_trailing_slash_is_the_same(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }

        response1 = self.send_request('listall "dummy"')
        response2 = self.send_request('listall "dummy/"')
        assert response1 == response2

    def test_listall_duplicate(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.directory(uri="dummy:/a1", name="a"),
                Ref.directory(uri="dummy:/a2", name="a"),
            ]
        }

        self.send_request("listall")
        self.assertInResponse("directory: dummy/a")
        self.assertInResponse("directory: dummy/a [2]")

    def test_listallinfo_without_uri(self):
        tracks = [
            Track(uri="dummy:/a", name="a"),
            Track(uri="dummy:/foo/b", name="b"),
        ]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
                Ref.album(uri="dummy:/album", name="album"),
                Ref.artist(uri="dummy:/artist", name="artist"),
                Ref.playlist(uri="dummy:/pl", name="pl"),
            ],
            "dummy:/foo": [Ref.track(uri="dummy:/foo/b", name="b")],
        }

        self.send_request("listallinfo")

        self.assertInResponse("file: dummy:/a")
        self.assertInResponse("Title: a")
        self.assertInResponse("directory: dummy/foo")
        self.assertInResponse("directory: dummy/album")
        self.assertInResponse("directory: dummy/artist")
        self.assertInResponse("directory: dummy/pl")
        self.assertInResponse("file: dummy:/foo/b")
        self.assertInResponse("Title: b")
        self.assertInResponse("OK")

    def test_listallinfo_with_uri(self):
        tracks = [
            Track(uri="dummy:/a", name="a"),
            Track(uri="dummy:/foo/b", name="b"),
        ]
        self.backend.library.dummy_library = tracks
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ],
            "dummy:/foo": [Ref.track(uri="dummy:/foo/b", name="b")],
        }

        self.send_request('listallinfo "/dummy/foo"')

        self.assertNotInResponse("file: dummy:/a")
        self.assertNotInResponse("Title: a")
        self.assertInResponse("directory: dummy/foo")
        self.assertInResponse("file: dummy:/foo/b")
        self.assertInResponse("Title: b")
        self.assertInResponse("OK")

    def test_listallinfo_with_unknown_uri(self):
        self.send_request('listallinfo "/unknown"')

        self.assertEqualResponse("ACK [50@0] {listallinfo} Not found")

    def test_listallinfo_for_dir_with_and_without_leading_slash_is_same(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }

        response1 = self.send_request('listallinfo "dummy"')
        response2 = self.send_request('listallinfo "/dummy"')
        assert response1 == response2

    def test_listallinfo_for_dir_with_and_without_trailing_slash_is_same(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }

        response1 = self.send_request('listallinfo "dummy"')
        response2 = self.send_request('listallinfo "dummy/"')
        assert response1 == response2

    def test_listallinfo_duplicate(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.directory(uri="dummy:/a1", name="a"),
                Ref.directory(uri="dummy:/a2", name="a"),
            ]
        }

        self.send_request("listallinfo")
        self.assertInResponse("directory: dummy/a")
        self.assertInResponse("directory: dummy/a [2]")

    def test_listfiles(self):
        self.send_request("listfiles")
        self.assertEqualResponse("ACK [0@0] {listfiles} Not implemented")

    @mock.patch.object(stored_playlists, "_get_last_modified")
    def test_lsinfo_without_path_returns_same_as_for_root(self, last_modified_mock):
        last_modified_mock.return_value = "2015-08-05T22:51:06Z"
        self.backend.playlists.set_dummy_playlists([Playlist(name="a", uri="dummy:/a")])

        response1 = self.send_request("lsinfo")
        response2 = self.send_request('lsinfo "/"')
        assert response1 == response2

    @mock.patch.object(stored_playlists, "_get_last_modified")
    def test_lsinfo_with_empty_path_returns_same_as_for_root(self, last_modified_mock):
        last_modified_mock.return_value = "2015-08-05T22:51:06Z"
        self.backend.playlists.set_dummy_playlists([Playlist(name="a", uri="dummy:/a")])

        response1 = self.send_request('lsinfo ""')
        response2 = self.send_request('lsinfo "/"')
        assert response1 == response2

    @mock.patch.object(stored_playlists, "_get_last_modified")
    def test_lsinfo_for_root_includes_playlists(self, last_modified_mock):
        last_modified_mock.return_value = "2015-08-05T22:51:06Z"
        self.backend.playlists.set_dummy_playlists([Playlist(name="a", uri="dummy:/a")])

        self.send_request('lsinfo "/"')
        self.assertInResponse("playlist: a")
        self.assertInResponse("Last-Modified: 2015-08-05T22:51:06Z")
        self.assertInResponse("OK")

    def test_lsinfo_for_root_includes_dirs_for_each_lib_with_content(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }

        self.send_request('lsinfo "/"')
        self.assertInResponse("directory: dummy")
        self.assertInResponse("OK")

    @mock.patch.object(stored_playlists, "_get_last_modified")
    def test_lsinfo_for_dir_with_and_without_leading_slash_is_the_same(
        self, last_modified_mock
    ):
        last_modified_mock.return_value = "2015-08-05T22:51:06Z"
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }

        response1 = self.send_request('lsinfo "dummy"')
        response2 = self.send_request('lsinfo "/dummy"')
        assert response1 == response2

    @mock.patch.object(stored_playlists, "_get_last_modified")
    def test_lsinfo_for_dir_with_and_without_trailing_slash_is_the_same(
        self, last_modified_mock
    ):
        last_modified_mock.return_value = "2015-08-05T22:51:06Z"
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }

        response1 = self.send_request('lsinfo "dummy"')
        response2 = self.send_request('lsinfo "dummy/"')
        assert response1 == response2

    def test_lsinfo_for_dir_includes_tracks(self):
        self.backend.library.dummy_library = [
            Track(uri="dummy:/a", name="a"),
        ]
        self.backend.library.dummy_browse_result = {
            "dummy:/": [Ref.track(uri="dummy:/a", name="a")]
        }

        self.send_request('lsinfo "/dummy"')
        self.assertInResponse("file: dummy:/a")
        self.assertInResponse("Title: a")
        self.assertInResponse("OK")

    def test_lsinfo_for_dir_includes_subdirs(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [Ref.directory(uri="dummy:/foo", name="foo")]
        }

        self.send_request('lsinfo "/dummy"')
        self.assertInResponse("directory: dummy/foo")
        self.assertInResponse("OK")

    def test_lsinfo_for_empty_dir_returns_nothing(self):
        self.backend.library.dummy_browse_result = {"dummy:/": []}

        self.send_request('lsinfo "/dummy"')
        self.assertInResponse("OK")

    def test_lsinfo_for_dir_does_not_recurse(self):
        self.backend.library.dummy_library = [
            Track(uri="dummy:/a", name="a"),
        ]
        self.backend.library.dummy_browse_result = {
            "dummy:/": [Ref.directory(uri="dummy:/foo", name="foo")],
            "dummy:/foo": [Ref.track(uri="dummy:/a", name="a")],
        }

        self.send_request('lsinfo "/dummy"')
        self.assertNotInResponse("file: dummy:/a")
        self.assertInResponse("OK")

    def test_lsinfo_for_dir_does_not_include_self(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [Ref.directory(uri="dummy:/foo", name="foo")],
            "dummy:/foo": [Ref.track(uri="dummy:/a", name="a")],
        }

        self.send_request('lsinfo "/dummy"')
        self.assertNotInResponse("directory: dummy")
        self.assertInResponse("OK")

    def test_lsinfo_for_root_returns_browse_result_before_playlists(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.track(uri="dummy:/a", name="a"),
                Ref.directory(uri="dummy:/foo", name="foo"),
            ]
        }
        self.backend.playlists.set_dummy_playlists([Playlist(name="a", uri="dummy:/a")])

        response = self.send_request('lsinfo "/"')
        assert response.index("directory: dummy") < response.index("playlist: a")

    def test_lsinfo_duplicate(self):
        self.backend.library.dummy_browse_result = {
            "dummy:/": [
                Ref.directory(uri="dummy:/a1", name="a"),
                Ref.directory(uri="dummy:/a2", name="a"),
            ]
        }

        self.send_request('lsinfo "/dummy"')
        self.assertInResponse("directory: dummy/a")
        self.assertInResponse("directory: dummy/a [2]")

    def test_update_without_uri(self):
        self.send_request("update")
        self.assertInResponse("updating_db: 0")
        self.assertInResponse("OK")

    def test_update_with_uri(self):
        self.send_request('update "file:///dev/urandom"')
        self.assertInResponse("updating_db: 0")
        self.assertInResponse("OK")

    def test_rescan_without_uri(self):
        self.send_request("rescan")
        self.assertInResponse("updating_db: 0")
        self.assertInResponse("OK")

    def test_rescan_with_uri(self):
        self.send_request('rescan "file:///dev/urandom"')
        self.assertInResponse("updating_db: 0")
        self.assertInResponse("OK")


class MusicDatabaseFindTest(protocol.BaseTestCase):
    def test_find_includes_fake_artist_and_album_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri="dummy:album:a", name="A", date="2001")],
            artists=[Artist(uri="dummy:artist:b", name="B")],
            tracks=[Track(uri="dummy:track:c", name="C")],
        )

        self.send_request('find "any" "foo"')

        self.assertInResponse("file: dummy:artist:b")
        self.assertInResponse("Title: Artist: B")

        self.assertInResponse("file: dummy:album:a")
        self.assertInResponse("Title: Album: A")
        self.assertInResponse("Date: 2001")

        self.assertInResponse("file: dummy:track:c")
        self.assertInResponse("Title: C")

        self.assertInResponse("OK")

    def test_find_artist_does_not_include_fake_artist_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri="dummy:album:a", name="A", date="2001")],
            artists=[Artist(uri="dummy:artist:b", name="B")],
            tracks=[Track(uri="dummy:track:c", name="C")],
        )

        self.send_request('find "artist" "foo"')

        self.assertNotInResponse("file: dummy:artist:b")
        self.assertNotInResponse("Title: Artist: B")

        self.assertInResponse("file: dummy:album:a")
        self.assertInResponse("Title: Album: A")
        self.assertInResponse("Date: 2001")

        self.assertInResponse("file: dummy:track:c")
        self.assertInResponse("Title: C")

        self.assertInResponse("OK")

    def test_find_albumartist_does_not_include_fake_artist_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri="dummy:album:a", name="A", date="2001")],
            artists=[Artist(uri="dummy:artist:b", name="B")],
            tracks=[Track(uri="dummy:track:c", name="C")],
        )

        self.send_request('find "albumartist" "foo"')

        self.assertNotInResponse("file: dummy:artist:b")
        self.assertNotInResponse("Title: Artist: B")

        self.assertInResponse("file: dummy:album:a")
        self.assertInResponse("Title: Album: A")
        self.assertInResponse("Date: 2001")

        self.assertInResponse("file: dummy:track:c")
        self.assertInResponse("Title: C")

        self.assertInResponse("OK")

    def test_find_artist_and_album_does_not_include_fake_tracks(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            albums=[Album(uri="dummy:album:a", name="A", date="2001")],
            artists=[Artist(uri="dummy:artist:b", name="B")],
            tracks=[Track(uri="dummy:track:c", name="C")],
        )

        self.send_request('find "artist" "foo" "album" "bar"')

        self.assertNotInResponse("file: dummy:artist:b")
        self.assertNotInResponse("Title: Artist: B")

        self.assertNotInResponse("file: dummy:album:a")
        self.assertNotInResponse("Title: Album: A")
        self.assertNotInResponse("Date: 2001")

        self.assertInResponse("file: dummy:track:c")
        self.assertInResponse("Title: C")

        self.assertInResponse("OK")

    def test_find_album(self):
        self.send_request('find "album" "what"')
        self.assertInResponse("OK")

    def test_find_album_without_quotes(self):
        self.send_request('find album "what"')
        self.assertInResponse("OK")

    def test_find_artist(self):
        self.send_request('find "artist" "what"')
        self.assertInResponse("OK")

    def test_find_artist_without_quotes(self):
        self.send_request('find artist "what"')
        self.assertInResponse("OK")

    def test_find_albumartist(self):
        self.send_request('find "albumartist" "what"')
        self.assertInResponse("OK")

    def test_find_albumartist_without_quotes(self):
        self.send_request('find albumartist "what"')
        self.assertInResponse("OK")

    def test_find_composer(self):
        self.send_request('find "composer" "what"')
        self.assertInResponse("OK")

    def test_find_composer_without_quotes(self):
        self.send_request('find composer "what"')
        self.assertInResponse("OK")

    def test_find_performer(self):
        self.send_request('find "performer" "what"')
        self.assertInResponse("OK")

    def test_find_performer_without_quotes(self):
        self.send_request('find performer "what"')
        self.assertInResponse("OK")

    def test_find_filename(self):
        self.send_request('find "filename" "afilename"')
        self.assertInResponse("OK")

    def test_find_filename_without_quotes(self):
        self.send_request('find filename "afilename"')
        self.assertInResponse("OK")

    def test_find_file(self):
        self.send_request('find "file" "afilename"')
        self.assertInResponse("OK")

    def test_find_file_without_quotes(self):
        self.send_request('find file "afilename"')
        self.assertInResponse("OK")

    def test_find_title(self):
        self.send_request('find "title" "what"')
        self.assertInResponse("OK")

    def test_find_title_without_quotes(self):
        self.send_request('find title "what"')
        self.assertInResponse("OK")

    def test_find_track_no(self):
        self.send_request('find "track" "10"')
        self.assertInResponse("OK")

    def test_find_track_no_without_quotes(self):
        self.send_request('find track "10"')
        self.assertInResponse("OK")

    def test_find_track_no_without_filter_value(self):
        self.send_request('find "track" ""')
        self.assertInResponse("OK")

    def test_find_genre(self):
        self.send_request('find "genre" "what"')
        self.assertInResponse("OK")

    def test_find_genre_without_quotes(self):
        self.send_request('find genre "what"')
        self.assertInResponse("OK")

    def test_find_date(self):
        self.send_request('find "date" "2002-01-01"')
        self.assertInResponse("OK")

    def test_find_date_without_quotes(self):
        self.send_request('find date "2002-01-01"')
        self.assertInResponse("OK")

    def test_find_date_with_capital_d_and_incomplete_date(self):
        self.send_request('find Date "2005"')
        self.assertInResponse("OK")

    def test_find_else_should_fail(self):
        self.send_request('find "somethingelse" "what"')
        self.assertEqualResponse("ACK [2@0] {find} incorrect arguments")

    def test_find_album_and_artist(self):
        self.send_request('find album "album_what" artist "artist_what"')
        self.assertInResponse("OK")

    def test_find_without_filter_value(self):
        self.send_request('find "album" ""')
        self.assertInResponse("OK")


class MusicDatabaseListTest(protocol.BaseTestCase):
    def test_list(self):
        self.backend.library.dummy_get_distinct_result = {"artist": {"A Artist"}}
        self.send_request('list "artist" "artist" "foo"')

        self.assertInResponse("Artist: A Artist")
        self.assertInResponse("OK")

    def test_list_foo_returns_ack(self):
        self.send_request('list "foO"')
        self.assertEqualResponse("ACK [2@0] {list} Unknown tag type: foO")

    def test_list_without_type_returns_ack(self):
        self.send_request("list")
        self.assertEqualResponse('ACK [2@0] {list} too few arguments for "list"')

    def test_list_all_supported_fields(self):
        # Be nice to use pytest's parametrize here.
        fields = [
            "album",
            "albumartist",
            "artist",
            "comment",
            "composer",
            "date",
            "disc",
            "file",
            "filename",
            "genre",
            "musicbrainz_albumid",
            "musicbrainz_artistid",
            "musicbrainz_trackid",
            "performer",
            "title",
            "track",
        ]
        for field in fields:
            self.send_request(f'list "{field}"')
            self.assertInResponse("OK")

    # Track title

    def test_list_title(self):
        self.send_request('list "title"')
        self.assertInResponse("OK")

    def test_list_title_by_title(self):
        self.send_request('list "title" "title" "atitle"')
        self.assertInResponse("OK")

    # Artist

    def test_list_artist_with_quotes(self):
        self.send_request('list "artist"')
        self.assertInResponse("OK")

    def test_list_artist_without_quotes(self):
        self.send_request("list artist")
        self.assertInResponse("OK")

    def test_list_artist_without_quotes_and_capitalized(self):
        self.send_request("list Artist")
        self.assertInResponse("OK")

    def test_list_artist_with_query_of_one_token(self):
        self.send_request('list "artist" "anartist"')
        self.assertEqualResponse('ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_artist_with_unknown_field_in_query_returns_ack(self):
        self.send_request('list "artist" "foo" "bar"')
        self.assertEqualResponse("ACK [2@0] {list} Unknown filter type")

    def test_list_artist_by_artist(self):
        self.send_request('list "artist" "artist" "anartist"')
        self.assertInResponse("OK")

    def test_list_artist_by_album(self):
        self.send_request('list "artist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_artist_by_full_date(self):
        self.send_request('list "artist" "date" "2001-01-01"')
        self.assertInResponse("OK")

    def test_list_artist_by_year(self):
        self.send_request('list "artist" "date" "2001"')
        self.assertInResponse("OK")

    def test_list_artist_by_genre(self):
        self.send_request('list "artist" "genre" "agenre"')
        self.assertInResponse("OK")

    def test_list_artist_by_artist_and_album(self):
        self.send_request('list "artist" "artist" "anartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_artist_without_filter_value(self):
        self.send_request('list "artist" "artist" ""')
        self.assertInResponse("OK")

    def test_list_artist_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(artists=[Artist(name="")])]
        )

        self.send_request('list "artist"')
        self.assertNotInResponse("Artist: ")
        self.assertInResponse("OK")

    # Albumartist

    def test_list_albumartist_with_quotes(self):
        self.send_request('list "albumartist"')
        self.assertInResponse("OK")

    def test_list_albumartist_without_quotes(self):
        self.send_request("list albumartist")
        self.assertInResponse("OK")

    def test_list_albumartist_without_quotes_and_capitalized(self):
        self.send_request("list Albumartist")
        self.assertInResponse("OK")

    def test_list_albumartist_with_query_of_one_token(self):
        self.send_request('list "albumartist" "anartist"')
        self.assertEqualResponse('ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_albumartist_with_unknown_field_in_query_returns_ack(self):
        self.send_request('list "albumartist" "foo" "bar"')
        self.assertEqualResponse("ACK [2@0] {list} Unknown filter type")

    def test_list_albumartist_by_artist(self):
        self.send_request('list "albumartist" "artist" "anartist"')
        self.assertInResponse("OK")

    def test_list_albumartist_by_album(self):
        self.send_request('list "albumartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_albumartist_by_full_date(self):
        self.send_request('list "albumartist" "date" "2001-01-01"')
        self.assertInResponse("OK")

    def test_list_albumartist_by_year(self):
        self.send_request('list "albumartist" "date" "2001"')
        self.assertInResponse("OK")

    def test_list_albumartist_by_genre(self):
        self.send_request('list "albumartist" "genre" "agenre"')
        self.assertInResponse("OK")

    def test_list_albumartist_by_artist_and_album(self):
        self.send_request('list "albumartist" "artist" "anartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_albumartist_without_filter_value(self):
        self.send_request('list "albumartist" "artist" ""')
        self.assertInResponse("OK")

    def test_list_albumartist_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(album=Album(artists=[Artist(name="")]))]
        )

        self.send_request('list "albumartist"')
        self.assertNotInResponse("Artist: ")
        self.assertNotInResponse("Albumartist: ")
        self.assertNotInResponse("Composer: ")
        self.assertNotInResponse("Performer: ")
        self.assertInResponse("OK")

    # Composer

    def test_list_composer_with_quotes(self):
        self.send_request('list "composer"')
        self.assertInResponse("OK")

    def test_list_composer_without_quotes(self):
        self.send_request("list composer")
        self.assertInResponse("OK")

    def test_list_composer_without_quotes_and_capitalized(self):
        self.send_request("list Composer")
        self.assertInResponse("OK")

    def test_list_composer_with_query_of_one_token(self):
        self.send_request('list "composer" "anartist"')
        self.assertEqualResponse('ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_composer_with_unknown_field_in_query_returns_ack(self):
        self.send_request('list "composer" "foo" "bar"')
        self.assertEqualResponse("ACK [2@0] {list} Unknown filter type")

    def test_list_composer_by_artist(self):
        self.send_request('list "composer" "artist" "anartist"')
        self.assertInResponse("OK")

    def test_list_composer_by_album(self):
        self.send_request('list "composer" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_composer_by_full_date(self):
        self.send_request('list "composer" "date" "2001-01-01"')
        self.assertInResponse("OK")

    def test_list_composer_by_year(self):
        self.send_request('list "composer" "date" "2001"')
        self.assertInResponse("OK")

    def test_list_composer_by_genre(self):
        self.send_request('list "composer" "genre" "agenre"')
        self.assertInResponse("OK")

    def test_list_composer_by_artist_and_album(self):
        self.send_request('list "composer" "artist" "anartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_composer_without_filter_value(self):
        self.send_request('list "composer" "artist" ""')
        self.assertInResponse("OK")

    def test_list_composer_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(composers=[Artist(name="")])]
        )

        self.send_request('list "composer"')
        self.assertNotInResponse("Artist: ")
        self.assertNotInResponse("Albumartist: ")
        self.assertNotInResponse("Composer: ")
        self.assertNotInResponse("Performer: ")
        self.assertInResponse("OK")

    # Performer

    def test_list_performer_with_quotes(self):
        self.send_request('list "performer"')
        self.assertInResponse("OK")

    def test_list_performer_without_quotes(self):
        self.send_request("list performer")
        self.assertInResponse("OK")

    def test_list_performer_without_quotes_and_capitalized(self):
        self.send_request("list Albumartist")
        self.assertInResponse("OK")

    def test_list_performer_with_query_of_one_token(self):
        self.send_request('list "performer" "anartist"')
        self.assertEqualResponse('ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_performer_with_unknown_field_in_query_returns_ack(self):
        self.send_request('list "performer" "foo" "bar"')
        self.assertEqualResponse("ACK [2@0] {list} Unknown filter type")

    def test_list_performer_by_artist(self):
        self.send_request('list "performer" "artist" "anartist"')
        self.assertInResponse("OK")

    def test_list_performer_by_album(self):
        self.send_request('list "performer" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_performer_by_full_date(self):
        self.send_request('list "performer" "date" "2001-01-01"')
        self.assertInResponse("OK")

    def test_list_performer_by_year(self):
        self.send_request('list "performer" "date" "2001"')
        self.assertInResponse("OK")

    def test_list_performer_by_genre(self):
        self.send_request('list "performer" "genre" "agenre"')
        self.assertInResponse("OK")

    def test_list_performer_by_artist_and_album(self):
        self.send_request('list "performer" "artist" "anartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_performer_without_filter_value(self):
        self.send_request('list "performer" "artist" ""')
        self.assertInResponse("OK")

    def test_list_performer_should_not_return_artists_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(performers=[Artist(name="")])]
        )

        self.send_request('list "performer"')
        self.assertNotInResponse("Artist: ")
        self.assertNotInResponse("Albumartist: ")
        self.assertNotInResponse("Composer: ")
        self.assertNotInResponse("Performer: ")
        self.assertInResponse("OK")

    # Album

    def test_list_album_with_quotes(self):
        self.send_request('list "album"')
        self.assertInResponse("OK")

    def test_list_album_without_quotes(self):
        self.send_request("list album")
        self.assertInResponse("OK")

    def test_list_album_without_quotes_and_capitalized(self):
        self.send_request("list Album")
        self.assertInResponse("OK")

    def test_list_album_with_artist_name(self):
        self.backend.library.dummy_get_distinct_result = {"album": {"foo"}}

        self.send_request('list "album" "anartist"')
        self.assertInResponse("Album: foo")
        self.assertInResponse("OK")

    def test_list_album_with_artist_name_without_filter_value(self):
        self.send_request('list "album" ""')
        self.assertInResponse("OK")

    def test_list_album_by_artist(self):
        self.send_request('list "album" "artist" "anartist"')
        self.assertInResponse("OK")

    def test_list_album_by_album(self):
        self.send_request('list "album" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_album_by_albumartist(self):
        self.send_request('list "album" "albumartist" "anartist"')
        self.assertInResponse("OK")

    def test_list_album_by_composer(self):
        self.send_request('list "album" "composer" "anartist"')
        self.assertInResponse("OK")

    def test_list_album_by_performer(self):
        self.send_request('list "album" "performer" "anartist"')
        self.assertInResponse("OK")

    def test_list_album_by_full_date(self):
        self.send_request('list "album" "date" "2001-01-01"')
        self.assertInResponse("OK")

    def test_list_album_by_year(self):
        self.send_request('list "album" "date" "2001"')
        self.assertInResponse("OK")

    def test_list_album_by_genre(self):
        self.send_request('list "album" "genre" "agenre"')
        self.assertInResponse("OK")

    def test_list_album_by_artist_and_album(self):
        self.send_request('list "album" "artist" "anartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_album_without_filter_value(self):
        self.send_request('list "album" "artist" ""')
        self.assertInResponse("OK")

    def test_list_album_should_not_return_albums_without_names(self):
        self.backend.library.dummy_find_exact_result = SearchResult(
            tracks=[Track(album=Album(name=""))]
        )

        self.send_request('list "album"')
        self.assertNotInResponse("Album: ")
        self.assertInResponse("OK")

    # Date

    def test_list_date_with_quotes(self):
        self.send_request('list "date"')
        self.assertInResponse("OK")

    def test_list_date_without_quotes(self):
        self.send_request("list date")
        self.assertInResponse("OK")

    def test_list_date_without_quotes_and_capitalized(self):
        self.send_request("list Date")
        self.assertInResponse("OK")

    def test_list_date_with_query_of_one_token(self):
        self.send_request('list "date" "anartist"')
        self.assertEqualResponse('ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_date_by_artist(self):
        self.send_request('list "date" "artist" "anartist"')
        self.assertInResponse("OK")

    def test_list_date_by_album(self):
        self.send_request('list "date" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_date_by_full_date(self):
        self.send_request('list "date" "date" "2001-01-01"')
        self.assertInResponse("OK")

    def test_list_date_by_year(self):
        self.send_request('list "date" "date" "2001"')
        self.assertInResponse("OK")

    def test_list_date_by_genre(self):
        self.send_request('list "date" "genre" "agenre"')
        self.assertInResponse("OK")

    def test_list_date_by_artist_and_album(self):
        self.send_request('list "date" "artist" "anartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_date_without_filter_value(self):
        self.send_request('list "date" "artist" ""')
        self.assertInResponse("OK")

    # Genre

    def test_list_genre_with_quotes(self):
        self.send_request('list "genre"')
        self.assertInResponse("OK")

    def test_list_genre_without_quotes(self):
        self.send_request("list genre")
        self.assertInResponse("OK")

    def test_list_genre_without_quotes_and_capitalized(self):
        self.send_request("list Genre")
        self.assertInResponse("OK")

    def test_list_genre_with_query_of_one_token(self):
        self.send_request('list "genre" "anartist"')
        self.assertEqualResponse('ACK [2@0] {list} should be "Album" for 3 arguments')

    def test_list_genre_by_artist(self):
        self.send_request('list "genre" "artist" "anartist"')
        self.assertInResponse("OK")

    def test_list_genre_by_album(self):
        self.send_request('list "genre" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_genre_by_full_date(self):
        self.send_request('list "genre" "date" "2001-01-01"')
        self.assertInResponse("OK")

    def test_list_genre_by_year(self):
        self.send_request('list "genre" "date" "2001"')
        self.assertInResponse("OK")

    def test_list_genre_by_genre(self):
        self.send_request('list "genre" "genre" "agenre"')
        self.assertInResponse("OK")

    def test_list_genre_by_artist_and_album(self):
        self.send_request('list "genre" "artist" "anartist" "album" "analbum"')
        self.assertInResponse("OK")

    def test_list_genre_without_filter_value(self):
        self.send_request('list "genre" "artist" ""')
        self.assertInResponse("OK")


class MusicDatabaseSearchTest(protocol.BaseTestCase):
    def test_search(self):
        self.backend.library.dummy_search_result = SearchResult(
            albums=[Album(uri="dummy:album:a", name="A")],
            artists=[Artist(uri="dummy:artist:b", name="B")],
            tracks=[Track(uri="dummy:track:c", name="C")],
        )

        self.send_request('search "any" "foo"')

        self.assertInResponse("file: dummy:album:a")
        self.assertInResponse("Title: Album: A")
        self.assertInResponse("file: dummy:artist:b")
        self.assertInResponse("Title: Artist: B")
        self.assertInResponse("file: dummy:track:c")
        self.assertInResponse("Title: C")

        self.assertInResponse("OK")

    def test_search_album(self):
        self.send_request('search "album" "analbum"')
        self.assertInResponse("OK")

    def test_search_album_without_quotes(self):
        self.send_request('search album "analbum"')
        self.assertInResponse("OK")

    def test_search_album_without_filter_value(self):
        self.send_request('search "album" ""')
        self.assertInResponse("OK")

    def test_search_artist(self):
        self.send_request('search "artist" "anartist"')
        self.assertInResponse("OK")

    def test_search_artist_without_quotes(self):
        self.send_request('search artist "anartist"')
        self.assertInResponse("OK")

    def test_search_artist_without_filter_value(self):
        self.send_request('search "artist" ""')
        self.assertInResponse("OK")

    def test_search_albumartist(self):
        self.send_request('search "albumartist" "analbumartist"')
        self.assertInResponse("OK")

    def test_search_albumartist_without_quotes(self):
        self.send_request('search albumartist "analbumartist"')
        self.assertInResponse("OK")

    def test_search_albumartist_without_filter_value(self):
        self.send_request('search "albumartist" ""')
        self.assertInResponse("OK")

    def test_search_composer(self):
        self.send_request('search "composer" "acomposer"')
        self.assertInResponse("OK")

    def test_search_composer_without_quotes(self):
        self.send_request('search composer "acomposer"')
        self.assertInResponse("OK")

    def test_search_composer_without_filter_value(self):
        self.send_request('search "composer" ""')
        self.assertInResponse("OK")

    def test_search_performer(self):
        self.send_request('search "performer" "aperformer"')
        self.assertInResponse("OK")

    def test_search_performer_without_quotes(self):
        self.send_request('search performer "aperformer"')
        self.assertInResponse("OK")

    def test_search_performer_without_filter_value(self):
        self.send_request('search "performer" ""')
        self.assertInResponse("OK")

    def test_search_filename(self):
        self.send_request('search "filename" "afilename"')
        self.assertInResponse("OK")

    def test_search_filename_without_quotes(self):
        self.send_request('search filename "afilename"')
        self.assertInResponse("OK")

    def test_search_filename_without_filter_value(self):
        self.send_request('search "filename" ""')
        self.assertInResponse("OK")

    def test_search_file(self):
        self.send_request('search "file" "afilename"')
        self.assertInResponse("OK")

    def test_search_file_without_quotes(self):
        self.send_request('search file "afilename"')
        self.assertInResponse("OK")

    def test_search_file_without_filter_value(self):
        self.send_request('search "file" ""')
        self.assertInResponse("OK")

    def test_search_title(self):
        self.send_request('search "title" "atitle"')
        self.assertInResponse("OK")

    def test_search_title_without_quotes(self):
        self.send_request('search title "atitle"')
        self.assertInResponse("OK")

    def test_search_title_without_filter_value(self):
        self.send_request('search "title" ""')
        self.assertInResponse("OK")

    def test_search_any(self):
        self.send_request('search "any" "anything"')
        self.assertInResponse("OK")

    def test_search_any_without_quotes(self):
        self.send_request('search any "anything"')
        self.assertInResponse("OK")

    def test_search_any_without_filter_value(self):
        self.send_request('search "any" ""')
        self.assertInResponse("OK")

    def test_search_track_no(self):
        self.send_request('search "track" "10"')
        self.assertInResponse("OK")

    def test_search_track_no_without_quotes(self):
        self.send_request('search track "10"')
        self.assertInResponse("OK")

    def test_search_track_no_without_filter_value(self):
        self.send_request('search "track" ""')
        self.assertInResponse("OK")

    def test_search_genre(self):
        self.send_request('search "genre" "agenre"')
        self.assertInResponse("OK")

    def test_search_genre_without_quotes(self):
        self.send_request('search genre "agenre"')
        self.assertInResponse("OK")

    def test_search_genre_without_filter_value(self):
        self.send_request('search "genre" ""')
        self.assertInResponse("OK")

    def test_search_date(self):
        self.send_request('search "date" "2002-01-01"')
        self.assertInResponse("OK")

    def test_search_date_without_quotes(self):
        self.send_request('search date "2002-01-01"')
        self.assertInResponse("OK")

    def test_search_date_with_capital_d_and_incomplete_date(self):
        self.send_request('search Date "2005"')
        self.assertInResponse("OK")

    def test_search_date_without_filter_value(self):
        self.send_request('search "date" ""')
        self.assertInResponse("OK")

    def test_search_comment(self):
        self.send_request('search "comment" "acomment"')
        self.assertInResponse("OK")

    def test_search_comment_without_quotes(self):
        self.send_request('search comment "acomment"')
        self.assertInResponse("OK")

    def test_search_comment_without_filter_value(self):
        self.send_request('search "comment" ""')
        self.assertInResponse("OK")

    def test_search_else_should_fail(self):
        self.send_request('search "sometype" "something"')
        self.assertEqualResponse("ACK [2@0] {search} incorrect arguments")
