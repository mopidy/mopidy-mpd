import unittest

from mopidy.core import PlaybackState
from mopidy.models import Track

from tests import protocol

PAUSED = PlaybackState.PAUSED
PLAYING = PlaybackState.PLAYING
STOPPED = PlaybackState.STOPPED


class PlaybackOptionsHandlerTest(protocol.BaseTestCase):
    def test_consume_off(self):
        self.send_request('consume "0"')
        assert not self.core.tracklist.get_consume().get()
        self.assertInResponse("OK")

    def test_consume_off_without_quotes(self):
        self.send_request("consume 0")
        assert not self.core.tracklist.get_consume().get()
        self.assertInResponse("OK")

    def test_consume_on(self):
        self.send_request('consume "1"')
        assert self.core.tracklist.get_consume().get()
        self.assertInResponse("OK")

    def test_consume_on_without_quotes(self):
        self.send_request("consume 1")
        assert self.core.tracklist.get_consume().get()
        self.assertInResponse("OK")

    def test_crossfade(self):
        self.send_request('crossfade "10"')
        self.assertInResponse("ACK [0@0] {crossfade} Not implemented")

    def test_random_off(self):
        self.send_request('random "0"')
        assert not self.core.tracklist.get_random().get()
        self.assertInResponse("OK")

    def test_random_off_without_quotes(self):
        self.send_request("random 0")
        assert not self.core.tracklist.get_random().get()
        self.assertInResponse("OK")

    def test_random_on(self):
        self.send_request('random "1"')
        assert self.core.tracklist.get_random().get()
        self.assertInResponse("OK")

    def test_random_on_without_quotes(self):
        self.send_request("random 1")
        assert self.core.tracklist.get_random().get()
        self.assertInResponse("OK")

    def test_repeat_off(self):
        self.send_request('repeat "0"')
        assert not self.core.tracklist.get_repeat().get()
        self.assertInResponse("OK")

    def test_repeat_off_without_quotes(self):
        self.send_request("repeat 0")
        assert not self.core.tracklist.get_repeat().get()
        self.assertInResponse("OK")

    def test_repeat_on(self):
        self.send_request('repeat "1"')
        assert self.core.tracklist.get_repeat().get()
        self.assertInResponse("OK")

    def test_repeat_on_without_quotes(self):
        self.send_request("repeat 1")
        assert self.core.tracklist.get_repeat().get()
        self.assertInResponse("OK")

    def test_single_off(self):
        self.send_request('single "0"')
        assert not self.core.tracklist.get_single().get()
        self.assertInResponse("OK")

    def test_single_off_without_quotes(self):
        self.send_request("single 0")
        assert not self.core.tracklist.get_single().get()
        self.assertInResponse("OK")

    def test_single_on(self):
        self.send_request('single "1"')
        assert self.core.tracklist.get_single().get()
        self.assertInResponse("OK")

    def test_single_on_without_quotes(self):
        self.send_request("single 1")
        assert self.core.tracklist.get_single().get()
        self.assertInResponse("OK")

    def test_replay_gain_mode_off(self):
        self.send_request('replay_gain_mode "off"')
        self.assertInResponse("ACK [0@0] {replay_gain_mode} Not implemented")

    def test_replay_gain_mode_track(self):
        self.send_request('replay_gain_mode "track"')
        self.assertInResponse("ACK [0@0] {replay_gain_mode} Not implemented")

    def test_replay_gain_mode_album(self):
        self.send_request('replay_gain_mode "album"')
        self.assertInResponse("ACK [0@0] {replay_gain_mode} Not implemented")

    def test_replay_gain_status_default(self):
        self.send_request("replay_gain_status")
        self.assertInResponse("OK")
        self.assertInResponse("replay_gain_mode: off")

    def test_mixrampdb(self):
        self.send_request('mixrampdb "10"')
        self.assertInResponse("ACK [0@0] {mixrampdb} Not implemented")

    def test_mixrampdelay(self):
        self.send_request('mixrampdelay "10"')
        self.assertInResponse("ACK [0@0] {mixrampdelay} Not implemented")

    @unittest.SkipTest
    def test_replay_gain_status_off(self):
        pass

    @unittest.SkipTest
    def test_replay_gain_status_track(self):
        pass

    @unittest.SkipTest
    def test_replay_gain_status_album(self):
        pass


class PlaybackControlHandlerTest(protocol.BaseTestCase):
    def setUp(self):
        super().setUp()
        self.tracks = [
            Track(uri="dummy:a", length=40000),
            Track(uri="dummy:b", length=40000),
        ]
        self.backend.library.dummy_library = self.tracks
        self.core.tracklist.add(uris=[t.uri for t in self.tracks]).get()

    def test_next(self):
        self.core.tracklist.clear().get()
        self.send_request("next")
        self.assertInResponse("OK")

    def test_pause_off(self):
        self.send_request('play "0"')
        self.send_request('pause "1"')
        self.send_request('pause "0"')
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

    def test_pause_on(self):
        self.send_request('play "0"')
        self.send_request('pause "1"')
        assert self.core.playback.get_state().get() == PAUSED
        self.assertInResponse("OK")

    def test_pause_toggle(self):
        self.send_request('play "0"')
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

        # Deprecated version
        self.send_request("pause")
        assert self.core.playback.get_state().get() == PAUSED
        self.assertInResponse("OK")
        self.send_request("pause")
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

    def test_play_without_pos(self):
        self.send_request("play")
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

    def test_play_with_pos(self):
        self.send_request('play "0"')
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

    def test_play_with_pos_without_quotes(self):
        self.send_request("play 0")
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

    def test_play_with_pos_out_of_bounds(self):
        self.core.tracklist.clear().get()
        self.send_request('play "0"')
        assert self.core.playback.get_state().get() == STOPPED
        self.assertInResponse("ACK [2@0] {play} Bad song index")

    def test_play_minus_one_plays_first_in_playlist_if_no_current_track(self):
        assert self.core.playback.get_current_track().get() is None

        self.send_request('play "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_current_track().get().uri == "dummy:a"
        self.assertInResponse("OK")

    def test_play_minus_one_plays_current_track_if_current_track_is_set(self):
        assert self.core.playback.get_current_track().get() is None
        self.core.playback.play()
        self.core.playback.next()
        self.core.playback.stop().get()
        assert self.core.playback.get_current_track().get() is not None

        self.send_request('play "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_current_track().get().uri == "dummy:b"
        self.assertInResponse("OK")

    def test_play_minus_one_on_empty_playlist_does_not_ack(self):
        self.core.tracklist.clear()

        self.send_request('play "-1"')
        assert self.core.playback.get_state().get() == STOPPED
        assert self.core.playback.get_current_track().get() is None
        self.assertInResponse("OK")

    def test_play_minus_is_ignored_if_playing(self):
        self.core.playback.play().get()
        self.core.playback.seek(30000)
        assert self.core.playback.get_time_position().get() >= 30000
        assert self.core.playback.get_state().get() == PLAYING

        self.send_request('play "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_play_minus_one_resumes_if_paused(self):
        self.core.playback.play().get()
        self.core.playback.seek(30000)
        assert self.core.playback.get_time_position().get() >= 30000
        assert self.core.playback.get_state().get() == PLAYING
        self.core.playback.pause()
        assert self.core.playback.get_state().get() == PAUSED

        self.send_request('play "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_playid(self):
        self.send_request('playid "1"')
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

    def test_playid_without_quotes(self):
        self.send_request("playid 1")
        assert self.core.playback.get_state().get() == PLAYING
        self.assertInResponse("OK")

    def test_playid_minus_1_plays_first_in_playlist_if_no_current_track(self):
        assert self.core.playback.get_current_track().get() is None

        self.send_request('playid "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_current_track().get().uri == "dummy:a"
        self.assertInResponse("OK")

    def test_playid_minus_1_plays_current_track_if_current_track_is_set(self):
        assert self.core.playback.get_current_track().get() is None
        self.core.playback.play().get()
        self.core.playback.next().get()
        self.core.playback.stop()
        assert self.core.playback.get_current_track().get() is not None

        self.send_request('playid "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_current_track().get().uri == "dummy:b"
        self.assertInResponse("OK")

    def test_playid_minus_one_on_empty_playlist_does_not_ack(self):
        self.core.tracklist.clear()

        self.send_request('playid "-1"')
        assert self.core.playback.get_state().get() == STOPPED
        assert self.core.playback.get_current_track().get() is None
        self.assertInResponse("OK")

    def test_playid_minus_is_ignored_if_playing(self):
        self.core.playback.play().get()
        self.core.playback.seek(30000)
        assert self.core.playback.get_time_position().get() >= 30000
        assert self.core.playback.get_state().get() == PLAYING

        self.send_request('playid "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_playid_minus_one_resumes_if_paused(self):
        self.core.playback.play().get()
        self.core.playback.seek(30000)
        assert self.core.playback.get_time_position().get() >= 30000
        assert self.core.playback.get_state().get() == PLAYING
        self.core.playback.pause()
        assert self.core.playback.get_state().get() == PAUSED

        self.send_request('playid "-1"')
        assert self.core.playback.get_state().get() == PLAYING
        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_playid_which_does_not_exist(self):
        self.send_request('playid "12345"')
        self.assertInResponse("ACK [50@0] {playid} No such song")

    def test_previous(self):
        self.core.tracklist.clear().get()
        self.send_request("previous")
        self.assertInResponse("OK")

    def test_seek_in_current_track(self):
        self.core.playback.play()

        self.send_request('seek "0" "30"')

        current_track = self.core.playback.get_current_track().get()
        assert current_track == self.tracks[0]
        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_seek_in_another_track(self):
        self.core.playback.play()
        current_track = self.core.playback.get_current_track().get()
        assert current_track != self.tracks[1]

        self.send_request('seek "1" "30"')

        current_track = self.core.playback.get_current_track().get()
        assert current_track == self.tracks[1]
        self.assertInResponse("OK")

    def test_seek_without_quotes(self):
        self.core.playback.play()

        self.send_request("seek 0 30")
        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_seek_with_float(self):
        self.core.playback.play()

        self.send_request('seek "0" "30.1"')
        assert self.core.playback.get_time_position().get() >= 30100
        self.assertInResponse("OK")

    def test_seekid_in_current_track(self):
        self.core.playback.play()

        self.send_request('seekid "1" "30"')

        current_track = self.core.playback.get_current_track().get()
        assert current_track == self.tracks[0]
        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_seekid_in_another_track(self):
        self.core.playback.play()

        self.send_request('seekid "2" "30"')

        current_tl_track = self.core.playback.get_current_tl_track().get()
        assert current_tl_track.tlid == 2
        assert current_tl_track.track == self.tracks[1]
        self.assertInResponse("OK")

    def test_seekid_with_float(self):
        self.core.playback.play()

        self.send_request('seekid "1" "30.1"')

        current_track = self.core.playback.get_current_track().get()
        assert current_track == self.tracks[0]
        assert self.core.playback.get_time_position().get() >= 30100
        self.assertInResponse("OK")

    def test_seekcur_absolute_value(self):
        self.core.playback.play().get()

        self.send_request('seekcur "30"')

        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_seekcur_positive_diff(self):
        self.core.playback.play().get()
        self.core.playback.seek(10000)
        assert self.core.playback.get_time_position().get() >= 10000

        self.send_request('seekcur "+20"')

        assert self.core.playback.get_time_position().get() >= 30000
        self.assertInResponse("OK")

    def test_seekcur_negative_diff(self):
        self.core.playback.play().get()
        self.core.playback.seek(30000)
        assert self.core.playback.get_time_position().get() >= 30000

        self.send_request('seekcur "-20"')

        assert self.core.playback.get_time_position().get() <= 15000
        self.assertInResponse("OK")

    def test_seekcur_absolute_float(self):
        self.core.playback.play().get()

        self.send_request('seekcur "30.1"')

        assert self.core.playback.get_time_position().get() >= 30100
        self.assertInResponse("OK")

    def test_seekcur_negative_float(self):
        self.core.playback.play().get()
        self.core.playback.seek(30000)
        assert self.core.playback.get_time_position().get() >= 30000

        self.send_request('seekcur "-20.1"')

        assert self.core.playback.get_time_position().get() <= 10000
        self.assertInResponse("OK")

    def test_stop(self):
        self.core.tracklist.clear().get()
        self.send_request("stop")
        assert self.core.playback.get_state().get() == STOPPED
        self.assertInResponse("OK")


class VolumeTest(protocol.BaseTestCase):
    def test_setvol_below_min(self):
        self.send_request('setvol "-10"')
        assert self.core.mixer.get_volume().get() == 0
        self.assertInResponse("OK")

    def test_setvol_min(self):
        self.send_request('setvol "0"')
        assert self.core.mixer.get_volume().get() == 0
        self.assertInResponse("OK")

    def test_setvol_middle(self):
        self.send_request('setvol "50"')
        assert self.core.mixer.get_volume().get() == 50
        self.assertInResponse("OK")

    def test_setvol_max(self):
        self.send_request('setvol "100"')
        assert self.core.mixer.get_volume().get() == 100
        self.assertInResponse("OK")

    def test_setvol_above_max(self):
        self.send_request('setvol "110"')
        assert self.core.mixer.get_volume().get() == 100
        self.assertInResponse("OK")

    def test_setvol_plus_is_ignored(self):
        self.send_request('setvol "+10"')
        assert self.core.mixer.get_volume().get() == 10
        self.assertInResponse("OK")

    def test_setvol_without_quotes(self):
        self.send_request("setvol 50")
        assert self.core.mixer.get_volume().get() == 50
        self.assertInResponse("OK")

    def test_volume_plus(self):
        self.core.mixer.set_volume(50)

        self.send_request("volume +20")

        assert self.core.mixer.get_volume().get() == 70
        self.assertInResponse("OK")

    def test_volume_minus(self):
        self.core.mixer.set_volume(50)

        self.send_request("volume -20")

        assert self.core.mixer.get_volume().get() == 30
        self.assertInResponse("OK")

    def test_volume_less_than_minus_100(self):
        self.core.mixer.set_volume(50)

        self.send_request("volume -110")

        assert self.core.mixer.get_volume().get() == 50
        self.assertInResponse("ACK [2@0] {volume} Invalid volume value")

    def test_volume_more_than_plus_100(self):
        self.core.mixer.set_volume(50)

        self.send_request("volume +110")

        assert self.core.mixer.get_volume().get() == 50
        self.assertInResponse("ACK [2@0] {volume} Invalid volume value")


class VolumeWithNoMixerTest(protocol.BaseTestCase):
    enable_mixer = False

    def test_setvol_without_mixer_fails(self):
        self.send_request('setvol "100"')
        self.assertInResponse("ACK [52@0] {setvol} problems setting volume")

    def test_volume_without_mixer_failes(self):
        self.send_request("volume +100")
        self.assertInResponse("ACK [52@0] {volume} problems setting volume")
