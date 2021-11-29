#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-04-18 10:00:00

import sys
import os
import pandas as pd
import logging

sys.path.append(os.getcwd())
from ch01 import get_stock_cost, Direction


orders = pd.read_csv('data/ch02/orders.csv').to_dict(orient='records')

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(thread)d %(levelname)s %(module)s - %(message)s')
logger = logging.getLogger(__name__)


def get_positions(date):
    """
    通过股票委托的最终成交状态推导持仓
    :param int date: 截止日期
    :return list: 持仓列表
    """
    positions = []
    for order in orders:
        if order['order_date'] > date or order['deal_volume'] == 0:
            continue
        arr = [p for p in positions if p['stock_code'] == order['stock_code'] and p['position_date'] == date]
        o_direction = -1 if order['direction'] == Direction.SELL else 1
        fee = get_stock_cost(str(order['stock_code']), order['deal_price'], order['deal_volume'], order['direction'])
        # 已经有持仓
        if arr:
            position = arr[0]
            p_direction = -1 if position['direction'] == Direction.SELL else 1
            volume = p_direction * position['volume'] + o_direction * order['deal_volume']
            if volume == 0:
                position['volume'] = 0
                position['price'] = 0
                position['direction'] = ''
            else:
                position['direction'] = Direction.SELL if volume < 0 else Direction.BUY
                position['price'] = (p_direction * position['volume'] * position['price'] +
                                     o_direction * order['deal_volume'] * order['deal_price'] +
                                     fee) / volume
                position['volume'] = -1 * volume if volume < 0 else volume
            logger.debug(position)
        else:
            position = {'stock_code': order['stock_code'],
                        'position_date': date,
                        'direction': order['direction'],
                        'volume': order['deal_volume'],
                        'price': (order['deal_price'] * order['deal_volume'] + fee) / order['deal_volume']
                        }
            logger.debug(position)
            positions.append(position)
    return positions


if __name__ == "__main__":
    logger.info(get_positions(20210105))
