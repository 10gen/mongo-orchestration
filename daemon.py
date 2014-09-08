#!/usr/bin/env python
# coding=utf-8
import atexit
import os
import sys
import time

from signal import SIGTERM

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'r+b')


class Daemon(object):
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method

    source: http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    def __init__(self, pidfile,
                 stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL,
                 timeout=0):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.timeout = timeout  # sleep before exit from parent

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.stdout.write("child process started successfully, parent exiting after {timeout} seconds\n".format(timeout=self.timeout))
                time.sleep(self.timeout)
                sys.exit(0)
        except OSError as error:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (error.errno, error.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as error:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (error.errno, error.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdin.flush()
        sys.stdout.flush()
        sys.stderr.flush()

        os.dup2(self.stdin.fileno(), sys.stdin.fileno())
        os.dup2(self.stdout.fileno(), sys.stdout.fileno())
        os.dup2(self.stderr.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)

    def delpid(self):
        """remove pidfile"""
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pidfile_fd = file(self.pidfile, 'r')
            pid = int(pidfile_fd.read().strip())
            pidfile_fd.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pidfile_fd = file(self.pidfile, 'r')
            pid = int(pidfile_fd.read().strip())
            pidfile_fd.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return  # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                raise

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
