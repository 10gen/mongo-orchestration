#!/usr/bin/python
# coding=utf-8

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import json
import traceback
import sys

sys.path.insert(0, '..')
from lib.rs import RS
from bottle import route, request, response, run


def send_result(code, result=None):
    logger.debug("send_result({code}, {result})".format(**locals()))
    content = None
    response.content_type = None
    if result is not None:
        content = json.dumps(result)
        response.content_type = "application/json"
    response.status = code
    return content


def error_wrap(f):
    def wrap(*arg, **kwd):
        f_name = f.func_name
        logger.debug("{f_name}({arg}, {kwd})".format(f_name=f_name, arg=arg, kwd=kwd))
        try:
            return f(*arg, **kwd)
        except StandardError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
            logger.error("Exception {exc_type} {exc_value} while {f_name}".format(**locals()))
            logger.error(err_message)
            return send_result(500, err_message)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
            logger.critical("Exception {exc_type} {exc_value} while {f_name}".format(**locals()))
            logger.critical(err_message)
            return send_result(500, err_message)

    return wrap


@route('/rs', method='POST')
@error_wrap
def rs_create():
    logger.debug("rs_create()")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    rs_id = RS().create(data)
    result = RS().info(rs_id)
    return send_result(200, result)


@route('/rs', method='GET')
@error_wrap
def rs_list():
    logger.debug("rs_list()")
    data = [info for info in RS()]
    return send_result(200, data)


@route('/rs/<rs_id>', method='GET')
@error_wrap
def rs_info(rs_id):
    logger.debug("rs_info({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().info(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>', method='DELETE')
@error_wrap
def rs_del(rs_id):
    logger.debug("rs_del({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().remove(rs_id)
    return send_result(204, result)


@route('/rs/<rs_id>/members', method='POST')
@error_wrap
def member_add(rs_id):
    logger.debug("member_add({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    member_id = RS().member_add(rs_id, data)
    result = RS().member_info(rs_id, member_id)
    return send_result(200, result)


@route('/rs/<rs_id>/members', method='GET')
@error_wrap
def members(rs_id):
    logger.debug("members({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().members(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>/secondaries', method='GET')
@error_wrap
def secondaries(rs_id):
    logger.debug("secondaries({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().secondaries(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>/arbiters', method='GET')
@error_wrap
def arbiters(rs_id):
    logger.debug("arbiters({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().arbiters(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>/hidden', method='GET')
@error_wrap
def hidden(rs_id):
    logger.debug("hidden({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().hidden(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>/passives', method='GET')
@error_wrap
def passives(rs_id):
    logger.debug("passives({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().passives(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>/hosts', method='GET')
@error_wrap
def hosts(rs_id):
    logger.debug("hosts({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)
    result = RS().hosts(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>', method='GET')
@error_wrap
def member_info(rs_id, member_id):
    logger.debug("member_info({rs_id}, {member_id})".format(**locals()))
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    result = RS().member_info(rs_id, member_id)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>', method='DELETE')
@error_wrap
def member_del(rs_id, member_id):
    logger.debug("member_del({rs_id}), {member_id}".format(**locals()))
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    result = RS().member_del(rs_id, member_id)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>', method='PUT')
@error_wrap
def member_update(rs_id, member_id):
    logger.debug("member_update({rs_id}, {member_id})".format(**locals()))
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    RS().member_update(rs_id, member_id, data)
    result = RS().member_info(rs_id, member_id)
    return send_result(200, result)


@route('/rs/<rs_id>/members/<member_id>/<command:re:(start)|(stop)|(restart)>', method='PUT')
@error_wrap
def member_command(rs_id, member_id, command):
    logger.debug("member_command({rs_id}, {member_id}, {command})".format(**locals()))
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)
    result = RS().member_command(rs_id, member_id, command)
    if result:
        return send_result(200)
    return send_result(400)


@route('/rs/<rs_id>/members/<member_id>/freeze', method='PUT')
@error_wrap
def member_freeze(rs_id, member_id):
    logger.debug("member_freeze({rs_id}, {member_id})".format(**locals()))
    member_id = int(member_id)
    if rs_id not in RS():
        return send_result(404)

    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)

    result = RS().member_freeze(rs_id, member_id, data.get('timeout', 60))
    if result:
        return send_result(200)
    return send_result(400)


@route('/rs/<rs_id>/primary', method='GET')
@error_wrap
def rs_member_primary(rs_id):
    logger.debug("rs_member_primary({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)

    result = RS().primary(rs_id)
    return send_result(200, result)


@route('/rs/<rs_id>/primary/stepdown', method='PUT')
@error_wrap
def primary_stepdown(rs_id):
    logger.debug("primary_stepdown({rs_id})".format(**locals()))
    if rs_id not in RS():
        return send_result(404)

    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    RS().primary_stepdown(rs_id, data.get('timeout', 60))
    return send_result(200)


if __name__ == '__main__':
    rs = RS()
    rs.set_settings()
    run(host='localhost', port=8889, debug=True, reloader=False)
