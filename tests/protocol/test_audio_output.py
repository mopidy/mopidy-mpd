from tests import protocol


class AudioOutputHandlerTest(protocol.BaseTestCase):
    def test_enableoutput(self):
        self.core.mixer.set_mute(False)

        self.send_request('enableoutput "0"')

        self.assertInResponse("OK")
        assert self.core.mixer.get_mute().get() is True

    def test_enableoutput_unknown_outputid(self):
        self.send_request('enableoutput "7"')

        self.assertInResponse("ACK [50@0] {enableoutput} No such audio output")

    def test_disableoutput(self):
        self.core.mixer.set_mute(True)

        self.send_request('disableoutput "0"')

        self.assertInResponse("OK")
        assert self.core.mixer.get_mute().get() is False

    def test_disableoutput_unknown_outputid(self):
        self.send_request('disableoutput "7"')

        self.assertInResponse("ACK [50@0] {disableoutput} No such audio output")

    def test_outputs_when_unmuted(self):
        self.core.mixer.set_mute(False)

        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 0")
        self.assertInResponse("OK")

    def test_outputs_when_muted(self):
        self.core.mixer.set_mute(True)

        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 1")
        self.assertInResponse("OK")

    def test_outputs_toggleoutput(self):
        self.core.mixer.set_mute(False)

        self.send_request('toggleoutput "0"')
        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 1")
        self.assertInResponse("OK")

        self.send_request('toggleoutput "0"')
        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 0")
        self.assertInResponse("OK")

        self.send_request('toggleoutput "0"')
        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 1")
        self.assertInResponse("OK")

    def test_outputs_toggleoutput_unknown_outputid(self):
        self.send_request('toggleoutput "7"')

        self.assertInResponse("ACK [50@0] {toggleoutput} No such audio output")


class AudioOutputHandlerNoneMixerTest(protocol.BaseTestCase):
    enable_mixer = False

    def test_enableoutput(self):
        assert self.core.mixer.get_mute().get() is None

        self.send_request('enableoutput "0"')
        self.assertInResponse("ACK [52@0] {enableoutput} problems enabling output")

        assert self.core.mixer.get_mute().get() is None

    def test_disableoutput(self):
        assert self.core.mixer.get_mute().get() is None

        self.send_request('disableoutput "0"')
        self.assertInResponse("ACK [52@0] {disableoutput} problems disabling output")

        assert self.core.mixer.get_mute().get() is None

    def test_outputs_when_unmuted(self):
        self.core.mixer.set_mute(False)

        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 0")
        self.assertInResponse("OK")

    def test_outputs_when_muted(self):
        self.core.mixer.set_mute(True)

        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 0")
        self.assertInResponse("OK")

    def test_outputs_toggleoutput(self):
        self.core.mixer.set_mute(False)

        self.send_request('toggleoutput "0"')
        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 0")
        self.assertInResponse("OK")

        self.send_request('toggleoutput "0"')
        self.send_request("outputs")

        self.assertInResponse("outputid: 0")
        self.assertInResponse("outputname: Mute")
        self.assertInResponse("outputenabled: 0")
        self.assertInResponse("OK")
