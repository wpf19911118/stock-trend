# 股票趋势跟踪机器人 V4.0

基于 Python 的专业级多因子中长线投资决策系统，支持 A股 + 美股，具备Web界面、投资组合管理、智能告警、风险管理等完整功能。

## 🎉 V4.0 新特性

### 🌐 Web界面仪表板
- **实时数据展示**: 评分、趋势、宏观指标
- **响应式设计**: 支持电脑、平板、手机访问
- **交互式操作**: 刷新数据、查看详情
- **可视化图表**: 评分趋势、估值分位

### 💼 投资组合管理
- **持仓跟踪**: 自动记录买入卖出
- **收益计算**: 已实现/未实现盈亏
- **调仓管理**: 一键调仓到目标配置
- **交易记录**: 完整历史交易流水

### 🔔 智能告警系统
- **多维度监控**: 评级变化、极值评分、风险事件
- **分级告警**: Critical/High/Medium/Low/Info
- **冷却机制**: 避免重复告警
- **多渠道通知**: 微信、邮件、Webhook

### ⚠️ 风险管理
- **风险评估**: 波动率、最大回撤、VaR
- **止损止盈**: 固定止损、移动止损
- **仓位控制**: 风险等级自适应仓位
- **Beta值**: 系统性风险评估

### 📊 回测验证
- **策略验证**: 对比买入持有收益
- **绩效分析**: 夏普比率、最大回撤
- **交易统计**: 胜率、调仓频率
- **净值曲线**: 可视化策略表现

---

## 快速开始

### 1. 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或使用国内镜像加速
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 配置环境变量

```bash
# Linux/Mac
export SERVERCHAN_KEY="你的pushplus_token"

# Windows
set SERVERCHAN_KEY=你的pushplus_token
```

### 3. 运行方式

#### 方式1: 命令行分析
```bash
# 运行完整分析
python stock_monitor_v2.py
```

#### 方式2: Web界面（推荐）
```bash
# 启动Web服务
python web_dashboard.py

# 访问 http://localhost:5000
```

#### 方式3: GitHub Actions自动化
- Fork 本仓库
- 配置 Secrets: `SERVERCHAN_KEY`
- 每天自动运行并推送结果

---

## 核心功能详解

### 📊 多因子评分系统

| 维度 | 权重 | 核心指标 | 评分标准 |
|-----|------|---------|---------|
| **技术面** | 30% | MA/ MACD/ RSI/ 布林带 | 均线排列、动量确认 |
| **估值面** | 35% | PE/PB历史分位、股债性价比 | <30%分位满分 |
| **宏观面** | 25% | 利率/VIX/美元指数 | 降息周期利好 |
| **情绪面** | 10% | 短期动量/波动率 | 低波动加分 |

### 📈 评级与仓位

| 总分 | 评级 | 建议仓位 | 操作建议 |
|-----|------|---------|---------|
| 80-100 | 🚀 A级 | 90-100% | 强烈买入 |
| 65-79 | 📈 B级 | 70-90% | 买入 |
| 50-64 | ➡️ C级 | 50-70% | 持有 |
| 35-49 | ⚠️ D级 | 30-50% | 观望 |
| 0-34 | 📉 E级 | 0-30% | 卖出 |

---

## 文件结构

```
stock_trend_monitor/
├── 📊 Core Modules (核心模块)
│   ├── stock_monitor_v2.py       # 主程序
│   ├── market_data.py            # 市场数据获取
│   ├── scoring_system_v2.py      # 多因子评分系统
│   └── valuation_analysis.py     # 估值分析
│
├── 🌐 Phase 4 - Web & Advanced (高级功能)
│   ├── web_dashboard.py          # Web界面 [V4.0]
│   ├── portfolio_manager.py      # 投资组合管理 [V4.0]
│   ├── alert_system.py           # 智能告警系统 [V4.0]
│   ├── risk_manager.py           # 风险管理 [V4.0]
│   └── config_manager.py         # 配置管理 [V3.0]
│
├── 📈 Phase 3 - Analysis (分析模块)
│   ├── backtest.py               # 回测验证 [V3.0]
│   ├── visualization.py          # 可视化图表 [V3.0]
│   ├── score_history.py          # 历史追踪 [V3.0]
│   └── data_cache.py             # 数据缓存 [V2.0]
│
├── 📋 Configuration (配置)
│   ├── config_template.py        # 配置模板
│   ├── requirements.txt          # 依赖列表
│   └── config.json               # 运行配置（自动生成）
│
├── 📚 Documentation (文档)
│   ├── README.md                 # 本文件
│   ├── INVESTMENT_PLAN.md        # 投资规划
│   ├── PHASE2_REPORT.md          # Phase 2报告
│   ├── PHASE3_REPORT.md          # Phase 3报告
│   └── PHASE4_REPORT.md          # Phase 4报告 [NEW]
│
├── 🔧 Automation (自动化)
│   └── .github/workflows/
│       └── daily_analysis.yml    # GitHub Actions
│
└── 📁 Output (输出目录)
    ├── results/                  # 分析结果
    │   ├── analysis_*.json       # 结构化数据
    │   ├── report_*.html         # HTML报告
    │   └── report_*.txt          # 文本报告
    │
    ├── results/charts/           # 可视化图表
    │   ├── score_trend_*.png     # 评分趋势
    │   ├── valuation_*.png       # 估值图
    │   └── backtest_*.png        # 回测图
    │
    ├── results/history/          # 历史数据
    │   └── *_history.json        # 评分历史
    │
    └── cache/                    # 数据缓存
```

---

## 使用指南

### Web界面

```bash
# 启动服务
python web_dashboard.py

# 访问地址
# - 本地: http://localhost:5000
# - 局域网: http://你的IP:5000
```

**功能特点：**
- 📊 实时评分展示
- 📈 资产对比
- 🔍 详情查询
- 🔄 手动刷新数据

### 投资组合管理

```python
from portfolio_manager import PortfolioManager

# 创建管理器
portfolio = PortfolioManager()

# 初始化资金
portfolio.initialize(1000000)

# 买入
portfolio.buy("000300", "沪深300", "A股", 10000, 3.5, reason="建仓")

# 卖出
portfolio.sell("000300", shares=5000, price=3.9, reason="获利了结")

# 查看报告
portfolio.print_portfolio_report()
```

### 智能告警

```python
from alert_system import AlertManager

# 创建告警管理器
alert_mgr = AlertManager()

# 检查告警
alerts = alert_mgr.check_alerts(
    symbol="000300",
    name="沪深300",
    score=88,
    score_change_7d=15
)

# 查看报告
alert_mgr.print_alert_report()
```

### 风险管理

```python
from risk_manager import RiskManager

# 创建风险管理器
risk_mgr = RiskManager()

# 风险评估
metrics = risk_mgr.assess_risk(
    symbol="000300",
    name="沪深300",
    prices=price_list
)

# 检查止损
triggered, reason = risk_mgr.check_stop_loss(current_price, avg_cost)
```

---

## 配置说明

### 基础配置

复制 `config_template.py` 为 `config.py`:

```python
# 监控标的
A_SHARE_INDICES = {
    "000300": "沪深300",
    "000905": "中证500",
    # 添加更多...
}

# 评分权重
WEIGHTS = {
    "technical": 0.30,
    "valuation": 0.35,
    "macro": 0.25,
    "sentiment": 0.10,
}
```

### 高级配置

使用配置管理器:

```python
from config_manager import ConfigManager

config = ConfigManager()

# 调整权重
config.update_strategy_weights({
    'technical': 0.25,
    'valuation': 0.40
})

# 添加标的
config.add_stock("399006", "创业板指", "A股")

# 启用功能
config.enable_feature("backtest")
config.enable_feature("charts")
```

---

## 监控标的

### 默认配置

| 市场 | 代码 | 名称 | 类型 |
|-----|------|------|------|
| A股 | 000300 | 沪深300 | 大盘 |
| A股 | 000905 | 中证500 | 中盘 |
| 美股 | ^IXIC | 纳斯达克 | 科技 |
| 美股 | ^GSPC | 标普500 | 大盘 |

### 可添加标的

- A股: 创业板指(399006)、上证50(000016)等
- 美股: 道琼斯(^DJI)、纳斯达克100(QQQ)等
- ETF: 各指数ETF基金

---

## 版本演进

| 版本 | 时间 | 主要功能 |
|-----|------|---------|
| **V1.0** | 2026-03-05 | 双均线策略，A股监控 |
| **V2.0** | 2026-03-06 | 多因子评分，美股支持，估值分析 |
| **V3.0** | 2026-03-07 | 回测验证，可视化图表，历史追踪 |
| **V4.0** | 2026-03-07 | **Web界面，投资组合，智能告警，风险管理** |

---

## 完整功能清单

### ✅ 数据分析
- [x] A股/美股数据获取
- [x] 宏观数据（利率/VIX/汇率）
- [x] PE/PB估值分析
- [x] 股债性价比计算
- [x] 历史分位计算

### ✅ 评分系统
- [x] 四维度12+指标
- [x] 动态权重调整
- [x] 分级评分（A/B/C/D/E）
- [x] 仓位建议生成

### ✅ 回测验证
- [x] 策略回测
- [x] 买入持有对比
- [x] 绩效分析（夏普/回撤）
- [x] 交易统计

### ✅ 可视化
- [x] 评分趋势图
- [x] 估值分位图
- [x] 回测对比图
- [x] 多资产对比
- [x] HTML图表画廊

### ✅ Web界面
- [x] Flask Web服务
- [x] 响应式设计
- [x] 实时数据API
- [x] 移动端适配

### ✅ 投资组合
- [x] 持仓跟踪
- [x] 交易记录
- [x] 盈亏计算
- [x] 调仓管理

### ✅ 智能告警
- [x] 多级告警
- [x] 冷却机制
- [x] 微信推送
- [x] 告警历史

### ✅ 风险管理
- [x] 波动率分析
- [x] 最大回撤
- [x] VaR计算
- [x] 止损止盈
- [x] 仓位建议

---

## 注意事项

⚠️ **风险提示**

- 本系统仅供个人学习研究，**不构成投资建议**
- 历史回测不代表未来表现
- 股市有风险，投资需谨慎
- 请根据自身风险承受能力决策
- 美股数据有15分钟延迟（免费数据源）

⚠️ **使用建议**

- 首次使用建议先用模拟盘测试
- 定期检查策略有效性
- 关注宏观环境变化
- 不要过度交易（建议季度调仓）

---

## 技术栈

- **Python 3.11+**
- **数据处理**: Pandas, NumPy
- **数据源**: Akshare, yfinance
- **Web框架**: Flask
- **可视化**: Matplotlib
- **自动化**: GitHub Actions

---

## 许可证

MIT License

**免责声明**: 本程序仅供学习交流使用，作者不对使用本程序产生的任何投资损失负责。

---

## 联系与反馈

如有问题或建议，欢迎提交 Issue。

**当前版本**: V4.0  
**最后更新**: 2026-03-07  
**状态**: ✅ 生产就绪
