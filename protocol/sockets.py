
import zmq
from protocol import SecureConnection


def bind_random_socket(address=None, context=None):
    ctx = context or zmq.Context()
    addr = address or 'tcp://*'
    conn = ctx.socket(zmq.ROUTER)
    pipe_port = conn.bind_to_random_port(addr)
    return pipe_port.to_bytes((pipe_port.bit_length() + 7) // 8, 'big'), conn


def secure_user_connection(address, entry_port=5556, context=None, debug=False):
    address = address + ':' if not address.endswith(':') else address
    ctx = context or zmq.Context()
    entry = ctx.socket(zmq.DEALER)
    entry.connect(address + str(entry_port))
    entry.send(b'INITENCRYPTION')
    pipe_port = int.from_bytes(entry.recv(), 'big')
    entry.close()
    pipe_unsecure = ctx.socket(zmq.DEALER)
    pipe_unsecure.connect(address + str(pipe_port))
    pipe_secure = SecureConnection(pipe_unsecure, debug=debug)
    pipe_secure.init_encryption()
    return pipe_secure

