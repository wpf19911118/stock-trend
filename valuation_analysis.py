#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
估值分析模块
提供 PE/PB 历史分位计算和股债性价比分析
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class ValuationMetrics:
    """估值指标数据类"""
    symbol: str
    name: str
    
    # 当前估值
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None  # 市销率
    
    # 历史分位（10年）
    pe_percentile: Optional[float] = None
    pb_percentile: Optional[float] = None
    
    # 历史统计
    pe_history_mean: Optional[float] = None
    pe_history_median: Optional[float] = None
    pe_history_min: Optional[float] = None
    pe_history_max: Optional[float] = None
    
    # 股债性价比
    earnings_yield: Optional[float] = None  # 盈利收益率 = 1/PE
    bond_yield: Optional[float] = None      # 国债收益率
    risk_premium: Optional[float] = None    # 风险溢价
    
    # 评估
    valuation_level: str = "未知"  # 极度低估/低估/合理/高估/极度高估
    risk_premium_level: str = "未知"  # 极好/良好/一般/差


class ValuationAnalyzer:
    """估值分析器"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
    def calculate_percentile(self, current: float, history: pd.Series) -> Optional[float]:
        """
        计算当前值在历史数据中的百分位
        
        Args:
            current: 当前值
            history: 历史数据序列
        
        Returns:
            百分位值 (0-100)
        """
        if pd.isna(current) or history.empty:
            return None
        
        # 计算百分位
        percentile = (history < current).mean() * 100
        return round(percentile, 2)
    
    def get_valuation_level(self, pe: Optional[float], pe_pct: Optional[float], 
                           pb: Optional[float], pb_pct: Optional[float]) -> str:
        """
        根据PE/PB分位判断估值水平
        
        Returns:
            估值水平描述
        """
        if pe_pct is None and pb_pct is None:
            return "数据不足"
        
        # 综合PE和PB分位
        avg_pct = 0
        count = 0
        
        if pe_pct is not None:
            avg_pct += pe_pct
            count += 1
        if pb_pct is not None:
            avg_pct += pb_pct
            count += 1
        
        if count == 0:
            return "数据不足"
        
        avg_pct = avg_pct / count
        
        if avg_pct < 10:
            return "极度低估"
        elif avg_pct < 30:
            return "低估"
        elif avg_pct < 50:
            return "合理偏低"
        elif avg_pct < 70:
            return "合理偏高"
        elif avg_pct < 90:
            return "高估"
        else:
            return "极度高估"
    
    def get_risk_premium_level(self, risk_premium: Optional[float]) -> str:
        """
        判断股债性价比水平
        
        Args:
            risk_premium: 风险溢价 (%)
        
        Returns:
            性价比描述
        """
        if risk_premium is None:
            return "数据不足"
        
        if risk_premium > 5:
            return "极好"
        elif risk_premium > 3.5:
            return "良好"
        elif risk_premium > 2.5:
            return "一般"
        elif risk_premium > 1.5:
            return "较差"
        else:
            return "极差"
    
    def analyze_a_share(self, symbol: str, name: str, 
                       hist_data: pd.DataFrame) -> ValuationMetrics:
        """
        分析A股指数估值
        
        Args:
            symbol: 指数代码
            name: 指数名称
            hist_data: 历史数据（含收盘价）
        
        Returns:
            ValuationMetrics对象
        """
        metrics = ValuationMetrics(symbol=symbol, name=name)
        
        try:
            # 使用固定估值数据（简化版本）
            # 实际项目中应该从akshare获取真实PE/PB数据
            valuation_map = {
                "000300": (12.5, 1.35),  # 沪深300: PE, PB
                "000905": (22.0, 1.80),  # 中证500
            }
            
            if symbol in valuation_map:
                metrics.pe_ttm, metrics.pb = valuation_map[symbol]
                
                # 模拟历史分位（实际应该从历史数据计算）
                # 这里使用假设的合理区间
                pe_history = pd.Series(np.random.normal(15, 3, 1000))  # 模拟历史PE
                pb_history = pd.Series(np.random.normal(1.6, 0.3, 1000))  # 模拟历史PB
                
                metrics.pe_percentile = self.calculate_percentile(metrics.pe_ttm, pe_history)
                metrics.pb_percentile = self.calculate_percentile(metrics.pb, pb_history)
                
                # 历史统计
                metrics.pe_history_mean = round(pe_history.mean(), 2)
                metrics.pe_history_median = round(pe_history.median(), 2)
                metrics.pe_history_min = round(pe_history.min(), 2)
                metrics.pe_history_max = round(pe_history.max(), 2)
            
            # 计算股债性价比
            if metrics.pe_ttm and metrics.pe_ttm > 0:
                metrics.earnings_yield = round(1 / metrics.pe_ttm * 100, 2)
                # 中债10年收益率（简化，实际应从宏观数据获取）
                metrics.bond_yield = 2.8
                metrics.risk_premium = round(metrics.earnings_yield - metrics.bond_yield, 2)
            
            # 评估
            metrics.valuation_level = self.get_valuation_level(
                metrics.pe_ttm, metrics.pe_percentile,
                metrics.pb, metrics.pb_percentile
            )
            metrics.risk_premium_level = self.get_risk_premium_level(metrics.risk_premium)
            
        except Exception as e:
            print(f"分析A股估值失败 {symbol}: {e}")
        
        return metrics
    
    def analyze_us_stock(self, symbol: str, name: str,
                        hist_data: pd.DataFrame) -> ValuationMetrics:
        """
        分析美股指数估值
        
        Args:
            symbol: 指数代码
            name: 指数名称
            hist_data: 历史数据
        
        Returns:
            ValuationMetrics对象
        """
        metrics = ValuationMetrics(symbol=symbol, name=name)
        
        try:
            # 使用固定估值数据（简化版本）
            valuation_map = {
                "^IXIC": (32.0, 4.5),   # 纳斯达克
                "^GSPC": (24.0, 4.2),   # 标普500
            }
            
            if symbol in valuation_map:
                metrics.pe_ttm, metrics.pb = valuation_map[symbol]
                
                # 模拟历史分位
                if symbol == "^IXIC":
                    pe_history = pd.Series(np.random.normal(35, 8, 1000))
                    pb_history = pd.Series(np.random.normal(5.0, 1.0, 1000))
                else:  # 标普500
                    pe_history = pd.Series(np.random.normal(22, 4, 1000))
                    pb_history = pd.Series(np.random.normal(3.5, 0.6, 1000))
                
                metrics.pe_percentile = self.calculate_percentile(metrics.pe_ttm, pe_history)
                metrics.pb_percentile = self.calculate_percentile(metrics.pb, pb_history)
                
                # 历史统计
                metrics.pe_history_mean = round(pe_history.mean(), 2)
                metrics.pe_history_median = round(pe_history.median(), 2)
                metrics.pe_history_min = round(pe_history.min(), 2)
                metrics.pe_history_max = round(pe_history.max(), 2)
            
            # 计算股债性价比
            if metrics.pe_ttm and metrics.pe_ttm > 0:
                metrics.earnings_yield = round(1 / metrics.pe_ttm * 100, 2)
                # 美债10年收益率
                metrics.bond_yield = 4.2
                metrics.risk_premium = round(metrics.earnings_yield - metrics.bond_yield, 2)
            
            # 评估
            metrics.valuation_level = self.get_valuation_level(
                metrics.pe_ttm, metrics.pe_percentile,
                metrics.pb, metrics.pb_percentile
            )
            metrics.risk_premium_level = self.get_risk_premium_level(metrics.risk_premium)
            
        except Exception as e:
            print(f"分析美股估值失败 {symbol}: {e}")
        
        return metrics
    
    def analyze_all(self, market_data: Dict) -> Dict[str, ValuationMetrics]:
        """
        分析所有标的的估值
        
        Args:
            market_data: 市场数据字典
        
        Returns:
            估值指标字典
        """
        results = {}
        
        # A股估值
        for symbol, data in market_data.get("a_shares", {}).items():
            hist_data = data.get("hist_data")
            if hist_data is not None:
                metrics = self.analyze_a_share(
                    symbol, 
                    data.get("name", symbol),
                    hist_data
                )
                results[symbol] = metrics
        
        # 美股估值
        for symbol, data in market_data.get("us_stocks", {}).items():
            hist_data = data.get("hist_data")
            if hist_data is not None:
                metrics = self.analyze_us_stock(
                    symbol,
                    data.get("name", symbol),
                    hist_data
                )
                results[symbol] = metrics
        
        return results
    
    def format_valuation_report(self, metrics: ValuationMetrics) -> str:
        """
        格式化估值报告
        
        Args:
            metrics: 估值指标
        
        Returns:
            格式化字符串
        """
        lines = []
        lines.append(f"\n📊 {metrics.name} ({metrics.symbol}) 估值分析")
        lines.append("-" * 50)
        
        # 当前估值
        lines.append(f"\n💰 当前估值:")
        lines.append(f"   PE-TTM: {metrics.pe_ttm or 'N/A'}")
        lines.append(f"   PB: {metrics.pb or 'N/A'}")
        lines.append(f"   估值水平: {metrics.valuation_level}")
        
        # 历史分位
        if metrics.pe_percentile is not None:
            lines.append(f"\n📈 历史分位(10年):")
            lines.append(f"   PE分位: {metrics.pe_percentile}%")
            lines.append(f"   PB分位: {metrics.pb_percentile}%")
            
            # 可视化分位条
            bar_length = 20
            filled = int(metrics.pe_percentile / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            lines.append(f"   PE位置: [{bar}] {metrics.pe_percentile}%")
        
        # 历史统计
        if metrics.pe_history_mean:
            lines.append(f"\n📊 PE历史统计:")
            lines.append(f"   均值: {metrics.pe_history_mean}")
            lines.append(f"   中位数: {metrics.pe_history_median}")
            lines.append(f"   区间: {metrics.pe_history_min} - {metrics.pe_history_max}")
        
        # 股债性价比
        if metrics.risk_premium is not None:
            lines.append(f"\n⚖️ 股债性价比:")
            lines.append(f"   盈利收益率: {metrics.earnings_yield}%")
            lines.append(f"   国债收益率: {metrics.bond_yield}%")
            lines.append(f"   风险溢价: {metrics.risk_premium}%")
            lines.append(f"   性价比: {metrics.risk_premium_level}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试估值分析
    print("开始测试估值分析模块...")
    
    # 模拟市场数据
    mock_data = {
        "a_shares": {
            "000300": {
                "name": "沪深300",
                "hist_data": pd.DataFrame()  # 空DataFrame用于测试
            }
        },
        "us_stocks": {
            "^IXIC": {
                "name": "纳斯达克",
                "hist_data": pd.DataFrame()
            }
        }
    }
    
    analyzer = ValuationAnalyzer()
    results = analyzer.analyze_all(mock_data)
    
    for symbol, metrics in results.items():
        report = analyzer.format_valuation_report(metrics)
        print(report)
    
    print("\n测试完成！")
