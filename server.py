# coding=utf-8

import json
from modules.hosts import Hosts
from bottle import route, run, request, response, abort

hosts = Hosts()
hosts.set_settings('/tmp/mongo-pids')


def send_result(code, result=None):
    content = None
    response.content_type = None
    if result is not None:
            content = json.dumps(result)
            response.content_type = "application/json"
    response.status = code
    if code > 399:
        return abort(code, content)
    return content


@route('/hosts', method='POST')
def host_create():
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        host_id = Hosts().h_new(data['name'], data.get('params', {}))
        result = Hosts().h_info(host_id)
    except StandardError as e:
        print repr(e)
        return send_result(500)
    return send_result(200, result)


@route('/hosts', method='GET')
def host_list():
    try:
        data = [info for info in Hosts()]
    except StandardError as e:
        print repr(e)
        return send_result(500)
    return send_result(200, data)


@route('/hosts/<host_id>', method='GET')
def host_info(host_id):
    if host_id not in Hosts():
        return send_result(404)
    try:
        result = Hosts().h_info(host_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/hosts/<host_id>', method='DELETE')
def host_del(host_id):
    if host_id not in Hosts():
        return send_result(404)
    try:
        Hosts().h_del(host_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(204)


@route('/hosts/<host_id>/<command:re:(start)|(stop)|(restart)>', method='PUT')
def host_command(host_id, command):
    if host_id not in Hosts():
        return send_result(404)
    try:
        Hosts().h_command(host_id, command)
    except StandardError as e:
        print repr(e)
        return send_result(500)
    return send_result(200)

import atexit
atexit.register(hosts.cleanup)
run(host='localhost', port=8889, debug=True, reloader=False)
