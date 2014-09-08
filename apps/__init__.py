import json
import logging
import sys
import traceback

from collections import namedtuple

from bottle import route, response

sys.path.insert(0, '..')

from lib.compat import reraise
from lib.errors import RequestError

logger = logging.getLogger(__name__)

Route = namedtuple('Route', ('path', 'method'))


def setup_versioned_routes(routes, version=None):
    """Set up routes with a version prefix."""
    prefix = '/' + version if version else ""
    for r in routes:
        path, method = r
        route(prefix + path, method, routes[r])


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
        f_name = f.__name__
        logger.debug("{f_name}({arg}, {kwd})".format(
            f_name=f_name, arg=arg, kwd=kwd))
        try:
            return f(*arg, **kwd)
        except RequestError:
            err_message = traceback.format_exception(*sys.exc_info())
            logger.critical(err_message)
            return send_result(400, err_message)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            err_message = traceback.format_exception(
                exc_type, exc_value, exc_tb)
            logger.critical(
                "Exception {exc_type} {exc_value} while {f_name}".format(
                    **locals()))
            logger.critical(err_message)
            return send_result(500, err_message)

    return wrap


def get_json(req):
    try:
        return json.loads(req)
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        message = "Could not parse the JSON sent to the server."
        reraise(RequestError, message, exc_tb)
