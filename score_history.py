#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评分历史追踪模块
追踪和记录评分变化，生成趋势分析和提醒
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class ScoreRecord:
    """评分记录"""
    date: str
    symbol: str
    name: str
    total_score: float
    technical_score: float
    valuation_score: float
    macro_score: float
    sentiment_score: float
    grade: str
    close: float
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]


class ScoreHistoryTracker:
    """评分历史追踪器"""
    
    def __init__(self, history_dir: str = "./results/history"):
        """
        初始化历史追踪器
        
        Args:
            history_dir: 历史数据存储目录
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def save_score(self, record: ScoreRecord):
        """
        保存评分记录
        
        Args:
            record: 评分记录
        """
        # 按股票代码分文件存储
        file_path = self.history_dir / f"{record.symbol.replace('^', '')}_history.json"
        
        # 读取现有历史
        history = []
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                history = []
        
        # 检查是否已有同一天记录
        existing_dates = [h['date'] for h in history]
        if record.date in existing_dates:
            # 更新已有记录
            for i, h in enumerate(history):
                if h['date'] == record.date:
                    history[i] = asdict(record)
                    break
        else:
            # 添加新记录
            history.append(asdict(record))
        
        # 按日期排序
        history.sort(key=lambda x: x['date'])
        
        # 保存
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def get_history(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """
        获取历史评分数据
        
        Args:
            symbol: 股票代码
            days: 最近多少天
        
        Returns:
            DataFrame包含历史评分
        """
        file_path = self.history_dir / f"{symbol.replace('^', '')}_history.json"
        
        if not file_path.exists():
            return pd.DataFrame()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            df = pd.DataFrame(history)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # 筛选最近days天
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df['date'] >= cutoff_date]
            
            return df
            
        except Exception as e:
            print(f"读取历史数据失败 {symbol}: {e}")
            return pd.DataFrame()
    
    def analyze_trend(self, symbol: str) -> Dict:
        """
        分析评分趋势
        
        Args:
            symbol: 股票代码
        
        Returns:
            趋势分析结果
        """
        df = self.get_history(symbol, days=90)
        
        if len(df) < 7:
            return {
                'symbol': symbol,
                'trend': '数据不足',
                'change_7d': None,
                'change_30d': None,
                'momentum': '未知',
                'volatility': None,
                'suggestion': '需要更多历史数据'
            }
        
        # 计算变化
        latest_score = df['total_score'].iloc[-1]
        score_7d = df['total_score'].iloc[-8] if len(df) >= 8 else df['total_score'].iloc[0]
        score_30d = df['total_score'].iloc[-31] if len(df) >= 31 else df['total_score'].iloc[0]
        
        change_7d = latest_score - score_7d
        change_30d = latest_score - score_30d
        
        # 计算动量（近期变化率）
        recent_scores = df['total_score'].tail(7)
        momentum = (recent_scores.iloc[-1] - recent_scores.iloc[0]) / 7
        
        # 计算波动率
        volatility = df['total_score'].tail(30).std() if len(df) >= 30 else df['total_score'].std()
        
        # 判断趋势
        if change_7d > 5:
            trend = '强劲上升'
        elif change_7d > 2:
            trend = '温和上升'
        elif change_7d > -2:
            trend = '横盘震荡'
        elif change_7d > -5:
            trend = '温和下降'
        else:
            trend = '快速下降'
        
        # 动量判断
        if momentum > 0.5:
            momentum_desc = '加速上升'
        elif momentum > 0.1:
            momentum_desc = '上升动能'
        elif momentum > -0.1:
            momentum_desc = '动能平稳'
        elif momentum > -0.5:
            momentum_desc = '下降动能'
        else:
            momentum_desc = '加速下降'
        
        # 建议
        if change_7d > 5 and latest_score >= 65:
            suggestion = '评分快速上升，关注买入机会'
        elif change_7d < -5 and latest_score < 50:
            suggestion = '评分快速下降，考虑减仓避险'
        elif abs(change_7d) < 2:
            suggestion = '评分稳定，维持当前仓位'
        else:
            suggestion = '评分变化中，持续观察'
        
        return {
            'symbol': symbol,
            'trend': trend,
            'change_7d': round(change_7d, 1),
            'change_30d': round(change_30d, 1),
            'momentum': momentum_desc,
            'volatility': round(volatility, 1),
            'latest_score': round(latest_score, 1),
            'suggestion': suggestion
        }
    
    def detect_signals(self, symbol: str) -> List[Dict]:
        """
        检测历史信号
        
        Args:
            symbol: 股票代码
        
        Returns:
            信号列表
        """
        df = self.get_history(symbol, days=180)
        signals = []
        
        if len(df) < 30:
            return signals
        
        # 1. 跨级变化信号
        for i in range(1, len(df)):
            prev_grade = df['grade'].iloc[i-1]
            curr_grade = df['grade'].iloc[i]
            
            grade_order = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
            prev_level = grade_order.get(prev_grade[0] if prev_grade else 'C', 3)
            curr_level = grade_order.get(curr_grade[0] if curr_grade else 'C', 3)
            
            if abs(curr_level - prev_level) >= 2:
                signals.append({
                    'date': df['date'].iloc[i].strftime('%Y-%m-%d'),
                    'type': '跨级变化',
                    'direction': '升级' if curr_level > prev_level else '降级',
                    'from_grade': prev_grade,
                    'to_grade': curr_grade,
                    'score': df['total_score'].iloc[i],
                    'importance': '高'
                })
        
        # 2. 极值信号
        if len(df) >= 30:
            recent_30 = df.tail(30)
            for i, row in recent_30.iterrows():
                if row['total_score'] >= 85:
                    signals.append({
                        'date': row['date'].strftime('%Y-%m-%d'),
                        'type': '极高评分',
                        'score': row['total_score'],
                        'importance': '中'
                    })
                elif row['total_score'] <= 30:
                    signals.append({
                        'date': row['date'].strftime('%Y-%m-%d'),
                        'type': '极低评分',
                        'score': row['total_score'],
                        'importance': '中'
                    })
        
        # 3. 趋势反转信号
        if len(df) >= 14:
            for i in range(14, len(df)):
                prev_7 = df.iloc[i-14:i-7]['total_score'].mean()
                curr_7 = df.iloc[i-7:i]['total_score'].mean()
                
                if prev_7 < curr_7 - 5 and df.iloc[i-14:i-7]['total_score'].is_monotonic_decreasing:
                    signals.append({
                        'date': df.iloc[i]['date'].strftime('%Y-%m-%d'),
                        'type': '趋势反转',
                        'direction': '由跌转升',
                        'score': df.iloc[i]['total_score'],
                        'importance': '高'
                    })
                elif prev_7 > curr_7 + 5 and df.iloc[i-14:i-7]['total_score'].is_monotonic_increasing:
                    signals.append({
                        'date': df.iloc[i]['date'].strftime('%Y-%m-%d'),
                        'type': '趋势反转',
                        'direction': '由升转跌',
                        'score': df.iloc[i]['total_score'],
                        'importance': '高'
                    })
        
        # 去重并排序
        seen = set()
        unique_signals = []
        for signal in sorted(signals, key=lambda x: x['date'], reverse=True):
            key = (signal['date'], signal.get('type'))
            if key not in seen:
                seen.add(key)
                unique_signals.append(signal)
        
        return unique_signals[:20]  # 最多返回20个信号
    
    def generate_history_report(self, symbol: str) -> str:
        """
        生成历史报告
        
        Args:
            symbol: 股票代码
        
        Returns:
            报告文本
        """
        df = self.get_history(symbol, days=90)
        
        if df.empty:
            return f"暂无 {symbol} 的历史数据"
        
        lines = []
        lines.append("=" * 70)
        lines.append(f"📊 评分历史报告: {symbol}")
        lines.append("=" * 70)
        
        # 趋势分析
        trend = self.analyze_trend(symbol)
        lines.append(f"\n📈 趋势分析:")
        lines.append(f"   当前趋势: {trend['trend']}")
        lines.append(f"   7日变化: {trend['change_7d']:+.1f}分")
        lines.append(f"   30日变化: {trend['change_30d']:+.1f}分")
        lines.append(f"   动量: {trend['momentum']}")
        lines.append(f"   波动率: {trend['volatility']:.1f}")
        lines.append(f"   💡 {trend['suggestion']}")
        
        # 历史信号
        signals = self.detect_signals(symbol)
        if signals:
            lines.append(f"\n🔔 历史信号 (最近):")
            for signal in signals[:10]:
                emoji = "🔴" if signal.get('importance') == '高' else "🟡"
                lines.append(f"   {emoji} {signal['date']} {signal['type']}")
                if 'direction' in signal:
                    lines.append(f"      方向: {signal['direction']}")
                if 'score' in signal:
                    lines.append(f"      评分: {signal['score']}")
        
        # 最近10天数据
        lines.append(f"\n📅 最近评分:")
        recent = df.tail(10)[['date', 'total_score', 'grade', 'close']]
        for _, row in recent.iterrows():
            date_str = row['date'].strftime('%m-%d')
            lines.append(f"   {date_str}: {row['total_score']:5.1f}分 ({row['grade']})  价格:{row['close']}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def compare_symbols(self, symbols: List[str]) -> pd.DataFrame:
        """
        对比多个标的的历史表现
        
        Args:
            symbols: 股票代码列表
        
        Returns:
            对比DataFrame
        """
        comparison = []
        
        for symbol in symbols:
            trend = self.analyze_trend(symbol)
            comparison.append(trend)
        
        return pd.DataFrame(comparison)


def test_history_tracker():
    """测试历史追踪器"""
    print("=" * 70)
    print("📚 测试评分历史追踪模块")
    print("=" * 70)
    
    tracker = ScoreHistoryTracker()
    
    # 生成模拟历史数据
    print("\n📝 生成模拟历史数据...")
    import numpy as np
    
    symbols = ["000300", "^IXIC"]
    names = ["沪深300", "纳斯达克"]
    
    for symbol, name in zip(symbols, names):
        print(f"\n  生成 {name} ({symbol}) 的历史...")
        
        for i in range(60, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # 模拟评分（带趋势）
            base_score = 50 + 20 * np.sin((60-i) / 15)
            score = base_score + np.random.normal(0, 5)
            score = max(0, min(100, score))
            
            record = ScoreRecord(
                date=date,
                symbol=symbol,
                name=name,
                total_score=round(score, 1),
                technical_score=round(score * 0.3, 1),
                valuation_score=round(score * 0.35, 1),
                macro_score=round(score * 0.25, 1),
                sentiment_score=round(score * 0.1, 1),
                grade='A' if score >= 80 else 'B' if score >= 65 else 'C' if score >= 50 else 'D',
                close=round(3000 + score * 10, 2),
                pe_ratio=round(15 + (50-score) / 10, 2),
                pb_ratio=round(1.5 + (50-score) / 100, 2)
            )
            
            tracker.save_score(record)
    
    print("\n✅ 历史数据已保存")
    
    # 测试趋势分析
    print("\n📊 测试趋势分析...")
    for symbol, name in zip(symbols, names):
        print(f"\n{name} ({symbol}):")
        trend = tracker.analyze_trend(symbol)
        print(f"  趋势: {trend['trend']}")
        print(f"  7日变化: {trend['change_7d']:+.1f}分")
        print(f"  动量: {trend['momentum']}")
    
    # 测试信号检测
    print("\n🔔 测试信号检测...")
    for symbol, name in zip(symbols, names):
        signals = tracker.detect_signals(symbol)
        if signals:
            print(f"\n{name} ({symbol}) 发现 {len(signals)} 个信号:")
            for signal in signals[:5]:
                print(f"  {signal['date']}: {signal['type']}")
    
    # 生成报告
    print("\n📄 生成历史报告...")
    report = tracker.generate_history_report("000300")
    print(report)
    
    # 对比分析
    print("\n📊 对比分析...")
    comparison = tracker.compare_symbols(symbols)
    print(comparison.to_string(index=False))
    
    print("\n" + "=" * 70)
    print("✅ 历史追踪测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    test_history_tracker()
