#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据获取模块
支持 A股(Akshare) + 美股(Yahoo Finance) + 宏观数据(FRED)
"""

import os
import sys
import json
import datetime
import pandas as pd
import numpy as np
import akshare as ak
import yfinance as yf
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class MarketData:
    """市场数据结构"""
    symbol: str
    name: str
    market: str  # 'A股' or 'US'
    close: float
    change_pct: float
    ma_20: float
    ma_50: float
    ma_200: float
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    volume: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    upper_band: Optional[float] = None
    lower_band: Optional[float] = None
    hist_data: Optional[pd.DataFrame] = None  # 历史数据


def get_a_share_index(symbol: str, name: str) -> Optional[MarketData]:
    """
    获取A股指数数据
    
    Args:
        symbol: 指数代码，如 '000300'
        name: 指数名称
    
    Returns:
        MarketData对象或None
    """
    try:
        # 获取日线数据
        if symbol == "000300":
            df = ak.stock_zh_index_daily(symbol="sh000300")
        elif symbol == "000905":
            df = ak.stock_zh_index_daily(symbol="sh000905")
        else:
            df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")
        
        # 统一列名
        df = df.rename(columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        # 获取至少200天的数据
        if len(df) < 200:
            print(f"{name} 历史数据不足200天")
            return None
        
        # 计算技术指标
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 涨跌幅
        change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100
        
        # 均线
        ma_20 = df["close"].rolling(20).mean().iloc[-1]
        ma_50 = df["close"].rolling(50).mean().iloc[-1]
        ma_200 = df["close"].rolling(200).mean().iloc[-1]
        
        # RSI (14日)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs.iloc[-1]))
        
        # MACD
        exp1 = df["close"].ewm(span=12, adjust=False).mean()
        exp2 = df["close"].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        
        # 布林带 (20日)
        ma_20_series = df["close"].rolling(20).mean()
        std_20 = df["close"].rolling(20).std()
        upper_band = ma_20_series.iloc[-1] + (std_20.iloc[-1] * 2)
        lower_band = ma_20_series.iloc[-1] - (std_20.iloc[-1] * 2)
        
        # 获取估值数据
        pe_ratio, pb_ratio = get_a_share_valuation(symbol)
        
        return MarketData(
            symbol=symbol,
            name=name,
            market="A股",
            close=round(latest["close"], 2),
            change_pct=round(change_pct, 2),
            ma_20=round(ma_20, 2),
            ma_50=round(ma_50, 2),
            ma_200=round(ma_200, 2),
            pe_ratio=pe_ratio,
            pb_ratio=pb_ratio,
            volume=latest.get("volume"),
            rsi_14=round(rsi_14, 2),
            macd=round(macd.iloc[-1], 4),
            macd_signal=round(macd_signal.iloc[-1], 4),
            upper_band=round(upper_band, 2),
            lower_band=round(lower_band, 2),
            hist_data=df.tail(252)  # 保存1年数据用于计算
        )
        
    except Exception as e:
        print(f"获取A股数据失败 {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_a_share_valuation(symbol: str) -> Tuple[Optional[float], Optional[float]]:
    """
    获取A股指数估值数据
    
    Returns:
        (PE, PB) 元组
    """
    try:
        # 尝试从akshare获取估值数据
        # 沪深300估值
        if symbol == "000300":
            df = ak.index_value_name_funddb(symbol="沪深300")
            if not df.empty:
                latest = df.iloc[0]
                pe = float(latest.get("市盈率", 0))
                pb = float(latest.get("市净率", 0))
                return (pe if pe > 0 else None, pb if pb > 0 else None)
        
        # 中证500估值
        elif symbol == "000905":
            df = ak.index_value_name_funddb(symbol="中证500")
            if not df.empty:
                latest = df.iloc[0]
                pe = float(latest.get("市盈率", 0))
                pb = float(latest.get("市净率", 0))
                return (pe if pe > 0 else None, pb if pb > 0 else None)
        
        return (None, None)
        
    except Exception as e:
        print(f"获取估值数据失败 {symbol}: {e}")
        return (None, None)


def get_us_stock(symbol: str, name: str) -> Optional[MarketData]:
    """
    获取美股数据（纳斯达克、标普500等）
    
    Args:
        symbol: Yahoo Finance代码，如 '^IXIC', 'QQQ'
        name: 指数名称
    
    Returns:
        MarketData对象或None
    """
    try:
        # 使用yfinance获取数据
        ticker = yf.Ticker(symbol)
        
        # 获取历史数据（1年半）
        df = ticker.history(period="18mo")
        
        if df.empty or len(df) < 200:
            print(f"{name} 历史数据不足")
            return None
        
        # 重命名列
        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        })
        df = df.reset_index()
        df["date"] = pd.to_datetime(df["Date"])
        
        # 计算技术指标
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 涨跌幅
        change_pct = (latest["close"] - prev["close"]) / prev["close"] * 100
        
        # 均线
        ma_20 = df["close"].rolling(20).mean().iloc[-1]
        ma_50 = df["close"].rolling(50).mean().iloc[-1]
        ma_200 = df["close"].rolling(200).mean().iloc[-1]
        
        # RSI (14日)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = 100 - (100 / (1 + rs.iloc[-1]))
        
        # MACD
        exp1 = df["close"].ewm(span=12, adjust=False).mean()
        exp2 = df["close"].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        
        # 布林带
        ma_20_series = df["close"].rolling(20).mean()
        std_20 = df["close"].rolling(20).std()
        upper_band = ma_20_series.iloc[-1] + (std_20.iloc[-1] * 2)
        lower_band = ma_20_series.iloc[-1] - (std_20.iloc[-1] * 2)
        
        # 获取估值数据（通过info）
        info = ticker.info
        pe_ratio = info.get('trailingPE')
        pb_ratio = info.get('priceToBook')
        
        return MarketData(
            symbol=symbol,
            name=name,
            market="美股",
            close=round(latest["close"], 2),
            change_pct=round(change_pct, 2),
            ma_20=round(ma_20, 2),
            ma_50=round(ma_50, 2),
            ma_200=round(ma_200, 2),
            pe_ratio=round(pe_ratio, 2) if pe_ratio else None,
            pb_ratio=round(pb_ratio, 2) if pb_ratio else None,
            volume=int(latest["volume"]) if not pd.isna(latest["volume"]) else None,
            rsi_14=round(rsi_14, 2),
            macd=round(macd.iloc[-1], 4),
            macd_signal=round(macd_signal.iloc[-1], 4),
            upper_band=round(upper_band, 2),
            lower_band=round(lower_band, 2),
            hist_data=df.tail(252)
        )
        
    except Exception as e:
        print(f"获取美股数据失败 {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_macro_data() -> Dict:
    """
    获取宏观数据
    
    Returns:
        包含宏观指标的字典
    """
    result = {
        "us_10y_yield": None,
        "cn_10y_yield": None,
        "vix": None,
        "cn_vix": None,  # 中国波指 iVIX
        "dxy": None,
        "fed_rate": None,
        "error": None
    }
    
    try:
        # 美债10年期收益率 (^TNX)
        try:
            tnx = yf.Ticker("^TNX")
            tnx_hist = tnx.history(period="5d")
            if not tnx_hist.empty:
                result["us_10y_yield"] = round(tnx_hist["Close"].iloc[-1], 2)
        except Exception as e:
            print(f"获取美债收益率失败: {e}")
        
        # VIX恐慌指数 (^VIX)
        try:
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="5d")
            if not vix_hist.empty:
                result["vix"] = round(vix_hist["Close"].iloc[-1], 2)
        except Exception as e:
            print(f"获取VIX失败: {e}")
        
        # 中国波指替代 - 使用50ETF历史波动率
        try:
            # 获取50ETF历史数据计算波动率
            etf_df = ak.fund_etf_hist_em(symbol="510050", period="daily", adjust="qfq")
            if not etf_df.empty and len(etf_df) >= 20:
                import numpy as np
                # 计算对数收益率
                etf_df['return'] = np.log(etf_df['收盘'] / etf_df['收盘'].shift(1))
                etf_df['return'] = etf_df['return'].replace([np.inf, -np.inf], np.nan).dropna()
                
                # 计算20日年化波动率
                returns = etf_df['return'].tail(20).dropna()
                if len(returns) >= 10:
                    volatility = returns.std() * np.sqrt(252) * 100
                    if not np.isnan(volatility):
                        result["cn_vix"] = round(volatility, 2)
                        print(f"  ✅ A股恐慌指数(50ETF波动率): {result['cn_vix']}")
        except Exception as e:
            print(f"  ⚠️  获取A股恐慌指数失败: {e}")
        
        # 美元指数 (DX-Y.NYB)
        try:
            dxy = yf.Ticker("DX-Y.NYB")
            dxy_hist = dxy.history(period="5d")
            if not dxy_hist.empty:
                result["dxy"] = round(dxy_hist["Close"].iloc[-1], 2)
        except Exception as e:
            print(f"获取美元指数失败: {e}")
        
        # 中债10年期收益率（从akshare获取）
        try:
            bond_df = ak.bond_zh_us_rate()
            if not bond_df.empty and "中国国债收益率10年" in bond_df.columns:
                latest_cn_yield = bond_df["中国国债收益率10年"].dropna().iloc[-1]
                result["cn_10y_yield"] = round(float(latest_cn_yield), 2)
        except Exception as e:
            print(f"获取中债收益率失败: {e}")
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        print(f"获取宏观数据失败: {e}")
        return result


def get_all_market_data() -> Dict:
    """
    获取所有监控标的的数据
    
    Returns:
        包含所有数据的字典
    """
    print("\n" + "=" * 60)
    print("开始获取市场数据...")
    print("=" * 60)
    
    # A股指数配置
    a_shares = {
        "000300": "沪深300",
        "000905": "中证500"
    }
    
    # 美股指数配置
    us_stocks = {
        "^IXIC": "纳斯达克",
        "^GSPC": "标普500"
    }
    
    result = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "a_shares": {},
        "us_stocks": {},
        "macro": {}
    }
    
    # 获取A股数据
    print("\n📊 获取A股数据...")
    for symbol, name in a_shares.items():
        print(f"  正在获取 {name} ({symbol})...", end=" ")
        data = get_a_share_index(symbol, name)
        if data:
            result["a_shares"][symbol] = asdict(data)
            print(f"✅ 成功")
        else:
            print(f"❌ 失败")
    
    # 获取美股数据
    print("\n📈 获取美股数据...")
    for symbol, name in us_stocks.items():
        print(f"  正在获取 {name} ({symbol})...", end=" ")
        data = get_us_stock(symbol, name)
        if data:
            result["us_stocks"][symbol] = asdict(data)
            print(f"✅ 成功")
        else:
            print(f"❌ 失败")
    
    # 获取宏观数据
    print("\n🌍 获取宏观数据...")
    result["macro"] = get_macro_data()
    if result["macro"].get("us_10y_yield"):
        print(f"  ✅ 美债收益率: {result['macro']['us_10y_yield']}%")
    if result["macro"].get("cn_10y_yield"):
        print(f"  ✅ 中债收益率: {result['macro']['cn_10y_yield']}%")
    if result["macro"].get("vix"):
        print(f"  ✅ VIX: {result['macro']['vix']}")
    if result["macro"].get("dxy"):
        print(f"  ✅ 美元指数: {result['macro']['dxy']}")
    
    print("\n" + "=" * 60)
    print("数据获取完成")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    # 测试数据获取
    data = get_all_market_data()
    
    # 保存测试结果
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    # 移除hist_data（太大不适合保存）
    for market_type in ["a_shares", "us_stocks"]:
        for symbol, item in data.get(market_type, {}).items():
            if item and "hist_data" in item:
                del item["hist_data"]
    
    output_file = output_dir / f"market_data_{datetime.datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试结果已保存到: {output_file}")
