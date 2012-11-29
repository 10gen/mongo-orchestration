# coding=utf-8
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import json
import sys

sys.path.insert(0, '..')
from lib.shards import Shards
from bottle import route, request, response, abort, run


def send_result(code, result=None):
    logger.debug("send_result({code}, {result})".format(**locals()))
    content = None
    response.content_type = None
    if result is not None:
            content = json.dumps(result)
            response.content_type = "application/json"
    response.status = code
    if code > 399:
        return abort(code, content)
    return content


@route('/sh', method='POST')
def sh_create():
    logger.debug("sh_create()")
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        sh_id = Shards().sh_new(data)
        result = Shards().sh_info(sh_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_create".format(**locals()))
        return send_result(500)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh', method='GET')
def sh_list():
    logger.debug("sh_list()")
    try:
        data = [info for info in Shards()]
    except StandardError as e:
        logger.error("Exception {e} while sh_list".format(**locals()))
        return send_result(500)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, data)


@route('/sh/<sh_id>', method='GET')
def sh_info(sh_id):
    logger.debug("sh_info({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    try:
        result = Shards().sh_info(sh_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_info".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh/<sh_id>', method='DELETE')
def sh_del(sh_id):
    logger.debug("sh_del({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    try:
        result = Shards().sh_del(sh_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_del".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(204, result)


@route('/sh/<sh_id>/members', method='POST')
def sh_member_add(sh_id):
    logger.debug("sh_member_add({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        result = Shards().sh_member_info(sh_id, data)
    except StandardError as e:
        logger.error("Exception {e} while sh_member_add".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh/<sh_id>/members', method='GET')
def sh_members(sh_id):
    logger.debug("sh_members({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    try:
        result = Shards().sh_members(sh_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_members".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh/<sh_id>/configservers', method='GET')
def sh_configservers(sh_id):
    logger.debug("sh_configservers({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    try:
        result = Shards().sh_configservers(sh_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_configservers".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh/<sh_id>/routers', method='GET')
def sh_routers(sh_id):
    logger.debug("sh_routers({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    try:
        result = Shards().sh_routers(sh_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_routers".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh/<sh_id>/routers', method='POST')
def sh_router_add(sh_id):
    logger.debug("sh_router_add({sh_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    data = {}
    json_data = request.body.read()
    if json_data:
        data = json.loads(json_data)
    try:
        result = Shards().sh_router_add(sh_id, data)
    except StandardError as e:
        logger.error("Exception {e} while sh_router_add".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh/<sh_id>/members/<member_id>', method='GET')
def sh_member_info(sh_id, member_id):
    logger.debug("sh_member_info({sh_id}, {member_id})".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    try:
        result = Shards().sh_member_info(sh_id, member_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_member_info".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


@route('/sh/<sh_id>/members/<member_id>', method='DELETE')
def sh_member_del(sh_id, member_id):
    logger.debug("sh_member_del({sh_id}), {member_id}".format(**locals()))
    if sh_id not in Shards():
        return send_result(404)
    try:
        result = Shards().sh_member_del(sh_id, member_id)
    except StandardError as e:
        logger.error("Exception {e} while sh_member_del".format(**locals()))
        return send_result(400)
    except Exception as e:
        logger.critical("Unknown Exception {e}".format(**locals()))
        return send_result(500)
    return send_result(200, result)


if __name__ == '__main__':
    rs = Shards()
    rs.set_settings('/tmp/mongo-orchestration.rs-storage', '')
    run(host='localhost', port=8889, debug=True, reloader=False)
