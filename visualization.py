#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化图表模块
生成评分趋势图、估值图、回测对比图等
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

# 尝试导入matplotlib
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib 未安装，可视化功能将受限")
    print("   安装命令: pip install matplotlib")


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self, output_dir: str = "./results/charts"):
        """
        初始化图表生成器
        
        Args:
            output_dir: 图表输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置中文字体（如果可用）
        if MATPLOTLIB_AVAILABLE:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
    
    def plot_score_trend(self, dates: List[datetime], scores: List[float], 
                        grades: List[str], symbol: str, name: str) -> Optional[Path]:
        """
        绘制评分趋势图
        
        Args:
            dates: 日期列表
            scores: 评分列表
            grades: 评级列表
            symbol: 股票代码
            name: 股票名称
        
        Returns:
            图表文件路径或None
        """
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib 未安装，无法生成图表")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # 绘制评分曲线
            ax.plot(dates, scores, 'b-', linewidth=2, label='综合评分')
            ax.fill_between(dates, scores, alpha=0.3)
            
            # 添加评级区域背景
            grade_colors = {
                'A': '#00C853',  # 绿色 - 强烈买入
                'B': '#64DD17',  # 浅绿 - 买入
                'C': '#FFC107',  # 黄色 - 持有
                'D': '#FF9800',  # 橙色 - 观望
                'E': '#F44336'   # 红色 - 卖出
            }
            
            # 绘制评级背景
            for i in range(len(dates)-1):
                grade = grades[i] if i < len(grades) else 'C'
                color = grade_colors.get(grade[0] if grade else 'C', '#999')
                ax.axvspan(dates[i], dates[i+1], alpha=0.1, color=color)
            
            # 添加水平参考线
            ax.axhline(y=80, color='green', linestyle='--', alpha=0.5, label='A级线(80分)')
            ax.axhline(y=65, color='lightgreen', linestyle='--', alpha=0.5, label='B级线(65分)')
            ax.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='C级线(50分)')
            ax.axhline(y=35, color='red', linestyle='--', alpha=0.5, label='D级线(35分)')
            
            # 设置图表属性
            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('评分', fontsize=12)
            ax.set_title(f'{name} ({symbol}) - 评分趋势', fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 100)
            
            # 格式化日期
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # 保存图表
            filename = f"score_trend_{symbol.replace('^', '')}_{dates[-1].strftime('%Y%m%d')}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 评分趋势图已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 生成评分趋势图失败: {e}")
            return None
    
    def plot_valuation_chart(self, pe_current: float, pe_history: pd.Series,
                            pb_current: float, pb_history: pd.Series,
                            symbol: str, name: str) -> Optional[Path]:
        """
        绘制估值分位图
        
        Args:
            pe_current: 当前PE
            pe_history: PE历史数据
            pb_current: 当前PB
            pb_history: PB历史数据
            symbol: 股票代码
            name: 股票名称
        
        Returns:
            图表文件路径或None
        """
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib 未安装，无法生成图表")
            return None
        
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
            
            # PE分位图
            ax1.hist(pe_history, bins=50, alpha=0.7, color='blue', edgecolor='black')
            ax1.axvline(pe_current, color='red', linestyle='--', linewidth=2, 
                       label=f'当前PE: {pe_current:.2f}')
            
            # 计算分位
            pe_percentile = (pe_history < pe_current).mean() * 100
            ax1.text(0.95, 0.95, f'分位: {pe_percentile:.1f}%', 
                    transform=ax1.transAxes, ha='right', va='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            ax1.set_xlabel('PE-TTM', fontsize=11)
            ax1.set_ylabel('频率', fontsize=11)
            ax1.set_title(f'{name} - PE分布', fontsize=12, fontweight='bold')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # PB分位图
            ax2.hist(pb_history, bins=50, alpha=0.7, color='green', edgecolor='black')
            ax2.axvline(pb_current, color='red', linestyle='--', linewidth=2,
                       label=f'当前PB: {pb_current:.2f}')
            
            pb_percentile = (pb_history < pb_current).mean() * 100
            ax2.text(0.95, 0.95, f'分位: {pb_percentile:.1f}%',
                    transform=ax2.transAxes, ha='right', va='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            ax2.set_xlabel('PB', fontsize=11)
            ax2.set_ylabel('频率', fontsize=11)
            ax2.set_title(f'{name} - PB分布', fontsize=12, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            filename = f"valuation_{symbol.replace('^', '')}_{datetime.now().strftime('%Y%m%d')}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 估值分位图已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 生成估值分位图失败: {e}")
            return None
    
    def plot_backtest_comparison(self, nav_df: pd.DataFrame, symbol: str, name: str) -> Optional[Path]:
        """
        绘制回测对比图
        
        Args:
            nav_df: 净值数据（包含策略和买入持有）
            symbol: 股票代码
            name: 股票名称
        
        Returns:
            图表文件路径或None
        """
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib 未安装，无法生成图表")
            return None
        
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # 净值对比
            ax1.plot(nav_df.index, nav_df['nav'], 'b-', linewidth=2, label='策略净值')
            
            # 买入持有净值（假设）
            if 'price' in nav_df.columns:
                buy_hold_nav = nav_df['price'] / nav_df['price'].iloc[0]
                ax1.plot(nav_df.index, buy_hold_nav, 'r--', linewidth=2, label='买入持有')
            
            ax1.set_ylabel('净值', fontsize=12)
            ax1.set_title(f'{name} ({symbol}) - 回测对比', fontsize=14, fontweight='bold')
            ax1.legend(loc='best')
            ax1.grid(True, alpha=0.3)
            
            # 仓位变化
            if 'position' in nav_df.columns:
                ax2.fill_between(nav_df.index, nav_df['position'], alpha=0.5, color='green')
                ax2.plot(nav_df.index, nav_df['position'], 'g-', linewidth=1)
                ax2.set_ylabel('仓位', fontsize=12)
                ax2.set_xlabel('日期', fontsize=12)
                ax2.set_title('仓位变化', fontsize=12, fontweight='bold')
                ax2.set_ylim(0, 1)
                ax2.grid(True, alpha=0.3)
            
            # 格式化日期
            for ax in [ax1, ax2]:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            filename = f"backtest_{symbol.replace('^', '')}_{datetime.now().strftime('%Y%m%d')}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 回测对比图已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 生成回测对比图失败: {e}")
            return None
    
    def plot_multi_asset_comparison(self, results: List[Dict]) -> Optional[Path]:
        """
        绘制多资产对比图
        
        Args:
            results: 多个资产的评分结果列表
        
        Returns:
            图表文件路径或None
        """
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib 未安装，无法生成图表")
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # 准备数据
            names = [r['name'] for r in results]
            scores = [r['total_score'] for r in results]
            colors = []
            
            for score in scores:
                if score >= 80:
                    colors.append('#00C853')
                elif score >= 65:
                    colors.append('#64DD17')
                elif score >= 50:
                    colors.append('#FFC107')
                elif score >= 35:
                    colors.append('#FF9800')
                else:
                    colors.append('#F44336')
            
            # 绘制条形图
            bars = ax.barh(names, scores, color=colors, alpha=0.8, edgecolor='black')
            
            # 添加数值标签
            for i, (bar, score) in enumerate(zip(bars, scores)):
                width = bar.get_width()
                ax.text(width + 1, bar.get_y() + bar.get_height()/2,
                       f'{score:.0f}分',
                       ha='left', va='center', fontweight='bold')
            
            # 添加参考线
            ax.axvline(x=80, color='green', linestyle='--', alpha=0.5, label='A级(80分)')
            ax.axvline(x=65, color='lightgreen', linestyle='--', alpha=0.5, label='B级(65分)')
            ax.axvline(x=50, color='orange', linestyle='--', alpha=0.5, label='C级(50分)')
            
            ax.set_xlabel('综合评分', fontsize=12)
            ax.set_title('多资产评分对比', fontsize=14, fontweight='bold')
            ax.legend(loc='lower right')
            ax.grid(True, alpha=0.3, axis='x')
            ax.set_xlim(0, 105)
            
            plt.tight_layout()
            
            filename = f"multi_asset_comparison_{datetime.now().strftime('%Y%m%d')}.png"
            filepath = self.output_dir / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 多资产对比图已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ 生成多资产对比图失败: {e}")
            return None
    
    def generate_html_gallery(self, chart_files: List[Path], title: str = "图表 gallery") -> Path:
        """
        生成HTML图表画廊
        
        Args:
            chart_files: 图表文件列表
            title: 页面标题
        
        Returns:
            HTML文件路径
        """
        html_parts = []
        html_parts.append("<!DOCTYPE html>")
        html_parts.append("<html>")
        html_parts.append("<head>")
        html_parts.append(f"<title>{title}</title>")
        html_parts.append("<style>")
        html_parts.append("""
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            .chart-container { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .chart-title { font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #555; }
            img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; }
            .timestamp { color: #999; font-size: 12px; margin-top: 20px; }
        """)
        html_parts.append("</style>")
        html_parts.append("</head>")
        html_parts.append("<body>")
        html_parts.append(f"<h1>📊 {title}</h1>")
        
        for chart_file in chart_files:
            if chart_file.exists():
                relative_path = chart_file.name
                html_parts.append(f'<div class="chart-container">')
                html_parts.append(f'<div class="chart-title">{chart_file.stem}</div>')
                html_parts.append(f'<img src="{relative_path}" alt="{chart_file.stem}">')
                html_parts.append('</div>')
        
        html_parts.append(f'<div class="timestamp">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>')
        html_parts.append("</body>")
        html_parts.append("</html>")
        
        html_content = "\n".join(html_parts)
        
        html_file = self.output_dir / "gallery.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ 图表画廊已生成: {html_file}")
        return html_file


def test_chart_generator():
    """测试图表生成器"""
    print("=" * 70)
    print("🎨 测试可视化图表模块")
    print("=" * 70)
    
    if not MATPLOTLIB_AVAILABLE:
        print("\n⚠️ matplotlib 未安装，跳过图表测试")
        print("安装命令: pip install matplotlib")
        return
    
    generator = ChartGenerator()
    
    # 测试1: 评分趋势图
    print("\n📈 生成评分趋势图...")
    dates = pd.date_range(end=datetime.now(), periods=180, freq='D')
    scores = [50 + 20 * np.sin(i/30) + np.random.normal(0, 5) for i in range(180)]
    grades = ['A' if s >= 80 else 'B' if s >= 65 else 'C' if s >= 50 else 'D' if s >= 35 else 'E' for s in scores]
    
    chart1 = generator.plot_score_trend(list(dates), scores, grades, "000300", "沪深300")
    
    # 测试2: 估值分位图
    print("\n💰 生成估值分位图...")
    pe_history = pd.Series(np.random.normal(15, 3, 1000))
    pb_history = pd.Series(np.random.normal(1.6, 0.3, 1000))
    
    chart2 = generator.plot_valuation_chart(12.5, pe_history, 1.4, pb_history, "000300", "沪深300")
    
    # 测试3: 多资产对比图
    print("\n📊 生成多资产对比图...")
    mock_results = [
        {'name': '沪深300', 'total_score': 75},
        {'name': '中证500', 'total_score': 62},
        {'name': '纳斯达克', 'total_score': 58},
        {'name': '标普500', 'total_score': 70}
    ]
    
    chart3 = generator.plot_multi_asset_comparison(mock_results)
    
    # 生成HTML画廊
    print("\n🌐 生成图表画廊...")
    charts = [c for c in [chart1, chart2, chart3] if c is not None]
    if charts:
        gallery = generator.generate_html_gallery(charts, "多因子策略分析图表")
        print(f"\n✅ 所有图表已保存到: {generator.output_dir}")
    
    print("\n" + "=" * 70)
    print("✅ 图表测试完成!")
    print("=" * 70)


if __name__ == "__main__":
    test_chart_generator()
