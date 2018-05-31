import os

class FileLogics:
    def __init__(self, files):
        self.files = os.path.normpath(files)

    def get_file(self, file, mode='rb'):
        filepath = os.path.join(self.files, file)
        if mode == 'rb' and not os.path.exists(filepath):
            return None
        return open(filepath, mode=mode)

    def get_path(self, file):
        filepath = os.path.join(self.files, file)
        return filepath

    def delete_file(self, file):
        filepath = os.path.join(self.files, file)
        os.remove(filepath)

    def is_empty(self, file):
        filepath = os.path.join(self.files, file)
        if not os.path.exists(filepath):
            return True
        if os.path.getsize(filepath) == 0:
            return True
        return False

if __name__ == '__main__':
    filelogics = FileLogics('/home/zloy/PycharmProjects/syncrypto/tmp/enc')

    print(filelogics.is_empty('01297fa7-ae88-447a-9522-72098e225755-9b80acdf5d10cb442d81e8aaf482b645'))

