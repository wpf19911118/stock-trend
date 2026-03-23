#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多因子评分系统 V2
基于技术、估值、宏观、情绪四个维度进行综合评分
整合估值分析模块
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from valuation_analysis import ValuationAnalyzer, ValuationMetrics


class Grade(Enum):
    """评级枚举"""
    A = "A级-强烈买入"
    B = "B级-买入"
    C = "C级-持有"
    D = "D级-观望"
    E = "E级-卖出"


@dataclass
class ScoreResult:
    """评分结果"""
    symbol: str
    name: str
    market: str
    
    # 各维度得分
    technical_score: float      # 技术面 (30分)
    valuation_score: float      # 估值面 (35分)
    macro_score: float          # 宏观面 (25分)
    sentiment_score: float      # 情绪面 (10分)
    
    # 总分和评级
    total_score: float
    grade: str
    grade_emoji: str
    
    # 详细信号
    technical_signals: List[str]
    valuation_signals: List[str]
    macro_signals: List[str]
    sentiment_signals: List[str]
    
    # 操作建议
    action: str
    position_suggest: str
    
    # 关键指标快照
    close: float
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    ma_50: float
    ma_200: float
    rsi_14: Optional[float]
    
    # 估值信息
    pe_percentile: Optional[float] = None
    pb_percentile: Optional[float] = None
    valuation_level: str = "未知"
    risk_premium: Optional[float] = None
    risk_premium_level: str = "未知"


class MultiFactorScorerV2:
    """多因子评分器 V2"""
    
    def __init__(self, market_data: Dict, macro_data: Dict):
        """
        初始化评分器
        
        Args:
            market_data: 市场数据字典
            macro_data: 宏观数据字典
        """
        self.market_data = market_data
        self.macro_data = macro_data
        
        # 初始化估值分析器
        self.valuation_analyzer = ValuationAnalyzer()
        
        # 计算所有估值指标
        print("\n📊 正在计算估值指标...")
        self.valuation_metrics = self.valuation_analyzer.analyze_all(market_data)
    
    def calculate_technical_score(self, data: Dict) -> Tuple[float, List[str]]:
        """
        计算技术面得分 (满分30分) - 优化版本
        
        评分标准：
        - 均线趋势 (12分): 50日>200日且价格>50日=12分；50日>200日=6分；死叉=0分
        - MACD (8分): 金叉且>0轴=8分；金叉>5分；死叉=0分
        - RSI (5分): 30-50区间=5分；<30=5分（超卖）；50-70=3分；>70=0分
        - 布林带 (5分): 下轨附近=5分；中轨=3分；上轨=1分
        """
        score = 0
        signals = []
        
        close = data.get("close", 0)
        ma_20 = data.get("ma_20", 0)
        ma_50 = data.get("ma_50", 0)
        ma_200 = data.get("ma_200", 0)
        macd = data.get("macd", 0)
        macd_signal = data.get("macd_signal", 0)
        rsi = data.get("rsi_14", 50)
        upper_band = data.get("upper_band", close * 1.1)
        lower_band = data.get("lower_band", close * 0.9)
        
        # 1. 均线趋势 (12分) - 权重最高
        if ma_50 > ma_200:
            if close > ma_50:
                score += 12
                signals.append("✅ 均线多头排列且价格在50日均线上方")
            else:
                score += 6
                signals.append("⚠️ 均线多头但价格在50日均线下方")
        else:
            signals.append("❌ 均线空头排列 (50日<200日)")
        
        # 2. MACD (8分)
        if macd > macd_signal:
            if macd > 0:
                score += 8
                signals.append("✅ MACD金叉且在零轴上方")
            else:
                score += 5
                signals.append("⚠️ MACD金叉但在零轴下方")
        else:
            if macd < 0 and macd_signal < 0:
                signals.append("❌ MACD死叉且在零轴下方（弱势）")
            else:
                signals.append("❌ MACD死叉")
        
        # 3. RSI (5分)
        if rsi is not None:
            if rsi < 30:
                score += 5
                signals.append(f"✅ RSI超卖 ({rsi:.1f}) - 强烈反弹信号")
            elif rsi < 50:
                score += 5
                signals.append(f"✅ RSI健康区间 ({rsi:.1f})")
            elif rsi < 70:
                score += 3
                signals.append(f"⚠️ RSI偏高 ({rsi:.1f})")
            else:
                signals.append(f"❌ RSI超买 ({rsi:.1f}) - 回调风险")
        
        # 4. 布林带 (5分)
        band_range = upper_band - lower_band
        if band_range > 0:
            position = (close - lower_band) / band_range
            if position < 0.3:
                score += 5
                signals.append("✅ 价格接近布林带下轨（超卖区）")
            elif position < 0.7:
                score += 3
                signals.append("⚠️ 价格在布林带中轨附近")
            elif position < 0.9:
                score += 1
                signals.append("⚠️ 价格接近布林带上轨")
            else:
                signals.append("❌ 价格突破布林带上轨（超买）")
        
        return score, signals
    
    def calculate_valuation_score(self, symbol: str, data: Dict) -> Tuple[float, List[str]]:
        """
        计算估值面得分 (满分35分) - 优化版本
        
        评分标准：
        - PE分位 (15分): <20%=15分；20-40%=12分；40-60%=7分；>60%=0分
        - PB分位 (10分): <20%=10分；20-40%=7分；40-60%=3分；>60%=0分
        - 股债性价比 (10分): >4%=10分；3-4%=7分；2-3%=3分；<2%=0分
        """
        score = 0
        signals = []
        
        # 获取估值指标
        metrics = self.valuation_metrics.get(symbol)
        
        if metrics:
            pe_pct = metrics.pe_percentile
            pb_pct = metrics.pb_percentile
            risk_premium = metrics.risk_premium
            
            # 1. PE分位评分 (15分)
            if pe_pct is not None:
                if pe_pct < 20:
                    score += 15
                    signals.append(f"✅ PE极度低估 ({pe_pct:.1f}%分位)")
                elif pe_pct < 40:
                    score += 12
                    signals.append(f"✅ PE低估 ({pe_pct:.1f}%分位)")
                elif pe_pct < 60:
                    score += 7
                    signals.append(f"⚠️ PE合理 ({pe_pct:.1f}%分位)")
                else:
                    signals.append(f"❌ PE高估 ({pe_pct:.1f}%分位)")
            else:
                signals.append("⚠️ PE分位数据缺失")
            
            # 2. PB分位评分 (10分)
            if pb_pct is not None:
                if pb_pct < 20:
                    score += 10
                    signals.append(f"✅ PB极度低估 ({pb_pct:.1f}%分位)")
                elif pb_pct < 40:
                    score += 7
                    signals.append(f"✅ PB低估 ({pb_pct:.1f}%分位)")
                elif pb_pct < 60:
                    score += 3
                    signals.append(f"⚠️ PB合理 ({pb_pct:.1f}%分位)")
                else:
                    signals.append(f"❌ PB高估 ({pb_pct:.1f}%分位)")
            else:
                signals.append("⚠️ PB分位数据缺失")
            
            # 3. 股债性价比 (10分)
            if risk_premium is not None:
                if risk_premium > 4:
                    score += 10
                    signals.append(f"✅ 股债性价比极佳 ({risk_premium:.1f}%)")
                elif risk_premium > 3:
                    score += 7
                    signals.append(f"✅ 股债性价比良好 ({risk_premium:.1f}%)")
                elif risk_premium > 2:
                    score += 3
                    signals.append(f"⚠️ 股债性价比一般 ({risk_premium:.1f}%)")
                else:
                    signals.append(f"❌ 股债性价比差 ({risk_premium:.1f}%)")
            else:
                signals.append("⚠️ 股债性价比数据缺失")
        else:
            signals.append("❌ 估值数据缺失")
        
        return score, signals
    
    def calculate_macro_score(self, market: str) -> Tuple[float, List[str]]:
        """
        计算宏观面得分 (满分25分) - 优化版本
        
        评分标准：
        - 利率环境 (10分): 降息/低利率=10分；中性=5分；加息/高利率=0分
        - VIX/中国波指恐慌指数 (8分): >30=8分；20-30=5分；<15=0分(过度乐观)
        - 美元指数 (7分): A股专用，走弱=7分；震荡=3分；走强=0分
        """
        score = 0
        signals = []
        
        us_yield = self.macro_data.get("us_10y_yield", 4.2)
        cn_yield = self.macro_data.get("cn_10y_yield", 2.8)
        vix = self.macro_data.get("vix", 20)
        cn_vix = self.macro_data.get("cn_vix", 20)  # 中国波指 iVIX
        dxy = self.macro_data.get("dxy", 102)
        
        # 1. 利率环境 (10分)
        if market == "美股":
            if us_yield < 3.5:
                score += 10
                signals.append(f"✅ 美债收益率低位 ({us_yield:.2f}%) - 利好成长股")
            elif us_yield < 4.5:
                score += 5
                signals.append(f"⚠️ 美债收益率中性 ({us_yield:.2f}%)")
            else:
                signals.append(f"❌ 美债收益率高位 ({us_yield:.2f}%) - 压制估值")
        else:  # A股
            if cn_yield < 2.8:
                score += 10
                signals.append(f"✅ 中债收益率下行 ({cn_yield:.2f}%) - 流动性宽松")
            elif cn_yield < 3.2:
                score += 5
                signals.append(f"⚠️ 中债收益率中性 ({cn_yield:.2f}%)")
            else:
                signals.append(f"❌ 中债收益率上行 ({cn_yield:.2f}%) - 流动性收紧")
        
        # 2. 恐慌指数 (8分) - 美股用VIX，A股用50ETF波动率（中国波指iVIX替代）
        if market == "美股":
            if vix:
                if vix > 35:
                    score += 8
                    signals.append(f"✅ VIX极度恐慌 ({vix:.1f}) - 逆向买入机会")
                elif vix > 25:
                    score += 5
                    signals.append(f"⚠️ VIX担忧情绪 ({vix:.1f})")
                elif vix > 20:
                    score += 2
                    signals.append(f"⚠️ VIX轻度担忧 ({vix:.1f})")
                else:
                    signals.append(f"❌ VIX极度贪婪 ({vix:.1f}) - 市场过热")
        else:  # A股 - 使用50ETF历史波动率（中国波指iVIX替代）
            if cn_vix:
                # 50ETF波动率阈值（低于VIX）
                if cn_vix > 30:
                    score += 8
                    signals.append(f"✅ A股恐慌 ({cn_vix:.1f}%) - 50ETF波动率高，逆向买入")
                elif cn_vix > 25:
                    score += 5
                    signals.append(f"⚠️ A股担忧 ({cn_vix:.1f}%) - 50ETF波动率偏高")
                elif cn_vix > 15:
                    score += 2
                    signals.append(f"⚠️ A股波动正常 ({cn_vix:.1f}%) - 50ETF波动率适中")
                else:
                    signals.append(f"❌ A股过度乐观 ({cn_vix:.1f}%) - 50ETF波动率过低，警惕风险")
        
        # 3. 美元指数 (7分) - 主要影响A股/新兴市场
        if market == "A股" and dxy:
            if dxy < 100:
                score += 7
                signals.append(f"✅ 美元指数走弱 ({dxy:.1f}) - 外资流入")
            elif dxy < 104:
                score += 3
                signals.append(f"⚠️ 美元指数震荡 ({dxy:.1f})")
            else:
                signals.append(f"❌ 美元指数走强 ({dxy:.1f}) - 资金回流美国")
        
        return score, signals
    
    def calculate_sentiment_score(self, data: Dict) -> Tuple[float, List[str]]:
        """
        计算情绪面得分 (满分10分) - 优化版本
        
        评分标准：
        - 短期动量 (4分): 近5日正收益=4分；震荡=2分；负收益=0分
        - 波动率 (3分): 低波动=3分；中波动=1分；高波动=0分
        - 趋势强度 (3分): 价格在均线上方且均线向上=3分；其他=1分
        """
        score = 0
        signals = []
        
        close = data.get("close", 0)
        ma_20 = data.get("ma_20", 0)
        hist = data.get("hist_data")
        
        if hist is not None and len(hist) >= 20:
            df = hist if isinstance(hist, pd.DataFrame) else pd.DataFrame(hist)
            
            # 1. 短期动量 (4分)
            if len(df) >= 5:
                recent_return = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5] * 100
                if recent_return > 3:
                    score += 4
                    signals.append(f"✅ 短期动量强劲 (+{recent_return:.1f}%)")
                elif recent_return > -2:
                    score += 2
                    signals.append(f"⚠️ 短期动量中性 ({recent_return:.1f}%)")
                else:
                    signals.append(f"❌ 短期动量疲软 ({recent_return:.1f}%)")
            
            # 2. 波动率 (3分)
            if len(df) >= 20:
                volatility = df["close"].pct_change().rolling(20).std().iloc[-1] * 100 * np.sqrt(252)
                if volatility < 15:
                    score += 3
                    signals.append(f"✅ 波动率较低 ({volatility:.1f}%年化)")
                elif volatility < 25:
                    score += 1
                    signals.append(f"⚠️ 波动率中等 ({volatility:.1f}%年化)")
                else:
                    signals.append(f"❌ 波动率较高 ({volatility:.1f}%年化)")
            
            # 3. 趋势强度 (3分)
            if close > ma_20 and len(df) >= 25:
                ma_20_slope = (df["close"].rolling(20).mean().iloc[-1] - 
                              df["close"].rolling(20).mean().iloc[-5]) / 5
                if ma_20_slope > 0:
                    score += 3
                    signals.append("✅ 价格站上20日均线且均线向上")
                else:
                    score += 1
                    signals.append("⚠️ 价格站上20日均线但均线走平")
            else:
                signals.append("❌ 价格位于20日均线下方")
        else:
            signals.append("⚠️ 历史数据不足，情绪指标缺失")
        
        return score, signals
    
    def get_grade(self, total_score: float) -> Tuple[str, str]:
        """
        根据总分确定评级
        
        Returns:
            (评级描述, emoji)
        """
        if total_score >= 80:
            return Grade.A.value, "🚀"
        elif total_score >= 65:
            return Grade.B.value, "📈"
        elif total_score >= 50:
            return Grade.C.value, "➡️"
        elif total_score >= 35:
            return Grade.D.value, "⚠️"
        else:
            return Grade.E.value, "📉"
    
    def get_action_advice(self, grade: str, score: float) -> Tuple[str, str]:
        """
        根据评级给出操作建议
        
        Returns:
            (操作建议, 仓位建议)
        """
        if "强烈买入" in grade:
            return "超配，积极加仓", "90-100%"
        elif "买入" in grade:
            return "标配，可建仓", "70-90%"
        elif "持有" in grade:
            return "中性，维持现状", "50-70%"
        elif "观望" in grade:
            return "减仓，等待机会", "30-50%"
        else:
            return "清仓或做空", "0-30%"
    
    def score_single(self, symbol: str, data: Dict) -> ScoreResult:
        """
        对单个标的进行评分
        
        Args:
            symbol: 代码
            data: 市场数据
        
        Returns:
            ScoreResult对象
        """
        market = data.get("market", "A股")
        name = data.get("name", symbol)
        
        print(f"\n📊 正在评分 {name} ({symbol})...")
        
        # 计算各维度得分
        tech_score, tech_signals = self.calculate_technical_score(data)
        val_score, val_signals = self.calculate_valuation_score(symbol, data)
        macro_score, macro_signals = self.calculate_macro_score(market)
        sent_score, sent_signals = self.calculate_sentiment_score(data)
        
        # 总分
        total_score = tech_score + val_score + macro_score + sent_score
        
        # 评级
        grade, emoji = self.get_grade(total_score)
        
        # 操作建议
        action, position = self.get_action_advice(grade, total_score)
        
        # 获取估值信息
        metrics = self.valuation_metrics.get(symbol)
        
        result = ScoreResult(
            symbol=symbol,
            name=name,
            market=market,
            technical_score=round(tech_score, 1),
            valuation_score=round(val_score, 1),
            macro_score=round(macro_score, 1),
            sentiment_score=round(sent_score, 1),
            total_score=round(total_score, 1),
            grade=grade,
            grade_emoji=emoji,
            technical_signals=tech_signals,
            valuation_signals=val_signals,
            macro_signals=macro_signals,
            sentiment_signals=sent_signals,
            action=action,
            position_suggest=position,
            close=data.get("close", 0),
            pe_ratio=data.get("pe_ratio"),
            pb_ratio=data.get("pb_ratio"),
            ma_50=data.get("ma_50", 0),
            ma_200=data.get("ma_200", 0),
            rsi_14=data.get("rsi_14"),
            pe_percentile=metrics.pe_percentile if metrics else None,
            pb_percentile=metrics.pb_percentile if metrics else None,
            valuation_level=metrics.valuation_level if metrics else "未知",
            risk_premium=metrics.risk_premium if metrics else None,
            risk_premium_level=metrics.risk_premium_level if metrics else "未知"
        )
        
        print(f"   技术:{tech_score}/30 估值:{val_score}/35 宏观:{macro_score}/25 情绪:{sent_score}/10")
        print(f"   总分:{total_score}/100 | 评级:{emoji} {grade}")
        
        return result
    
    def score_all(self) -> List[ScoreResult]:
        """
        对所有标的进行评分
        
        Returns:
            ScoreResult列表
        """
        results = []
        
        # A股评分
        for symbol, data in self.market_data.get("a_shares", {}).items():
            result = self.score_single(symbol, data)
            results.append(result)
        
        # 美股评分
        for symbol, data in self.market_data.get("us_stocks", {}).items():
            result = self.score_single(symbol, data)
            results.append(result)
        
        return results


def format_score_report(results: List[ScoreResult]) -> str:
    """
    格式化评分报告
    
    Args:
        results: 评分结果列表
    
    Returns:
        格式化后的报告文本
    """
    lines = []
    lines.append("=" * 70)
    lines.append("📊 多因子综合评分报告 V2")
    lines.append("=" * 70)
    
    # 按得分排序
    sorted_results = sorted(results, key=lambda x: x.total_score, reverse=True)
    
    for i, r in enumerate(sorted_results, 1):
        lines.append(f"\n{i}. {r.grade_emoji} {r.name} ({r.symbol})")
        lines.append(f"   综合得分: {r.total_score}/100 | {r.grade}")
        lines.append(f"   当前价格: {r.close}")
        
        # 估值信息
        if r.pe_ratio:
            pe_pct_str = f"(分位{r.pe_percentile}%)" if r.pe_percentile else ""
            lines.append(f"   PE: {r.pe_ratio:.1f} {pe_pct_str} | 估值: {r.valuation_level}")
        
        if r.risk_premium:
            lines.append(f"   股债性价比: {r.risk_premium}%")
        
        lines.append(f"   操作建议: {r.action} | 仓位: {r.position_suggest}")
        lines.append("")
        lines.append(f"   分项得分:")
        lines.append(f"     技术面: {r.technical_score}/30  估值面: {r.valuation_score}/35")
        lines.append(f"     宏观面: {r.macro_score}/25  情绪面: {r.sentiment_score}/10")
        lines.append("")
        
        # 显示关键信号（每类最多2个）
        all_signals = (
            [("技术面", s) for s in r.technical_signals[:2]] +
            [("估值面", s) for s in r.valuation_signals[:2]] +
            [("宏观面", s) for s in r.macro_signals[:1]]
        )
        
        lines.append(f"   关键信号:")
        for category, signal in all_signals:
            lines.append(f"     • {signal}")
        lines.append("")
    
    lines.append("=" * 70)
    lines.append("💡 策略说明: 基于技术+估值+宏观+情绪四维度综合评分")
    lines.append("⏰ 建议调仓周期: 每季度评估 | 数据来源: Yahoo Finance / Akshare")
    lines.append("=" * 70)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试评分系统
    print("\n开始测试多因子评分系统 V2...")
    
    # 模拟市场数据
    mock_data = {
        "a_shares": {
            "000300": {
                "symbol": "000300",
                "name": "沪深300",
                "market": "A股",
                "close": 3500.0,
                "change_pct": 0.5,
                "ma_20": 3450.0,
                "ma_50": 3400.0,
                "ma_200": 3300.0,
                "rsi_14": 45.0,
                "macd": 10.5,
                "macd_signal": 8.2,
                "upper_band": 3600.0,
                "lower_band": 3300.0,
                "hist_data": pd.DataFrame({
                    "close": [3300 + i*2 for i in range(30)]
                })
            }
        },
        "us_stocks": {
            "^IXIC": {
                "symbol": "^IXIC",
                "name": "纳斯达克",
                "market": "美股",
                "close": 15000.0,
                "change_pct": 1.2,
                "ma_20": 14800.0,
                "ma_50": 14500.0,
                "ma_200": 14000.0,
                "rsi_14": 55.0,
                "macd": 25.3,
                "macd_signal": 20.1,
                "upper_band": 15500.0,
                "lower_band": 14500.0,
                "hist_data": pd.DataFrame({
                    "close": [14000 + i*30 for i in range(30)]
                })
            }
        }
    }
    
    mock_macro = {
        "us_10y_yield": 4.2,
        "cn_10y_yield": 2.8,
        "vix": 22.0,
        "dxy": 102.5
    }
    
    # 创建评分器
    scorer = MultiFactorScorerV2(mock_data, mock_macro)
    
    # 评分
    results = scorer.score_all()
    
    # 生成报告
    report = format_score_report(results)
    print("\n" + report)
    
    print("\n测试完成！")
