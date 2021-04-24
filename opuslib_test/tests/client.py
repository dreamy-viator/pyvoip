

from audio_out import AudioOutput
from mic import MicDevice
from rtp_client import RTPReceiveClient, RTPSendClient
import pyaudio

import opuslib
import numpy as np

class Client:
    SAMPLE_RATE = 16000
    #CHUNK_SIZE = 4096

    def __init__(
            self,
            remote_host_address,
            remote_host_port,
            host_address,
            rtp_port):
        self.CHUNK_SIZE = 960 #640 #320
        self.mic = MicDevice(sr=self.SAMPLE_RATE,
                             chunk_size=self.CHUNK_SIZE)

        self.sender = RTPSendClient(remote_host_address=remote_host_address,
                                    remote_host_port=remote_host_port)

        self.receiver = RTPReceiveClient(host_address=host_address,
                                         rtp_port=rtp_port)
        self.opus_encode = opuslib.Encoder(self.SAMPLE_RATE, 1, opuslib.APPLICATION_VOIP)
        self.opus_decode = opuslib.Decoder(self.SAMPLE_RATE, 1)

        self.aout = AudioOutput()
        self.frame_count = 0
        self.start_ts = -1.0
        print('init client')

    def _callback(self, in_data, frame_count, time_info, status):
        timestamp = time_info['input_buffer_adc_time']
        if self.start_ts == -1:
            self.start_ts = timestamp

        ts = timestamp - self.start_ts
        ts = int(ts * 1000 * 1000)  #microseconds

        """ add opus """
        encoded = self.opus_encode.encode(pcm_data=in_data, frame_size=self.CHUNK_SIZE)

        self.sender.send_audio(
            data=encoded,
            ts=ts,
            frame_count=self.frame_count)

        self.frame_count += 1
        return (None, pyaudio.paContinue)

    def _receive_callback(self, audio):
        decoded = self.opus_decode.decode(audio, frame_size=self.CHUNK_SIZE)
        self.aout.write(decoded)

    def start_calling(self):
        self.sender.start()
        self.receiver.start(self._receive_callback)
        # mic
        self.mic.start(self._callback)
        # audio output
        self.aout.open()
        self.aout.start()

        print('start calling ...')

    def stop_calling(self):
        # TODO
        print('stop calling')

