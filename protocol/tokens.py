import jwt

def generate_token(payload, secret):
    encoded = jwt.encode(payload, secret, algorithm='HS256')
    return encoded.decode('utf-8')

def verify_token(token, secret):
    try:
        jwt.decode(token.encode('utf-8'), secret, algorithms=['HS256'], verify=True)
    except jwt.exceptions.InvalidSignatureError:
        return False
    else:
        return True

def decode_token(token):
    try:
        info = jwt.decode(token.encode('utf-8'), algorithms=['HS256'], verify=False)
    except jwt.exceptions.DecodeError:
        return None
    else:
        return info

