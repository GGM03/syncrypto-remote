
from hashlib import md5

def checksum(data):
    if not isinstance(data, (bytes, str)):
        try:
            data = str(data)
        except:
            return ''
    data = data.encode('utf-8') if type(data) == str else data
    h = md5()
    h.update(data)
    return h.hexdigest()

def checksum_chain(items):
    hashed = checksum(items[0])
    for item in items[1:]:
        hashed = checksum(hashed + checksum(item))
    return hashed

def file_digest(path, buffer_size=10240):
    md5_obj = md5()
    with open(path, 'rb') as f:
        while True:
            data = f.read(buffer_size)
            if len(data) <= 0:
                break
            md5_obj.update(data)
    return md5_obj.hexdigest()
