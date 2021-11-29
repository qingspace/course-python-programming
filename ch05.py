#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-04-20 10:00:00

import sys
import os
import pandas as pd
import logging
sys.path.append(os.getcwd())
from ch01 import Direction, Exchange

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(thread)d %(levelname)s %(module)s - %(message)s')
logger = logging.getLogger(__name__)


class OrderProcessor:
    """
    委托数据处理
    """

    DEFAULT_STOCK_TAX_RATE = 0.001  # 印花税率
    DEFAULT_SH_TRANSFER_FEE_RATE = 0.00002  # 上证过户费率
    DEFAULT_SZ_TRANSFER_FEE_RATE = 0  # 深证过户费率
    DEFAULT_COMMISSION_RATE = 0.0002  # 佣金费率
    DEFAULT_COMMISSION_MIN = 0  # 佣金下限
    DEFAULT_EXCHANGE_FEE_RATE = 0  # 交易所规费费率
    DEFAULT_OTHER_FEE_RATE = 0  # 其他费用费率

    def __init__(self):
        self.orders = []
        self.quotations = []

    def get_orders(self):
        if not self.orders:
            self.orders = pd.read_csv('data/ch02/orders.csv').to_dict(orient='records')
            logger.debug('Load orders ok')
        return self.orders

    def get_quotations(self):
        """
        获取全部行情
        :return list: 行情列表
        """
        if not self.quotations:
            self.quotations = pd.read_csv('data/ch02/quotations.csv').to_dict(orient='records')
            logger.debug('Load quotations ok')
        return self.quotations

    @staticmethod
    def get_exchange(stock_code):
        """
        判断股票交易市场
        :param str stock_code: 股票代码
        :return Exchange: 交易市场
        """
        if not stock_code:
            return None
        stock_code = stock_code.strip()
        if stock_code.startswith('60') or stock_code.startswith('900') or stock_code.startswith('688') or stock_code.startswith('689'):
            return Exchange.SSE
        elif stock_code.startswith('00') or stock_code.startswith('200') or stock_code.startswith('300'):
            return Exchange.SZSE
        elif stock_code.startswith('50') or stock_code.startswith('51') or stock_code.startswith('52'):
            return Exchange.SSE
        elif stock_code.startswith('18') or stock_code.startswith('16') or stock_code.startswith('15'):
            return Exchange.SZSE
        if stock_code.startswith('10') or stock_code.startswith('11'):
            return Exchange.SSE
        elif stock_code.startswith('12'):
            return Exchange.SZSE
        return None

    def get_stock_cost(self, stock_code, price, volume, direction,
                       tax_rate=DEFAULT_STOCK_TAX_RATE,
                       sz_transfer_fee_rate=DEFAULT_SZ_TRANSFER_FEE_RATE,
                       sh_transfer_fee_rate=DEFAULT_SH_TRANSFER_FEE_RATE,
                       commission_rate=DEFAULT_COMMISSION_RATE,
                       commission_min=DEFAULT_COMMISSION_MIN,
                       exchange_fee_rate=DEFAULT_EXCHANGE_FEE_RATE,
                       other_fee_rate=DEFAULT_OTHER_FEE_RATE):
        """
        计算股票交易成本
        :param str stock_code: 股票代码
        :param float price: 成交价格
        :param int volume: 成交数量
        :param str direction: Direction，买入卖出
        :param float tax_rate: 印花税率
        :param float sh_transfer_fee_rate: 上证过户费费率
        :param float sz_transfer_fee_rate: 深圳过户费费率
        :param float commission_rate: 佣金费率
        :param float commission_min: 佣金下限
        :param float exchange_fee_rate: 交易所规费费率
        :param float other_fee_rate: 其他费用费率
        :return float: 交易成本
        """
        tax, fee, commission, exchange_fee, other_fee = 0, 0, 0, 0, 0
        amount = price * volume
        exchange = self.get_exchange(stock_code)
        if direction == Direction.SELL:
            tax = amount * tax_rate
        if exchange == Exchange.SSE:
            fee = amount * sh_transfer_fee_rate
        elif exchange == Exchange.SZSE:
            fee = amount * sz_transfer_fee_rate
        if commission_rate:
            commission = amount * commission_rate
        if 0 < commission < commission_min:
            commission = commission_min
        if exchange_fee_rate:
            exchange_fee = amount * exchange_fee_rate
        if other_fee_rate:
            other_fee = amount * other_fee_rate
        return tax + fee + commission + exchange_fee + other_fee

    def get_close_price(self, stock_code, date):
        """
        获取每日收盘价
        :param str stock_code: 股票代码
        :param int date: 日期
        :return float: 收盘价
        """
        for quotation in self.get_quotations():
            if quotation['stock_code'] == stock_code and quotation['trade_date'] == date:
                return quotation['close_price']
        return 0

    def get_net_profit(self, order, date):
        """
        计算每个委托收益
        :param dict order: 委托
        :param int date: 日期
        :return float: 委托收益
        """
        net_profit = 0
        if order and order['deal_volume'] > 0:
            fee = self.get_stock_cost(str(order['stock_code']), order['deal_price'], order['deal_volume'], order['direction'])
            direction = (-1 if order['direction'] == Direction.SELL else 1)
            net_profit = direction * (self.get_close_price(order['stock_code'], date) - order['deal_price']) * order['deal_volume'] - fee
        logger.debug('Order %d %s net profit: %f' % (date, order['order_code'], net_profit))
        return net_profit

    def get_account_accumulated_net_profit(self, date):
        """
        计算账户累计收益
        :param int date: 截止日期
        :return float: 账户累计收益
        """
        accumulated_net_profit = 0
        for order in self.get_orders():
            if order['order_date'] <= date:
                accumulated_net_profit = accumulated_net_profit + self.get_net_profit(order, date)
        logger.debug('Account %d accumulated net profit: %f' % (date, accumulated_net_profit))
        return accumulated_net_profit

    def run(self, init_cash, dates):
        """
        计算账户所有委托累计收益，收益，累计收益率，收益率
        :return dict: 累计收益，收益，累计收益率，收益率
        """
        if not dates:
            dates = []
        results = {}
        yesterday_net_profit = 0
        for date in dates:
            net_profit = self.get_account_accumulated_net_profit(date)
            today_net_profit = net_profit - yesterday_net_profit
            ratio = net_profit / init_cash
            today_ratio = today_net_profit / (init_cash + yesterday_net_profit)
            results[date] = (net_profit, today_net_profit, ratio, today_ratio)
            yesterday_net_profit = net_profit
        return results


if __name__ == "__main__":
    processor = OrderProcessor()
    ret = processor.run(500000, [20210104, 20210105])
    logger.info(ret)
