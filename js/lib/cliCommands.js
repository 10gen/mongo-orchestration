'use strict';

const childProcess = require('child_process');
const path = require('path');

const moPath = path.resolve(__dirname, '..', 'mongo_orchestration', 'server.py');

// MongoOrchestration Options
// -h, --help            show this help message and exit
// -f CONFIG, --config CONFIG
// -e ENV, --env ENV
// --no-fork
// -b BIND, --bind BIND
// -p PORT, --port PORT
// --enable-majority-read-concern
// -s {cherrypy,wsgiref}, --server {cherrypy,wsgiref}
// --version             show program's version number and exit
// --socket-timeout-ms SOCKET_TIMEOUT
// --pidfile PIDFILE

function optionsToCliArgs(options) {
  options = options || {};
  const cliArgs = [];
  ['config', 'env', 'bind', 'port', 'pidfile', 'server'].forEach(option => {
    if (options[option]) {
      cliArgs.push(`--${option}`);
      cliArgs.push(options[option]);
    }
  });

  if (options.enableMajorityReadConcern) {
    cliArgs.push('--enable-majority-read-concern');
  }

  if (options.noFork) {
    cliArgs.push('--no-fork');
  }

  if (options.socketTimeoutMs) {
    cliArgs.push('--socket-timeout-ms');
    cliArgs.push(options.socketTimeoutMs);
  }

  return cliArgs;
}

function runOrchestrationCommand(cmd, cliArgs) {
  const args = [moPath, cmd].concat(cliArgs);
  return new Promise((resolve, reject) => {
    const proc = childProcess.spawn('python', args, { detatched: true, stdio: 'ignore' });

    proc.on('error', err => reject(err));
    proc.on('close', code => (code ? reject(code) : resolve()));
  });
}

function makeCommand(name) {
  return function(options) {
    return runOrchestrationCommand(name, optionsToCliArgs(options));
  };
}

module.exports = {
  start: makeCommand('start'),
  stop: makeCommand('stop'),
  restart: makeCommand('restart')
};
