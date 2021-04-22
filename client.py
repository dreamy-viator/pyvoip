

from audio_out import AudioOutput
from mic import MicDevice
from rtp_client import RTPReceiveClient, RTPSendClient
import pyaudio
import aioice
import numpy as np
import websockets
import json
import asyncio
import threading
from rtp.rtp_packet import RTPPacket

from queue import Queue

class Client:
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 4096
    STUN_SERVER = ("stun.l.google.com", 19302)
    SIGNAL_SERVER = 'ws://47.242.210.177:8765'

    def __init__(
            self,
            remote_host_address,
            remote_host_port,
            host_address,
            rtp_port):

        self.queue = []
        self.mic = MicDevice(sr=self.SAMPLE_RATE,
                             chunk_size=self.CHUNK_SIZE)

        self.sender = RTPSendClient(remote_host_address=remote_host_address,
                                    remote_host_port=remote_host_port)

        self.receiver = RTPReceiveClient(host_address=host_address,
                                         rtp_port=rtp_port)
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
        packet = self.sender.send_audio_packet(
            data=in_data,
            ts=ts,
            frame_count=self.frame_count)
        with self.lock:
            self.queue.append(packet)
        self.frame_count += 1
        return (None, pyaudio.paContinue)

    def _receive_callback(self, audio):
        self.aout.write(audio)

    def thr1(self):
        # we need to create a new loop for the thread, and set it as the 'default'
        # loop that will be returned by calls to asyncio.get_event_loop() from this
        # thread.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self.answer())
        loop.close()

    def thr2(self):
        # we need to create a new loop for the thread, and set it as the 'default'
        # loop that will be returned by calls to asyncio.get_event_loop() from this
        # thread.
        # self.mic.start(self._callback)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(self.send())
        loop.close()


    def start_calling(self, roomId):
        self.roomId = roomId
        asyncio.get_event_loop().run_until_complete(self.init_singaling())
        asyncio.get_event_loop().run_until_complete(self.get_remote())
        self.sender.start()
        # self.receiver.start(self._receive_callback)
        # # mic
        self.mic.start(self._callback)
        # # audio output
        self.aout.open()
        self.aout.start()
        threads = []

        # thread1 = threading.Thread(target=self.thr1)
        thread2 = threading.Thread(target=self.thr2)
        # threads.append(thread1)
        threads.append(thread2)

        [t.start() for t in threads]
        # [t.join() for t in threads]
        asyncio.get_event_loop().run_until_complete(self.answer())
        # num_threads = 2
        # threads = [threading.Thread(target=self.thr, args=(i,)) for i in range(num_threads)]
        # [t.start() for t in threads]
        # [t.join() for t in threads]
        #
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
