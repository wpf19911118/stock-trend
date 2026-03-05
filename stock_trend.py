#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票趋势跟踪机器人 V1.0
双均线策略（中长线趋势跟踪）
推送到微信（Server酱）
"""

import os
import io
import sys

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import sys
import json
import datetime
import requests
import pandas as pd
import akshare as ak
import numpy as np
from pathlib import Path

# ==================== 配置 ====================
# 从环境变量或配置文件读取
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")  # Server酱 token
PUSHPLUS_WEBHOOK = os.environ.get("PUSHPLUS_WEBHOOK", "wxa551176bf758ffc7")  # pushplus webhook

# 股票配置
STOCKS = {
    "沪深300": "000300",
    "中证500": "000905",
}

# 均线参数
MA_SHORT = 20   # 短期均线（1个月）
MA_LONG = 60    # 长期均线（3个月）

# ==================== 数据获取 ====================
def get_stock_daily(symbol: str, adjust: str = "qfq") -> pd.DataFrame:
    """
    获取股票日线数据
    akshare 接口
    """
    try:
        # 沪深指数需要特殊处理
        if symbol.startswith("000") or symbol.startswith("399"):
            df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")
        else:
            df = ak.stock_zh_a_hist(symbol=symbol, adjust=adjust, period="daily")

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
        return df
    except Exception as e:
        print(f"获取数据失败 {symbol}: {e}")
        return pd.DataFrame()


def get_index_daily(symbol: str) -> pd.DataFrame:
    """获取指数日线数据"""
    try:
        # 统一处理指数代码
        if symbol == "000300":
            df = ak.stock_zh_index_daily(symbol="sh000300")
        elif symbol == "000905":
            df = ak.stock_zh_index_daily(symbol="sh000905")
        else:
            df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")

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
        return df
    except Exception as e:
        print(f"获取指数数据失败 {symbol}: {e}")
        return pd.DataFrame()


# ==================== 策略计算 ====================
def calculate_ma(df: pd.DataFrame, window: int) -> pd.Series:
    """计算移动平均线"""
    return df["close"].rolling(window=window).mean()


def calculate_trend_duration(df: pd.DataFrame, ma_short: int, ma_long: int) -> dict:
    """
    计算趋势持续时间和预期
    返回: 趋势方向、持续天数、预期剩余时间
    """
    if len(df) < ma_long + 5:
        return {
            "trend": "未知",
            "direction": "unknown",
            "duration_days": 0,
            "expected_remaining": "数据不足",
            "signal": "观望"
        }

    # 计算均线
    df = df.copy()
    df["ma_short"] = calculate_ma(df, ma_short)
    df["ma_long"] = calculate_ma(df, ma_long)

    # 最新数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 判断金叉/死叉
    # 金叉: 短期均线从下方穿过长期均线
    # 死叉: 短期均线从上方穿过长期均线
    current_cross = latest["ma_short"] - latest["ma_long"]
    prev_cross = prev["ma_short"] - prev["ma_long"]

    if current_cross > 0 and prev_cross <= 0:
        # 金叉 - 上升趋势
        direction = "上升"
        signal = "持仓待涨"

        # 计算金叉以来持续的天数
        for i in range(len(df) - 1, -1, -1):
            if df.iloc[i]["ma_short"] - df.iloc[i]["ma_long"] <= 0:
                duration = len(df) - 1 - i
                break
        else:
            duration = len(df)

        # 历史回测估算（简化版：假设上升趋势平均持续20-40个交易日）
        # 结合当前动量
        recent_return = (latest["close"] - df.iloc[-20]["close"]) / df.iloc[-20]["close"] if len(df) >= 20 else 0

        if recent_return > 0.1:
            expected = "4-6周（强劲上涨）"
        elif recent_return > 0.05:
            expected = "3-4周（稳健上涨）"
        else:
            expected = "2-3周（初期震荡）"

    elif current_cross < 0 and prev_cross >= 0:
        # 死叉 - 下降趋势
        direction = "下降"
        signal = "空仓观望"

        # 计算死叉以来持续的天数
        for i in range(len(df) - 1, -1, -1):
            if df.iloc[i]["ma_short"] - df.iloc[i]["ma_long"] >= 0:
                duration = len(df) - 1 - i
                break
        else:
            duration = len(df)

        recent_return = (latest["close"] - df.iloc[-20]["close"]) / df.iloc[-20]["close"] if len(df) >= 20 else 0

        if recent_return < -0.1:
            expected = "3-4周（快速下跌）"
        elif recent_return < -0.05:
            expected = "2-3周（震荡下行）"
        else:
            expected = "1-2周（初期回调）"

    elif current_cross > 0:
        # 持续上涨
        direction = "上升"
        signal = "持仓待涨"

        # 找到最近一次金叉
        for i in range(len(df) - 1, -1, -1):
            if df.iloc[i]["ma_short"] - df.iloc[i]["ma_long"] <= 0:
                duration = len(df) - 1 - i
                break
        else:
            duration = len(df)

        recent_return = (latest["close"] - df.iloc[-20]["close"]) / df.iloc[-20]["close"] if len(df) >= 20 else 0

        if recent_return > 0.1:
            expected = "4-6周"
        elif recent_return > 0.05:
            expected = "3-4周"
        else:
            expected = "2-3周"

    elif current_cross < 0:
        # 持续下跌
        direction = "下降"
        signal = "空仓观望"

        for i in range(len(df) - 1, -1, -1):
            if df.iloc[i]["ma_short"] - df.iloc[i]["ma_long"] >= 0:
                duration = len(df) - 1 - i
                break
        else:
            duration = len(df)

        recent_return = (latest["close"] - df.iloc[-20]["close"]) / df.iloc[-20]["close"] if len(df) >= 20 else 0

        if recent_return < -0.1:
            expected = "3-4周"
        elif recent_return < -0.05:
            expected = "2-3周"
        else:
            expected = "1-2周"

    else:
        direction = "震荡"
        signal = "观望"
        duration = 0
        expected = "等待方向明确"

    return {
        "trend": f"{direction}趋势",
        "direction": direction,
        "duration_days": duration,
        "expected_remaining": expected,
        "signal": signal,
        "close": latest["close"],
        "ma_short": latest["ma_short"],
        "ma_long": latest["ma_long"]
    }


# ==================== 消息推送 ====================
def send_wechat_message(title: str, content: str) -> bool:
    """Server酱推送 (pushplus新版)"""
    if not SERVERCHAN_KEY:
        print("未配置 SERVERCHAN_KEY，跳过推送")
        print(f"消息内容:\n{title}\n{content}")
        return False

    # 新版 pushplus API
    url = "https://www.pushplus.plus/api/send"
    data = {
        "token": SERVERCHAN_KEY,
        "title": title,
        "content": content,
        "template": "html",
        "channel": "wechat",
        "webhook": PUSHPLUS_WEBHOOK
    }

    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        if result.get("code") == 200:
            print("推送成功!")
            return True
        else:
            print(f"推送失败: {result}")
            return False
    except Exception as e:
        print(f"推送异常: {e}")
        return False
        return False


# ==================== 主程序 ====================
def main():
    print("=" * 50)
    print("股票趋势跟踪机器人 V1.0")
    print(f"运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    results = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for name, code in STOCKS.items():
        print(f"\n分析 {name} ({code})...")

        # 获取数据
        df = get_index_daily(code)

        if df.empty:
            print(f"  获取数据失败，跳过")
            results.append({"name": name, "error": "数据获取失败"})
            continue

        # 计算趋势
        trend_info = calculate_trend_duration(df, MA_SHORT, MA_LONG)

        print(f"  当前: {trend_info['trend']}")
        print(f"  已持续: {trend_info['duration_days']} 个交易日")
        print(f"  预计还能走: {trend_info['expected_remaining']}")
        print(f"  建议: {trend_info['signal']}")

        results.append({
            "name": name,
            "code": code,
            **trend_info
        })

    # 生成推送消息
    message_lines = [f"📅 今日({today})复盘\n"]

    for r in results:
        if "error" in r:
            message_lines.append(f"• {r['name']}: 数据获取失败")
            continue

        trend_emoji = "📈" if r["direction"] == "上升" else "📉" if r["direction"] == "下降" else "➡️"
        signal_emoji = "✅" if r["signal"] == "持仓待涨" else "❌" if r["signal"] == "空仓观望" else "⏳"

        line = f"{trend_emoji} {r['name']} 当前为【{r['trend']}】"
        line += f"（已持续{r['duration_days']}个交易日，预计{r['expected_remaining']}）"
        line += f"\n   {signal_emoji} 建议【{r['signal']}】"

        message_lines.append(line)

    message_lines.append("\n💡 策略说明: 20日均线 vs 60日均线金叉/死叉")
    message_lines.append("⏰ 每天15:30自动推送")

    full_message = "\n".join(message_lines)

    print("\n" + "=" * 50)
    print("推送内容:")
    print(full_message)
    print("=" * 50)

    # 推送
    title = f"股票趋势跟踪 {today}"
    send_wechat_message(title, full_message)

    # 保存结果到文件（方便调试）
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"trend_{today.replace('-', '')}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "date": today,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
