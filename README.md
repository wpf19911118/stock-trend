# 股票趋势跟踪机器人

基于 Python 的中长线双指数趋势跟踪与推送机器人。

## 功能特点

- 📊 自动获取沪深300、中证500日线数据
- 📈 双均线策略（20日 & 60日）判断多空趋势
- ⏰ 每天下午收盘后自动推送趋势分析到微信
- ☁️ 支持 GitHub Actions 24小时自动运行

## 快速开始

### 1. 准备 Server酱 Key

1. 访问 [pushplus.plus](https://www.pushplus.plus/)
2. 微信扫码登录
3. 获取你的 token（格式：`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`）

### 2. 配置 GitHub Secrets

1. Fork 本仓库
2. 进入 Settings → Secrets and variables → Actions
3. 新建 Secret:
   - Name: `SERVERCHAN_KEY`
   - Value: 你的 Server酱 token

### 3. 自动运行

- 每天北京时间 15:30（A股收盘后）自动运行
- 也可以手动触发：进入 Actions → Daily Stock Trend Monitor → Run workflow

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export SERVERCHAN_KEY="你的token"

# 运行
python stock_trend.py
```

## 策略说明

- **金叉**：20日均线从下方穿过60日均线 → 上升趋势 → 建议持仓待涨
- **死叉**：20日均线从上方穿过60日均线 → 下降趋势 → 建议空仓观望
- **趋势持续时间**：根据当前动量（近20日涨幅）估算

## 文件结构

```
stock_trend_monitor/
├── stock_trend.py      # 主程序
├── config.py           # 配置文件模板
├── requirements.txt    # Python 依赖
├── .github/
│   └── workflows/
│       └── daily_trend.yml  # GitHub Actions 配置
└── results/            # 运行结果（自动生成）
```

## 注意事项

- 本工具仅供个人学习参考，不构成投资建议
- 股市有风险，投资需谨慎
- 数据来源：akshare（免费开源库）
