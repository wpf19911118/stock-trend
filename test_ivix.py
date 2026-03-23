#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试中国波指 iVIX 获取功能
"""

import io
import sys

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import akshare as ak
import pandas as pd

def test_ivix():
    """测试获取中国波指"""
    print("=" * 60)
    print("测试中国波指 iVIX (000188.SH) 获取")
    print("=" * 60)
    
    try:
        # 方法1: 使用 stock_zh_index_daily
        print("\n方法1: ak.stock_zh_index_daily")
        df = ak.stock_zh_index_daily(symbol="sh000188")
        
        if not df.empty:
            print(f"成功获取数据，共 {len(df)} 条记录")
            print(f"\n最新数据:")
            latest = df.iloc[-1]
            print(f"  日期: {latest.get('date', 'N/A')}")
            print(f"  收盘: {latest.get('close', 'N/A')}")
            print(f"  开盘: {latest.get('open', 'N/A')}")
            print(f"  最高: {latest.get('high', 'N/A')}")
            print(f"  最低: {latest.get('low', 'N/A')}")
            
            # 计算状态
            ivix_value = float(latest.get('close', 0))
            if ivix_value > 30:
                status = "恐慌 (>30)"
            elif ivix_value > 20:
                status = "担忧 (20-30)"
            elif ivix_value > 15:
                status = "正常 (15-20)"
            else:
                status = "过度乐观 (<15)"
            
            print(f"  状态: {status}")
            
            # 显示近5日趋势
            print(f"\n近5日趋势:")
            recent = df.tail(5)
            for idx, row in recent.iterrows():
                date = row.get('date', 'N/A')
                close = row.get('close', 0)
                print(f"  {date}: {close}")
            
            return ivix_value
        else:
            print("获取数据为空")
            return None
            
    except Exception as e:
        print(f"获取失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    ivix = test_ivix()
    print("\n" + "=" * 60)
    if ivix:
        print(f"当前中国波指 iVIX: {ivix}")
    print("=" * 60)
