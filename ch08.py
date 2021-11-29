#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-04-23 10:00:00

from functools import wraps
from typing import Mapping, Dict, List, Callable, Optional, Any
import requests
from requests import Response
import pandas as pd
import logging
from pyquery import PyQuery
import re
import time

logger = logging.getLogger(__name__)


def retry(num: int):
    """
    重试装饰器，若被装饰函数执行失败，则重试num次
    :param num: 重试次数
    """

    def retry_decorator(func: Callable):
        @wraps(func)
        def retry_wrapper(*args, **kwargs):
            for i in range(num + 1):
                if i > 0:
                    logger.info('Retry: %d/%d' % (i, num))
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error('Error: %s' % e, exc_info=True)
                    time.sleep(1)

        return retry_wrapper

    return retry_decorator


class CrawlerBase:
    """
    爬虫框架基类
    """

    def __init__(self):
        self.request_headers: Dict = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.96 Safari/537.36'
        }
        self.results: Optional[List] = []
        self.methods: Mapping[str, Callable] = {
            'get': self.get,
            'post': self.post
        }
        self.jobs = []

    @retry(3)
    def get(self, url: str, headers: Optional[Dict] = None, *args, **kwargs) -> Response:
        """
        GET请求
        :param url: 请求URL
        :param headers: 请求头
        :param args: requests请求位置参数
        :param kwargs: requests请求关键字参数
        :return: Response 响应对象
        """
        _headers: Dict = headers.copy() if headers else {}
        _headers.update(self.request_headers)
        response: Response = requests.get(url, headers=_headers, *args, **kwargs)
        logger.info('[GET %d] %s' % (response.status_code, response.url))
        return response

    @retry(3)
    def post(self, url: str, data: Optional[Any] = None, headers: Optional[Dict] = None, *args, **kwargs) -> Response:
        """
        POST请求
        :param url: 请求URL
        :param data: 请求BODY
        :param headers: 请求头
        :param args: requests请求位置参数
        :param kwargs: requests请求关键字参数
        :return: 响应对象
        """
        _headers: Dict = headers.copy() if headers else {}
        _headers.update(self.request_headers)
        response: Response = requests.post(url, data=data, headers=_headers, *args, **kwargs)
        logger.info('[POST %d] %s' % (response.status_code, response.url))
        return response

    def crawl(self, url: str, callback: Callable, save: Optional[Mapping] = None,
              method: Optional[str] = 'get', wait: int = 0, *args, **kwargs) -> None:
        """
        发起一个请求，并用回调函数处理结果
        :param url: 请求URL
        :param callback: 回调函数
        :param save: 向回调函数传递数据
        :param method: 请求方式，支持get，post，默认为get
        :param wait: 等待时长，单位秒
        :param args: requests请求位置参数
        :param kwargs: requests请求关键字参数
        """

        if method not in self.methods.keys():
            raise 'Method not allowed: %s' % method
        try:
            if url not in self.jobs:
                time.sleep(wait)
                response = self.methods[method](url, *args, **kwargs)
                self.jobs.append(url)
                callback(response, save=save)
        except Exception as e:
            logger.error('Crawl [%s] error' % url, exc_info=True)

    def save_data(self, record: Any) -> None:
        """
        在内存中缓存单条记录
        :param record: 单条记录对象
        """
        if self.results is None:
            self.results = []
        self.results.append(record)
        logger.debug('Saved: %s' % record)

    def to_excel(self, filename: Optional[str] = 'data', sheet_name: Optional[str] = 'data') -> None:
        """
        将全部缓存的数据导出为Excel
        :param filename 文件名，不包含后缀名
        :param sheet_name excel 表名
        """
        try:
            result_df = pd.DataFrame.from_records(data=self.results)
            result_df.to_excel("%s.xlsx" % filename, sheet_name=sheet_name, index=False)
            logger.info('Save to excel successfully')
        except Exception as e:
            logger.error('Save to excel failed', exc_info=True)
        return None


class TestCrawler(CrawlerBase):

    def __init__(self):
        super().__init__()
        self.start_url = 'https://www.baidu.com'

    def run(self):
        save = {'id': 0}
        self.crawl(self.start_url, self.index_page, save=save, method='get')

    def index_page(self, response: Response, save: Optional[Mapping] = None):
        doc = PyQuery(response.text)
        save['id'] += 1
        self.save_data(
            {'id': save['id'], 'url': response.url, 'status_code': response.status_code, 'title': doc('title').text()})
        items = doc('a[href^="http"]').items()
        for item in items:
            self.crawl(item.attr.href, self.detail_page, save=save)

    def detail_page(self, response: Response, save: Optional[Mapping] = None):
        doc = PyQuery(response.text)
        save['id'] += 1
        self.save_data(
            {'id': save['id'], 'url': response.url, 'status_code': response.status_code, 'title': doc('title').text()})


class SearchCrawler(CrawlerBase):

    def __init__(self, keys):
        super().__init__()
        self.keys = keys
        self.start_url = 'https://www.baidu.com/s?wd=%s%%20site:open.163.com'
        self.flv_url = 'http://www.flvcd.com/parse.php?format=&kw=%s'
        self.open_url = 'https://open.163.com/newview/movie/free?pid=%s'
        self.request_headers['Accept'] = '*/*'
        self.request_headers['Accept-Encoding'] = 'gzip, deflate, br'
        self.request_headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'

    def run(self):
        for key in self.keys:
            self.crawl(self.start_url % key, self.search_page, method='get', wait=3)

    def search_page(self, response: Response, save: Optional[Mapping] = None):
        logger.info('Get search page: %d %s', response.status_code, response.url)
        doc = PyQuery(response.text)
        items = [(item('a').attr('href'), item('div.c-span-last').text()) for item in
                 doc('div.c-container div.c-gap-top-small').items()]
        if len(items) > 0:
            self.crawl(items[0][0], self.redirect_page, method='get', allow_redirects=False, wait=3)

    def redirect_page(self, response: Response, save: Optional[Mapping] = None):
        logger.info('Get redirect page: %d %s', response.status_code, response.url)
        redirect_url = ''
        if response.status_code == 302:
            redirect_url = response.headers.get('location')
        elif response.status_code == 200:
            match = re.search(r'URL=\'(.*?)\'', response.text, re.S)
            redirect_url = match.group(1)
        if redirect_url:
            self.crawl(self.flv_url % redirect_url, self.video_page, method='get')

    def video_page(self, response: Response, save: Optional[Mapping] = None):
        logger.info('Get video page: %d %s', response.status_code, response.url)
        doc = PyQuery(response.text)
        items = [item.attr('href') for item in doc('a[href^="http"].link').items()]
        if len(items) > 0 and items[0]:
            video_url = items[0]
            self.save_data(video_url)
            logger.info('Finally video url is: %s', video_url)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(thread)d %(levelname)s %(module)s - %(message)s')
    # c = TestCrawler()
    # c.run()
    # print(c.results)

    c = SearchCrawler(['如何掌控你的自由时间', '阅读全世界', '如何做得更好'])
    c.run()
    print(c.results)



