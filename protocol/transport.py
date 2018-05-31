
from itertools import cycle
from noise.connection import NoiseConnection
from io import UnsupportedOperation
from pprint import pformat

from protocol.utils import Logging

class ProtocolError(Exception):
    pass


class SocketTypeError(ProtocolError):
    pass


class SecureConnection(Logging):
    def __init__(self, connection, security=b'Noise_NN_25519_ChaChaPoly_SHA256', debug=False):
        self.conn = connection
        super(SecureConnection, self).__init__('NOISE')
        self._debug = debug

        if self.conn.type == 6:
            self.type = 'SERVER'
        elif self.conn.type == 5:
            self.type = 'CLIENT'
        self.noise = NoiseConnection.from_name(security)

    # def _req_verification(self):
    #     encrypted_message = self.noise.encrypt(b'HELLO')
    #     self.conn.send(encrypted_message)
    #     ciphertext = self.conn.recv(2048)
    #     plaintext = self.noise.decrypt(ciphertext)
    #     # print(plaintext)
    #
    # def _resp_verification(self):
    #     user, encr = self.conn.recv_multipart()
    #     # print(self.noise.decrypt(encr))
    #     conn.send_multipart([user, self.noise.encrypt(b'WORLD')])

    def response_encryption(self):
        self.noise.set_as_responder()
        self.noise.start_handshake()
        self.debug('Encryption initalized as responder')
        for action in cycle(['receive', 'send']):
            if self.noise.handshake_finished:
                break
            elif action == 'send':
                ciphertext = self.noise.write_message()
                self.debug('Sending own part of handshake: {0}'.format(ciphertext.hex()))
                self.conn.send_multipart([user, ciphertext])
            elif action == 'receive':
                self.debug('Waiting for hadnshake')
                user, data = self.conn.recv_multipart()
                self.debug('Recieved handshake {0}'.format(data.hex()))
                self.noise.read_message(data)
        self.debug('Encrypted connection estabilished')
        # self._resp_verification()

    def init_encryption(self):
        self.noise.set_as_initiator()
        self.noise.start_handshake()
        self.debug('Encryption initalized as initiator')
        message = self.noise.write_message()
        self.debug('Sending own part of handshake: {0}'.format(message.hex()))
        self.conn.send(message)
        received = self.conn.recv(2048)
        self.debug('Recieved handshake {0}'.format(received.hex()))
        self.noise.read_message(received)
        self.debug('Encrypted connection estabilished')

    def _assert_state(self):
        if not self.noise.handshake_finished:
            raise ProtocolError('A secure connection is not established')

    def _assert_server_type(self):
        if self.type == 'CLIENT':
            raise ProtocolError('Wrong socket type to perform this operation')

    def _assert_client_type(self):
        if self.type == 'SERVER':
            raise ProtocolError('Wrong socket type to perform this operation')

    def send(self,  data):
        self._assert_state()
        return self.conn.send(self.noise.encrypt(data))

    def recv(self, flags=0, copy=True, track=False):
        self._assert_state()
        data = self.noise.decrypt(self.conn.recv(flags, copy, track))
        if self._debug == 3:
            self.debug('RECV: {0}'.format(data))
        return data

    def send_multipart(self, data):
        self._assert_state()
        self._assert_server_type()
        user = data[0]
        # data = self.noise.encrypt(json.dumps(data[1:]))
        if self._debug == 3:
            self.debug('SEND: {0}'.format(data))
        data = self.noise.encrypt(data[1])
        return self.conn.send_multipart([user, data])

    def recv_multipart(self, flags=0, copy=True, track=False):
        self._assert_state()
        self._assert_server_type()
        message = self.conn.recv_multipart(flags, copy, track)
        user = message[0]
        data = self.noise.decrypt(message[1])
        return [user] + [data]

#
# class ServerTunnel:
#     def __init__(self, pipe, fd):
#         self.tunnel = pipe
#         self.fd = fd
#
#     def read_in_chunks(self, chunk_size=1024*16):
#         """Lazy function (generator) to read a file piece by piece.
#         Default chunk size: 1k."""
#         while True:
#             data = self.fd.read(chunk_size)
#             if not data:
#                 break
#             yield data
#
#     def recv(self):
#         user, data = self.tunnel.recv_multipart()
#         if not data == b'BEGINOFTRANSFER':
#             return
#
#         user, data = self.tunnel.recv_multipart()
#         while data != b'ENDOFTRANSFER':
#             if data != b'BEGINOFTRANSFER':
#                 self.fd.write(data)
#             user, data = self.tunnel.recv_multipart()
#         self.fd.close()
#
#     def send(self):
#         user, data = self.tunnel.recv_multipart()
#         for data in self.read_in_chunks():
#             self.tunnel.send_multipart([user, data])
#         self.fd.close()

import io

class ClientTunnel:

    def __init__(self, pipe, type='rb'):
        self.tunnel = pipe
        self.type = type
        self.tunnel.send(b'BEGINOFTRANSFER')

    def read(self, n=0):
        if self.type != 'rb':
            raise UnsupportedOperation
        # return self.tunnel.recv(n)
        buf = io.BytesIO()
        data = self.tunnel.recv()
        while data != b'ENDOFTRANSFER':
            buf.write(data)
            data = self.tunnel.recv()
            # print(data)
        return buf.getvalue()


    def write(self, data):
        if self.type != 'wb':
            raise UnsupportedOperation
        self.tunnel.send(data)
        # self.tunnel.recv()

    def close(self):
        self.tunnel.send(b'ENDOFTRANSFER')
        self.tunnel.recv()

# import io
#
# class ServerTunnel:
#     def __init__(self, pipe, fd):
#         self.tunnel = pipe
#         self.fd = fd
#
#     def read_in_chunks(self, chunk_size=1024*16):
#         """Lazy function (generator) to read a file piece by piece.
#         Default chunk size: 1k."""
#         while True:
#             data = self.fd.read(chunk_size)
#             if not data:
#                 break
#             yield data
#
#     def recv(self):
#         user, data = self.tunnel.recv_multipart()
#         if not data == b'BEGINOFTRANSFER':
#             return
#
#         user, data = self.tunnel.recv_multipart()
#         while data != b'ENDOFTRANSFER':
#             if data != b'BEGINOFTRANSFER':
#                 self.fd.write(data)
#             user, data = self.tunnel.recv_multipart()
#         self.fd.close()
#
#     def send(self):
#         user, data = self.tunnel.recv_multipart()
#         for data in self.read_in_chunks():
#             self.tunnel.send_multipart([user, data])
#         self.fd.close()
#
#
# class ClientTunnel:
#
#     def __init__(self, pipe):
#         self.tunnel = pipe
#         self.fd = io.BytesIO()
#         self.tunnel.send(b'BEGINOFTRANSFER')
#
#     def read(self, n=0):
#         return self.tunnel.recv(n)
#
#     def write(self, data):
#         self.tunnel.send(data)
#         # self.tunnel.recv()
#
#     def close(self):
#         self.tunnel.send(b'ENDOFTRANSFER')