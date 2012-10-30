# coding=utf-8
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import json
from modules.hosts import Hosts
from modules.rs import RS
from bottle import route, run, request, response, abort

hosts = Hosts()
hosts.set_settings('/tmp/mongo-pids')
rs = RS()
rs.set_settings('/tmp/mongo-pids')


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
        print repr(e)
        return send_result(500)
    return send_result(200, result)


@route('/hosts', method='GET')
def host_list():
    logger.info("host_list request")
    try:
        data = [info for info in Hosts()]
    except StandardError as e:
        print repr(e)
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
        print repr(e)
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
        print repr(e)
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
        print repr(e)
        return send_result(500)
    return send_result(200)



@route('/rs', method='POST')
def rs_create():
    logger.info("rs_create request")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        rs_id = RS().rs_new(data)
        print 'rs_id: ', rs_id
        result = RS().repl_info(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(500)
    return send_result(200, result)

@route('/rs', method='GET')
def rs_list():
    logger.info("rs_list request")
    try:
        data = [info for info in RS()]
    except StandardError as e:
        print repr(e)
        return send_result(500)
    return send_result(200, data)



@route('/rs/<rs_id>', method='GET')
def rs_info(rs_id):
    logger.info("repl_info request")
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().repl_info(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>', method='DELETE')
def rs_del(rs_id):
    logger.info("rs_del request")
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().rs_del(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(204, result)


@route('/rs/<rs_id>/members', method='POST')
def rs_member_add(rs_id):
    logger.info("member_add request")
    if rs_id not in RS():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        if RS().rs_member_add(rs_id, data):
            result = RS().rs_members(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>/members', method='GET')
def rs_members(rs_id):
    logger.info("member_list request")
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().rs_members(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>/secondaries', method='GET')
def rs_secondaries(rs_id):
    logger.info("secondaries request")
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().rs_secondaries(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)

@route('/rs/<rs_id>/arbiters', method='GET')
def rs_arbiters(rs_id):
    logger.info("arbiters request")
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().rs_arbiters(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>', method='GET')
def rs_member_info(rs_id, member_id):
    logger.info("member_info request")
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().rs_member_info(rs_id, member_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>', method='DELETE')
def rs_member_del(rs_id, member_id):
    logger.info("member_del request")
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().rs_member_del(rs_id, member_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>', method='PUT')
def rs_member_update(rs_id, member_id):
    logger.info("member_update request")
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        RS().rs_member_update(rs_id, member_id, data)
        result = RS().rs_member_info(rs_id, member_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>/<command:re:(start)|(stop)|(restart)>', method='PUT')
def rs_member_command(rs_id, member_id, command):
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    try:
        result = RS().rs_member_command(rs_id, member_id, command)
        print 'command result: ', result
        if result:
            return send_result(200)
        return send_result(400)
    except StandardError as e:
        print repr(e)
        return send_result(400)

@route('/rs/<rs_id>/primary', method='GET')
def rs_member_primary(rs_id):
    logger.info("member_primary request")
    if rs_id not in RS():
        return send_result(404)

    try:
        result = RS().rs_primary(rs_id)
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200, result)


@route('/rs/<rs_id>/primary/stepdown', method='PUT')
def rs_primary_stepdown(rs_id):
    logger.info("primary stepdown request")
    if rs_id not in RS():
        return send_result(404)

    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        RS().rs_primary_stepdown(rs_id, data.get('timeout', 60))
    except StandardError as e:
        print repr(e)
        return send_result(400)
    return send_result(200)



import atexit
atexit.register(hosts.cleanup)
run(host='localhost', port=8889, debug=True, reloader=False)


