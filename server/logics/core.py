from datetime import datetime


from protocol import JsonSerializer as Serializer
from protocol.utils import Logging

def _protected_area(method):
    def wrapper(self, *args, **kwargs):
        if not 'token' in args[0]:
            return 401, None
        if not self.controller.verify_token(args[0]['token']):
            return 401, None
        return method(self, *args, **kwargs)
    return wrapper

def _wrap_response(method, *, debug=True):
    def wrapper(self, *args, **kwargs):
        errors = {
            400: 'Bad Request',
            401: 'Unauthorized',
            403: 'Forbidden',
            404: 'Not Found',
            406: 'Not Acceptable',
        }
        response = {}
        response['timestamp'] = int(datetime.utcnow().timestamp())
        response['data'] = {}
        response['error'] = ''

        if not debug:
            try:
                code, data = method(self, *args, **kwargs)
            except Exception as e:
                response['error'] = str(e)
                return response
            else:
                response['status'] = code
                if code in errors:
                    response['error'] = errors[code]
                else:
                    response['data'] = data
                return response

        else:
            code, data = method(self, *args, **kwargs)
            response['status'] = code
            if code in errors:
                response['error'] = errors[code]
            else:
                response['data'] = data
            return response
    return wrapper

# def _aviable_commands(method, *, commands=None):
#     def wrapper(self, *args, **kwargs):
#         print(args)
#         if not 'command' in args[0]:
#             return 404, None
#         if not 'command' in args[0]['command']:
#             return 404, None
#         if commands:
#             if args[0]['command']['command'] not in commands:
#                 return 401, None
#             return method(self, *args, **kwargs)
#         else:
#             return method(self, *args, **kwargs)
#     return wrapper

class ServerLogics(Logging):
    def __init__(self, controller, filemanager, serializer=None):
        super(ServerLogics, self).__init__('Backend')
        self.s = serializer or Serializer()
        self.filelogics = filemanager
        self.controller = controller

        self.resources = {
            'users': self.users,
            'files': self.files,
        }

    @_wrap_response
    def users(self, request, pipe):
        token = request['token']
        command = request['command']['command']
        args = request['command']['args']

        if not command in ['auth', 'register', 'info', 'tree']:
            return 404, None
        if command == 'auth':
            self.debug('Auth requested {0}'.format(request['command']['args']))
            if self.controller.auth(**args):
                token = self.controller.generate_token(args['username'])
                return 200, {'token': token}
            else:
                return 406, None

        elif command == 'register':
            self.debug('Registration requested {0}'.format(request['command']['args']))
            new_user = self.controller.register(**args)
            if new_user:
                return 201, new_user
            else:
                return 400, None

        elif command == 'info':
            self.debug('Information requested {0}'.format(request['command']['args']))
            if not token:
                return 401, None
            user = self.controller.get_user_info(token)
            if user:
                return 200, user
            else:
                return 401, None

        elif command == 'tree':
            self.debug('Tree requested {0}'.format(request['command']['args']))
            if not token:
                return 401, None
            user = self.controller.get_user_info(token)
            if not user:
                return 401, None

            return 200, {'tree': not self.filelogics.is_empty(user['treefile'])}

    @_wrap_response
    def _recv_file_accept(self, info):
        return 200, info

    @_wrap_response
    @_protected_area
    def files(self, request, pipe):
        command = request['command']['command']
        token = request['token']
        args = request['command']['args']
        if not command in ['post', 'get', 'delete']:
            return 404, None

        if command == 'post':
            self.debug('File upload requested {0}'.format(request['command']['args']))
            user = self.controller.get_user_info(token)
            file = self.controller.check_userfile(user['id'], args['filename'])
            if not file:
                file = self.controller.create_file(user['id'], args['filename'])
                if not file:
                    return 404, None

            pipe.send(self.s.dumps(self._recv_file_accept(file)))
            buf = self.filelogics.get_file(file['filename'], mode='wb')
            path = self.filelogics.get_path(file['filename'])
            # buf = io.BytesIO()
            assert pipe.recv() == b'BEGINOFTRANSFER'
            data = pipe.recv()
            while data != b'ENDOFTRANSFER':
                buf.write(data)
                data = pipe.recv()
                # print(data)

            buf.close()
            self.controller.update_file(file['filename'], path)
            return 200, None

        elif command == 'get':
            self.debug('File download requested {0}'.format(request['command']['args']))
            user = self.controller.get_user_info(token)
            file = self.controller.check_userfile(user['id'], args['filename'])

            if not file:
                return 404, None
            else:
                pipe.send(self.s.dumps(self._recv_file_accept(file)))

            fd = self.filelogics.get_file(args['filename'], mode='rb')
            assert pipe.recv() == b'BEGINOFTRANSFER'
            data = fd.read(1024)
            while data:
                pipe.send(data)
                data = fd.read(1024)
            pipe.send(b'ENDOFTRANSFER')
            _ = pipe.recv()
            return 200, None

        elif command == 'delete':
            self.debug('File deletion requested {0}'.format(request['command']['args']))
            user = self.controller.get_user_info(token)
            file = self.controller.check_userfile(user['id'], args['filename'])
            if not file:
                return 403, None
            # else:
                # pipe.send(self.s.dumps(self._recv_file_accept(file)))
            self.filelogics.delete_file(args['filename'])
            self.controller.unlink_file(user['id'], args['filename'])
            return 202, None

    # @_wrap_response
    # @_protected_area
    def call_resource(self, resource, request, pipe):
        resource = self.resources.get(resource)
        if not resource:
            return 404, None
        response = resource(request, pipe)
        return response

    def parse(self, pipe, bytestring, *args, **kwargs):
        # print(bytestring)
        request = self.s.loads(bytestring)
        resource = request['resource']
        result = self.call_resource(resource, request, pipe)
        return self.s.dumps(result)

    def __call__(self, *args, **kwargs):
        return self.parse(*args, **kwargs)


if __name__ == '__main__':
    pass