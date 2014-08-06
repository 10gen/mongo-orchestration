#!/usr/bin/python
# coding=utf-8

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import json
import traceback
import sys

sys.path.insert(0, '..')
from lib.shards import Shards
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


@route('/sh', method='POST')
@error_wrap
def sh_create():
    logger.debug("sh_create()")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    sh_id = Shards().create(data)
    result = Shards().info(sh_id)
    return send_result(200, result)


@route('/sh', method='GET')
@error_wrap
def sh_list():
    logger.debug("sh_list()")
    data = [sh_info for sh_info in Shards()]
    return send_result(200, data)


@route('/sh/<sh_id>', method='GET')
@error_wrap
def info(sh_id):
    logger.debug("info({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().info(sh_id)
    return send_result(200, result)


@route('/sh/<sh_id>', method='DELETE')
@error_wrap
def sh_del(sh_id):
    logger.debug("sh_del({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().remove(sh_id)
    return send_result(204, result)


@route('/sh/<sh_id>/members', method='POST')
@error_wrap
def member_add(sh_id):
    logger.debug("member_add({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    result = Shards().member_add(sh_id, data)
    return send_result(200, result)


@route('/sh/<sh_id>/members', method='GET')
@error_wrap
def members(sh_id):
    logger.debug("members({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().members(sh_id)
    return send_result(200, result)


@route('/sh/<sh_id>/configservers', method='GET')
@error_wrap
def configservers(sh_id):
    logger.debug("configservers({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().configservers(sh_id)
    return send_result(200, result)


@route('/sh/<sh_id>/routers', method='GET')
@error_wrap
def routers(sh_id):
    logger.debug("routers({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().routers(sh_id)
    return send_result(200, result)


@route('/sh/<sh_id>/routers', method='POST')
@error_wrap
def router_add(sh_id):
    logger.debug("router_add({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    result = Shards().router_add(sh_id, data)
    return send_result(200, result)

@route('/sh/<sh_id>/routers/<router_id>', method='DELETE')
@error_wrap
def router_del(sh_id, router_id):
    logger.debug("router_del({sh_id}), {router_id}".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().router_del(sh_id, router_id)
    return send_result(200, result)

@route('/sh/<sh_id>/members/<member_id>', method='GET')
@error_wrap
def member_info(sh_id, member_id):
    logger.debug("member_info({sh_id}, {member_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().member_info(sh_id, member_id)
    return send_result(200, result)


@route('/sh/<sh_id>/members/<member_id>', method='DELETE')
@error_wrap
def member_del(sh_id, member_id):
    logger.debug("member_del({sh_id}), {member_id}".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    result = Shards().member_del(sh_id, member_id)
    return send_result(200, result)


if __name__ == '__main__':
    rs = Shards()
    rs.set_settings()
    run(host='localhost', port=8889, debug=True, reloader=False)
