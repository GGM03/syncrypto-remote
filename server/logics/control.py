from protocol import checksum_chain
from uuid import uuid4
from server.logics.datamodel import User, File

from protocol import generate_token, verify_token, decode_token

def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

class Controller:
    def __init__(self, session, masterkey=None):
        self.session = session
        self.masterkey = masterkey or 'NiceStrongKeyWithEntropy01234-=-}{{_0'

    def register(self, username, password):
        check = self._get_user_by_name(username)
        if check:
            return None
        token = str(uuid4())
        treefile = str(uuid4()) + '-' + checksum_chain([username, password, token])
        user = User(username, password, treefile, token)
        self.session.add(user)
        self.session.commit()
        return self._user2dict(user)

    def auth(self, username, password):
        check = self._get_user_by_name(username)
        if not check:
            return False
        else:
            if check.password != password:
                return False
            else:
                return True

    def generate_token(self, username):
        user = self._get_user_by_name(username)
        if not user:
            return ''
        token = generate_token({'id':user.id}, user.token)
        return token

    def verify_token(self, token):
        if not token:
            return False
        payload = decode_token(token)
        user = self._get_user_by_id(payload['id'])
        if not user:
            return False
        return verify_token(token, user.token)

    def get_user_info(self, token):
        if self.verify_token(token):
            payload = decode_token(token)
            user = self._get_user_by_id(payload['id'])
            if user:
                return self._user2dict(user)

    def check_userfile(self, uid, filename):
        user = self._get_user_by_id(uid)
        if not user:
            return
        file = self.session.query(File).filter(User.id == uid).filter(User.files.any(File.name == filename)).first()
        if not file:
            return
        return self._file2dict(file)

    def create_file(self, uid, filename):
        user = self._get_user_by_id(uid)
        if not user:
            return
        f = File(filename)
        user.files.append(f)
        self.session.commit()
        return self._file2dict(f)

    def unlink_file(self, uid, filename):
        self.session.query(File).filter(File.name == filename).delete()
        self.session.commit()

    def update_file(self, filename, local_path):
        file = self.session.query(File).filter(File.name == filename).first()
        file.update_from_file(local_path)
        self.session.commit()

    def _get_user_by_id(self, uid):
        return  self.session.query(User).filter(User.id == uid).first()

    def _get_user_by_name(self, username):
        return  self.session.query(User).filter(User.name == username).first()

    def set_user_limit(self, uid, limit):
        user = self._get_user_by_id(uid)
        if not user:
            return False
        user.limit = limit
        self.session.commit()
        return True

    def set_user_drivesize(self, uid, size):
        user = self._get_user_by_id(uid)
        if not user:
            return False
        user.used = size
        self.session.commit()
        return True

    def _user2dict(self, user):
        return {
            'id': user.id,
            'username': user.name,
            # 'password': user.password,
            'treefile': user.treefile,
            'used': user.used,
            'limit': user.limit
        }

    # def get_user_by_name(self, username):
    #     user = self._get_user_by_name(username)
    #     return self._user2dict(user)
    #
    # def get_user_by_id(self, uid):
    #     user = self._get_user_by_id(uid)
    #     return self._user2dict(user)

    def _file2dict(self, file):
        return {
            'id': file.id,
            'filename': file.name,
            # 'path': file.path,
            'size': file.size,
            'timestamp': int(file.timestamp.timestamp()),
            'checksum': file.checksum
        }

if __name__ == '__main__':
    # init_db()
    u = Controller(session)
    # print(u.register('zloy','qweasdzxc'))
    # t = u.generate_token('zloy')
    # print(t)
    # print(u.verify_token(t))

    print(u.check_userfile(1, '1234'))

    # print(u.auth('zloy','qweasdzxc'))