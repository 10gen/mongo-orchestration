# coding=utf-8
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import json
import sys

sys.path.insert(0, '..')
from lib.hosts import Hosts
from bottle import route, request, response, abort, run


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
    logger.info("host_create request")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        host_id = Hosts().h_new(data['name'], data.get('params', {}))
        result = Hosts().h_info(host_id)
    except StandardError as e:
        return send_result(500)
    return send_result(200, result)


@route('/hosts', method='GET')
def host_list():
    logger.info("host_list request")
    try:
        data = [info for info in Hosts()]
    except StandardError as e:
        return send_result(500)
    return send_result(200, data)


@route('/hosts/<host_id>', method='GET')
def host_info(host_id):
    logger.info("host_info request")
    if host_id not in Hosts():
        return send_result(404)
    try:
        result = Hosts().h_info(host_id)
    except StandardError as e:
        return send_result(400)
    return send_result(200, result)


@route('/hosts/<host_id>', method='DELETE')
def host_del(host_id):
    logger.info("host_del request")
    if host_id not in Hosts():
        return send_result(404)
    try:
        Hosts().h_del(host_id)
    except StandardError as e:
        return send_result(400)
    return send_result(204)


@route('/hosts/<host_id>/<command:re:(start)|(stop)|(restart)>', method='PUT')
def host_command(host_id, command):
    logger.info("host_command request")
    if host_id not in Hosts():
        return send_result(404)
    try:
        Hosts().h_command(host_id, command)
    except StandardError as e:
        return send_result(500)
    return send_result(200)


if __name__ == '__main__':
    hs = Hosts()
    hs.set_settings('/tmp/mongo-orchestration.hs-storage', '')
    run(host='localhost', port=8889, debug=True, reloader=False)
