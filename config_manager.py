#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级配置管理模块
支持多环境配置、动态权重调整、个性化设置
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class StrategyConfig:
    """策略配置"""
    # 评分权重
    technical_weight: float = 0.30
    valuation_weight: float = 0.35
    macro_weight: float = 0.25
    sentiment_weight: float = 0.10
    
    # 评级阈值
    grade_a_threshold: float = 80.0
    grade_b_threshold: float = 65.0
    grade_c_threshold: float = 50.0
    grade_d_threshold: float = 35.0
    
    # 调仓参数
    rebalance_interval_days: int = 90
    rebalance_threshold: int = 2  # 跨级阈值
    min_position: float = 0.0
    max_position: float = 1.0
    
    # 仓位配置
    grade_a_position: float = 0.95
    grade_b_position: float = 0.80
    grade_c_position: float = 0.60
    grade_d_position: float = 0.40
    grade_e_position: float = 0.10


@dataclass
class MarketConfig:
    """市场配置"""
    # A股标的
    a_share_indices: Dict[str, str] = None
    
    # 美股标的
    us_indices: Dict[str, str] = None
    
    # 估值参数
    a_share_pe_low: float = 10.0
    a_share_pe_high: float = 25.0
    a_share_pb_low: float = 1.0
    a_share_pb_high: float = 2.5
    
    us_pe_low: float = 15.0
    us_pe_high: float = 30.0
    us_pb_low: float = 2.0
    us_pb_high: float = 4.0
    
    def __post_init__(self):
        if self.a_share_indices is None:
            self.a_share_indices = {
                "000300": "沪深300",
                "000905": "中证500"
            }
        if self.us_indices is None:
            self.us_indices = {
                "^IXIC": "纳斯达克",
                "^GSPC": "标普500"
            }


@dataclass
class NotificationConfig:
    """通知配置"""
    serverchan_key: str = ""
    pushplus_webhook: str = ""
    email_smtp: str = ""
    email_user: str = ""
    email_password: str = ""
    email_to: str = ""
    
    # 通知触发条件
    notify_on_rebalance: bool = True
    notify_on_grade_change: bool = True
    notify_on_extreme_score: bool = True  # 极高/极低评分
    notify_daily: bool = True


@dataclass
class SystemConfig:
    """系统配置"""
    # 缓存设置
    cache_enabled: bool = True
    cache_expire_hours: int = 6
    
    # 日志设置
    log_level: str = "INFO"
    log_to_file: bool = True
    
    # 数据保存
    save_results: bool = True
    save_history: bool = True
    
    # 回测设置
    backtest_enabled: bool = False
    backtest_days: int = 365
    
    # 可视化
    charts_enabled: bool = True
    charts_format: str = "png"  # png, pdf, svg


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        
        # 初始化默认配置
        self.strategy = StrategyConfig()
        self.market = MarketConfig()
        self.notification = NotificationConfig()
        self.system = SystemConfig()
        
        # 从环境变量读取敏感信息
        self._load_from_env()
        
        # 从文件加载配置
        if self.config_file.exists():
            self.load()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # 通知配置
        self.notification.serverchan_key = os.environ.get("SERVERCHAN_KEY", "")
        self.notification.pushplus_webhook = os.environ.get("PUSHPLUS_WEBHOOK", "")
        
        # 邮件配置
        self.notification.email_smtp = os.environ.get("EMAIL_SMTP", "")
        self.notification.email_user = os.environ.get("EMAIL_USER", "")
        self.notification.email_password = os.environ.get("EMAIL_PASSWORD", "")
        self.notification.email_to = os.environ.get("EMAIL_TO", "")
    
    def load(self):
        """从文件加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载各模块配置
            if 'strategy' in data:
                self.strategy = StrategyConfig(**data['strategy'])
            if 'market' in data:
                self.market = MarketConfig(**data['market'])
            if 'notification' in data:
                self.notification = NotificationConfig(**data['notification'])
            if 'system' in data:
                self.system = SystemConfig(**data['system'])
            
            print(f"✅ 配置已加载: {self.config_file}")
            
        except Exception as e:
            print(f"⚠️ 加载配置失败: {e}，使用默认配置")
    
    def save(self):
        """保存配置到文件"""
        try:
            data = {
                'strategy': asdict(self.strategy),
                'market': asdict(self.market),
                'notification': asdict(self.notification),
                'system': asdict(self.system)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 配置已保存: {self.config_file}")
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def update_strategy_weights(self, weights: Dict[str, float]):
        """
        更新策略权重
        
        Args:
            weights: 权重字典，如 {'technical': 0.25, 'valuation': 0.40}
        """
        if 'technical' in weights:
            self.strategy.technical_weight = weights['technical']
        if 'valuation' in weights:
            self.strategy.valuation_weight = weights['valuation']
        if 'macro' in weights:
            self.strategy.macro_weight = weights['macro']
        if 'sentiment' in weights:
            self.strategy.sentiment_weight = weights['sentiment']
        
        # 验证权重和为1
        total = (self.strategy.technical_weight + self.strategy.valuation_weight +
                self.strategy.macro_weight + self.strategy.sentiment_weight)
        
        if abs(total - 1.0) > 0.01:
            print(f"⚠️ 权重和不等于1 (当前: {total:.2f})，已自动归一化")
            # 归一化
            self.strategy.technical_weight /= total
            self.strategy.valuation_weight /= total
            self.strategy.macro_weight /= total
            self.strategy.sentiment_weight /= total
        
        self.save()
        print("✅ 策略权重已更新")
    
    def add_stock(self, symbol: str, name: str, market: str = "A股"):
        """
        添加监控标的
        
        Args:
            symbol: 股票代码
            name: 股票名称
            market: 市场 (A股/美股)
        """
        if market == "A股":
            self.market.a_share_indices[symbol] = name
        else:
            self.market.us_indices[symbol] = name
        
        self.save()
        print(f"✅ 已添加 {market} 标的: {name} ({symbol})")
    
    def remove_stock(self, symbol: str, market: str = "A股"):
        """
        移除监控标的
        
        Args:
            symbol: 股票代码
            market: 市场 (A股/美股)
        """
        if market == "A股":
            if symbol in self.market.a_share_indices:
                del self.market.a_share_indices[symbol]
                print(f"✅ 已移除 A股 标的: {symbol}")
        else:
            if symbol in self.market.us_indices:
                del self.market.us_indices[symbol]
                print(f"✅ 已移除 美股 标的: {symbol}")
        
        self.save()
    
    def get_all_stocks(self) -> Dict[str, Dict[str, str]]:
        """获取所有监控标的"""
        return {
            "A股": self.market.a_share_indices,
            "美股": self.market.us_indices
        }
    
    def set_notification(self, **kwargs):
        """
        设置通知配置
        
        Args:
            **kwargs: 通知配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self.notification, key):
                setattr(self.notification, key, value)
        
        self.save()
        print("✅ 通知配置已更新")
    
    def enable_feature(self, feature: str):
        """
        启用功能
        
        Args:
            feature: 功能名称 (backtest, charts, cache等)
        """
        if feature == "backtest":
            self.system.backtest_enabled = True
        elif feature == "charts":
            self.system.charts_enabled = True
        elif feature == "cache":
            self.system.cache_enabled = True
        elif feature == "history":
            self.system.save_history = True
        
        self.save()
        print(f"✅ 已启用功能: {feature}")
    
    def disable_feature(self, feature: str):
        """
        禁用功能
        
        Args:
            feature: 功能名称
        """
        if feature == "backtest":
            self.system.backtest_enabled = False
        elif feature == "charts":
            self.system.charts_enabled = False
        elif feature == "cache":
            self.system.cache_enabled = False
        elif feature == "history":
            self.system.save_history = False
        
        self.save()
        print(f"✅ 已禁用功能: {feature}")
    
    def print_config(self):
        """打印当前配置"""
        print("\n" + "=" * 70)
        print("📋 当前配置")
        print("=" * 70)
        
        print("\n🎯 策略权重:")
        print(f"   技术面: {self.strategy.technical_weight*100:.0f}%")
        print(f"   估值面: {self.strategy.valuation_weight*100:.0f}%")
        print(f"   宏观面: {self.strategy.macro_weight*100:.0f}%")
        print(f"   情绪面: {self.strategy.sentiment_weight*100:.0f}%")
        
        print("\n📊 评级阈值:")
        print(f"   A级: ≥{self.strategy.grade_a_threshold}分")
        print(f"   B级: ≥{self.strategy.grade_b_threshold}分")
        print(f"   C级: ≥{self.strategy.grade_c_threshold}分")
        print(f"   D级: ≥{self.strategy.grade_d_threshold}分")
        
        print("\n🔄 调仓配置:")
        print(f"   周期: {self.strategy.rebalance_interval_days}天")
        print(f"   跨级阈值: {self.strategy.rebalance_threshold}级")
        print(f"   仓位范围: {self.strategy.min_position*100:.0f}% - {self.strategy.max_position*100:.0f}%")
        
        print("\n📈 监控标的:")
        print("   A股:")
        for symbol, name in self.market.a_share_indices.items():
            print(f"      {symbol}: {name}")
        print("   美股:")
        for symbol, name in self.market.us_indices.items():
            print(f"      {symbol}: {name}")
        
        print("\n🔔 通知配置:")
        print(f"   Server酱: {'已配置' if self.notification.serverchan_key else '未配置'}")
        print(f"   日常推送: {'开启' if self.notification.notify_daily else '关闭'}")
        print(f"   调仓提醒: {'开启' if self.notification.notify_on_rebalance else '关闭'}")
        
        print("\n⚙️ 系统设置:")
        print(f"   缓存: {'开启' if self.system.cache_enabled else '关闭'}")
        print(f"   历史记录: {'开启' if self.system.save_history else '关闭'}")
        print(f"   图表生成: {'开启' if self.system.charts_enabled else '关闭'}")
        print(f"   回测: {'开启' if self.system.backtest_enabled else '关闭'}")
        
        print("=" * 70)


def create_default_config():
    """创建默认配置文件"""
    print("=" * 70)
    print("🛠️ 创建默认配置文件")
    print("=" * 70)
    
    manager = ConfigManager("config.json")
    manager.save()
    manager.print_config()
    
    print("\n✅ 默认配置文件已创建: config.json")
    print("\n提示:")
    print("1. 敏感信息（API密钥等）建议通过环境变量配置")
    print("2. 可以通过修改 config.json 调整策略参数")
    print("3. 配置说明请参考文档")


if __name__ == "__main__":
    create_default_config()
