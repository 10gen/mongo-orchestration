#!/usr/bin/python
# coding=utf-8
import sys
import os
import argparse
import json
import atexit
from daemon import Daemon

work_dir = os.path.split(os.path.join(os.getcwd(), __file__))[0]

pid_file = os.path.join(work_dir, 'server.pid')
log_file = os.path.join(work_dir, 'server.log')
cfg_file = os.path.join(work_dir, 'mongo-orchestration.config')

DEFAULT_PORT = 8889

import logging
logging.basicConfig(level=logging.DEBUG, filename=log_file, filemode='w')


def read_env():
    """return command-line arguments"""
    parser = argparse.ArgumentParser(description='mongo-orchestration server')
    parser.add_argument('-f', '--config', action='store', default=cfg_file, type=str, dest='config')
    parser.add_argument('-e', '--env', action='store', type=str, dest='env', default='default')
    parser.add_argument(action='store', type=str, dest='command', default='start', choices=('start', 'stop', 'restart'))
    parser.add_argument('--no-fork', action='store_true', dest='no_fork', default=False)
    parser.add_argument('-p', '--port', action='store', dest='port', default=DEFAULT_PORT)
    cli_args = parser.parse_args()

    if cli_args.command == 'stop':
        return cli_args
    try:
        # read config
        config = json.loads(open(cli_args.config, 'r').read())
        cli_args.release_path = config['releases'][cli_args.env]
        return cli_args
    except (IOError):
        print("config file not found")
        sys.exit(1)
    except (ValueError):
        print("config file is corrupted")
        sys.exit(1)


def setup(release_path):
    """setup storages"""
    from lib import set_bin_path, cleanup_storage
    set_bin_path(release_path)
    atexit.register(cleanup_storage)


def get_app():
    """return bottle app that includes all sub-apps"""
    from bottle import default_app
    default_app.push()
    for module in ("apps.hosts", "apps.rs", "apps.sh"):
        __import__(module)
    app = default_app.pop()
    return app


class MyDaemon(Daemon):
    """class uses to run server as daemon"""

    def __init__(self, *args, **kwd):
        super(MyDaemon, self).__init__(*args, **kwd)

    def run(self):
        from bottle import run
        setup(getattr(self.args, "release_path", ""))
        if self.args.command in ('start', 'restart'):
            run(get_app(), host='localhost', port=self.args.port, debug=False, reloader=False, quiet=not self.args.no_fork)

    def set_args(self, args):
        self.args = args

if __name__ == "__main__":
    daemon = MyDaemon(pid_file, timeout=5)
    args = read_env()
    daemon.set_args(args)
    if args.command == 'stop':
        setup(getattr(args, "release_path", ""))
        daemon.stop()
    if args.command == 'start' and not args.no_fork:
        daemon.start()
    if args.command == 'start' and args.no_fork:
        daemon.run()
    if args.command == 'restart':
        daemon.restart()
