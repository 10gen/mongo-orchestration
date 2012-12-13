import requests
import json


def request(method, url, data=''):
    method = method.lower()
    if method not in ('post', 'get', 'delete', 'put'):
        raise ValueError("Unknown method '{method}'".format(**locals()))
    if not (isinstance(data, str) or isinstance(data, unicode)):
        data = json.dumps(data)
    r = getattr(requests, method)(url, data=data)
    try:
        response = json.loads(r.text)
    except ValueError:
        response = ''
    if not (200 <= r.status_code < 300):
        raise RuntimeError("request return {code} code".format(code=r.status_code))
    return response
