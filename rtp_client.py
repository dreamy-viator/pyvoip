
from rtp.rtp_packet import RTPPacket
from rtp.rtsp_packet import RTSPPacket

import socket
import numpy as np
from time import sleep
from threading import Thread

DEFAULT_CHUNK_SIZE = 4096 + 12

class RTPReceiveClient:
    DEFAULT_LOCAL_HOST = '127.0.0.1'
    RTP_TIMEOUT = 10000  # in milliseconds

    def __init__(
            self,
            rtp_port: int):

        self.rtp_port = rtp_port
        self._frame_buffer = [] #TODO.. FrameSize Limit
        self.is_receiving_rtp = False
        self.current_frame_number = -1


    def get_next_frame(self):
        if self._frame_buffer:
            self.current_frame_number += 1
            return self._frame_buffer.pop(0), self.current_frame_number

        return None


    def start(self, callback):
        self.is_receiving_rtp = True
        self._start_rtp_receive_thread()
        self.callback = callback

    def pause(self):
        #TODO
        self.is_receiving_rtp = False

    def _handle_audio_receive(self):
        self._rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rtp_socket.bind((self.DEFAULT_LOCAL_HOST, self.rtp_port))
        self._rtp_socket.settimeout(self.RTP_TIMEOUT / 1000.)
        while True:
            if not self.is_receiving_rtp:
                sleep(self.RTP_TIMEOUT / 1000.)  # diminish cpu hogging
                continue

            print('receive packet\n')
            packet = self._recv_rtp_packet()
            # for debugging
            packet.print_header()

            audio_data = packet.payload
            buffer = np.frombuffer(audio_data, dtype=np.int)
            self.callback(buffer)
            # self._frame_buffer.append(buffer)

    def _recv_rtp_packet(self, size=DEFAULT_CHUNK_SIZE) -> RTPPacket:
        recv = bytes()
        print('Waiting RTP packet...')
        while True:
            try:
                recv = self._rtp_socket.recv(size)
                # TODO.. maybe check if packet is full.
                break
            except socket.timeout:
                print('Receive RTP Socket timeout')
                continue
        print(f"Received from server: {repr(recv)}")

        return RTPPacket.from_packet(recv)


    def _start_rtp_receive_thread(self):
        self._rtp_receive_thread = Thread(target=self._handle_audio_receive)
        self._rtp_receive_thread.setDaemon(True)
        self._rtp_receive_thread.start()



class RTPSendClient:
    def __init__(
            self,
            remote_host_address: str,
            remote_host_port: int):

        self._remote_address: (str, int) = (remote_host_address, remote_host_port)

    def start(self):
        self._setup_rtp()

    def send_audio(self, data, ts, frame_count):
        rtp_packet = RTPPacket(payload_type=RTPPacket.TYPE.OPUS,
                           sequence_number=frame_count,
                           timestamp=ts,
                           payload=data)

        print('send packet\n')
        rtp_packet.print_header()
        packet = rtp_packet.get_packet()
        self._send_rtp_packet(packet)

    def _setup_rtp(self):
        print('Setting up RTP socket...')
        self._rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self._start_rtp_send_thread()

    def _start_rtp_send_thread(self):
        self._rtp_send_thread = Thread(target=self._handle_audio_send)
        self._rtp_send_thread.setDaemon(True)
        self._rtp_send_thread.start()


    def _send_rtp_packet(self, packet: bytes):
        to_send = packet[:]
        while to_send:
            try:
                self._rtp_socket.sendto(to_send[:DEFAULT_CHUNK_SIZE], self._remote_address)
            except socket.error as e:
                print(f"failed to send rtp packet: {e}")
                return
            # trim bytes sent
            to_send = to_send[DEFAULT_CHUNK_SIZE:]
