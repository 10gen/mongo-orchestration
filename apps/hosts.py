#!/usr/bin/python
# coding=utf-8

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import json
import traceback
import sys
sys.path.insert(0, '..')
from lib.hosts import Hosts
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
        logger.debug("{f_name}({arg}, {kwd})".format(**locals()))
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


@route('/hosts', method='POST')
@error_wrap
def host_create():
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    host_id = Hosts().create(data['name'],
                             data.get('params', {}),
                             data.get('auth_key', ''),
                             data.get('login', ''), data.get('password', ''),
                             data.get('timeout', 300),
                             data.get('autostart', True))
    result = Hosts().info(host_id)
    return send_result(200, result)


@route('/hosts', method='GET')
@error_wrap
def host_list():
    logger.debug("host_list()")
    data = [info for info in Hosts()]
    return send_result(200, data)


@route('/hosts/<host_id>', method='GET')
@error_wrap
def host_info(host_id):
    logger.debug("host_info({host_id})".format(**locals()))
    if host_id not in Hosts():
        return send_result(404)
    result = Hosts().info(host_id)
    return send_result(200, result)


@route('/hosts/<host_id>', method='DELETE')
@error_wrap
def host_del(host_id):
    logger.debug("host_del({host_id})")
    if host_id not in Hosts():
        return send_result(404)
    Hosts().remove(host_id)
    return send_result(204)


@route('/hosts/<host_id>/<command:re:(start)|(stop)|(restart)>', method='PUT')
@error_wrap
def host_command(host_id, command):
    logger.debug("host_command({host_id}, {command})".format(**locals()))
    if host_id not in Hosts():
        return send_result(404)
    Hosts().command(host_id, command)
    return send_result(200)


if __name__ == '__main__':
    hs = Hosts()
    hs.set_settings('/tmp/mongo-orchestration.hs-storage', '')
    run(host='localhost', port=8889, debug=True, reloader=False)
