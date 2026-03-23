#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多因子评分系统
基于技术、估值、宏观、情绪四个维度进行综合评分
"""

import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


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


class MultiFactorScorer:
    """多因子评分器"""
    
    def __init__(self, market_data: Dict, macro_data: Dict):
        """
        初始化评分器
        
        Args:
            market_data: 市场数据字典
            macro_data: 宏观数据字典
        """
        self.market_data = market_data
        self.macro_data = macro_data
        
    def calculate_technical_score(self, data: Dict) -> Tuple[float, List[str]]:
        """
        计算技术面得分 (满分30分)
        
        评分标准：
        - 均线趋势 (10分): 50日>200日且向上=10分；50日>200日=5分；死叉=0分
        - MACD (10分): 金叉且>0轴=10分；金叉=5分；死叉=0分
        - RSI (5分): 30-50区间=5分；<30=5分（超卖）；>70=0分（超买）
        - 布林带 (5分): 下轨附近=5分；中轨=3分；上轨=0分
        """
        score = 0
        signals = []
        
        close = data.get("close", 0)
        ma_50 = data.get("ma_50", 0)
        ma_200 = data.get("ma_200", 0)
        macd = data.get("macd", 0)
        macd_signal = data.get("macd_signal", 0)
        rsi = data.get("rsi_14", 50)
        upper_band = data.get("upper_band", close * 1.1)
        lower_band = data.get("lower_band", close * 0.9)
        
        # 1. 均线趋势 (10分)
        if ma_50 > ma_200:
            # 判断趋势方向（简单判断，可以用更复杂的逻辑）
            score += 10
            signals.append("✅ 均线多头排列 (50日>200日)")
        else:
            signals.append("❌ 均线空头排列 (50日<200日)")
        
        # 2. MACD (10分)
        if macd > macd_signal:
            if macd > 0:
                score += 10
                signals.append("✅ MACD金叉且在零轴上方")
            else:
                score += 5
                signals.append("⚠️ MACD金叉但在零轴下方")
        else:
            signals.append("❌ MACD死叉")
        
        # 3. RSI (5分)
        if rsi is not None:
            if rsi < 30:
                score += 5
                signals.append(f"✅ RSI超卖 ({rsi:.1f}) - 潜在反弹")
            elif rsi < 50:
                score += 5
                signals.append(f"✅ RSI处于合理区间 ({rsi:.1f})")
            elif rsi < 70:
                score += 3
                signals.append(f"⚠️ RSI偏高 ({rsi:.1f})")
            else:
                signals.append(f"❌ RSI超买 ({rsi:.1f}) - 注意回调风险")
        
        # 4. 布林带 (5分)
        band_range = upper_band - lower_band
        if band_range > 0:
            position = (close - lower_band) / band_range
            if position < 0.3:
                score += 5
                signals.append("✅ 价格处于布林带下轨附近")
            elif position < 0.7:
                score += 3
                signals.append("⚠️ 价格处于布林带中轨附近")
            else:
                signals.append("❌ 价格处于布林带上轨附近")
        
        return score, signals
    
    def calculate_valuation_score(self, data: Dict, market: str) -> Tuple[float, List[str]]:
        """
        计算估值面得分 (满分35分)
        
        评分标准：
        - PE分位 (15分): <30%=15分；30-50%=10分；50-70%=5分；>70%=0分
        - PB分位 (10分): <30%=10分；30-50%=7分；50-70%=3分；>70%=0分
        - 股债性价比 (10分): >4%=10分；3-4%=7分；2-3%=3分；<2%=0分
        """
        score = 0
        signals = []
        
        pe = data.get("pe_ratio")
        pb = data.get("pb_ratio")
        
        # 历史估值分位（简化版本，使用固定阈值）
        # A股合理PE区间：10-25，美股合理PE区间：15-30
        if market == "A股":
            pe_low, pe_high = 10, 25
            pb_low, pb_high = 1.0, 2.5
        else:  # 美股
            pe_low, pe_high = 15, 30
            pb_low, pb_high = 2.0, 4.0
        
        # 1. PE评分 (15分)
        if pe:
            if pe < pe_low:
                score += 15
                signals.append(f"✅ PE极度低估 ({pe:.1f} < {pe_low})")
            elif pe < (pe_low + pe_high) / 2:
                score += 10
                signals.append(f"✅ PE合理偏低 ({pe:.1f})")
            elif pe < pe_high:
                score += 5
                signals.append(f"⚠️ PE偏高 ({pe:.1f})")
            else:
                signals.append(f"❌ PE高估 ({pe:.1f} > {pe_high})")
        else:
            signals.append("⚠️ PE数据缺失")
        
        # 2. PB评分 (10分)
        if pb:
            if pb < pb_low:
                score += 10
                signals.append(f"✅ PB极度低估 ({pb:.1f} < {pb_low})")
            elif pb < (pb_low + pb_high) / 2:
                score += 7
                signals.append(f"✅ PB合理偏低 ({pb:.1f})")
            elif pb < pb_high:
                score += 3
                signals.append(f"⚠️ PB偏高 ({pb:.1f})")
            else:
                signals.append(f"❌ PB高估 ({pb:.1f} > {pb_high})")
        else:
            signals.append("⚠️ PB数据缺失")
        
        # 3. 股债性价比 (10分)
        if pe and pe > 0:
            earnings_yield = 1 / pe * 100  # 盈利收益率 %
            
            # 获取对应市场的国债收益率
            if market == "A股":
                bond_yield = self.macro_data.get("cn_10y_yield", 2.5)
            else:
                bond_yield = self.macro_data.get("us_10y_yield", 4.0)
            
            risk_premium = earnings_yield - bond_yield
            
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
                signals.append(f"❌ 股债性价比差 ({risk_premium:.1f}%) - 债券更优")
        
        return score, signals
    
    def calculate_macro_score(self, market: str) -> Tuple[float, List[str]]:
        """
        计算宏观面得分 (满分25分)
        
        评分标准：
        - 利率环境 (10分): 降息周期=10分；维持=5分；加息=0分
        - 美元指数 (8分): 走弱=8分；震荡=4分；走强=0分 (主要影响A股)
        - VIX (7分): >30=7分；20-30=4分；<20=0分
        """
        score = 0
        signals = []
        
        us_yield = self.macro_data.get("us_10y_yield", 4.0)
        cn_yield = self.macro_data.get("cn_10y_yield", 2.5)
        vix = self.macro_data.get("vix", 20)
        dxy = self.macro_data.get("dxy", 100)
        
        # 1. 利率环境 (10分) - 基于美债收益率趋势
        # 简化判断：收益率>4.5%视为紧缩，2.5-4.5%中性，<2.5%宽松
        if market == "美股":
            if us_yield < 3.5:
                score += 10
                signals.append(f"✅ 美债收益率下行 ({us_yield:.2f}%) - 利好股市")
            elif us_yield < 4.5:
                score += 5
                signals.append(f"⚠️ 美债收益率中性 ({us_yield:.2f}%)")
            else:
                signals.append(f"❌ 美债收益率高位 ({us_yield:.2f}%) - 压制估值")
        else:  # A股
            if cn_yield < 2.8:
                score += 10
                signals.append(f"✅ 中债收益率下行 ({cn_yield:.2f}%) - 利好股市")
            elif cn_yield < 3.2:
                score += 5
                signals.append(f"⚠️ 中债收益率中性 ({cn_yield:.2f}%)")
            else:
                signals.append(f"❌ 中债收益率上行 ({cn_yield:.2f}%) - 流动性收紧")
        
        # 2. VIX恐慌指数 (7分)
        if vix:
            if vix > 30:
                score += 7
                signals.append(f"✅ VIX极度恐慌 ({vix:.1f}) - 逆向布局机会")
            elif vix > 20:
                score += 4
                signals.append(f"⚠️ VIX轻度担忧 ({vix:.1f})")
            else:
                signals.append(f"❌ VIX极度贪婪 ({vix:.1f}) - 市场过热")
        
        # 3. 美元指数 (8分) - 主要影响新兴市场/A股
        if market == "A股" and dxy:
            if dxy < 100:
                score += 8
                signals.append(f"✅ 美元指数走弱 ({dxy:.1f}) - 资金流入新兴市场")
            elif dxy < 105:
                score += 4
                signals.append(f"⚠️ 美元指数震荡 ({dxy:.1f})")
            else:
                signals.append(f"❌ 美元指数走强 ({dxy:.1f}) - 资金回流美国")
        
        return score, signals
    
    def calculate_sentiment_score(self, data: Dict) -> Tuple[float, List[str]]:
        """
        计算情绪面得分 (满分10分)
        
        评分标准：
        - 短期动量 (4分): 近5日正收益=4分；震荡=2分；负收益=0分
        - 波动率 (3分): 低波动=3分；中波动=1分；高波动=0分
        - 成交量 (3分): 放量上涨=3分；缩量=1分；放量下跌=0分
        """
        score = 0
        signals = []
        
        # 从hist_data计算情绪指标
        hist = data.get("hist_data")
        
        if hist is not None and len(hist) >= 20:
            df = hist if isinstance(hist, pd.DataFrame) else pd.DataFrame(hist)
            
            # 1. 短期动量 (4分) - 近5日收益
            if len(df) >= 5:
                recent_return = (df["close"].iloc[-1] - df["close"].iloc[-5]) / df["close"].iloc[-5] * 100
                if recent_return > 2:
                    score += 4
                    signals.append(f"✅ 短期动量强劲 (+{recent_return:.1f}%)")
                elif recent_return > -2:
                    score += 2
                    signals.append(f"⚠️ 短期动量中性 ({recent_return:.1f}%)")
                else:
                    signals.append(f"❌ 短期动量疲软 ({recent_return:.1f}%)")
            
            # 2. 波动率 (3分)
            if len(df) >= 20:
                volatility = df["close"].pct_change().rolling(20).std().iloc[-1] * 100
                if volatility < 1.0:
                    score += 3
                    signals.append(f"✅ 波动率较低 ({volatility:.1f}%)")
                elif volatility < 2.0:
                    score += 1
                    signals.append(f"⚠️ 波动率中等 ({volatility:.1f}%)")
                else:
                    signals.append(f"❌ 波动率较高 ({volatility:.1f}%)")
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
    
    def get_action_advice(self, grade: str) -> Tuple[str, str]:
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
        
        # 计算各维度得分
        tech_score, tech_signals = self.calculate_technical_score(data)
        val_score, val_signals = self.calculate_valuation_score(data, market)
        macro_score, macro_signals = self.calculate_macro_score(market)
        sent_score, sent_signals = self.calculate_sentiment_score(data)
        
        # 总分
        total_score = tech_score + val_score + macro_score + sent_score
        
        # 评级
        grade, emoji = self.get_grade(total_score)
        
        # 操作建议
        action, position = self.get_action_advice(grade)
        
        return ScoreResult(
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
            rsi_14=data.get("rsi_14")
        )
    
    def score_all(self) -> List[ScoreResult]:
        """
        对所有标的进行评分
        
        Returns:
            ScoreResult列表
        """
        results = []
        
        # A股评分
        for symbol, data in self.market_data.get("a_shares", {}).items():
            print(f"\n📊 正在评分 {data.get('name', symbol)}...")
            result = self.score_single(symbol, data)
            results.append(result)
            print(f"   总分: {result.total_score}/100 | 评级: {result.grade}")
        
        # 美股评分
        for symbol, data in self.market_data.get("us_stocks", {}).items():
            print(f"\n📈 正在评分 {data.get('name', symbol)}...")
            result = self.score_single(symbol, data)
            results.append(result)
            print(f"   总分: {result.total_score}/100 | 评级: {result.grade}")
        
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
    lines.append("=" * 60)
    lines.append("📊 多因子综合评分报告")
    lines.append("=" * 60)
    lines.append("")
    
    # 按得分排序
    sorted_results = sorted(results, key=lambda x: x.total_score, reverse=True)
    
    for i, r in enumerate(sorted_results, 1):
        lines.append(f"\n{i}. {r.grade_emoji} {r.name} ({r.symbol})")
        lines.append(f"   综合得分: {r.total_score}/100 | {r.grade}")
        lines.append(f"   当前价格: {r.close} | PE: {r.pe_ratio or 'N/A'} | PB: {r.pb_ratio or 'N/A'}")
        lines.append(f"   操作建议: {r.action} | 建议仓位: {r.position_suggest}")
        lines.append("")
        lines.append(f"   分项得分:")
        lines.append(f"     • 技术面: {r.technical_score}/30  估值面: {r.valuation_score}/35")
        lines.append(f"     • 宏观面: {r.macro_score}/25  情绪面: {r.sentiment_score}/10")
        lines.append("")
        
        # 显示关键信号
        all_signals = (
            [("技术面", s) for s in r.technical_signals[:2]] +
            [("估值面", s) for s in r.valuation_signals[:2]] +
            [("宏观面", s) for s in r.macro_signals[:2]]
        )
        
        lines.append(f"   关键信号:")
        for category, signal in all_signals:
            lines.append(f"     • {signal}")
        lines.append("")
    
    lines.append("=" * 60)
    lines.append("💡 策略说明: 基于技术+估值+宏观+情绪四维度评分")
    lines.append("⏰ 建议调仓周期: 每季度评估一次")
    lines.append("=" * 60)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # 测试评分系统
    from market_data import get_all_market_data
    
    print("\n开始测试多因子评分系统...")
    
    # 获取市场数据
    data = get_all_market_data()
    
    # 创建评分器
    scorer = MultiFactorScorer(data, data.get("macro", {}))
    
    # 评分
    results = scorer.score_all()
    
    # 生成报告
    report = format_score_report(results)
    print("\n" + report)
    
    # 保存结果
    import json
    from pathlib import Path
    from dataclasses import asdict
    
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"score_result_{pd.Timestamp.now().strftime('%Y%m%d')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)
    
    print(f"\n评分结果已保存到: {output_file}")
