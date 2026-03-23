#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理模块
风险评估、止损止盈、仓位控制
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RiskMetrics:
    """风险指标"""
    symbol: str
    name: str
    
    # 波动率指标
    volatility_20d: float  # 20日波动率
    volatility_60d: float  # 60日波动率
    max_drawdown_90d: float  # 90日最大回撤
    
    # 风险价值
    var_95: float  # 95%置信度VaR
    var_99: float  # 99%置信度VaR
    
    # Beta值（相对于市场）
    beta: Optional[float]
    
    # 风险评级
    risk_level: str  # 低/中/高/极高
    
    # 建议
    suggestion: str


class RiskManager:
    """风险管理器"""
    
    def __init__(self, max_position_pct: float = 0.3, max_drawdown_pct: float = 0.15):
        """
        初始化风险管理器
        
        Args:
            max_position_pct: 单个标的最大仓位（默认30%）
            max_drawdown_pct: 最大回撤容忍度（默认15%）
        """
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        
        # 止损止盈设置
        self.stop_loss_pct = 0.10  # 止损10%
        self.take_profit_pct = 0.20  # 止盈20%
        self.trailing_stop_pct = 0.08  # 移动止损8%
    
    def calculate_volatility(self, prices: List[float], window: int = 20) -> float:
        """
        计算波动率
        
        Args:
            prices: 价格列表
            window: 计算窗口
        
        Returns:
            年化波动率 (%)
        """
        if len(prices) < window + 1:
            return 0.0
        
        import numpy as np
        
        # 计算日收益率
        returns = []
        for i in range(1, len(prices)):
            daily_return = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(daily_return)
        
        # 计算标准差（年化）
        volatility = np.std(returns[-window:]) * np.sqrt(252) * 100
        
        return round(volatility, 2)
    
    def calculate_max_drawdown(self, prices: List[float]) -> float:
        """
        计算最大回撤
        
        Args:
            prices: 价格列表
        
        Returns:
            最大回撤 (%)
        """
        if not prices:
            return 0.0
        
        max_dd = 0.0
        peak = prices[0]
        
        for price in prices:
            if price > peak:
                peak = price
            drawdown = (peak - price) / peak
            max_dd = max(max_dd, drawdown)
        
        return round(max_dd * 100, 2)
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        计算风险价值 (VaR)
        
        Args:
            returns: 收益率列表
            confidence: 置信度
        
        Returns:
            VaR (%)
        """
        if not returns:
            return 0.0
        
        import numpy as np
        
        var = np.percentile(returns, (1 - confidence) * 100)
        return round(abs(var) * 100, 2)
    
    def calculate_beta(self, stock_returns: List[float], market_returns: List[float]) -> Optional[float]:
        """
        计算Beta值
        
        Args:
            stock_returns: 股票收益率
            market_returns: 市场收益率
        
        Returns:
            Beta值
        """
        if len(stock_returns) != len(market_returns) or len(stock_returns) < 30:
            return None
        
        import numpy as np
        
        covariance = np.cov(stock_returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        
        if market_variance == 0:
            return None
        
        beta = covariance / market_variance
        return round(beta, 2)
    
    def assess_risk(self, symbol: str, name: str, prices: List[float], 
                   market_prices: Optional[List[float]] = None) -> RiskMetrics:
        """
        风险评估
        
        Args:
            symbol: 股票代码
            name: 股票名称
            prices: 价格数据
            market_prices: 市场基准价格（用于计算Beta）
        
        Returns:
            RiskMetrics对象
        """
        import numpy as np
        
        # 计算收益率
        returns = []
        for i in range(1, len(prices)):
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        # 波动率
        vol_20d = self.calculate_volatility(prices, 20)
        vol_60d = self.calculate_volatility(prices, 60)
        
        # 最大回撤
        max_dd = self.calculate_max_drawdown(prices)
        
        # VaR
        var_95 = self.calculate_var(returns, 0.95)
        var_99 = self.calculate_var(returns, 0.99)
        
        # Beta
        beta = None
        if market_prices and len(market_prices) == len(prices):
            market_returns = []
            for i in range(1, len(market_prices)):
                market_returns.append((market_prices[i] - market_prices[i-1]) / market_prices[i-1])
            beta = self.calculate_beta(returns, market_returns)
        
        # 风险评级
        risk_score = 0
        if vol_20d > 30:
            risk_score += 3
        elif vol_20d > 20:
            risk_score += 2
        elif vol_20d > 10:
            risk_score += 1
        
        if max_dd > 20:
            risk_score += 3
        elif max_dd > 15:
            risk_score += 2
        elif max_dd > 10:
            risk_score += 1
        
        if var_95 > 3:
            risk_score += 2
        elif var_95 > 2:
            risk_score += 1
        
        if risk_score >= 7:
            risk_level = "极高"
            suggestion = "风险极高，建议减仓或清仓"
        elif risk_score >= 5:
            risk_level = "高"
            suggestion = "风险较高，建议控制仓位"
        elif risk_score >= 3:
            risk_level = "中"
            suggestion = "风险中等，正常监控"
        else:
            risk_level = "低"
            suggestion = "风险较低，可正常持有"
        
        return RiskMetrics(
            symbol=symbol,
            name=name,
            volatility_20d=vol_20d,
            volatility_60d=vol_60d,
            max_drawdown_90d=max_dd,
            var_95=var_95,
            var_99=var_99,
            beta=beta,
            risk_level=risk_level,
            suggestion=suggestion
        )
    
    def check_stop_loss(self, current_price: float, avg_cost: float) -> Tuple[bool, str]:
        """
        检查止损
        
        Args:
            current_price: 当前价格
            avg_cost: 平均成本
        
        Returns:
            (是否触发止损, 原因)
        """
        if avg_cost <= 0:
            return False, ""
        
        loss_pct = (current_price - avg_cost) / avg_cost
        
        if loss_pct <= -self.stop_loss_pct:
            return True, f"触发止损线 {self.stop_loss_pct*100:.0f}%，当前亏损 {abs(loss_pct)*100:.1f}%"
        
        return False, ""
    
    def check_take_profit(self, current_price: float, avg_cost: float) -> Tuple[bool, str]:
        """
        检查止盈
        
        Args:
            current_price: 当前价格
            avg_cost: 平均成本
        
        Returns:
            (是否触发止盈, 原因)
        """
        if avg_cost <= 0:
            return False, ""
        
        profit_pct = (current_price - avg_cost) / avg_cost
        
        if profit_pct >= self.take_profit_pct:
            return True, f"触发止盈线 {self.take_profit_pct*100:.0f}%，当前盈利 {profit_pct*100:.1f}%"
        
        return False, ""
    
    def check_trailing_stop(self, current_price: float, highest_price: float) -> Tuple[bool, str]:
        """
        检查移动止损
        
        Args:
            current_price: 当前价格
            highest_price: 期间最高价
        
        Returns:
            (是否触发移动止损, 原因)
        """
        if highest_price <= 0:
            return False, ""
        
        drawdown_from_peak = (highest_price - current_price) / highest_price
        
        if drawdown_from_peak >= self.trailing_stop_pct:
            return True, f"触发移动止损 {self.trailing_stop_pct*100:.0f}%，从高点回撤 {drawdown_from_peak*100:.1f}%"
        
        return False, ""
    
    def get_position_suggestion(self, symbol: str, risk_level: str, 
                               current_weight: float, score: float) -> Dict:
        """
        获取仓位建议
        
        Args:
            symbol: 股票代码
            risk_level: 风险等级
            current_weight: 当前仓位权重
            score: 综合评分
        
        Returns:
            建议字典
        """
        suggestion = {
            'action': 'hold',
            'target_weight': current_weight,
            'reason': '维持现状'
        }
        
        # 根据风险等级调整
        if risk_level == "极高":
            suggestion['action'] = 'reduce'
            suggestion['target_weight'] = max(0.05, current_weight * 0.5)
            suggestion['reason'] = '风险极高，建议大幅减仓'
        elif risk_level == "高":
            if current_weight > self.max_position_pct:
                suggestion['action'] = 'reduce'
                suggestion['target_weight'] = self.max_position_pct
                suggestion['reason'] = f'风险较高，仓位不超过{self.max_position_pct*100:.0f}%'
        
        # 根据评分调整
        if score >= 80 and risk_level in ["低", "中"]:
            if current_weight < self.max_position_pct:
                suggestion['action'] = 'increase'
                suggestion['target_weight'] = min(self.max_position_pct, current_weight + 0.1)
                suggestion['reason'] = '评分高且风险可控，可适当加仓'
        elif score < 35:
            suggestion['action'] = 'reduce'
            suggestion['target_weight'] = max(0.05, current_weight * 0.5)
            suggestion['reason'] = '评分极低，建议减仓'
        
        return suggestion
    
    def print_risk_report(self, metrics: RiskMetrics):
        """打印风险报告"""
        print("\n" + "=" * 70)
        print(f"⚠️ 风险报告: {metrics.name} ({metrics.symbol})")
        print("=" * 70)
        
        print(f"\n📊 风险指标:")
        print(f"   20日波动率: {metrics.volatility_20d:.2f}%")
        print(f"   60日波动率: {metrics.volatility_60d:.2f}%")
        print(f"   最大回撤: {metrics.max_drawdown_90d:.2f}%")
        print(f"   VaR (95%): {metrics.var_95:.2f}%")
        print(f"   VaR (99%): {metrics.var_99:.2f}%")
        
        if metrics.beta:
            print(f"   Beta值: {metrics.beta:.2f}")
        
        # 风险评级颜色
        risk_colors = {
            "低": "🟢",
            "中": "🟡",
            "高": "🔴",
            "极高": "🚨"
        }
        
        emoji = risk_colors.get(metrics.risk_level, "⚪")
        print(f"\n{emoji} 风险评级: {metrics.risk_level}")
        print(f"💡 建议: {metrics.suggestion}")
        
        print("=" * 70)


def demo_risk_manager():
    """演示风险管理"""
    print("=" * 70)
    print("⚠️ 风险管理演示")
    print("=" * 70)
    
    # 创建风险管理器
    risk_mgr = RiskManager(max_position_pct=0.3, max_drawdown_pct=0.15)
    
    # 模拟价格数据
    import numpy as np
    np.random.seed(42)
    
    # 生成波动较大的价格序列
    returns = np.random.normal(0.001, 0.025, 100)
    prices = [100]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    
    # 风险评估
    print("\n📊 风险评估...")
    metrics = risk_mgr.assess_risk(
        symbol="000300",
        name="沪深300",
        prices=prices,
        market_prices=None
    )
    
    risk_mgr.print_risk_report(metrics)
    
    # 止损检查
    print("\n🛑 止损检查演示:")
    avg_cost = 105
    current_price = 92
    
    triggered, reason = risk_mgr.check_stop_loss(current_price, avg_cost)
    if triggered:
        print(f"   触发止损: {reason}")
    else:
        print(f"   未触发止损: 成本{avg_cost}, 现价{current_price}")
    
    # 止盈检查
    print("\n🎯 止盈检查演示:")
    avg_cost = 100
    current_price = 125
    
    triggered, reason = risk_mgr.check_take_profit(current_price, avg_cost)
    if triggered:
        print(f"   触发止盈: {reason}")
    
    # 仓位建议
    print("\n📈 仓位建议:")
    suggestion = risk_mgr.get_position_suggestion(
        symbol="000300",
        risk_level=metrics.risk_level,
        current_weight=0.35,
        score=45
    )
    print(f"   建议操作: {suggestion['action']}")
    print(f"   目标仓位: {suggestion['target_weight']*100:.0f}%")
    print(f"   原因: {suggestion['reason']}")
    
    print("\n✅ 演示完成!")


if __name__ == "__main__":
    demo_risk_manager()
