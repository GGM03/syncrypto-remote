from datetime import datetime
import zmq
import io

# from protocol import SecureConnection
from protocol import JsonSerializer as Serializer
from protocol.transport import ClientTunnel
from protocol import secure_user_connection
from protocol.utils import Logging

class ClientWorker(Logging):
    def __init__(self, pipe, token='', treefile='', serializer=None, debug=0):
        super(ClientWorker, self).__init__('Client')
        self.secure = pipe
        self.s = serializer or Serializer()
        self.token = token
        self.treefile = treefile
        self._debug = debug

    @property
    def is_logged(self):
        return bool(self.token)

    def register(self, username, password):
        command = {
            'token':self.token,
            'resource': 'users',
            'command': {
                'command': 'register',
                'args': {'username': username, 'password':password},
            },
            'timestamp': int(datetime.utcnow().timestamp())
        }
        self.secure.send(self.s.dumps(command))
        return self.s.loads(self.secure.recv())

    def auth(self, username, password):
        command = {
            'token':self.token,
            'resource': 'users',
            'command': {
                'command': 'auth',
                'args': {'username': username, 'password':password},
            },
            'timestamp': int(datetime.utcnow().timestamp())
        }
        self.secure.send(self.s.dumps(command))
        return self.s.loads(self.secure.recv())

    def get_info(self):
        command = {
            'token':self.token,
            'resource': 'users',
            'command': {
                'command': 'info',
                'args': {},
            },
            'timestamp': int(datetime.utcnow().timestamp())
        }
        self.secure.send(self.s.dumps(command))
        return self.s.loads(self.secure.recv())

    def get_tree(self):
        if not self.treefile:
            info = self.get_info()
            if not info or info['status'] != 200:
                return
            self.treefile = info['data']['treefile']

        has = self.has_tree()


        if has:
            return self.get_file(self.treefile)
        else:
            return None

    def has_tree(self):
        command = {
            'token': self.token,
            'resource': 'users',
            'command': {
                'command': 'tree',
                'args': {},
            },
            'timestamp': int(datetime.utcnow().timestamp())
        }
        self.secure.send(self.s.dumps(command))
        resp = self.s.loads(self.secure.recv())
        if not resp or resp['status'] != 200:
            return False
        return resp['data']['tree']

    def post_tree(self):
        if not self.treefile:
            info = self.get_info()
            if not info or info['status'] != 200:
                return
            self.treefile = info['data']['treefile']
        return self.post_file(self.treefile)

    def delete_file(self, filename):
        command = {
            'token': self.token,
            'resource': 'files',
            'command': {
                'command': 'delete',
                'args': {'filename': filename},
            },
            'timestamp': int(datetime.utcnow().timestamp())
        }
        self.secure.send(self.s.dumps(command))
        return self.s.loads(self.secure.recv())

    def get_file(self, filename):
        command = {
            'token': self.token,
            'resource': 'files',
            'command': {
                'command': 'get',
                'args': {'filename': filename},
            },
            'timestamp': int(datetime.utcnow().timestamp())
        }
        self.secure.send(self.s.dumps(command))
        respone = self.secure.recv()
        file_response = self.s.loads(respone)
        if file_response['status'] != 200:
            print('ERROR COLLECTING FILE')
            # return None
            return io.BytesIO()
        return ClientTunnel(self.secure, type='rb')
        # return self.s.loads(self.secure.recv())

    def post_file(self, filename):
        command = {
            'token': self.token,
            'resource': 'files',
            'command': {
                'command': 'post',
                'args': {'filename': filename},
            },
            'timestamp': int(datetime.utcnow().timestamp())
        }
        self.secure.send(self.s.dumps(command))
        file_response = self.s.loads(self.secure.recv())
        if file_response['status'] != 200:
            print('ERROR COLLECTING FILE')
            # return None
            return io.BytesIO()
        return ClientTunnel(self.secure, type='wb')
        # open('/home/zloy/PycharmProjects/syncrypto/test2.py', 'rb'))
        # return self.s.loads(self.secure.recv())

    @classmethod
    def from_creds(cls, pipe, username, password, **kwargs):
        worker = cls(pipe, **kwargs)
        auth_data = worker.auth(username, password)
        if not auth_data:
            print('Error auth!')
            return worker
        elif auth_data['error']:
            print('Server error "{0}"'.format(auth_data['error']))
            return worker
        elif auth_data['status'] == 200:
            worker.token = auth_data['data']['token']
            return worker

    @classmethod
    def from_registration(cls, pipe, username, password, **kwargs):
        worker = cls(pipe, **kwargs)
        register_inf = worker.register(username, password)

        print(register_inf)
        if register_inf['status'] != 201:
            print('Registration falied!')
            print('Trying to login with this creds!')
            # exit(-1)

        auth_data = worker.auth(username, password)
        if not auth_data:
            print('Error auth!')
            return worker
        elif auth_data['error']:
            print('Server error {0}'.format(auth_data['error']))
            return worker
        elif auth_data['status'] == 200:
            worker.token = auth_data['data']['token']
            return worker



if __name__ == '__main__':
    secure = secure_user_connection('tcp://127.0.0.1')
    # u = ClientWorker(secure)
    # dat = u.register('123456','123')
    # print(dat)
    # u = ClientWorker.from_creds(secure, '123456','123')

    u = ClientWorker.from_registration(secure, 'zloy', 'helloworld')

    # f = u.post_file('1234')
    # f.write(b'1')
    # f.close()
    #
    f = u.post_file('4321')
    f.write(b'2')
    f.close()

    print(u.delete_file('4321'))

    # f = u.get_file('4321')
    # print(f.read())
    # f.close()
    # print(u.file())
    # dat = cl.auth('123456','123')
    # print(dat)
