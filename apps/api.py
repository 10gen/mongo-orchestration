#!/usr/bin/python
# coding=utf-8

import json
import traceback
import sys
from bottle import route, request, response


def send_result(code, result=None):
    content = None
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Allow', 'GET, POST, DELETE, PUT')
    response.content_type = None
    if result is not None:
            content = json.dumps(result)
            response.content_type = "application/json"
    response.status = code
    return content


def error_wrap(f):
    def wrap(*arg, **kwd):
        try:
            return f(*arg, **kwd)
        except StandardError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
            return send_result(500, err_message)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            err_message = traceback.format_exception(exc_type, exc_value, exc_tb)
            return send_result(500, err_message)

    return wrap


@route('/api', method="GET")
@error_wrap
def documentation():
    content = open('/home/mmamrouski/development/mongo-orchestration/docs/api-doc.json', 'r').read().replace('\n', ' ')
    content = json.loads(content)
    response.set_header('Allow', 'GET, POST, DELETE, PUT')
    return send_result(200, content)


@route('/api/hosts', method="GET")
@error_wrap
def documentation_hosts():
    content = open('/home/mmamrouski/development/mongo-orchestration/docs/api-hosts.json', 'r').read().replace('\n', ' ')
    content = json.loads(content)
    return send_result(200, content)


@route('/api/rs', method="GET")
@error_wrap
def documentation_rs():
    content = open('/home/mmamrouski/development/mongo-orchestration/docs/api-rs.json', 'r').read().replace('\n', ' ')
    content = json.loads(content)
    return send_result(200, content)


@route('/api/sh', method="GET")
@error_wrap
def documentation_sh():
    content = open('/home/mmamrouski/development/mongo-orchestration/docs/api-sh.json', 'r').read().replace('\n', ' ')
    content = json.loads(content)
    return send_result(200, content)


@route('/hosts', method="OPTIONS")
@error_wrap
def hosts_options():
    content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<application xmlns="http://wadl.dev.java.net/2009/02">
    <doc xmlns:jersey="http://jersey.java.net/" jersey:generatedBy="Jersey: 1.13 06/29/2012 05:14 PM"/>
    <grammars/>
    <resources base="http://localhost:8889/api/">
        <resource path="hosts">
            <method name="POST" id="createHost">
                <response>
                    <representation mediaType="application/json"/>
                </response>
            </method>
        </resource>
    </resources>
</application>
    """
    response.set_header('Access-Control-Allow-Headers', 'Content-Type, api_key, Authorization')
    response.set_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, PUT')
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Allow', 'OPTIONS, POST')
    response.status = 200
    response.content_type = "application/vnd.sun.wadl+xml"
    return content

    # return send_result(200, content)
