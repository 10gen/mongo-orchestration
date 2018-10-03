'use strict';

const request = require('request-promise');

function defaultRequestFunction(method, uri, body) {
  return request({ method, uri, body });
}

module.exports = { defaultRequestFunction };
