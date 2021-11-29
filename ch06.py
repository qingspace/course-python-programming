#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-04-22 10:00:00

from paramiko import SFTPClient, SFTPFile, Transport
from threading import Timer
from datetime import datetime
from typing import Dict
from pytz import timezone
import os
import logging
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(thread)d %(levelname)s %(module)s - %(message)s')
logger = logging.getLogger(__name__)


class LoopTimer(Timer):
    """
    循环定时器
    """

    def __init__(self, interval, func, args=None, kwargs=None):
        Timer.__init__(self, interval, func, args=args, kwargs=kwargs)

    def run(self):
        while True:
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)
            if self.finished.is_set():
                self.finished.set()
                break


class LocalFileHandler:
    """
    本地文件处理类
    """

    def __init__(self):
        self.files = {}

    def is_file_closed(self, file_path):
        return file_path not in self.files or self.files[file_path].closed

    def open_file(self, file_path, mode='r'):
        """
        为每个文件缓存file对象
        """
        if self.is_file_closed(file_path):
            self.files[file_path] = open(file_path, mode=mode)
        return self.files[file_path]

    def close_file(self, file_path):
        if file_path in self.files:
            if self.files[file_path]:
                self.files[file_path].close()
            del self.files[file_path]

    @staticmethod
    def stat(file_path):
        """
        获取文件状态，文件修改时间和大小，文件不存在为None
        """
        try:
            stat = os.stat(file_path)
            return stat.st_mtime, stat.st_size
        except IOError:
            logger.error('No such file or IO error')
            return None

    def read(self, file_path, callback):
        """
        读取文件
        """
        if self.stat(file_path):
            with self.open_file(file_path, mode='r') as f:
                content = f.read()
                if callback:
                    callback(content.strip())
                return content

    def read_lines(self, file_path, callback):
        """
        读取文件，直到空行
        """
        if self.stat(file_path):
            with self.open_file(file_path, mode='r') as f:
                li = []
                for line in f.readlines():
                    if callback:
                        callback(line.strip())
                    li.append(line)
                return li

    def read_stream(self, file_path, callback):
        """
        读取文件流，注意关闭文件
        """
        if self.stat(file_path) and self.is_file_closed(file_path):
            try:
                f = self.open_file(file_path, mode='r')
                while True:
                    line = f.readline()
                    if line:
                        callback(line.strip())
                    else:
                        time.sleep(0.1)
            except Exception:
                logger.error('Read stream error', exc_info=True)
            finally:
                self.close_file(file_path)

    def write(self, file_path, content):
        """
        覆盖写入文件
        """
        with self.open_file(file_path, 'w') as f:
            f.write(content)

    def write_lines(self, file_path, lines):
        """
        覆盖写入文件
        """
        with self.open_file(file_path, 'w') as f:
            li = []
            i = 0
            for line in lines:
                li.append((os.linesep + line) if i else line)
                i += 1
            f.writelines(li)

    def write_append(self, file_path, lines):
        """
        追加写入文件
        """
        with self.open_file(file_path, 'a') as f:
            li = []
            i = 0
            pos = f.tell()
            for line in lines:
                li.append((os.linesep + line) if i + pos else line)
                i += 1
            f.writelines(li)

    def write_stream(self, file_path, lines):
        """
        追加写入文件流，注意关闭文件 self.close_file(file_path)
        """
        try:
            f = self.open_file(file_path, mode='r')
            li = []
            i = 0
            pos = f.tell()
            for line in lines:
                li.append((os.linesep + line) if i + pos else line)
                i += 1
            f.writelines(li)
        except Exception:
            logger.error('Write stream error', exc_info=True)
        finally:
            self.close_file(file_path)

    def dispose(self):
        for file_path in self.files:
            self.close_file(file_path)
        self.files.clear()


class SFTPFileHandler(LocalFileHandler):
    """
    远程文件处理类，SFTP协议
    """

    def __init__(self, host='127.0.0.1', port=22, username=None, password=None):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.transport = None
        self.clients = {}

    def is_connected(self):
        """
        SFTP是否连接
        """
        if self.transport:
            return self.transport.is_active()
        return False

    def connect(self):
        """
        连接SFTP
        """
        self.transport = Transport((self.host, self.port))
        self.transport.connect(username=self.username, password=self.password)

    def disconnect(self):
        """
        断开SFTP
        """
        for key, file in self.files.items():
            if file:
                file.close()
        for key, client in self.clients.items():
            if client:
                client.close()
        if self.transport:
            self.transport.close()

    def get_client(self, file_path):
        """
        为每个文件缓存channel对象
        """
        if file_path not in self.clients:
            self.clients[file_path] = SFTPClient.from_transport(self.transport)
        return self.clients[file_path]

    def open_file(self, file_path, mode='r'):
        """
        为每个文件缓存file对象
        """
        if self.is_file_closed(file_path):
            self.files[file_path] = self.get_client(file_path).open(file_path, mode=mode)
        return self.files[file_path]

    def stat(self, file_path):
        """
        获取文件状态，文件不存在为None
        """
        if not self.is_connected():
            self.connect()
        try:
            stat = self.get_client(file_path).stat(file_path)
            return stat.st_mtime, stat.st_size
        except IOError:
            logger.error('No such file or IO error')
            return None

    def read(self, file_path, callback):
        """
        读取文件
        """
        if not self.is_connected():
            self.connect()
        super().read(file_path, callback)

    def read_lines(self, file_path, callback):
        """
        读取文件，直到空行
        """
        if not self.is_connected():
            self.connect()
        super().read_lines(file_path, callback)

    def read_stream(self, file_path, callback):
        """
        读取文件流，注意关闭文件
        """
        if not self.is_connected():
            self.connect()
        super().read_stream(file_path, callback)

    def write(self, file_path, content):
        """
        覆盖写入文件
        """
        if not self.is_connected():
            self.connect()
        super().write(file_path, content)

    def write_lines(self, file_path, lines):
        """
        覆盖写入文件
        """
        if not self.is_connected():
            self.connect()
        super().write_lines(file_path, lines)

    def write_append(self, file_path, lines):
        """
        追加写入文件
        """
        if not self.is_connected():
            self.connect()
        super().write_append(file_path, lines)

    def write_stream(self, file_path, lines):
        """
        追加写入文件流，注意关闭文件
        """
        if not self.is_connected():
            self.connect()
        super().write_stream(file_path, lines)

    def dispose(self):
        self.disconnect()
        self.files.clear()
        self.clients.clear()


class TradeClient:

    def __init__(self, path):
        self._tz = timezone('Asia/Shanghai')
        self.today = datetime.now(tz=self._tz).strftime("%Y%m%d")
        self.handler = LocalFileHandler()
        self.path = path
        self._hb = 'Ping'
        self._hb_file = '%s/ping%s.dat' % (self.path, self.today)
        self._hb_timer = None
        self._hb_interval = 2
        self._hb_started = False
        self._watch_hb = 'Pong'
        self._watch_files = [('%s/pong%s.dat' % (self.path, self.today), self.handle_heartbeat, False)]
        self._watch_timers = {}
        self._watch_stats = {}
        self._watch_interval = 0.3
        self._watch_started = False

    def _watch_file(self, file_path, line_handle, stream_mode):
        """
        判断文件变化，如果发生变化则读取文件
        """
        new_stat = self.handler.stat(file_path)
        if new_stat and (
                file_path not in self._watch_stats or (
                self._watch_stats[file_path][0] < new_stat[0] or
                self._watch_stats[file_path][1] != new_stat[1])):
            prev_stat = self._watch_stats[file_path] if file_path in self._watch_stats else (0, 0)
            self._watch_stats[file_path] = new_stat
            logger.debug('File [%s] has been changed: [%d, %d] > [%d, %d]', file_path, *prev_stat, *new_stat)
            self._read_file(file_path, line_handle, stream_mode)

    def _read_file(self, file_path, line_handle, stream_mode):
        """
        读取文件并处理
        """
        if stream_mode:
            self.handler.read_stream(file_path, line_handle)
        else:
            self.handler.read_lines(file_path, line_handle)

    def start_watch(self, file_names=None):
        """
        启动监控文件任务
        :param file_names: 需要监控的文件列表，为None则全部都监控
        """
        for file_path, line_handle, stream_mode in self._watch_files:
            if not file_names or any([file_name in file_path for file_name in file_names]):
                _timer = LoopTimer(self._watch_interval, self._watch_file, (file_path, line_handle, stream_mode))
                self._watch_timers[file_path] = _timer
                _timer.start()
                logger.info('Watch [%s] start', file_path)
        self._watch_started = True

    def stop_watch(self):
        """
        停止监控文件任务
        """
        for file_path, timer in self._watch_timers:
            if self._watch_timers[file_path]:
                self._watch_timers[file_path].cancel()
            logger.info('Watch [%s] stop', file_path)
        self._watch_timers.clear()
        self._watch_stats.clear()

    def _do_heartbeat(self):
        """
        心跳
        """
        t = datetime.now(tz=self._tz).strftime("%H%M%S%f")
        self.handler.write_lines(self._hb_file, [t])
        logger.info('%s: %s', self._hb, t)

    def start_heartbeat(self):
        """
        启动心跳任务
        :return:
        """
        self._hb_timer = LoopTimer(self._hb_interval, self._do_heartbeat)
        self._hb_timer.start()
        self._hb_started = True
        logger.info('%s start', self._hb)

    def stop_heartbeat(self):
        """
        停止心跳任务
        """
        if self._hb_timer:
            self._hb_timer.cancle()
        logger.info('%s stop', self._hb)

    def handle_heartbeat(self, line):
        """
        用户继承或重写，心跳回调
        """
        logger.info('%s: %s', self._watch_hb, line)

    def dispose(self):
        self.handler.dispose()
        if self._watch_started:
            self.stop_watch()
        if self._hb_started:
            self.stop_heartbeat()


class TradeServer(TradeClient):

    def __init__(self, path, host='127.0.0.1', port=22, username=None, password=None):
        super().__init__(path)
        self.handler = SFTPFileHandler(host=host, port=port, username=username, password=password)
        self.path = path
        self._hb = 'Pong'
        self._hb_file = '%s/pong%s.dat' % (self.path, self.today)
        self._watch_hb = 'Ping'
        self._watch_files = [('%s/ping%s.dat' % (self.path, self.today), self.handle_heartbeat, False)]

    def handle_heartbeat(self, line):
        """
        用户继承或重写，心跳回调
        """
        logger.info('%s: %s', self._watch_hb, line)
        self._do_heartbeat()


if __name__ == "__main__":
    import time
    p = os.path.join(os.getcwd(), 'data/ch06')
    pwd = input()
    server = TradeServer(p, username='qingspace', password=pwd)
    server.start_watch()

    client = TradeClient(p)
    client.start_watch()
    client.start_heartbeat()
    while True:
        time.sleep(10)







