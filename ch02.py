#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-04-17 10:00:00

import sys
import os
from ch01 import get_stock_cost, Direction
import pandas as pd
sys.path.append(os.getcwd())

quotations = pd.read_csv('data/ch02/quotations.csv').to_dict(orient='records')
orders = pd.read_csv('data/ch02/orders.csv').to_dict(orient='records')


def get_close_price(stock_code, date):
    """
    获取每日收盘价
    :param str stock_code: 股票代码
    :param int date: 日期
    :return: 收盘价
    """
    for quotation in quotations:
        if quotation['stock_code'] == stock_code and quotation['trade_date'] == date:
            return quotation['close_price']
    return 0


def get_net_profit(order, date):
    """
    计算每个委托收益
    :param dict order: 委托
    :param int date: 日期
    :return flaot: 委托收益
    """
    if order and order['deal_volume'] > 0:
        fee = get_stock_cost(str(order['stock_code']), order['deal_price'], order['deal_volume'], order['direction'])
        direction = (-1 if order['direction'] == Direction.SELL else 1)
        return direction * (get_close_price(order['stock_code'], date) - order['deal_price']) * order['deal_volume'] - fee
    return 0


def get_account_accumulated_net_profit(date):
    """
    计算账户累计收益
    :param int date: 截止日期
    :return float: 账户累计收益
    """
    accumulated_net_profit = 0
    for order in orders:
        if order['order_date'] <= date:
            accumulated_net_profit = accumulated_net_profit + get_net_profit(order, date)

    return accumulated_net_profit


def run(init_cash):
    """
    计算账户所有委托累计收益，收益，累计收益率，收益率
    :return float: 累计收益，收益，累计收益率，收益率
    """
    results = {}
    yesterday_net_profit = 0
    for date in (20210104, 20210105):
        net_profit = get_account_accumulated_net_profit(date)
        today_net_profit = net_profit - yesterday_net_profit
        ratio = net_profit / init_cash
        today_ratio = today_net_profit / (init_cash + yesterday_net_profit)
        results[date] = (net_profit, today_net_profit, ratio, today_ratio)
        yesterday_net_profit = net_profit
    return results


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(thread)d %(levelname)s %(module)s - %(message)s')
    logging.info(run(500000))
