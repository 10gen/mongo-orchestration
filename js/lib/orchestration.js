'use strict';

const cliCommands = require('./cliCommands');
const Crud = require('./crud').Crud;
const defaultRequestFunction = require('./defaultRequestFunction').defaultRequestFunction;

const DEFAULT_OPTIONS = {
  bind: '127.0.0.1',
  port: 8888
};

class Conductor {
  constructor(options) {
    this.options = Object.assign({}, DEFAULT_OPTIONS, options);
    this._p = Promise.resolve();
    const baseUrl = this.baseUrl;
    const requestFn = (method, uri, body) =>
      this.run(() => defaultRequestFunction(method, uri, body));

    Object.defineProperty(this, 'crud', {
      value: new Crud({ baseUrl, requestFn })
    });
  }

  get port() {
    return this.options.port;
  }

  get binding() {
    return this.options.bind;
  }

  get address() {
    return `${this.binding}:${this.port}`;
  }

  get baseUrl() {
    return `http://${this.binding}:${this.port}/v1`;
  }

  run(fn) {
    this._p = this._p.then(() => fn());
    return this._p;
  }

  start() {
    return this.run(() => cliCommands.start(this.options));
  }

  stop() {
    return this.run(() => cliCommands.stop(this.options));
  }
}

module.exports = { Conductor };
