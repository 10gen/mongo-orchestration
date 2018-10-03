'use strict';

module.exports = [
  {
    description: 'should properly get info',
    method: 'GET',
    route: '/v1/',
    body: undefined,
    fn: crud => crud.info()
  },
  {
    description: 'should properly get releases',
    method: 'GET',
    route: '/v1/releases',
    body: undefined,
    fn: crud => crud.releases()
  },
  {
    description: 'should properly get all servers',
    method: 'GET',
    route: '/v1/servers',
    body: undefined,
    fn: crud => crud.servers()
  },
  {
    description: 'should properly add a new server',
    method: 'POST',
    route: '/v1/servers',
    body: { foo: 'bar' },
    args: [{ foo: 'bar' }],
    fn: (crud, body) => crud.createServer(body)
  },
  {
    description: 'should properly add a new server with id',
    method: 'PUT',
    route: '/v1/servers/foo',
    body: { foo: 'bar' },
    args: ['foo', { foo: 'bar' }],
    fn: (crud, id, body) => crud.createServer(id, body)
  },
  {
    description: 'should properly add a new replicaSet',
    method: 'POST',
    route: '/v1/replica_sets',
    body: { foo: 'bar' },
    args: [{ foo: 'bar' }],
    fn: (crud, body) => crud.createReplicaSet(body)
  },
  {
    description: 'should properly add a new replicaSet with id',
    method: 'PUT',
    route: '/v1/replica_sets/foo',
    body: { foo: 'bar' },
    args: ['foo', { foo: 'bar' }],
    fn: (crud, id, body) => crud.createReplicaSet(id, body)
  },
  {
    description: 'should properly add a new sharded cluster',
    method: 'POST',
    route: '/v1/sharded_clusters',
    body: { foo: 'bar' },
    args: [{ foo: 'bar' }],
    fn: (crud, body) => crud.createShardedCluster(body)
  },
  {
    description: 'should properly add a new sharded cluster with id',
    method: 'PUT',
    route: '/v1/sharded_clusters/foo',
    body: { foo: 'bar' },
    args: ['foo', { foo: 'bar' }],
    fn: (crud, id, body) => crud.createShardedCluster(id, body)
  },
  {
    description: 'should properly get info from a single server',
    method: 'GET',
    route: '/v1/servers/foo/',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.server(id).info()
  },
  {
    description: 'should properly delete a single server',
    method: 'DELETE',
    route: '/v1/servers/foo/',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.server(id).remove()
  },
  {
    description: 'should properly command a single server',
    method: 'POST',
    route: '/v1/servers/foo/',
    body: { cmd: 'fizz' },
    args: ['foo', { cmd: 'fizz' }],
    fn: (crud, id, cmd) => crud.server(id).command(cmd)
  },
  {
    description: 'should properly get info from a single replicaSet',
    method: 'GET',
    route: '/v1/replica_sets/foo/',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).info()
  },
  {
    description: 'should properly command a single replicaSet',
    method: 'POST',
    route: '/v1/replica_sets/foo/',
    body: { cmd: 'fizz' },
    args: ['foo', { cmd: 'fizz' }],
    fn: (crud, id, cmd) => crud.replicaSet(id).command(cmd)
  },
  {
    description: 'should properly delete a single replicaSet',
    method: 'DELETE',
    route: '/v1/replica_sets/foo/',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).remove()
  },
  {
    description: 'should properly add a replicaSet member',
    method: 'POST',
    route: '/v1/replica_sets/foo/members',
    body: { cmd: 'fizz' },
    args: ['foo', { cmd: 'fizz' }],
    fn: (crud, id, body) => crud.replicaSet(id).addMember(body)
  },
  {
    description: 'should properly get all replicaSet members',
    method: 'GET',
    route: '/v1/replica_sets/foo/members',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).members()
  },
  {
    description: 'should properly get all replicaSet servers',
    method: 'GET',
    route: '/v1/replica_sets/foo/servers',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).servers()
  },
  {
    description: 'should properly get a replicaSet primary',
    method: 'GET',
    route: '/v1/replica_sets/foo/primary',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).primary()
  },
  {
    description: 'should properly get all replicaSet secondaries',
    method: 'GET',
    route: '/v1/replica_sets/foo/secondaries',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).secondaries()
  },
  {
    description: 'should properly get all replicaSet arbiters',
    method: 'GET',
    route: '/v1/replica_sets/foo/arbiters',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).arbiters()
  },
  {
    description: 'should properly get all replicaSet hidden members',
    method: 'GET',
    route: '/v1/replica_sets/foo/hidden',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.replicaSet(id).hidden()
  },
  {
    description: 'should properly get info on a replicaSet member',
    method: 'GET',
    route: '/v1/replica_sets/foo/members/bar/',
    body: undefined,
    args: ['foo', 'bar'],
    fn: (crud, id, id2) =>
      crud
        .replicaSet(id)
        .member(id2)
        .info()
  },
  {
    description: 'should properly configure a replicaSet member',
    method: 'PATCH',
    route: '/v1/replica_sets/foo/members/bar/',
    body: { fizz: 'buzz' },
    args: ['foo', 'bar', { fizz: 'buzz' }],
    fn: (crud, id, id2, body) =>
      crud
        .replicaSet(id)
        .member(id2)
        .configure(body)
  },
  {
    description: 'should properly remove a replicaSet member',
    method: 'DELETE',
    route: '/v1/replica_sets/foo/members/bar/',
    body: undefined,
    args: ['foo', 'bar'],
    fn: (crud, id, id2) =>
      crud
        .replicaSet(id)
        .member(id2)
        .remove()
  },
  {
    description: 'should properly get info on a sharded cluster',
    method: 'GET',
    route: '/v1/sharded_clusters/foo/',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.shardedCluster(id).info()
  },
  {
    description: 'should properly remove a sharded cluster',
    method: 'DELETE',
    route: '/v1/sharded_clusters/foo/',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.shardedCluster(id).remove()
  },
  {
    description: 'should properly command a sharded cluster',
    method: 'POST',
    route: '/v1/sharded_clusters/foo/',
    body: { cmd: 'fizz' },
    args: ['foo', { cmd: 'fizz' }],
    fn: (crud, id, cmd) => crud.shardedCluster(id).command(cmd)
  },
  {
    description: 'should properly add a shard to a sharded cluster',
    method: 'POST',
    route: '/v1/sharded_clusters/foo/shards',
    body: { cmd: 'fizz' },
    args: ['foo', { cmd: 'fizz' }],
    fn: (crud, id, cmd) => crud.shardedCluster(id).addShard(cmd)
  },
  {
    description: 'should properly get all shards in a sharded cluster',
    method: 'GET',
    route: '/v1/sharded_clusters/foo/shards',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.shardedCluster(id).shards()
  },
  {
    description: 'should properly get all configu servers in a sharded cluster',
    method: 'GET',
    route: '/v1/sharded_clusters/foo/configsvrs',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.shardedCluster(id).configServers()
  },
  {
    description: 'should properly get all routers in a sharded cluster',
    method: 'GET',
    route: '/v1/sharded_clusters/foo/routers',
    body: undefined,
    args: ['foo'],
    fn: (crud, id) => crud.shardedCluster(id).routers()
  },
  {
    description: 'should properly get info on a shards in a sharded cluster',
    method: 'GET',
    route: '/v1/sharded_clusters/foo/shards/bar/',
    body: undefined,
    args: ['foo', 'bar'],
    fn: (crud, id, id2) =>
      crud
        .shardedCluster(id)
        .shard(id2)
        .info()
  },
  {
    description: 'should properly remove a shards from a sharded cluster',
    method: 'DELETE',
    route: '/v1/sharded_clusters/foo/shards/bar/',
    body: undefined,
    args: ['foo', 'bar'],
    fn: (crud, id, id2) =>
      crud
        .shardedCluster(id)
        .shard(id2)
        .remove()
  },
  {
    description: 'should properly remove a router from a sharded cluster',
    method: 'DELETE',
    route: '/v1/sharded_clusters/foo/routers/bar/',
    body: undefined,
    args: ['foo', 'bar'],
    fn: (crud, id, id2) =>
      crud
        .shardedCluster(id)
        .router(id2)
        .remove()
  }
];
