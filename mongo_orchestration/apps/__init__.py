# Copyright 2012-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import sys
import traceback

from collections import namedtuple

from bottle import route, response

sys.path.insert(0, '..')

from mongo_orchestration.compat import reraise, PY3
from mongo_orchestration.errors import RequestError

if PY3:
    unicode = str

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


def get_json(req_body):
    try:
        str_body = req_body.read()
        if str_body:
            str_body = str_body.decode('utf-8')
            return json.loads(str_body)
        return {}
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        message = "Could not parse the JSON sent to the server."
        reraise(RequestError, message, exc_tb)
