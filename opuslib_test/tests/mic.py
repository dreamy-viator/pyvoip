import pyaudio
import time


class MicDevice:
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 960 #640 #320

    def __init__(self, sr=RATE,
                 chunk_size=CHUNK):

        self.p = pyaudio.PyAudio()
        self.RATE = sr
        self.CHUNK = chunk_size

    def __del__(self):
        self.stop()
        self.p.terminate()


    def start(self, callback):
        self.stream = self.p.open(format=self.FORMAT,
                                  channels=self.CHANNELS,
                                  rate=self.RATE,
                                  input=True,
                                  frames_per_buffer=self.CHUNK,
                                  stream_callback=callback)

        self.stream.start_stream()


    def stop(self):
        self.stream.stop_stream()
        self.stream.close()


if __name__ == "__main__":
    # Example usage of MicDevice
    def callback(in_data, frame_count, time_info, status):
        print(len(in_data), frame_count, time_info, status)
        return (None, pyaudio.paContinue)

    m = MicDevice()
    m.start(callback)

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        m.stop()
        pass