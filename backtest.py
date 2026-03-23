#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测验证模块
验证多因子评分系统的历史有效性
对比策略收益 vs 买入持有收益
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json


@dataclass
class Trade:
    """交易记录"""
    date: str
    action: str  # 'buy', 'sell', 'rebalance'
    symbol: str
    price: float
    score: float
    grade: str
    position: float  # 仓位比例
    reason: str


@dataclass
class BacktestResult:
    """回测结果"""
    symbol: str
    name: str
    start_date: str
    end_date: str
    
    # 策略表现
    strategy_return: float
    strategy_annual_return: float
    strategy_sharpe: float
    strategy_max_drawdown: float
    strategy_volatility: float
    
    # 买入持有表现
    buy_hold_return: float
    buy_hold_annual_return: float
    buy_hold_sharpe: float
    buy_hold_max_drawdown: float
    buy_hold_volatility: float
    
    # 超额收益
    excess_return: float
    excess_annual_return: float
    win_rate: float
    
    # 交易统计
    total_trades: int
    avg_position_days: float
    trades: List[Trade] = field(default_factory=list)
    
    # 每日净值
    daily_nav: pd.DataFrame = field(default_factory=pd.DataFrame)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        
    def generate_mock_history(self, symbol: str, days: int = 365) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        生成模拟历史数据（用于测试）
        
        Args:
            symbol: 股票代码
            days: 历史天数
        
        Returns:
            (价格数据, 评分历史)
        """
        # 生成日期范围
        end_date = datetime.now()
        dates = pd.date_range(end=end_date, periods=days, freq='D')
        
        # 生成价格数据（带趋势的随机游走）
        np.random.seed(42)
        returns = np.random.normal(0.0003, 0.015, days)  # 日收益
        
        # 添加趋势周期
        trend = np.sin(np.linspace(0, 4*np.pi, days)) * 0.005
        returns += trend
        
        # 计算价格
        price = 100 * np.exp(np.cumsum(returns))
        
        df_price = pd.DataFrame({
            'date': dates,
            'close': price,
            'volume': np.random.randint(1000000, 5000000, days)
        })
        df_price.set_index('date', inplace=True)
        
        # 生成评分历史（与价格相关但滞后）
        scores = []
        for i in range(days):
            # 评分与未来收益相关（模拟预测能力）
            future_return = returns[i:min(i+20, days)].sum() if i < days-20 else 0
            
            # 基础分50
            base_score = 50
            
            # 根据未来收益调整（模拟预测）
            if future_return > 0.1:
                score = np.random.randint(75, 95)
            elif future_return > 0.05:
                score = np.random.randint(65, 80)
            elif future_return > -0.05:
                score = np.random.randint(45, 65)
            elif future_return > -0.1:
                score = np.random.randint(30, 50)
            else:
                score = np.random.randint(10, 35)
            
            scores.append(score)
        
        df_score = pd.DataFrame({
            'date': dates,
            'score': scores
        })
        df_score.set_index('date', inplace=True)
        
        return df_price, df_score
    
    def get_grade_from_score(self, score: float) -> str:
        """根据评分确定评级"""
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "E"
    
    def run_backtest(self, symbol: str, name: str, df_price: pd.DataFrame, 
                     df_score: pd.DataFrame, rebalance_days: int = 90) -> BacktestResult:
        """
        运行回测
        
        Args:
            symbol: 股票代码
            name: 股票名称
            df_price: 价格数据
            df_score: 评分数据
            rebalance_days: 调仓周期（天）
        
        Returns:
            BacktestResult对象
        """
        # 合并数据
        df = df_price.join(df_score, how='inner')
        df = df.dropna()
        
        if len(df) < 60:
            raise ValueError("数据不足，需要至少60天数据")
        
        # 初始化
        capital = self.initial_capital
        position = 0.0  # 当前仓位比例
        position_value = 0.0
        cash = capital
        
        trades = []
        nav_history = []
        
        last_rebalance = None
        
        for i, (date, row) in enumerate(df.iterrows()):
            price = row['close']
            score = row['score']
            grade = self.get_grade_from_score(score)
            
            # 计算当前总市值
            total_value = cash + position_value
            
            # 调仓逻辑
            should_rebalance = False
            reason = ""
            
            # 1. 定期调仓
            if last_rebalance is None or (date - last_rebalance).days >= rebalance_days:
                should_rebalance = True
                reason = f"定期调仓 ({rebalance_days}天)"
            
            # 2. 跨级调仓
            if i > 0:
                prev_score = df.iloc[i-1]['score']
                prev_grade = self.get_grade_from_score(prev_score)
                
                grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
                if abs(grade_order.get(grade, 3) - grade_order.get(prev_grade, 3)) >= 2:
                    should_rebalance = True
                    reason = f"评级跨级变化 {prev_grade}→{grade}"
            
            if should_rebalance:
                last_rebalance = date
                
                # 根据评级确定目标仓位
                target_position = 0.0
                if grade == "A":
                    target_position = 0.95
                elif grade == "B":
                    target_position = 0.80
                elif grade == "C":
                    target_position = 0.60
                elif grade == "D":
                    target_position = 0.40
                else:  # E
                    target_position = 0.10
                
                # 执行调仓
                action = "rebalance"
                if target_position > position:
                    action = "buy"
                elif target_position < position:
                    action = "sell"
                
                # 计算目标持仓市值
                target_value = total_value * target_position
                
                # 调仓
                position_value = target_value
                cash = total_value - position_value
                position = target_position
                
                # 记录交易
                trades.append(Trade(
                    date=date.strftime('%Y-%m-%d'),
                    action=action,
                    symbol=symbol,
                    price=price,
                    score=score,
                    grade=grade,
                    position=position,
                    reason=reason
                ))
            
            # 更新持仓市值
            position_value = total_value * position
            cash = total_value - position_value
            
            # 记录净值
            nav_history.append({
                'date': date,
                'nav': total_value / self.initial_capital,
                'price': price,
                'score': score,
                'grade': grade,
                'position': position
            })
        
        # 转换为DataFrame
        nav_df = pd.DataFrame(nav_history)
        nav_df.set_index('date', inplace=True)
        
        # 计算策略收益
        strategy_return = (nav_df['nav'].iloc[-1] - 1) * 100
        strategy_annual_return = ((1 + strategy_return/100) ** (365/len(df)) - 1) * 100
        
        # 计算买入持有收益
        buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        buy_hold_annual_return = ((1 + buy_hold_return/100) ** (365/len(df)) - 1) * 100
        
        # 计算最大回撤
        strategy_mdd = self.calculate_max_drawdown(nav_df['nav'])
        buy_hold_mdd = self.calculate_max_drawdown(df['close'] / df['close'].iloc[0])
        
        # 计算波动率（年化）
        strategy_vol = nav_df['nav'].pct_change().std() * np.sqrt(252) * 100
        buy_hold_vol = df['close'].pct_change().std() * np.sqrt(252) * 100
        
        # 计算夏普比率（假设无风险利率2%）
        risk_free_rate = 2.0
        strategy_sharpe = (strategy_annual_return - risk_free_rate) / strategy_vol if strategy_vol > 0 else 0
        buy_hold_sharpe = (buy_hold_annual_return - risk_free_rate) / buy_hold_vol if buy_hold_vol > 0 else 0
        
        # 超额收益
        excess_return = strategy_return - buy_hold_return
        excess_annual_return = strategy_annual_return - buy_hold_annual_return
        
        # 胜率（盈利交易日占比）
        daily_returns = nav_df['nav'].pct_change().dropna()
        win_rate = (daily_returns > 0).mean() * 100
        
        # 平均持仓天数
        avg_position_days = len(df) / max(1, len(trades)) if trades else len(df)
        
        return BacktestResult(
            symbol=symbol,
            name=name,
            start_date=df.index[0].strftime('%Y-%m-%d'),
            end_date=df.index[-1].strftime('%Y-%m-%d'),
            strategy_return=round(strategy_return, 2),
            strategy_annual_return=round(strategy_annual_return, 2),
            strategy_sharpe=round(strategy_sharpe, 2),
            strategy_max_drawdown=round(strategy_mdd * 100, 2),
            strategy_volatility=round(strategy_vol, 2),
            buy_hold_return=round(buy_hold_return, 2),
            buy_hold_annual_return=round(buy_hold_annual_return, 2),
            buy_hold_sharpe=round(buy_hold_sharpe, 2),
            buy_hold_max_drawdown=round(buy_hold_mdd * 100, 2),
            buy_hold_volatility=round(buy_hold_vol, 2),
            excess_return=round(excess_return, 2),
            excess_annual_return=round(excess_annual_return, 2),
            win_rate=round(win_rate, 2),
            total_trades=len(trades),
            avg_position_days=round(avg_position_days, 1),
            trades=trades,
            daily_nav=nav_df
        )
    
    def calculate_max_drawdown(self, series: pd.Series) -> float:
        """计算最大回撤"""
        cummax = series.cummax()
        drawdown = (series - cummax) / cummax
        return drawdown.min()
    
    def format_backtest_report(self, result: BacktestResult) -> str:
        """格式化回测报告"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"📊 回测报告: {result.name} ({result.symbol})")
        lines.append("=" * 70)
        lines.append(f"\n回测区间: {result.start_date} ~ {result.end_date}")
        lines.append(f"初始资金: {self.initial_capital:,.0f} 元")
        lines.append(f"调仓周期: 90天")
        
        lines.append("\n" + "-" * 70)
        lines.append("策略表现 vs 买入持有")
        lines.append("-" * 70)
        
        # 创建对比表
        data = {
            '指标': ['总收益', '年化收益', '最大回撤', '波动率', '夏普比率'],
            '策略': [
                f"{result.strategy_return:+.2f}%",
                f"{result.strategy_annual_return:+.2f}%",
                f"{result.strategy_max_drawdown:.2f}%",
                f"{result.strategy_volatility:.2f}%",
                f"{result.strategy_sharpe:.2f}"
            ],
            '买入持有': [
                f"{result.buy_hold_return:+.2f}%",
                f"{result.buy_hold_annual_return:+.2f}%",
                f"{result.buy_hold_max_drawdown:.2f}%",
                f"{result.buy_hold_volatility:.2f}%",
                f"{result.buy_hold_sharpe:.2f}"
            ]
        }
        
        df_compare = pd.DataFrame(data)
        lines.append("\n" + df_compare.to_string(index=False))
        
        lines.append("\n" + "-" * 70)
        lines.append("超额收益")
        lines.append("-" * 70)
        lines.append(f"总超额收益: {result.excess_return:+.2f}%")
        lines.append(f"年化超额收益: {result.excess_annual_return:+.2f}%")
        lines.append(f"日胜率: {result.win_rate:.1f}%")
        
        lines.append("\n" + "-" * 70)
        lines.append("交易统计")
        lines.append("-" * 70)
        lines.append(f"总调仓次数: {result.total_trades}")
        lines.append(f"平均持仓天数: {result.avg_position_days:.1f} 天")
        
        # 最近5次交易
        if result.trades:
            lines.append("\n最近5次调仓:")
            for trade in result.trades[-5:]:
                emoji = "🟢" if trade.action == "buy" else "🔴" if trade.action == "sell" else "🟡"
                lines.append(f"  {emoji} {trade.date} {trade.action:10} 评分:{trade.score:.0f}({trade.grade}) 仓位:{trade.position*100:.0f}%")
                lines.append(f"      原因: {trade.reason}")
        
        # 评估
        lines.append("\n" + "=" * 70)
        lines.append("📋 策略评估")
        lines.append("=" * 70)
        
        if result.excess_return > 0:
            lines.append(f"✅ 策略跑赢基准 {result.excess_return:+.2f}%")
            if result.excess_return > 10:
                lines.append("🌟 超额收益显著，策略有效！")
            else:
                lines.append("👍 有一定超额收益，策略可行")
        else:
            lines.append(f"⚠️ 策略跑输基准 {result.excess_return:.2f}%")
            lines.append("💡 建议: 优化评分权重或调整调仓阈值")
        
        if result.strategy_sharpe > result.buy_hold_sharpe:
            lines.append("✅ 策略风险调整收益更优（夏普比率）")
        
        if result.strategy_max_drawdown < result.buy_hold_max_drawdown:
            lines.append("✅ 策略回撤控制更好")
        
        return "\n".join(lines)
    
    def save_backtest_result(self, result: BacktestResult, output_dir: str = "./results"):
        """保存回测结果"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 保存JSON
        result_dict = {
            'symbol': result.symbol,
            'name': result.name,
            'start_date': result.start_date,
            'end_date': result.end_date,
            'strategy_return': result.strategy_return,
            'strategy_annual_return': result.strategy_annual_return,
            'strategy_sharpe': result.strategy_sharpe,
            'strategy_max_drawdown': result.strategy_max_drawdown,
            'strategy_volatility': result.strategy_volatility,
            'buy_hold_return': result.buy_hold_return,
            'buy_hold_annual_return': result.buy_hold_annual_return,
            'buy_hold_sharpe': result.buy_hold_sharpe,
            'buy_hold_max_drawdown': result.buy_hold_max_drawdown,
            'buy_hold_volatility': result.buy_hold_volatility,
            'excess_return': result.excess_return,
            'excess_annual_return': result.excess_annual_return,
            'win_rate': result.win_rate,
            'total_trades': result.total_trades,
            'avg_position_days': result.avg_position_days,
            'trades': [t.__dict__ for t in result.trades]
        }
        
        json_file = output_path / f"backtest_{result.symbol.replace('^', '')}_{result.end_date.replace('-', '')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        
        # 保存净值CSV
        csv_file = output_path / f"backtest_nav_{result.symbol.replace('^', '')}_{result.end_date.replace('-', '')}.csv"
        result.daily_nav.to_csv(csv_file)
        
        print(f"✅ 回测结果已保存:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file}")


def run_mock_backtest():
    """运行模拟回测（用于演示）"""
    print("=" * 70)
    print("🧪 多因子策略回测验证")
    print("=" * 70)
    
    engine = BacktestEngine(initial_capital=100000)
    
    # 测试标的
    test_symbols = [
        ("000300", "沪深300"),
        ("^IXIC", "纳斯达克")
    ]
    
    for symbol, name in test_symbols:
        print(f"\n\n{'='*70}")
        print(f"📊 回测 {name} ({symbol})")
        print(f"{'='*70}")
        
        # 生成模拟数据
        print("\n📝 生成模拟历史数据...")
        df_price, df_score = engine.generate_mock_history(symbol, days=365*2)
        
        # 运行回测
        print("🔄 运行回测...")
        result = engine.run_backtest(symbol, name, df_price, df_score, rebalance_days=90)
        
        # 打印报告
        report = engine.format_backtest_report(result)
        print("\n" + report)
        
        # 保存结果
        engine.save_backtest_result(result)
    
    print("\n" + "=" * 70)
    print("✅ 回测完成!")
    print("=" * 70)


if __name__ == "__main__":
    run_mock_backtest()
