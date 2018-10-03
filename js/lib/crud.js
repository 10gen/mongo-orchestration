'use strict';

const defaultRequestFunction = require('./defaultRequestFunction').defaultRequestFunction;

class CrudBase {
  constructor(options) {
    options = options || {};
    this.baseUrl = options.baseUrl || '/v1';
    this.requestFn =
      typeof options.requestFn === 'function' ? options.requestFn : defaultRequestFunction;
  }

  request(method, route, body) {
    if (typeof route === 'object' && typeof body === 'undefined') {
      body = route;
      route = '';
    }

    route = route || '';

    const uri = `${this.baseUrl}/${route}`;

    return Promise.resolve().then(() => this.requestFn(method, uri, body));
  }
}

class CrudServer extends CrudBase {
  info() {
    return this.request('GET');
  }

  command(body) {
    return this.request('POST', body);
  }

  remove() {
    return this.request('DELETE');
  }
}

class CrudReplicaSetMember extends CrudBase {
  info() {
    return this.request('GET');
  }

  configure(body) {
    return this.request('PATCH', body);
  }

  remove() {
    return this.request('DELETE');
  }
}

class CrudReplicaSet extends CrudBase {
  info() {
    return this.request('GET');
  }

  command(body) {
    return this.request('POST', body);
  }

  remove() {
    return this.request('DELETE');
  }

  addMember(body) {
    return this.request('POST', 'members', body);
  }

  members() {
    return this.request('GET', 'members');
  }

  member(id) {
    return new CrudReplicaSetMember({
      baseUrl: `${this.baseUrl}/members/${id}`,
      requestFn: this.requestFn
    });
  }

  servers() {
    return this.request('GET', 'servers');
  }

  primary() {
    return this.request('GET', 'primary');
  }

  secondaries() {
    return this.request('GET', 'secondaries');
  }

  arbiters() {
    return this.request('GET', 'arbiters');
  }

  hidden() {
    return this.request('GET', 'hidden');
  }
}

class CrudShard extends CrudBase {
  info() {
    return this.request('GET');
  }

  remove() {
    return this.request('DELETE');
  }
}

class CrudRouter extends CrudBase {
  remove() {
    return this.request('DELETE');
  }
}

class CrudShardedCluster extends CrudBase {
  info() {
    return this.request('GET');
  }

  command(body) {
    return this.request('POST', body);
  }

  remove() {
    return this.request('DELETE');
  }

  addShard(body) {
    return this.request('POST', 'shards', body);
  }

  shards() {
    return this.request('GET', 'shards');
  }

  shard(id) {
    return new CrudShard({
      baseUrl: `${this.baseUrl}/shards/${id}`,
      requestFn: this.requestFn
    });
  }

  configServers() {
    return this.request('GET', 'configsvrs');
  }

  addRouter(body) {
    return this.request('POST', 'routers', body);
  }

  routers() {
    return this.request('GET', 'routers');
  }

  router(id) {
    return new CrudRouter({
      baseUrl: `${this.baseUrl}/routers/${id}`,
      requestFn: this.requestFn
    });
  }
}

class Crud extends CrudBase {
  // Basic Mongo-Orchestration Info
  info() {
    return this.request('GET');
  }

  releases() {
    return this.request('GET', 'releases');
  }

  // API for individual servers
  servers() {
    return this.request('GET', 'servers');
  }

  createServer(id, body) {
    if (typeof id === 'string') {
      return this.request('PUT', `servers/${id}`, body);
    }
    return this.request('POST', 'servers', id);
  }

  server(id) {
    return new CrudServer({
      baseUrl: `${this.baseUrl}/servers/${id}`,
      requestFn: this.requestFn
    });
  }

  // API for Replicasets
  createReplicaSet(id, body) {
    if (typeof id === 'string') {
      return this.request('PUT', `replica_sets/${id}`, body);
    }
    return this.request('POST', 'replica_sets', id);
  }

  replicaSet(id) {
    return new CrudReplicaSet({
      baseUrl: `${this.baseUrl}/replica_sets/${id}`,
      requestFn: this.requestFn
    });
  }

  // API for Sharded Clusters
  createShardedCluster(id, body) {
    if (typeof id === 'string') {
      return this.request('PUT', `sharded_clusters/${id}`, body);
    }
    return this.request('POST', 'sharded_clusters', id);
  }

  shardedCluster(id) {
    return new CrudShardedCluster({
      baseUrl: `${this.baseUrl}/sharded_clusters/${id}`,
      requestFn: this.requestFn
    });
  }
}

module.exports = { Crud };
