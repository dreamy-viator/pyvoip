
import pyaudio

class AudioOutput:
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    RATE = 16000

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.is_running = False

    def __del__(self):
        self.close()
        self.p.terminate()

    def open(self):
        self.stream = self.p.open(format=self.FORMAT,
                                  channels=self.CHANNELS,
                                  rate=self.RATE,
                                  output=True)

    def start(self):
        self.stream.start_stream()
        self.is_running = True

    def stop(self):
        self.stream.stop_stream()
        self.is_running = False

    def close(self):
        self.stop()
        self.stream.close()


    def write(self, data):
        if self.is_running:
            self.stream.write(data)




if __name__ == '__main__':
    import wave

    #Example Usage of AudioOutput
    ao = AudioOutput()
    ao.open()
    ao.start()

    wave_path = 'resources/myvoice.wav'
    chunk = 1024
    af = wave.open(wave_path, 'rb')
    data = af.readframes(chunk)

    while data != '':
        ao.write(data)
        data = af.readframes(chunk)

    ao.stop()
    ao.close()


