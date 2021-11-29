#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: qingspace
# Created on 2021-04-16 10:00:00

DEFAULT_STOCK_TAX_RATE = 0.001  # 印花税率
DEFAULT_SH_TRANSFER_FEE_RATE = 0.00002  # 上证过户费率
DEFAULT_SZ_TRANSFER_FEE_RATE = 0  # 深证过户费率
DEFAULT_COMMISSION_RATE = 0.0002  # 佣金费率
DEFAULT_COMMISSION_MIN = 0  # 佣金下限
DEFAULT_EXCHANGE_FEE_RATE = 0  # 交易所规费费率
DEFAULT_OTHER_FEE_RATE = 0  # 其他费用费率


class Direction:
    """
    买卖方向
    """
    BUY = 'BUY'
    SELL = 'SELL'


class Exchange:
    """
    交易市场
    """
    SSE = 'SSE'
    SZSE = 'SZSE'


def get_exchange(stock_code):
    """
    判断股票交易市场
    60是上证A股，900是上证B股，68是上证科创板，其中688是股票、689是存托凭证
    00是深证A股，200是深证B股，002是深证中小板, 300是创业板
    50是上证封闭式基金，51是上证ETF基金
    18是深证封闭式基金，16是深证LOF基金，15是深证ETF基金或分级基金
    100或110是沪市可转债
    125或126是深市可转债
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


def get_stock_cost(stock_code, price, volume, direction,
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
    if direction == Direction.SELL:
        tax = amount * tax_rate
    if get_exchange(stock_code) == Exchange.SSE:
        fee = amount * sh_transfer_fee_rate
    elif get_exchange(stock_code) == Exchange.SZSE:
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


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(thread)d %(levelname)s %(module)s - %(message)s')
    logging.info(get_stock_cost('600318', 76.18, 100, Direction.BUY))
