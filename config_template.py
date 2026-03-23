#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件模板
使用前请复制为 config.py 并填入你的配置
"""

import os

# ==================== 推送配置 ====================
# Server酱 Token（用于微信推送）
# 获取地址: https://www.pushplus.plus/
SERVERCHAN_KEY = ""

# Pushplus Webhook（可选）
PUSHPLUS_WEBHOOK = ""

# ==================== 监控标的配置 ====================
# A股指数
A_SHARE_INDICES = {
    "000300": "沪深300",
    "000905": "中证500",
    # 可添加更多
    # "000016": "上证50",
    # "399006": "创业板指",
}

# 美股指数
US_INDICES = {
    "^IXIC": "纳斯达克",
    "^GSPC": "标普500",
    # 可添加更多
    # "^DJI": "道琼斯",
    # "QQQ": "纳斯达克100ETF",
}

# ==================== 评分权重配置 ====================
# 可根据个人偏好调整（默认已优化）
WEIGHTS = {
    "technical": 0.30,    # 技术面权重
    "valuation": 0.35,    # 估值面权重
    "macro": 0.25,        # 宏观面权重
    "sentiment": 0.10,    # 情绪面权重
}

# ==================== 评分阈值配置 ====================
# 可根据市场环境调整
THRESHOLDS = {
    # 评级阈值
    "grade_A": 80,   # 强烈买入
    "grade_B": 65,   # 买入
    "grade_C": 50,   # 持有
    "grade_D": 35,   # 观望
    
    # 估值阈值 (A股)
    "a_share_pe_low": 10,
    "a_share_pe_high": 25,
    "a_share_pb_low": 1.0,
    "a_share_pb_high": 2.5,
    
    # 估值阈值 (美股)
    "us_pe_low": 15,
    "us_pe_high": 30,
    "us_pb_low": 2.0,
    "us_pb_high": 4.0,
    
    # 股债性价比
    "risk_premium_high": 4.0,   # 极佳
    "risk_premium_good": 3.0,   # 良好
    "risk_premium_fair": 2.0,   # 一般
}

# ==================== 调仓配置 ====================
REBALANCE_CONFIG = {
    "check_interval_days": 90,  # 调仓检查周期（季度）
    "min_position": 0.0,        # 最小仓位
    "max_position": 1.0,        # 最大仓位
    "rebalance_threshold": 2,   # 评级变化超过多少级才触发调仓
}

# ==================== 数据缓存配置 ====================
CACHE_CONFIG = {
    "enable_cache": True,
    "cache_dir": "./cache",
    "cache_expire_hours": 6,  # 缓存过期时间
}
