from collections import namedtuple

from bottle import route

Route = namedtuple('Route', ('path', 'method'))


def setup_versioned_routes(routes, version=None):
    """Set up routes with a version prefix."""
    prefix = '/' + version if version else ""
    for r in routes:
        path, method = r
        route(prefix + path, method, routes[r])
