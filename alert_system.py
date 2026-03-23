#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能告警系统模块
多维度监控，当触发条件时发送告警
支持微信、邮件、Webhook等多种通知方式
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class AlertLevel(Enum):
    """告警级别"""
    CRITICAL = "critical"  # 严重
    HIGH = "high"         # 高
    MEDIUM = "medium"     # 中
    LOW = "low"          # 低
    INFO = "info"        # 信息


class AlertType(Enum):
    """告警类型"""
    REBALANCE = "rebalance"           # 调仓提醒
    GRADE_CHANGE = "grade_change"     # 评级变化
    EXTREME_SCORE = "extreme_score"   # 极值评分
    PRICE_ALERT = "price_alert"       # 价格告警
    RISK_ALERT = "risk_alert"         # 风险告警
    NEWS_ALERT = "news_alert"         # 新闻告警
    SYSTEM = "system"                 # 系统告警


@dataclass
class Alert:
    """告警记录"""
    id: str
    timestamp: str
    level: AlertLevel
    type: AlertType
    symbol: str
    name: str
    title: str
    message: str
    data: Dict
    read: bool = False


class AlertRule:
    """告警规则"""
    
    def __init__(self, name: str, condition: Callable, level: AlertLevel, 
                 alert_type: AlertType, cooldown_hours: int = 24):
        """
        初始化告警规则
        
        Args:
            name: 规则名称
            condition: 触发条件函数
            level: 告警级别
            alert_type: 告警类型
            cooldown_hours: 冷却时间（小时）
        """
        self.name = name
        self.condition = condition
        self.level = level
        self.alert_type = alert_type
        self.cooldown_hours = cooldown_hours
        self.last_triggered = None
    
    def check(self, **kwargs) -> bool:
        """检查是否触发"""
        # 检查冷却时间
        if self.last_triggered:
            if datetime.now() - self.last_triggered < timedelta(hours=self.cooldown_hours):
                return False
        
        # 执行条件检查
        if self.condition(**kwargs):
            self.last_triggered = datetime.now()
            return True
        
        return False


class AlertManager:
    """告警管理器"""
    
    def __init__(self, alerts_file: str = "./alerts.json"):
        """
        初始化告警管理器
        
        Args:
            alerts_file: 告警记录文件路径
        """
        self.alerts_file = Path(alerts_file)
        self.alerts: List[Alert] = []
        self.rules: List[AlertRule] = []
        self.notification_config = {}
        
        self._load_alerts()
        self._setup_default_rules()
    
    def _load_alerts(self):
        """加载历史告警"""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for alert_data in data.get('alerts', []):
                    alert = Alert(
                        id=alert_data['id'],
                        timestamp=alert_data['timestamp'],
                        level=AlertLevel(alert_data['level']),
                        type=AlertType(alert_data['type']),
                        symbol=alert_data['symbol'],
                        name=alert_data['name'],
                        title=alert_data['title'],
                        message=alert_data['message'],
                        data=alert_data.get('data', {}),
                        read=alert_data.get('read', False)
                    )
                    self.alerts.append(alert)
                    
            except Exception as e:
                print(f"加载告警历史失败: {e}")
    
    def _save_alerts(self):
        """保存告警记录"""
        try:
            data = {
                'alerts': [
                    {
                        'id': alert.id,
                        'timestamp': alert.timestamp,
                        'level': alert.level.value,
                        'type': alert.type.value,
                        'symbol': alert.symbol,
                        'name': alert.name,
                        'title': alert.title,
                        'message': alert.message,
                        'data': alert.data,
                        'read': alert.read
                    }
                    for alert in self.alerts[-200:]  # 只保留最近200条
                ]
            }
            
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存告警失败: {e}")
    
    def _setup_default_rules(self):
        """设置默认告警规则"""
        # 1. 跨级变化告警
        self.add_rule(
            name="评级跨级变化",
            condition=lambda **kwargs: kwargs.get('grade_change_level', 0) >= 2,
            level=AlertLevel.HIGH,
            alert_type=AlertType.GRADE_CHANGE,
            cooldown_hours=12
        )
        
        # 2. 极高评分告警
        self.add_rule(
            name="极高评分(买入机会)",
            condition=lambda **kwargs: kwargs.get('score', 0) >= 85,
            level=AlertLevel.MEDIUM,
            alert_type=AlertType.EXTREME_SCORE,
            cooldown_hours=72
        )
        
        # 3. 极低评分告警
        self.add_rule(
            name="极低评分(卖出警示)",
            condition=lambda **kwargs: kwargs.get('score', 0) <= 25,
            level=AlertLevel.HIGH,
            alert_type=AlertType.EXTREME_SCORE,
            cooldown_hours=72
        )
        
        # 4. 快速下跌告警
        self.add_rule(
            name="评分快速下跌",
            condition=lambda **kwargs: kwargs.get('score_change_7d', 0) <= -10,
            level=AlertLevel.HIGH,
            alert_type=AlertType.RISK_ALERT,
            cooldown_hours=24
        )
        
        # 5. 调仓周期告警
        self.add_rule(
            name="调仓周期提醒",
            condition=lambda **kwargs: kwargs.get('days_since_rebalance', 0) >= 90,
            level=AlertLevel.MEDIUM,
            alert_type=AlertType.REBALANCE,
            cooldown_hours=168  # 一周
        )
        
        # 6. VIX恐慌指数告警
        self.add_rule(
            name="VIX极度恐慌",
            condition=lambda **kwargs: kwargs.get('vix', 0) >= 35,
            level=AlertLevel.HIGH,
            alert_type=AlertType.RISK_ALERT,
            cooldown_hours=24
        )
    
    def add_rule(self, name: str, condition: Callable, level: AlertLevel, 
                 alert_type: AlertType, cooldown_hours: int = 24):
        """
        添加告警规则
        
        Args:
            name: 规则名称
            condition: 触发条件函数
            level: 告警级别
            alert_type: 告警类型
            cooldown_hours: 冷却时间
        """
        rule = AlertRule(name, condition, level, alert_type, cooldown_hours)
        self.rules.append(rule)
        print(f"✅ 告警规则已添加: {name}")
    
    def check_alerts(self, symbol: str, name: str, **kwargs) -> List[Alert]:
        """
        检查告警
        
        Args:
            symbol: 股票代码
            name: 股票名称
            **kwargs: 检查参数
        
        Returns:
            触发的告警列表
        """
        triggered = []
        
        for rule in self.rules:
            if rule.check(symbol=symbol, name=name, **kwargs):
                # 生成告警
                alert_id = f"{symbol}_{rule.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                alert = Alert(
                    id=alert_id,
                    timestamp=datetime.now().isoformat(),
                    level=rule.level,
                    type=rule.alert_type,
                    symbol=symbol,
                    name=name,
                    title=f"[{rule.level.value.upper()}] {rule.name}",
                    message=self._generate_message(rule, symbol, name, kwargs),
                    data=kwargs
                )
                
                self.alerts.append(alert)
                triggered.append(alert)
                
                # 发送通知
                self._send_notification(alert)
        
        if triggered:
            self._save_alerts()
        
        return triggered
    
    def _generate_message(self, rule: AlertRule, symbol: str, name: str, data: Dict) -> str:
        """生成告警消息"""
        messages = {
            "评级跨级变化": f"{name}({symbol}) 评级发生跨级变化，建议关注调仓",
            "极高评分(买入机会)": f"{name}({symbol}) 评分极高({data.get('score', 0):.0f}分)，可能是买入机会",
            "极低评分(卖出警示)": f"{name}({symbol}) 评分极低({data.get('score', 0):.0f}分)，建议减仓避险",
            "评分快速下跌": f"{name}({symbol}) 评分7日下跌{data.get('score_change_7d', 0):.1f}分，注意风险",
            "调仓周期提醒": f"距离上次调仓已{data.get('days_since_rebalance', 0)}天，建议重新评估仓位",
            "VIX极度恐慌": f"VIX指数达到{data.get('vix', 0):.1f}，市场极度恐慌，可能存在逆向机会"
        }
        
        return messages.get(rule.name, f"{rule.name}: {name}({symbol})")
    
    def _send_notification(self, alert: Alert):
        """发送通知"""
        # 微信推送
        self._send_wechat(alert)
        
        # 邮件通知
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
            self._send_email(alert)
    
    def _send_wechat(self, alert: Alert):
        """发送到微信"""
        try:
            serverchan_key = self.notification_config.get('serverchan_key', '')
            if not serverchan_key:
                return
            
            url = "https://www.pushplus.plus/api/send"
            
            # 根据级别设置emoji
            emoji_map = {
                AlertLevel.CRITICAL: "🚨",
                AlertLevel.HIGH: "⚠️",
                AlertLevel.MEDIUM: "📢",
                AlertLevel.LOW: "ℹ️",
                AlertLevel.INFO: "💬"
            }
            
            emoji = emoji_map.get(alert.level, "📢")
            
            data = {
                "token": serverchan_key,
                "title": f"{emoji} {alert.title}",
                "content": f"<b>{alert.name} ({alert.symbol})</b><br><br>{alert.message}<br><br>时间: {alert.timestamp}",
                "template": "html"
            }
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("code") == 200:
                print(f"✅ 微信告警已发送: {alert.title}")
            else:
                print(f"❌ 微信告警发送失败: {result}")
                
        except Exception as e:
            print(f"❌ 微信告警异常: {e}")
    
    def _send_email(self, alert: Alert):
        """发送邮件（简化版，实际使用时需要配置SMTP）"""
        # 这里只是示例，实际实现需要配置邮件服务器
        pass
    
    def get_recent_alerts(self, hours: int = 24, unread_only: bool = False) -> List[Alert]:
        """
        获取最近告警
        
        Args:
            hours: 最近多少小时
            unread_only: 仅未读
        
        Returns:
            告警列表
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent = []
        for alert in self.alerts:
            alert_time = datetime.fromisoformat(alert.timestamp)
            if alert_time >= cutoff:
                if not unread_only or not alert.read:
                    recent.append(alert)
        
        return sorted(recent, key=lambda x: x.timestamp, reverse=True)
    
    def mark_as_read(self, alert_id: str):
        """标记为已读"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.read = True
                break
        self._save_alerts()
    
    def mark_all_as_read(self):
        """标记所有为已读"""
        for alert in self.alerts:
            alert.read = True
        self._save_alerts()
    
    def get_alert_summary(self) -> Dict:
        """获取告警摘要"""
        total = len(self.alerts)
        unread = sum(1 for a in self.alerts if not a.read)
        
        # 按级别统计
        level_counts = {}
        for level in AlertLevel:
            level_counts[level.value] = sum(1 for a in self.alerts if a.level == level)
        
        # 按类型统计
        type_counts = {}
        for alert_type in AlertType:
            type_counts[alert_type.value] = sum(1 for a in self.alerts if a.type == alert_type)
        
        return {
            'total': total,
            'unread': unread,
            'by_level': level_counts,
            'by_type': type_counts
        }
    
    def print_alert_report(self, hours: int = 24):
        """打印告警报告"""
        alerts = self.get_recent_alerts(hours)
        
        print("\n" + "=" * 70)
        print(f"🔔 告警报告 (最近{hours}小时)")
        print("=" * 70)
        
        if not alerts:
            print("\n✅ 无告警")
            return
        
        # 按级别分组
        by_level = {}
        for alert in alerts:
            level = alert.level.value
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(alert)
        
        # 打印
        for level in ['critical', 'high', 'medium', 'low', 'info']:
            if level in by_level:
                emoji = {"critical": "🚨", "high": "⚠️", "medium": "📢", "low": "ℹ️", "info": "💬"}.get(level, "📢")
                print(f"\n{emoji} {level.upper()} ({len(by_level[level])})")
                print("-" * 70)
                
                for alert in by_level[level]:
                    time_str = datetime.fromisoformat(alert.timestamp).strftime('%m-%d %H:%M')
                    read_mark = "🔴" if not alert.read else "⚪"
                    print(f"   {read_mark} [{time_str}] {alert.name}")
                    print(f"      {alert.message}")
        
        print("\n" + "=" * 70)


def demo_alert_system():
    """演示告警系统"""
    print("=" * 70)
    print("🔔 智能告警系统演示")
    print("=" * 70)
    
    # 创建告警管理器
    alert_manager = AlertManager("./demo_alerts.json")
    
    # 模拟检查
    print("\n📊 模拟告警检查...")
    
    # 场景1: 极高评分
    alerts = alert_manager.check_alerts(
        symbol="000300",
        name="沪深300",
        score=88,
        grade_change_level=0
    )
    
    if alerts:
        print(f"   触发 {len(alerts)} 个告警")
    
    # 场景2: 跨级变化
    alerts = alert_manager.check_alerts(
        symbol="^IXIC",
        name="纳斯达克",
        score=45,
        grade_change_level=2
    )
    
    if alerts:
        print(f"   触发 {len(alerts)} 个告警")
    
    # 场景3: 评分快速下跌
    alerts = alert_manager.check_alerts(
        symbol="000905",
        name="中证500",
        score=52,
        score_change_7d=-15
    )
    
    if alerts:
        print(f"   触发 {len(alerts)} 个告警")
    
    # 打印报告
    alert_manager.print_alert_report()
    
    # 打印统计
    summary = alert_manager.get_alert_summary()
    print("\n📈 告警统计:")
    print(f"   总计: {summary['total']}")
    print(f"   未读: {summary['unread']}")
    print(f"   按级别: {summary['by_level']}")
    
    print("\n✅ 演示完成!")


if __name__ == "__main__":
    demo_alert_system()
