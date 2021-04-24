

from audio_out import AudioOutput
from mic import MicDevice
from rtp_client import RTPReceiveClient, RTPSendClient
import pyaudio
import aioice
import websockets
import json
import asyncio
import threading
from rtp.rtp_packet import RTPPacket
import opuslib


class Client:
    SAMPLE_RATE = 16000
    STUN_SERVER = ("stun.l.google.com", 19302)
    SIGNAL_SERVER = 'ws://47.242.210.177:8765'

    def __init__(
            self,
            remote_host_address,
            remote_host_port,
            host_address,
            rtp_port):


        self.queue = []
        self.CHUNK_SIZE = 960

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
        self.lock = threading.Lock()
        print('init client')

    def _callback(self, in_data, frame_count, time_info, status):
        timestamp = time_info['input_buffer_adc_time']
        if self.start_ts == -1:
            self.start_ts = timestamp

        ts = timestamp - self.start_ts
        ts = int(ts * 1000 * 1000)  #microseconds

        """ add opus """
        encoded = self.opus_encode.encode(pcm_data=in_data, frame_size=self.CHUNK_SIZE)
        packet = self.sender.send_audio_packet(
            data=encoded,
            ts=ts,
            frame_count=self.frame_count)

        with self.lock:
            self.queue.append(packet)
        self.frame_count += 1
        return (None, pyaudio.paContinue)

    def _receive_callback(self, audio):
        decoded = self.opus_decode.decode(audio, frame_size=self.CHUNK_SIZE)
        self.aout.write(decoded)


    def send_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self.send())
        loop.close()


    def start_calling(self, roomId):
        self.roomId = roomId
        asyncio.get_event_loop().run_until_complete(self.init_singaling())
        asyncio.get_event_loop().run_until_complete(self.get_remote())
        self.sender.start()

        self.mic.start(self._callback)
        self.aout.open()
        self.aout.start()
        thread = threading.Thread(target=self.send_thread)
        thread.start()
        asyncio.get_event_loop().run_until_complete(self.answer())
        thread.join()
        print('start calling ...')

    def stop_calling(self):
        # TODO
        print('stop calling')


    async def get_remote(self):
        active_pair = self.connection._nominated.get(1)
        if active_pair:
            self.remote = active_pair.remote_addr
            self.sender._remote_address = self.remote
            print(self.remote)
        else:
            raise ConnectionError("Cannot send data, not connected")

    async def send(self):
        component = 1
        while True:
            with self.lock:
                if len(self.queue):
                    packet = self.queue.pop()
                else:
                    continue
                # print("sending %s on component %d" % (repr(packet), component))
                await self.connection.sendto(packet, component)

    async def answer(self):
        # echo data back
        while True:
            data, component = await self.connection.recvfrom()
            # print("echoing %s on component %d" % (repr(data), component))
            packet = RTPPacket.from_packet(data)
            audio_data = packet.payload
            print("received", len(audio_data))
            self._receive_callback(audio_data)
            # await asyncio.sleep(1)



    async def init_singaling(self):
        connection = aioice.Connection(
            ice_controlling=True, components=1, stun_server=self.STUN_SERVER
        )
        self.connection = connection
        websocket = await websockets.connect(self.SIGNAL_SERVER)
        joinCmd = json.dumps({
            "cmd": "joinRoom",
            "roomId": self.roomId
        })
        await websocket.send(joinCmd)
        print("> {}".format(joinCmd))

        response = await websocket.recv()
        print("< {}".format(response))

        resp = json.loads(response)
        respCmd = resp["cmd"]
        if respCmd == "playStream":
            print('playstream cmd received')
            await connection.gather_candidates()
            await websocket.send(
                json.dumps(
                    {
                        "cmd": "candidate",
                        "candidates": [c.to_sdp() for c in connection.local_candidates],
                        "password": connection.local_password,
                        "username": connection.local_username,
                    }
                )
            )
            response = await websocket.recv()
            print("< {}".format(response))

            resp = json.loads(response)
            for c in resp["candidates"]:
                await connection.add_remote_candidate(aioice.Candidate.from_sdp(c))

            await connection.add_remote_candidate(None)
            connection.remote_username = resp["username"]
            connection.remote_password = resp["password"]

            await connection.connect()
            print("connected")


        elif respCmd == "candidate":
            print('candidate')
            print(resp)
            for c in resp["candidates"]:
                await connection.add_remote_candidate(aioice.Candidate.from_sdp(c))

            await connection.add_remote_candidate(None)
            connection.remote_username = resp["username"]
            connection.remote_password = resp["password"]

            await connection.gather_candidates()
            await websocket.send(
                json.dumps(
                    {
                        "cmd": "candidate",
                        "candidates": [c.to_sdp() for c in connection.local_candidates],
                        "password": connection.local_password,
                        "username": connection.local_username,
                    }
                )
            )
            await connection.connect()
            print("connected")
