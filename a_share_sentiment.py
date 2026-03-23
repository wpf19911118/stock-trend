#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股情绪指标获取模块
由于中国波指 iVIX (000188) 已于2018年停止发布，使用替代指标：
1. 50ETF期权隐含波动率 (作为iVIX替代)
2. A股换手率
3. 融资余额变化率
"""

import io
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import akshare as ak
import pandas as pd
import numpy as np
from typing import Optional, Dict


def get_50etf_option_iv() -> Optional[float]:
    """
    获取50ETF期权隐含波动率（作为中国波指iVIX的替代）
    
    Returns:
        隐含波动率数值或None
    """
    try:
        # 获取50ETF期权数据
        df = ak.option_finance_board(symbol="510050")
        if not df.empty:
            # 计算隐含波动率的平均值
            iv_data = df[df['隐含波动率'].notna()]['隐含波动率']
            if not iv_data.empty:
                avg_iv = iv_data.mean()
                print(f"✅ 50ETF期权隐含波动率: {avg_iv:.2f}%")
                return round(avg_iv, 2)
    except Exception as e:
        print(f"获取50ETF期权IV失败: {e}")
    return None


def get_a_share_turnover() -> Optional[Dict]:
    """
    获取A股市场换手率数据
    
    Returns:
        换手率数据字典或None
    """
    try:
        # 获取A股成交额数据
        df = ak.stock_zh_a_spot_em()
        if not df.empty:
            # 计算平均换手率
            turnover_list = pd.to_numeric(df['换手率'], errors='coerce').dropna()
            avg_turnover = turnover_list.mean()
            
            result = {
                'avg_turnover': round(avg_turnover, 2),
                'high_turnover_count': int((turnover_list > 10).sum()),
                'low_turnover_count': int((turnover_list < 1).sum())
            }
            
            print(f"✅ A股平均换手率: {result['avg_turnover']}%")
            print(f"   高换手率个股(>10%): {result['high_turnover_count']}只")
            print(f"   低换手率个股(<1%): {result['low_turnover_count']}只")
            return result
    except Exception as e:
        print(f"获取A股换手率失败: {e}")
    return None


def get_margin_data() -> Optional[Dict]:
    """
    获取融资融券数据
    
    Returns:
        融资融券数据字典或None
    """
    try:
        # 获取融资融券余额
        df = ak.stock_margin_detail_szse()
        if not df.empty:
            latest = df.iloc[0]
            result = {
                'margin_balance': float(latest.get('融资余额', 0)) / 100000000,  # 转为亿
                'margin_buy': float(latest.get('融资买入额', 0)) / 100000000,
                'short_balance': float(latest.get('融券余额', 0)) / 100000000
            }
            print(f"✅ 融资余额: {result['margin_balance']:.2f}亿")
            return result
    except Exception as e:
        print(f"获取融资融券数据失败: {e}")
    return None


def calculate_a_share_sentiment_index() -> Dict:
    """
    计算A股综合情绪指数（替代iVIX）
    
    综合以下指标：
    - 50ETF期权隐含波动率 (权重40%)
    - A股平均换手率 (权重30%)
    - 融资余额变化 (权重30%)
    
    Returns:
        情绪指数数据字典
    """
    print("\n" + "=" * 60)
    print("计算A股综合情绪指数（iVIX替代指标）")
    print("=" * 60)
    
    sentiment_data = {
        'ivix_proxy': None,
        'turnover_data': None,
        'margin_data': None,
        'composite_index': None,
        'sentiment_level': '未知',
        'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 1. 获取50ETF期权IV
    iv = get_50etf_option_iv()
    sentiment_data['ivix_proxy'] = iv
    
    # 2. 获取换手率数据
    turnover = get_a_share_turnover()
    sentiment_data['turnover_data'] = turnover
    
    # 3. 获取融资数据
    margin = get_margin_data()
    sentiment_data['margin_data'] = margin
    
    # 4. 计算综合情绪指数
    if iv is not None:
        # 使用50ETF期权IV作为主要指标（40%权重）
        # 换手率（30%权重）- 标准化到0-50范围
        turnover_score = 0
        if turnover:
            avg_to = turnover['avg_turnover']
            if avg_to > 5:
                turnover_score = 40  # 极度活跃
            elif avg_to > 3:
                turnover_score = 30  # 活跃
            elif avg_to > 1.5:
                turnover_score = 20  # 正常
            else:
                turnover_score = 10  # 低迷
        
        # 综合计算
        composite = iv * 0.6 + turnover_score * 0.4
        sentiment_data['composite_index'] = round(composite, 2)
        
        # 判断情绪等级
        if composite > 35:
            sentiment_data['sentiment_level'] = '恐慌'
        elif composite > 25:
            sentiment_data['sentiment_level'] = '担忧'
        elif composite > 15:
            sentiment_data['sentiment_level'] = '正常'
        else:
            sentiment_data['sentiment_level'] = '过度乐观'
    
    print("\n" + "=" * 60)
    if sentiment_data['composite_index']:
        print(f"📊 综合情绪指数: {sentiment_data['composite_index']}")
        print(f"📊 情绪等级: {sentiment_data['sentiment_level']}")
    print("=" * 60)
    
    return sentiment_data


if __name__ == "__main__":
    result = calculate_a_share_sentiment_index()
    print("\n完整结果:")
    print(result)
