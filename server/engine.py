import zmq
from protocol import SecureConnection
from protocol import bind_random_socket
from protocol import Logging

class ServerWorker(Logging):
    def __init__(self, logics, entryp_addr, context=None, debug=False):
        super(ServerWorker, self).__init__('Server')
        self.logics = logics
        self._debug = debug
        self.ctx = context or zmq.Context()
        self.poller = zmq.Poller()
        self.users = []
        self.register_entrypoint(entryp_addr)
        self.debug('Server initalized')

    def register_entrypoint(self, addr):
        self.entrypount = self.ctx.socket(zmq.ROUTER)
        self.entrypount.bind(addr)
        self.poller.register(self.entrypount, zmq.POLLIN)

    def create_secure_pipe(self, user):
        # conn = self.ctx.socket(zmq.ROUTER)
        # # conn.bind("tcp://*:5556")
        # pipe_port = conn.bind_to_random_port('tcp://*')
        port, conn = bind_random_socket(context=self.ctx)
        # self.entrypount.send_multipart([user, pipe_port.to_bytes((pipe_port.bit_length() + 7) // 8, 'big')])
        self.entrypount.send_multipart([user, port])
        self.debug('New connection created on port {0}'.format(int.from_bytes(port, 'big')))
        s = SecureConnection(conn, debug=self._debug)
        s.response_encryption()
        return s

    def poll(self):
        socks = dict(self.poller.poll())
        try:
            if self.entrypount in socks:
                user, msg = self.entrypount.recv_multipart()
                if msg == b'INITENCRYPTION':
                    self.debug('New encryption request from user {0}'.format(user.hex()))
                    pipe = self.create_secure_pipe(user)
                    self.poller.register(pipe.conn,  zmq.POLLIN)
                    self.users.append(pipe)
                    self.debug('Encrypted pipe successfully started')
            else:
                for user in self.users:
                    if user.conn in socks:
                        username, request = user.recv_multipart()
                        self.debug('Recieved data from user {0}'.format(username.hex()))
                        response = self.logics(self.get_tunnel(user, username), request)
                        user.send_multipart([username, response])
        except KeyboardInterrupt:
            print('Shutting down...')
            exit(-1)


    def get_tunnel(self, pipe, user):
        return SenderTunnel(pipe, user)


    def main_loop(self):
        while True:
            self.poll()

class SenderTunnel:
    def __init__(self, pipe, user):
        self.user = user
        self.pipe = pipe

    def send(self, data):
        self.pipe.send_multipart([self.user, data])

    def recv(self):
        return self.pipe.recv_multipart()[1]

if __name__ == '__main__':
    pass
    # from server.logics import ServerLogics
    # s = ServerWorker(ServerLogics(), 'tcp://127.0.0.1:8765')
    # s.main_loop()
    # s = SecureConnection('tcp://127.0.0.1')