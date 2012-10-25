# coding=utf-8

from UserDict import DictMixin
import sqlite3 as sqlite
from pickle import dumps, loads
import threading


class Storage(DictMixin, object):
    """Dict-like storage, use sqlite to store items"""
    def __init__(self, path, name):
        self.db = path
        self.name = name
        self.local = threading.local()

        with self.connect() as conn:
            query = "create table if not exists {name} (hash unique not null, key, value)".format(name=self.name)
            conn.execute(query)

    def connect(self):
        try:
            return self.local.conn
        except AttributeError:
            self.local.conn = sqlite.connect(self.db)
        return self.local.conn

    def clear(self):
        with self.connect() as conn:
            query = "delete from {name}".format(name=self.name)
            conn.execute(query)

    def __getitem__(self, key):
        cursor = self.connect().cursor()
        cursor.execute("select value from {table} where hash = {h}".format(table=self.name, h=hash(key)))
        try:
            return loads(cursor.fetchone()[0])
        except (TypeError, IndexError):
            raise KeyError(key)

    def __setitem__(self, key, value):
        with self.connect() as conn:
            conn.execute('insert or replace into {table} values({h}, "{key}", "{value}")'.format(table=self.name,
                                                                                                 h=hash(key),
                                                                                                 key=dumps(key),
                                                                                                 value=dumps(value)))

    def __delitem__(self, key):
        with self.connect() as conn:
            conn.execute('delete from {table} where hash = {h}'.format(table=self.name, h=hash(key)))

    def __len__(self):
        cursor = self.connect().cursor()
        cursor.execute("select count(*) from {table}".format(table=self.name))
        return cursor.fetchone()[0]

    def __contains__(self, key):
        cursor = self.connect().cursor()
        cursor.execute("select value from {table} where hash = {h}".format(table=self.name, h=hash(key)))
        return not (cursor.fetchone() is None)

    def __iter__(self):
        cursor = self.connect().cursor()
        cursor.execute("select key from {table}".format(table=self.name))
        for row in cursor.fetchall():
            yield loads(row[0])
