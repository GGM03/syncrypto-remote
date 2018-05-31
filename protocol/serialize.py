import json

class JsonSerializer:

    def dumps(self, data):
        return json.dumps(data).encode('utf-8')

    def loads(self, data):
        return json.loads(data.decode('utf-8'))
