#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-04-21 10:00:00

import pymysql
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class MySqlHelper:
    """
    MySql帮助类
    """

    def __init__(self, **config):
        self.username = config['username'] if 'username' in config else 'root'
        self.password = config['password'] if 'password' in config else 'root'
        self.database = config['database'] if 'database' in config else 'db'
        self.host = config['host'] if 'host' in config else 'localhost'
        self.port = config['port'] if 'port' in config else 3306
        self.charset = config['charset'] if 'charset' in config else "utf8"
        self.connection = None
        self.connect()

    @staticmethod
    def escape(string):
        return '`%s`' % string

    def connect(self):
        """
        建立连接
        """
        if self.connection:
            self.connection.close()
        try:
            self.connection = pymysql.connect(
                user=self.username,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database,
                charset='utf8mb4')
            return True
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return False

    def disconnect(self):
        """
        断开连接
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def replace(self, table='', close=False, record=None):
        """
        根据主键或唯一索引更新记录或新增记录，注意replace方法将删除具有相同主键或唯一索引值的记录，然后插入新记录，注意其使用场景
        :param str table: 表名
        :param bool close: 结束后断开连接
        :param dict record: 更新或新增的记录
        :return bool: 操作成功与否
        """
        if record is None:
            record = {}
        if self.connection is None or not self.connection.open:
            self.connect()

        table = self.escape(table)

        cur = None
        try:
            cur = self.connection.cursor()
            if record:
                keys, values = zip(*record.items())
                sql = 'replace into %s (%s) values (%s)' % (table,
                                                            ', '.join([self.escape(key) for key in keys]),
                                                            ', '.join(['%s', ] * len(values)))
                cur.execute(sql, self._to_none(values))
                self.connection.commit()
            return True
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return False
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def replace_many(self, table='', close=False, records=None):
        """
        根据主键更新记录或新增多条记录
        :param str table: 表名
        :param bool close: 结束后断开连接
        :param list records: 更新或新增的记录集合，item是dict
        :return bool: 操作成功与否
        """
        if records is None:
            records = []
        if self.connection is None or not self.connection.open:
            self.connect()

        table = self.escape(table)
        cur = None
        try:
            cur = self.connection.cursor()
            if records and len(records) > 0:
                keys, values = zip(*records[0].items())
                sql = 'replace into %s (%s) values (%s)' % (table,
                                                            ', '.join(self.escape(k) for k in keys),
                                                            ', '.join(['%s', ] * len(values)))
                arr = []
                for result in records:
                    arr.append(self._to_none(result.values()))
                cur.executemany(sql, arr)
                self.connection.commit()
            return True
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return False
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def update(self, table='', where='', close=False, record=None):
        """
        更新一个表中的一条记录
        :param str table: 表名
        :param str where: sql条件语句
        :param bool close: 结束后断开连接
        :param dict record: 更新的记录
        :return bool: 操作成功与否
        """
        if record is None:
            record = {}
        if self.connection is None or not self.connection.open:
            self.connect()
        table = self.escape(table)
        cur = None
        try:
            cur = self.connection.cursor()
            if record:
                pairs = ', '.join(self.escape(k) + '=%s' for k in record)
                w = (' where ' + where) if where else ''
                sql = 'update %s set %s %s' % (table, pairs, w)
                cur.execute(sql, self._to_none(record.values()))
                self.connection.commit()
            return True
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return False
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def insert(self, table='', close=False, record=None):
        """
        根据条件插入数据
        :param str table: 表名
        :param bool close: 是否结束时关闭连接
        :param dict record: 待插入数据
        :return bool: 操作成功与否
        """

        if record is None:
            record = {}
        if self.connection is None or not self.connection.open:
            self.connect()

        table = self.escape(table)
        cur = None
        try:
            cur = self.connection.cursor()
            if record:
                keys, values = zip(*record.items())
                sql = 'insert into %s (%s) values (%s);' % (table,
                                                            ', '.join([self.escape(k) for k in keys]),
                                                            ', '.join(['%s', ] * len(values)))
                cur.execute(sql, self._to_none(values))
                self.connection.commit()
            return True
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return False
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def exist_table(self, table=''):
        """
        检查表是否存在
        :param str table: 表名
        :return bool: 操作成功与否
        """
        tables = self.sql('show tables')
        for t in tables:
            if table in t.values():
                return True
        return False

    def exec_procedure(self, name=None, params=None):
        """
        执行存储过程
        :param str name: 存储过程名
        :param list params: 存储过程参数
        :return bool: 操作成功与否
        """

        if self.connection is None or not self.connection.open:
            self.connect()

        cur = None
        try:
            cur = self.connection.cursor()
            cur.callproc(name, params)
            return True
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return False
        finally:
            if cur:
                cur.close()

    def select(self, fields='*', table='', page_size=100, page_number=1, where='', order_by='', close=False):
        """
        查询一个表中的记录
        :param str fields: 查询的字段
        :param str table: 表名
        :param int page_size: 获取记录数，等于0不分页
        :param int page_number: 页码，大于0的数字
        :param str where: sql条件语句
        :param str order_by: sql排序语句
        :param bool close: 结束后断开连接
        :return list: 结果记录集合，item是dict
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        table = self.escape(table)
        cur = None
        try:
            cur = self.connection.cursor(pymysql.cursors.DictCursor)
            w = (' where ' + where) if where else ''
            o = (' order by ' + order_by) if order_by else ''
            offset = (page_number - 1) * page_size
            p = (' limit %d, %d' % (offset, page_size)) if page_size else ''
            sql = 'select %s from %s%s%s%s' % (fields, table, w, o, p)
            cur.execute(sql)
            return cur.fetchall()
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return []
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def select_tables(self, fields='*', table=None, page_size=100, page_number=1, where=None, order_by='', close=False):
        """
        查询多个表中的记录
        :param str fields: 查询的字段
        :param str table: 表名列表
        :param int page_size: 获取记录数，等于0不分页
        :param int page_number: 页码，大于0的数字
        :param str where: sql条件语句
        :param str order_by: sql排序语句
        :param bool close: 结束后断开连接
        :return list: 结果记录集合，item是dict
        """
        if where is None:
            where = []
        if table is None:
            table = []
        if self.connection is None or not self.connection.open:
            self.connect()

        for x in range(len(table)):
            table[x] = self.escape(table[x])
        cur = None
        try:
            cur = self.connection.cursor(pymysql.cursors.DictCursor)
            w = [(' where ' + x) for x in where if x] if [(' where ' + x) for x in where if x] else []
            w.extend([''] * (len(table) - len(w)))
            o = (' order by ' + order_by) if order_by else ''
            offset = (page_number - 1) * page_size
            p = (' limit %d,%d' % (offset, page_size)) if page_size else ''
            sql_union = ''
            for i in range(len(table)):
                sql = 'select %s from %s%s' % (fields, table[i], w[i])
                if i < len(table) - 1:
                    sql_union += sql + ' union '
                else:
                    sql_union += sql + '%s%s' % (o, p)
            cur.execute(sql_union)
            return cur.fetchall()
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return []
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def select_one(self, table='', where='', close=False):
        """
        查询一个表中的一条记录
        :param table: 表名
        :param where: sql条件语句
        :param close: 结束后断开连接
        :return dict: 结果记录
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        table = self.escape(table)
        cur = None
        try:
            cur = self.connection.cursor(pymysql.cursors.DictCursor)
            w = (' where ' + where) if where else ''
            sql = 'select * from %s%s' % (table, w)
            cur.execute(sql)
            return cur.fetchone()
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return {}
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def sql(self, sql, close=False):
        """
        执行sql语句
        :param str sql: sql完整语句
        :param bool close: 结束后断开连接
        :return list: 结果记录集合，item是dict
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        cur = None
        try:
            cur = self.connection.cursor(pymysql.cursors.DictCursor)
            cur.execute(sql)
            self.connection.commit()
            try:
                return cur.fetchall()
            except Exception:
                return None
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return []
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    def count(self, table='', where='', close=False):
        """
        查询一个表中的记录数
        :param str table: 表名
        :param str where: sql条件语句
        :param bool close: 结束后断开连接
        :return int: 记录数
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        table = self.escape(table)
        cur = None
        try:
            cur = self.connection.cursor(pymysql.cursors.DictCursor)
            w = (' where ' + where) if where else ''
            sql = 'select count(*) as count from %s %s' % (table, w)
            cur.execute(sql)
            return cur.fetchone()
        except Exception:
            logger.error('An error occurred', exc_info=True)
            return 0
        finally:
            if cur:
                cur.close()
            if close:
                self.disconnect()

    @staticmethod
    def _to_none(values):
        """
        替换nan等特殊空值
        """
        return [None if pd.isna(value) else value for value in values]


if __name__ == "__main__":
    helper = MySqlHelper(username='root', password='root', host='127.0.0.1', port=3306, database='test')
    print(helper.exist_table('quotation'))
    helper.sql('update quotation set close_price=100 where id=1')
    r = helper.sql('select * from quotation')
    print(r)
    q = helper.select_one(table='quotation', where='id=1')
    print(q)
    q['close_price'] = 200
    helper.replace(table='quotation', record=q)
    q = helper.select(table='quotation', where='id=1')
    print(q)
