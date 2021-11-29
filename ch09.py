#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-05-21 10:00:00

from abc import abstractmethod, ABCMeta
from typing import List, Optional, NoReturn
import logging
import easyquotation
import tushare
import requests
import time
import re

logger = logging.getLogger(__name__)


class NoQuotationException(Exception):
    """
    无法获取行情异常
    """
    pass


class SourceType:
    """
    行情源枚举
    """
    EasyQuotation = 1
    TuShare = 2
    Sina = 3


class Quotation:
    """
    行情数据
    """

    def __init__(self):
        self.stock_code: str = ''  # 股票代码
        self.stock_name: str = ''  # 股票名称
        self.trade_date: int = 0  # 交易日期 20190501
        self.trade_time: str = ''  # 交易时间 2019-05-01 10:00:00
        self.price: float = 0.0  # 当前价
        self.open: float = 0.0  # 今日开盘价
        self.pre_close: float = 0.0  # 昨日收盘价

    def __str__(self):
        return '%s %s %f' % (self.trade_time, self.stock_code, self.open)


class StockQuotationInterface(metaclass=ABCMeta):
    """
    行情接口
    """

    @abstractmethod
    def init(self, source=SourceType.EasyQuotation) -> NoReturn:
        """
        初始化
        """
        pass

    @abstractmethod
    def get_realtime_quotations(self, stock_codes: List[str]) -> List[Quotation]:
        """
        获取实时行情
        :param stock_codes: 股票代码
        :return: 行情结果
        """
        pass


class EasyQuotationHelper(StockQuotationInterface):
    """
    利用EasyQuotation库实现接口
    """

    def __init__(self, provider='sina', prefix=False):
        """
        初始化
        :param provider: 数据源
        :param prefix: 是否显示股票前缀
        """
        self.provider = provider
        self.prefix = prefix

    def init(self, source=SourceType.EasyQuotation) -> NoReturn:
        pass

    def get_realtime_quotations(self, stock_codes: List[str]) -> List[Quotation]:
        if not stock_codes:
            return []
        handler = easyquotation.use(self.provider)
        results = handler.stocks(stock_codes, prefix=self.prefix)
        if not results:
            raise NoQuotationException('Empty results')
        logger.debug('Get realtime quotations successfully')
        quotations = []
        for key, value in results.items():
            quotation = Quotation()
            quotation.stock_code = key
            quotation.stock_name = value['name']
            quotation.trade_date = int(value['date'].replace('-', ''))
            quotation.trade_time = value['date'] + ' ' + value['time']
            quotation.price = value['now']
            quotation.open = value['open']
            quotation.pre_close = value['close']
            quotations.append(quotation)
        return quotations


class TuShareHelper(StockQuotationInterface):
    """
    利用Tushare库实现接口
    """

    def __init__(self, ts_token=''):
        self.ts_token = ts_token
        self.ts = tushare
        self.ts_pro = None

    def init(self, source=SourceType.EasyQuotation) -> NoReturn:
        if self.ts_token:
            self.ts_pro = self.ts.pro_api(self.ts_token)

    def get_realtime_quotations(self, stock_codes: List[str]) -> List[Quotation]:
        if not stock_codes:
            return []
        results = self.ts.get_realtime_quotes(stock_codes)
        if results is None or results.empty:
            raise NoQuotationException('Empty results')
        logger.debug('Get realtime quotations successfully')
        quotations = []
        for value in results.to_dict('index').values():
            quotation = Quotation()
            quotation.stock_code = value['code']
            quotation.stock_name = value['name']
            quotation.trade_date = int(value['date'].replace('-', ''))
            quotation.trade_time = value['date'] + ' ' + value['time']
            quotation.price = float(value['price'])
            quotation.open = float(value['open'])
            quotation.pre_close = float(value['pre_close'])
            quotations.append(quotation)
        return quotations


class StockQuotationHelper(StockQuotationInterface):
    """
    代理模式，实现不同源选择
    """

    def __init__(self):
        self.helper: Optional[StockQuotationInterface] = None

    def init(self, source=SourceType.EasyQuotation) -> NoReturn:
        if source == SourceType.EasyQuotation:
            self.helper = EasyQuotationHelper()
            logger.info('Use easyquotation library')
        elif source == SourceType.TuShare:
            self.helper = TuShareHelper()
            logger.info('Use tushare library')
        if self.helper:
            self.helper.init()

    def get_realtime_quotations(self, stock_codes: List[str]) -> List[Quotation]:
        return self.helper.get_realtime_quotations(stock_codes)


class SinaQuotationHelper(StockQuotationInterface):

    def __init__(self):
        self.headers = {
            "Accept-Encoding": "gzip, deflate, sdch",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/54.0.2840.100 "
                "Safari/537.36"
            ),
        }
        self.grep_detail = re.compile(r"(\d+)=[^\s]([^\s,]+?)%s%s" % (r",([\.\d]+)" * 29, r",([-\.\d:]+)" * 2))

    @staticmethod
    def get_exchange_prefix(stock_code: str) -> str:
        """判断股票ID对应的证券市场
        :param stock_code:股票ID, 若以 'sz', 'sh' 开头直接返回对应类型，否则使用内置规则判断
        :return 'sh' or 'sz'
        """
        sh_head = ("50", "51", "60", "90", "110", "113",
                   "132", "204", "5", "6", "9", "7")
        if stock_code.startswith(("sh", "sz", "zz")):
            return stock_code[:2]
        else:
            return "sh" if stock_code.startswith(sh_head) else "sz"

    @property
    def get_api(self) -> str:
        return f"http://hq.sinajs.cn/rn={int(time.time() * 1000)}&list="

    def init(self, source=SourceType.EasyQuotation) -> NoReturn:
        pass

    def get_realtime_quotations(self, stock_codes: List[str]) -> List[Quotation]:
        if not stock_codes:
            return []
        stock_codes = [self.get_exchange_prefix(stock_code) + stock_code for stock_code in stock_codes]
        params = ','.join(stock_codes)
        response = requests.get(self.get_api + params, headers=self.headers)
        if not response.text:
            raise NoQuotationException('Empty results')
        logger.debug('Get realtime quotations successfully')
        quotations = []
        results = self.grep_detail.finditer(response.text)
        for result in results:
            value = result.groups()
            quotation = Quotation()
            quotation.stock_code = value[0]
            quotation.stock_name = value[1]
            quotation.trade_date = int(value[31].replace('-', ''))
            quotation.trade_time = value[31] + ' ' + value[32]
            quotation.price = float(value[4])
            quotation.open = float(value[2])
            quotation.pre_close = float(value[3])
            quotations.append(quotation)
        return quotations


class StockQuotationExHelper(StockQuotationHelper):

    def __init__(self):
        super().__init__()

    def init(self, source=SourceType.EasyQuotation) -> NoReturn:
        if source == SourceType.Sina:
            self.helper = SinaQuotationHelper()
            logger.info('Use sina http api')
        super().init(source=source)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(thread)d %(levelname)s %(module)s - %(message)s')
    # helper = EasyQuotationHelper()
    # data = helper.get_realtime_quotations(['600120'])
    # helper = TuShareHelper()
    # data = helper.get_realtime_quotations(['600120'])
    # helper = StockQuotationHelper()
    # helper.init(source=SourceType.TuShare)
    # helper = SinaQuotationHelper()
    helper = StockQuotationExHelper()
    helper.init(source=SourceType.Sina)
    data = helper.get_realtime_quotations(['600120'])
    for i in data:
        print(i)
