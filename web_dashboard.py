#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web界面仪表板模块
提供实时数据展示、评分查询、历史趋势查看等功能
使用 Flask 轻量级Web框架
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️ Flask 未安装，Web功能将不可用")
    print("安装命令: pip install flask flask-cors")

import pandas as pd

# 导入自定义模块
from market_data import get_all_market_data
from scoring_system_v2 import MultiFactorScorerV2
from score_history import ScoreHistoryTracker
from config_manager import ConfigManager

app = Flask(__name__) if FLASK_AVAILABLE else None
if FLASK_AVAILABLE:
    CORS(app)

# 全局数据缓存
latest_data = {}
latest_results = []


class DashboardData:
    """仪表板数据管理"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.history_tracker = ScoreHistoryTracker()
        self.last_update = None
        
    def refresh_data(self):
        """刷新数据"""
        global latest_data, latest_results
        
        try:
            # 获取市场数据
            market_data = get_all_market_data()
            
            # 评分
            scorer = MultiFactorScorerV2(market_data, market_data.get("macro", {}))
            results = scorer.score_all()
            
            # 保存到历史
            for result in results:
                from score_history import ScoreRecord
                record = ScoreRecord(
                    date=datetime.now().strftime('%Y-%m-%d'),
                    symbol=result.symbol,
                    name=result.name,
                    total_score=result.total_score,
                    technical_score=result.technical_score,
                    valuation_score=result.valuation_score,
                    macro_score=result.macro_score,
                    sentiment_score=result.sentiment_score,
                    grade=result.grade,
                    close=result.close,
                    pe_ratio=result.pe_ratio,
                    pb_ratio=result.pb_ratio
                )
                self.history_tracker.save_score(record)
            
            latest_data = market_data
            latest_results = results
            self.last_update = datetime.now()
            
            return True
            
        except Exception as e:
            print(f"刷新数据失败: {e}")
            return False
    
    def get_summary(self) -> Dict:
        """获取摘要数据"""
        if not latest_results:
            return {"error": "暂无数据"}
        
        # 统计
        avg_score = sum([r.total_score for r in latest_results]) / len(latest_results)
        a_count = sum([1 for r in latest_results if r.total_score >= 80])
        b_count = sum([1 for r in latest_results if 65 <= r.total_score < 80])
        d_count = sum([1 for r in latest_results if 35 <= r.total_score < 50])
        e_count = sum([1 for r in latest_results if r.total_score < 35])
        
        # 最佳最差
        sorted_results = sorted(latest_results, key=lambda x: x.total_score, reverse=True)
        best = sorted_results[0]
        worst = sorted_results[-1]
        
        return {
            "timestamp": self.last_update.strftime('%Y-%m-%d %H:%M:%S') if self.last_update else None,
            "total_assets": len(latest_results),
            "avg_score": round(avg_score, 1),
            "grade_distribution": {
                "A": a_count,
                "B": b_count,
                "C": len(latest_results) - a_count - b_count - d_count - e_count,
                "D": d_count,
                "E": e_count
            },
            "best": {
                "symbol": best.symbol,
                "name": best.name,
                "score": best.total_score,
                "grade": best.grade
            },
            "worst": {
                "symbol": worst.symbol,
                "name": worst.name,
                "score": worst.total_score,
                "grade": worst.grade
            },
            "macro": latest_data.get("macro", {})
        }
    
    def get_all_scores(self) -> List[Dict]:
        """获取所有评分"""
        if not latest_results:
            return []
        
        return [
            {
                "symbol": r.symbol,
                "name": r.name,
                "market": r.market,
                "total_score": r.total_score,
                "technical_score": r.technical_score,
                "valuation_score": r.valuation_score,
                "macro_score": r.macro_score,
                "sentiment_score": r.sentiment_score,
                "grade": r.grade,
                "grade_emoji": r.grade_emoji,
                "close": r.close,
                "pe_ratio": r.pe_ratio,
                "pb_ratio": r.pb_ratio,
                "action": r.action,
                "position_suggest": r.position_suggest
            }
            for r in latest_results
        ]
    
    def get_asset_detail(self, symbol: str) -> Dict:
        """获取单个资产详情"""
        # 查找当前评分
        current = None
        for r in latest_results:
            if r.symbol == symbol:
                current = r
                break
        
        if not current:
            return {"error": "资产不存在"}
        
        # 获取历史
        history_df = self.history_tracker.get_history(symbol, days=90)
        history_list = []
        
        if not history_df.empty:
            for _, row in history_df.iterrows():
                history_list.append({
                    "date": row['date'].strftime('%Y-%m-%d'),
                    "score": row['total_score'],
                    "grade": row['grade'],
                    "close": row['close']
                })
        
        # 趋势分析
        trend = self.history_tracker.analyze_trend(symbol)
        
        return {
            "symbol": current.symbol,
            "name": current.name,
            "market": current.market,
            "current": {
                "score": current.total_score,
                "grade": current.grade,
                "close": current.close,
                "technical": current.technical_score,
                "valuation": current.valuation_score,
                "macro": current.macro_score,
                "sentiment": current.sentiment_score,
                "pe_ratio": current.pe_ratio,
                "pb_ratio": current.pb_ratio,
                "risk_premium": current.risk_premium,
                "valuation_level": current.valuation_level
            },
            "history": history_list,
            "trend": trend
        }


# 初始化数据管理器
dashboard_data = DashboardData() if FLASK_AVAILABLE else None


# ============ API 路由 ============

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/summary')
def api_summary():
    """API: 获取摘要"""
    return jsonify(dashboard_data.get_summary())


@app.route('/api/scores')
def api_scores():
    """API: 获取所有评分"""
    return jsonify(dashboard_data.get_all_scores())


@app.route('/api/asset/<symbol>')
def api_asset(symbol):
    """API: 获取单个资产详情"""
    return jsonify(dashboard_data.get_asset_detail(symbol))


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """API: 刷新数据"""
    success = dashboard_data.refresh_data()
    return jsonify({"success": success})


@app.route('/api/config')
def api_config():
    """API: 获取配置"""
    config = ConfigManager()
    return jsonify({
        "strategy": {
            "technical_weight": config.strategy.technical_weight,
            "valuation_weight": config.strategy.valuation_weight,
            "macro_weight": config.strategy.macro_weight,
            "sentiment_weight": config.strategy.sentiment_weight
        },
        "stocks": config.get_all_stocks()
    })


# ============ HTML 模板 ============

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>股票趋势跟踪系统 - Web仪表板</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .header .subtitle {
            opacity: 0.9;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: transform 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        
        .card-title {
            font-size: 0.875rem;
            color: #666;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .card-value {
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }
        
        .card-subtitle {
            font-size: 0.875rem;
            color: #999;
            margin-top: 0.25rem;
        }
        
        .grade-a { color: #00C853; }
        .grade-b { color: #64DD17; }
        .grade-c { color: #FFC107; }
        .grade-d { color: #FF9800; }
        .grade-e { color: #F44336; }
        
        .scores-table {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow-x: auto;
        }
        
        .scores-table h2 {
            margin-bottom: 1rem;
            color: #333;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        th {
            font-weight: 600;
            color: #666;
            font-size: 0.875rem;
            text-transform: uppercase;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .score-bar {
            display: inline-block;
            width: 60px;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-right: 8px;
        }
        
        .score-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }
        
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .badge-a { background: #E8F5E9; color: #00C853; }
        .badge-b { background: #F1F8E9; color: #64DD17; }
        .badge-c { background: #FFF8E1; color: #FFC107; }
        .badge-d { background: #FFF3E0; color: #FF9800; }
        .badge-e { background: #FFEBEE; color: #F44336; }
        
        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            margin-bottom: 2rem;
            transition: opacity 0.2s;
        }
        
        .refresh-btn:hover {
            opacity: 0.9;
        }
        
        .refresh-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 3rem;
            color: #666;
        }
        
        .loading.active {
            display: block;
        }
        
        .last-update {
            color: #999;
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .header h1 {
                font-size: 1.5rem;
            }
            
            .card-value {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 股票趋势跟踪系统</h1>
        <div class="subtitle">多因子策略 · 中长期投资 · 智能调仓</div>
    </div>
    
    <div class="container">
        <div class="last-update" id="lastUpdate">加载中...</div>
        
        <button class="refresh-btn" id="refreshBtn" onclick="refreshData()">
            🔄 刷新数据
        </button>
        
        <div class="loading" id="loading">
            <div>正在加载数据...</div>
        </div>
        
        <div id="content">
            <div class="summary-cards" id="summaryCards">
                <!-- 动态生成 -->
            </div>
            
            <div class="scores-table">
                <h2>📈 资产评分详情</h2>
                <table id="scoresTable">
                    <thead>
                        <tr>
                            <th>资产</th>
                            <th>综合评分</th>
                            <th>技术面</th>
                            <th>估值面</th>
                            <th>宏观面</th>
                            <th>情绪面</th>
                            <th>评级</th>
                            <th>建议</th>
                        </tr>
                    </thead>
                    <tbody id="scoresTableBody">
                        <!-- 动态生成 -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        // 页面加载时获取数据
        document.addEventListener('DOMContentLoaded', loadData);
        
        async function loadData() {
            showLoading(true);
            
            try {
                // 获取摘要
                const summaryRes = await fetch('/api/summary');
                const summary = await summaryRes.json();
                
                // 获取评分列表
                const scoresRes = await fetch('/api/scores');
                const scores = await scoresRes.json();
                
                renderSummary(summary);
                renderScores(scores);
                
                if (summary.timestamp) {
                    document.getElementById('lastUpdate').textContent = 
                        '最后更新: ' + summary.timestamp;
                }
            } catch (error) {
                console.error('加载数据失败:', error);
                alert('加载数据失败，请稍后重试');
            } finally {
                showLoading(false);
            }
        }
        
        async function refreshData() {
            const btn = document.getElementById('refreshBtn');
            btn.disabled = true;
            btn.textContent = '🔄 更新中...';
            
            try {
                const res = await fetch('/api/refresh', { method: 'POST' });
                const result = await res.json();
                
                if (result.success) {
                    await loadData();
                    alert('数据已更新');
                } else {
                    alert('更新失败');
                }
            } catch (error) {
                console.error('刷新失败:', error);
                alert('刷新失败');
            } finally {
                btn.disabled = false;
                btn.textContent = '🔄 刷新数据';
            }
        }
        
        function showLoading(show) {
            document.getElementById('loading').classList.toggle('active', show);
            document.getElementById('content').style.display = show ? 'none' : 'block';
        }
        
        function renderSummary(data) {
            const container = document.getElementById('summaryCards');
            
            const gradeEmoji = {
                'A': '🚀', 'B': '📈', 'C': '➡️', 'D': '⚠️', 'E': '📉'
            };
            
            container.innerHTML = `
                <div class="card">
                    <div class="card-title">监控资产</div>
                    <div class="card-value">${data.total_assets || 0}</div>
                    <div class="card-subtitle">个标的</div>
                </div>
                
                <div class="card">
                    <div class="card-title">平均评分</div>
                    <div class="card-value ${getGradeClass(data.avg_score)}">${(data.avg_score || 0).toFixed(1)}</div>
                    <div class="card-subtitle">综合评分</div>
                </div>
                
                <div class="card">
                    <div class="card-title">最佳标的</div>
                    <div class="card-value grade-a">${gradeEmoji[data.best?.grade?.[0]] || '➡️'}</div>
                    <div class="card-subtitle">${data.best?.name || '-'} (${data.best?.score?.toFixed(0) || 0}分)</div>
                </div>
                
                <div class="card">
                    <div class="card-title">买入信号</div>
                    <div class="card-value grade-a">${(data.grade_distribution?.A || 0) + (data.grade_distribution?.B || 0)}</div>
                    <div class="card-subtitle">个标的 (A级+B级)</div>
                </div>
                
                <div class="card">
                    <div class="card-title">风险提示</div>
                    <div class="card-value grade-e">${(data.grade_distribution?.D || 0) + (data.grade_distribution?.E || 0)}</div>
                    <div class="card-subtitle">个标的 (D级+E级)</div>
                </div>
                
                <div class="card">
                    <div class="card-title">VIX指数</div>
                    <div class="card-value">${data.macro?.vix?.toFixed(1) || '-'}</div>
                    <div class="card-subtitle">市场恐慌度</div>
                </div>
            `;
        }
        
        function renderScores(scores) {
            const tbody = document.getElementById('scoresTableBody');
            
            tbody.innerHTML = scores.map(s => `
                <tr>
                    <td>
                        <strong>${s.name}</strong><br>
                        <small style="color: #999;">${s.symbol}</small>
                    </td>
                    <td>
                        <div style="display: flex; align-items: center;">
                            <div class="score-bar">
                                <div class="score-bar-fill ${getGradeClass(s.total_score)}" 
                                     style="width: ${s.total_score}%; background: ${getScoreColor(s.total_score)}"></div>
                            </div>
                            <strong>${s.total_score.toFixed(1)}</strong>
                        </div>
                    </td>
                    <td>${s.technical_score.toFixed(1)}</td>
                    <td>${s.valuation_score.toFixed(1)}</td>
                    <td>${s.macro_score.toFixed(1)}</td>
                    <td>${s.sentiment_score.toFixed(1)}</td>
                    <td>
                        <span class="badge badge-${s.grade?.[0]?.toLowerCase() || 'c'}">
                            ${s.grade_emoji} ${s.grade?.[0] || 'C'}
                        </span>
                    </td>
                    <td>
                        <small>${s.action}</small><br>
                        <small style="color: #999;">仓位: ${s.position_suggest}</small>
                    </td>
                </tr>
            `).join('');
        }
        
        function getGradeClass(score) {
            if (score >= 80) return 'grade-a';
            if (score >= 65) return 'grade-b';
            if (score >= 50) return 'grade-c';
            if (score >= 35) return 'grade-d';
            return 'grade-e';
        }
        
        function getScoreColor(score) {
            if (score >= 80) return '#00C853';
            if (score >= 65) return '#64DD17';
            if (score >= 50) return '#FFC107';
            if (score >= 35) return '#FF9800';
            return '#F44336';
        }
    </script>
</body>
</html>
"""


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """
    运行Web仪表板
    
    Args:
        host: 主机地址
        port: 端口号
        debug: 是否调试模式
    """
    if not FLASK_AVAILABLE:
        print("❌ Flask 未安装，无法启动Web服务")
        return
    
    print("=" * 70)
    print("🌐 启动Web仪表板")
    print("=" * 70)
    
    # 初始化数据
    print("\n📊 初始化数据...")
    if dashboard_data:
        dashboard_data.refresh_data()
    
    print(f"\n✅ 服务启动成功!")
    print(f"🌐 访问地址: http://{host}:{port}")
    print(f"📱 支持设备: 电脑、平板、手机")
    print(f"\n按 Ctrl+C 停止服务\n")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_dashboard(debug=True)
