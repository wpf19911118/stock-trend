#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股恐慌指数替代方案
由于中国波指 iVIX (000188.SH) 已于2018年停止发布，使用以下替代指标：

1. 50ETF历史波动率（基于过去20日收益率计算）
2. 50ETF收盘价（作为市场情绪参考）
3. 涨跌停家数比（反映市场情绪）

恐慌阈值：
- >30: 恐慌（类似iVIX>30）
- 20-30: 担忧
- 15-20: 正常
- <15: 过度乐观
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


def get_50etf_hist_volatility() -> Optional[float]:
    """
    计算50ETF历史波动率（年化）
    作为中国波指iVIX的替代指标
    
    Returns:
        年化历史波动率或None
    """
    try:
        # 获取50ETF历史数据
        # 50ETF代码: 510050
        df = ak.fund_etf_hist_em(symbol="510050", period="daily", adjust="qfq")
        
        if not df.empty and len(df) >= 20:
            # 计算对数收益率（避免除零）
            df['return'] = np.log(df['收盘'] / df['收盘'].shift(1))
            df['return'] = df['return'].replace([np.inf, -np.inf], np.nan).dropna()
            
            # 计算20日波动率（年化）
            returns = df['return'].tail(20).dropna()
            if len(returns) >= 10:  # 确保有足够数据
                volatility = returns.std() * np.sqrt(252) * 100
                
                if not np.isnan(volatility):
                    print(f"✅ 50ETF 20日历史波动率: {volatility:.2f}%")
                    return round(volatility, 2)
    except Exception as e:
        print(f"获取50ETF波动率失败: {e}")
    return None


def get_50etf_price() -> Optional[Dict]:
    """
    获取50ETF当前价格和涨跌
    
    Returns:
        价格数据字典或None
    """
    try:
        df = ak.fund_etf_hist_em(symbol="510050", period="daily", adjust="qfq", limit=5)
        
        if not df.empty:
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            result = {
                'close': float(latest['收盘']),
                'change_pct': round((latest['收盘'] - prev['收盘']) / prev['收盘'] * 100, 2),
                'volume': float(latest['成交量']) / 10000  # 转为万手
            }
            
            print(f"✅ 50ETF 当前价格: {result['close']}")
            print(f"   涨跌幅: {result['change_pct']}%")
            return result
    except Exception as e:
        print(f"获取50ETF价格失败: {e}")
    return None


def calculate_a_share_panic_index() -> Dict:
    """
    计算A股恐慌指数（综合指标）
    
    评分标准（参考iVIX）：
    - 历史波动率 >30%: 恐慌（逆向买入机会）
    - 历史波动率 20-30%: 担忧
    - 历史波动率 15-20%: 正常
    - 历史波动率 <15%: 过度乐观（风险）
    
    Returns:
        恐慌指数数据字典
    """
    print("\n" + "=" * 60)
    print("计算A股恐慌指数（中国波指iVIX替代）")
    print("=" * 60)
    
    panic_data = {
        'symbol': '510050',
        'name': '50ETF波动率',
        'value': None,
        'status': '未知',
        'signal': '无信号',
        'recommendation': '无法评估',
        'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 获取历史波动率
    vol = get_50etf_hist_volatility()
    panic_data['value'] = vol
    
    # 获取价格信息
    price_info = get_50etf_price()
    
    if vol is not None:
        # 根据波动率判断状态
        if vol > 30:
            panic_data['status'] = '🔴 恐慌'
            panic_data['signal'] = '强烈买入信号'
            panic_data['recommendation'] = 'A股市场恐慌，考虑逆向加仓'
        elif vol > 25:
            panic_data['status'] = '🟠 担忧'
            panic_data['signal'] = '谨慎买入'
            panic_data['recommendation'] = '市场情绪偏悲观，可分批建仓'
        elif vol > 20:
            panic_data['status'] = '🟡 谨慎'
            panic_data['signal'] = '中性'
            panic_data['recommendation'] = '市场情绪正常，保持观察'
        elif vol > 15:
            panic_data['status'] = '🟢 正常'
            panic_data['signal'] = '持有'
            panic_data['recommendation'] = '市场情绪平稳'
        else:
            panic_data['status'] = '🔵 过度乐观'
            panic_data['signal'] = '警惕风险'
            panic_data['recommendation'] = '市场过度乐观，注意风险控制'
    
    print("\n" + "=" * 60)
    if panic_data['value']:
        print(f"📊 恐慌指数: {panic_data['value']}")
        print(f"📊 状态: {panic_data['status']}")
        print(f"📊 信号: {panic_data['signal']}")
        print(f"📊 建议: {panic_data['recommendation']}")
    else:
        print("❌ 无法获取恐慌指数数据")
    print("=" * 60)
    
    return panic_data


if __name__ == "__main__":
    result = calculate_a_share_panic_index()
    print("\n完整结果:")
    for key, value in result.items():
        print(f"  {key}: {value}")
