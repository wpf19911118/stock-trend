#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票趋势跟踪机器人 V2.0
多因子策略（中长期调仓 6个月~1年）
支持 A股 + 美股（纳斯达克）
增强版：含估值分析、数据缓存、优化评分算法
"""

import os
import io
import sys

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import datetime
import requests
import pandas as pd
from pathlib import Path
from typing import List, Dict
from dataclasses import asdict

# 导入自定义模块
from market_data import get_all_market_data
from scoring_system_v2 import MultiFactorScorerV2, ScoreResult, format_score_report
from data_cache import cache

# ==================== 配置 ====================
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")
PUSHPLUS_WEBHOOK = os.environ.get("PUSHPLUS_WEBHOOK", "wxa551176bf758ffc7")

# ==================== 消息推送 ====================
def send_wechat_message(title: str, content: str) -> bool:
    """Server酱推送 (pushplus新版)"""
    if not SERVERCHAN_KEY:
        print("⚠️ 未配置 SERVERCHAN_KEY，跳过推送")
        print(f"\n消息预览:\n{title}\n{'='*50}\n{content[:500]}...")
        return False

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
            print("✅ 微信推送成功!")
            return True
        else:
            print(f"❌ 推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False


def generate_html_report(results: List[ScoreResult], macro_data: Dict) -> str:
    """
    生成HTML格式的报告（用于微信推送）
    
    Args:
        results: 评分结果列表
        macro_data: 宏观数据
    
    Returns:
        HTML格式字符串
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    html_parts = []
    
    # 标题
    html_parts.append(f"<h3>📅 {today} 市场分析报告 V2.0</h3>")
    html_parts.append("<hr>")
    
    # 宏观数据摘要
    html_parts.append("<h4>🌍 宏观环境</h4>")
    html_parts.append("<ul>")
    if macro_data.get("us_10y_yield"):
        html_parts.append(f"<li>🇺🇸 美债10年: {macro_data['us_10y_yield']}%</li>")
    if macro_data.get("cn_10y_yield"):
        html_parts.append(f"<li>🇨🇳 中债10年: {macro_data['cn_10y_yield']}%</li>")
    if macro_data.get("vix"):
        vix_color = "red" if macro_data['vix'] > 30 else "orange" if macro_data['vix'] > 20 else "green"
        html_parts.append(f"<li>📊 VIX: <span style='color:{vix_color}'>{macro_data['vix']}</span></li>")
    if macro_data.get("cn_vix"):
        cn_vix = macro_data['cn_vix']
        # 50ETF波动率阈值（低于VIX）
        if cn_vix > 30:
            cn_vix_color = "red"
            cn_vix_status = "恐慌"
        elif cn_vix > 25:
            cn_vix_color = "orange"
            cn_vix_status = "担忧"
        elif cn_vix > 15:
            cn_vix_color = "green"
            cn_vix_status = "正常"
        else:
            cn_vix_color = "blue"
            cn_vix_status = "过度乐观"
        html_parts.append(f"<li>🇨🇳 A股恐慌指数(50ETF波动率): <span style='color:{cn_vix_color}'>{cn_vix}% ({cn_vix_status})</span></li>")
    if macro_data.get("dxy"):
        html_parts.append(f"<li>💵 美元指数: {macro_data['dxy']}</li>")
    html_parts.append("</ul>")
    html_parts.append("<hr>")
    
    # 各标的评分
    html_parts.append("<h4>📊 标的评分</h4>")
    
    # 按得分排序
    sorted_results = sorted(results, key=lambda x: x.total_score, reverse=True)
    
    for r in sorted_results:
        # 颜色标记
        if r.total_score >= 80:
            color = "#00C853"  # 绿色 - 强烈买入
            bg_color = "#E8F5E9"
        elif r.total_score >= 65:
            color = "#64DD17"  # 浅绿 - 买入
            bg_color = "#F1F8E9"
        elif r.total_score >= 50:
            color = "#FFC107"  # 黄色 - 持有
            bg_color = "#FFF8E1"
        elif r.total_score >= 35:
            color = "#FF9800"  # 橙色 - 观望
            bg_color = "#FFF3E0"
        else:
            color = "#F44336"  # 红色 - 卖出
            bg_color = "#FFEBEE"
        
        html_parts.append(f"<div style='margin:12px 0;padding:12px;border-left:5px solid {color};background:{bg_color};border-radius:4px;'>")
        
        # 标题行
        html_parts.append(f"<div style='font-size:16px;font-weight:bold;margin-bottom:8px;'>")
        html_parts.append(f"{r.grade_emoji} {r.name} ({r.symbol})")
        html_parts.append(f"<span style='float:right;color:{color};font-size:20px;'>{r.total_score}分</span>")
        html_parts.append("</div>")
        
        # 评级
        html_parts.append(f"<div style='color:{color};font-weight:bold;margin-bottom:8px;'>{r.grade}</div>")
        
        # 价格和估值
        html_parts.append(f"<div style='font-size:13px;color:#666;margin-bottom:8px;'>")
        html_parts.append(f"💰 价格: {r.close}")
        if r.pe_ratio:
            html_parts.append(f" | PE: {r.pe_ratio:.1f}")
        if r.pe_percentile is not None:
            html_parts.append(f" (分位{r.pe_percentile}%)")
        if r.valuation_level != "未知":
            html_parts.append(f" | 估值: {r.valuation_level}")
        html_parts.append("</div>")
        
        # 股债性价比
        if r.risk_premium is not None:
            rp_color = "green" if r.risk_premium > 3 else "orange" if r.risk_premium > 2 else "red"
            html_parts.append(f"<div style='font-size:13px;margin-bottom:8px;'>⚖️ 股债性价比: <span style='color:{rp_color}'>{r.risk_premium}% ({r.risk_premium_level})</span></div>")
        
        # 操作建议
        html_parts.append(f"<div style='font-size:14px;margin-top:10px;padding:6px;background:rgba(255,255,255,0.5);border-radius:3px;'>")
        html_parts.append(f"<b>建议:</b> {r.action} | 仓位: {r.position_suggest}")
        html_parts.append("</div>")
        
        # 分项得分
        html_parts.append(f"<div style='font-size:12px;color:#888;margin-top:8px;'>")
        html_parts.append(f"技术:{r.technical_score}/30 | 估值:{r.valuation_score}/35 | 宏观:{r.macro_score}/25 | 情绪:{r.sentiment_score}/10")
        html_parts.append("</div>")
        
        html_parts.append("</div>")
    
    html_parts.append("<hr>")
    
    # 调仓建议
    html_parts.append("<h4>💡 调仓建议</h4>")
    
    # 找出最佳和最差的
    best = sorted_results[0] if sorted_results else None
    worst = sorted_results[-1] if sorted_results else None
    
    if best and best.total_score >= 65:
        html_parts.append(f"<div style='padding:8px;background:#E8F5E9;border-radius:4px;margin-bottom:8px;'>")
        html_parts.append(f"🎯 <b>重点关注:</b> {best.name} ({best.total_score}分) - {best.action}")
        html_parts.append("</div>")
    
    if worst and worst.total_score < 50:
        html_parts.append(f"<div style='padding:8px;background:#FFEBEE;border-radius:4px;margin-bottom:8px;'>")
        html_parts.append(f"⚠️ <b>风险提示:</b> {worst.name} ({worst.total_score}分) - {worst.action}")
        html_parts.append("</div>")
    
    # 资产配置建议
    a_shares_results = [r for r in results if r.market == "A股"]
    us_results = [r for r in results if r.market == "美股"]
    
    if a_shares_results and us_results:
        a_shares_score = sum([r.total_score for r in a_shares_results]) / len(a_shares_results)
        us_score = sum([r.total_score for r in us_results]) / len(us_results)
        
        html_parts.append(f"<div style='padding:10px;background:#E3F2FD;border-radius:4px;margin-top:12px;'>")
        html_parts.append(f"<b>🌏 全球配置建议</b><br>")
        
        if a_shares_score > us_score + 10:
            html_parts.append(f"A股评分 {a_shares_score:.0f}分 > 美股评分 {us_score:.0f}分<br>")
            html_parts.append(f"建议: <b>A股偏向 (70% A股 / 30% 美股)</b>")
        elif us_score > a_shares_score + 10:
            html_parts.append(f"美股评分 {us_score:.0f}分 > A股评分 {a_shares_score:.0f}分<br>")
            html_parts.append(f"建议: <b>美股偏向 (30% A股 / 70% 美股)</b>")
        else:
            html_parts.append(f"两地市场评分接近 (A股{a_shares_score:.0f}分 / 美股{us_score:.0f}分)<br>")
            html_parts.append(f"建议: <b>均衡配置 (50% A股 / 50% 美股)</b>")
        
        html_parts.append("</div>")
    
    html_parts.append("<hr>")
    html_parts.append("<small style='color:#999;'>💬 策略说明: 多因子综合评分系统 V2.0 (技术30%+估值35%+宏观25%+情绪10%)</small><br>")
    html_parts.append("<small style='color:#999;'>⏰ 建议调仓周期: 每季度评估 | 推送时间: 每日08:00(北京时间)</small><br>")
    html_parts.append("<small style='color:#999;'>📊 数据来源: Yahoo Finance / Akshare</small>")
    
    return "".join(html_parts)


def save_results(results: List[ScoreResult], macro_data: Dict, html_report: str):
    """
    保存分析结果到文件
    
    Args:
        results: 评分结果列表
        macro_data: 宏观数据
        html_report: HTML报告
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    # 1. 保存JSON数据
    output_data = {
        "date": today,
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "2.0",
        "macro": macro_data,
        "results": [asdict(r) for r in results]
    }
    
    json_file = output_dir / f"analysis_v2_{today.replace('-', '')}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 数据已保存: {json_file}")
    
    # 2. 保存HTML报告
    html_file = output_dir / f"report_v2_{today.replace('-', '')}.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    print(f"✅ HTML报告已保存: {html_file}")
    
    # 3. 保存文本报告
    text_report = format_score_report(results)
    text_file = output_dir / f"report_v2_{today.replace('-', '')}.txt"
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(text_report)
    
    print(f"✅ 文本报告已保存: {text_file}")


def check_rebalance_signal(current_results: List[ScoreResult]) -> tuple[bool, str]:
    """
    检查是否需要调仓信号
    
    Returns:
        (是否需要调仓, 原因)
    """
    output_dir = Path(__file__).parent / "results"
    
    # 查找最近的历史文件
    json_files = sorted(output_dir.glob("analysis_v2_*.json"), reverse=True)
    
    if not json_files:
        return True, "📌 首次运行，建议建立基准仓位"
    
    # 读取上次结果
    try:
        with open(json_files[0], "r", encoding="utf-8") as f:
            last_data = json.load(f)
        
        last_date = datetime.datetime.strptime(last_data["date"], "%Y-%m-%d")
        days_diff = (datetime.datetime.now() - last_date).days
        
        # 检查是否超过3个月
        if days_diff >= 90:
            return True, f"📌 距离上次调仓已 {days_diff} 天，建议重新评估"
        
        # 检查评分跨级变化
        last_results = {r["symbol"]: r for r in last_data.get("results", [])}
        changes = []
        
        for current in current_results:
            symbol = current.symbol
            if symbol in last_results:
                last_grade = last_results[symbol]["grade"]
                current_grade = current.grade
                
                # 提取等级
                last_level = last_grade[0] if last_grade else "C"
                current_level = current_grade[0] if current_grade else "C"
                
                grade_order = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
                
                last_score = grade_order.get(last_level, 3)
                current_score = grade_order.get(current_level, 3)
                
                if abs(current_score - last_score) >= 2:
                    changes.append(f"{current.name}: {last_grade} → {current_grade}")
        
        if changes:
            return True, f"📌 评级跨级变化: {'; '.join(changes[:3])}"
        
        return False, f"✅ 评分稳定，距离下次评估还有 {90 - days_diff} 天"
        
    except Exception as e:
        return True, f"⚠️ 读取历史数据失败: {e}"


def print_summary(results: List[ScoreResult], macro_data: Dict):
    """打印分析摘要"""
    print("\n" + "=" * 70)
    print("📊 分析摘要")
    print("=" * 70)
    
    # 宏观环境
    print("\n🌍 宏观环境:")
    if macro_data.get("us_10y_yield"):
        print(f"   美债10年: {macro_data['us_10y_yield']}%")
    if macro_data.get("cn_10y_yield"):
        print(f"   中债10年: {macro_data['cn_10y_yield']}%")
    if macro_data.get("vix"):
        print(f"   VIX: {macro_data['vix']}")
    if macro_data.get("dxy"):
        print(f"   美元指数: {macro_data['dxy']}")
    
    # 各标的概况
    print("\n📈 标的概况:")
    for r in results:
        print(f"   {r.name:10} | {r.total_score:5.1f}分 | {r.grade:15} | 仓位: {r.position_suggest}")
    
    # 统计
    avg_score = sum([r.total_score for r in results]) / len(results) if results else 0
    a_count = sum([1 for r in results if r.total_score >= 80])
    b_count = sum([1 for r in results if 65 <= r.total_score < 80])
    d_count = sum([1 for r in results if 35 <= r.total_score < 50])
    e_count = sum([1 for r in results if r.total_score < 35])
    
    print(f"\n📊 统计:")
    print(f"   平均分: {avg_score:.1f}")
    print(f"   买入(A+B): {a_count + b_count}个")
    print(f"   观望/卖出(D+E): {d_count + e_count}个")
    
    print("=" * 70)


# ==================== 主程序 ====================
def main():
    print("=" * 70)
    print("🚀 股票趋势跟踪机器人 V2.0")
    print("📊 多因子策略（中长期调仓 6个月~1年）")
    print("🆕 新特性: 估值分析 + 历史分位 + 优化算法")
    print(f"⏰ 运行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 清理过期缓存
    print("\n🧹 清理过期缓存...")
    cache.clear_expired()
    
    # 步骤1: 获取市场数据
    print("\n📥 步骤1: 获取市场数据...")
    print("-" * 70)
    
    try:
        market_data = get_all_market_data()
    except Exception as e:
        print(f"❌ 获取市场数据失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 检查数据完整性
    if not market_data.get("a_shares") and not market_data.get("us_stocks"):
        print("❌ 未获取到有效数据，退出")
        return
    
    # 步骤2: 多因子评分
    print("\n📊 步骤2: 多因子评分...")
    print("-" * 70)
    
    try:
        scorer = MultiFactorScorerV2(market_data, market_data.get("macro", {}))
        results = scorer.score_all()
    except Exception as e:
        print(f"❌ 评分失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    if not results:
        print("❌ 评分结果为空，退出")
        return
    
    # 步骤3: 生成报告
    print("\n📄 步骤3: 生成报告...")
    print("-" * 70)
    
    try:
        html_report = generate_html_report(results, market_data.get("macro", {}))
        text_report = format_score_report(results)
        
        # 打印摘要
        print_summary(results, market_data.get("macro", {}))
        
        # 打印详细报告
        print("\n详细报告:")
        print(text_report)
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 步骤4: 检查调仓信号
    print("\n🔔 步骤4: 检查调仓信号...")
    print("-" * 70)
    
    need_rebalance, reason = check_rebalance_signal(results)
    print(reason)
    
    # 步骤5: 推送消息
    print("\n📤 步骤5: 推送消息...")
    print("-" * 70)
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    title = f"📊 市场分析 V2.0 {today}"
    
    if need_rebalance:
        title = f"🔔 调仓提醒 V2.0 {today}"
    
    send_wechat_message(title, html_report)
    
    # 步骤6: 保存结果
    print("\n💾 步骤6: 保存结果...")
    print("-" * 70)
    
    try:
        save_results(results, market_data.get("macro", {}), html_report)
    except Exception as e:
        print(f"⚠️ 保存结果失败: {e}")
    
    # 完成
    print("\n" + "=" * 70)
    print("✅ 分析完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
