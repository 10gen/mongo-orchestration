'use strict';

const chai = require('chai');
const expect = chai.expect;
const sinon = require('sinon');
chai.use(require('sinon-chai'));

const Crud = require('../lib/crud').Crud;
const configs = require('./crud_test_config');

describe('CRUD', function() {
  it('is a constructor', function() {
    expect(Crud).to.be.a('function');
    expect(() => new Crud()).to.not.throw();
  });

  function makeCrud(baseUrl) {
    const crud = new Crud({ baseUrl });
    sinon.stub(crud, 'requestFn');
    return crud;
  }

  configs.forEach(config => {
    it(config.description, function() {
      const args = config.args || [];

      const crud = makeCrud();
      return config.fn.apply(null, [crud].concat(args)).then(() => {
        expect(crud.requestFn).to.have.been.calledOnce;
        expect(crud.requestFn).to.have.been.calledWithMatch(
          config.method,
          config.route,
          config.body
        );
      });
    });
  });
});
