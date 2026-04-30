# A股主线识别 Skill — 使用说明

## 功能

每日自动生成 A股市场主线识别报告，包含市场环境、主线方向、核心个股、情绪周期、持续性评估和明日观察重点。

## 处理流程

```
fetch_data.py (取数) → analyze_data.py (分析) → generate_report.py (大模型生成报告)
      ~15min                  <1s                         ~10s
```

## 使用方式

### 1. 环境准备

```bash
# 安装依赖
pip install -r scripts/requirements.txt

# 配置大模型 API
cp scripts/.env.example scripts/.env
# 编辑 .env 填入 LLM_API_KEY
```

### 2. 一键执行

```bash
cd scripts

# 指定日期
python fetch_data.py 2026-04-20
python analyze_data.py 2026-04-20
python generate_report.py 2026-04-20

# 不传日期则默认取最近一个交易日
python fetch_data.py
python analyze_data.py
python generate_report.py
```

### 3. 输出

- 中间数据：`scripts/data/*.json`
- 分析结果：`scripts/data/analysis.json`
- 最终报告：`A股主线识别(auto)-YYYYMMDD.md`

## 配置说明

### 大模型配置（scripts/.env）

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | 是 | - | API Key |
| `LLM_BASE_URL` | 否 | 智谱 | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 否 | `glm-5.1` | 模型名称 |

支持的模型（任选一个）：
- 智谱：`glm-5.1`、`glm-4-plus`
- DeepSeek：`deepseek-chat`（base_url 改为 `https://api.deepseek.com/v1`）
- 通义：`qwen-plus`（base_url 改为 `https://dashscope.aliyuncs.com/compatible-mode/v1`）

### 数据源依赖

本 skill 依赖 [OpenClaw](https://openclaw.com) 财新数据 skill 集合，从 https://yun.ccxe.com.cn/data/Skills 获取。

实际用到的 skill（3个）：

| Skill | 用途 | 调用的 API |
|-------|------|-----------|
| stock-market-information | 行情、行业涨跌（一级+二级）、情绪温度、异动、市值、大宗交易 | getStkHotMarketByCond-G, getInduDayQuoByCond-G, getStkDayQuoByCond-G, getStatTradeDateMainByCond-G, getDStkValueMidByCond-G, getDStkBlockTradeByCond-G |
| stock-basic-information | 个股行业分类（申万三级） | getDPubComInfo1ByCond-G |
| public-opinion-stock-index | 正面/负面舆情指数 | getIndexLyricalList1ByCond-G, getIndexLyricalList2ByCond-G |

各 skill 的 `scripts/.env` 中需配置 `CXDA_USER_KEY`。

## 报告模板（六段式）

1. **市场环境** — 指数强弱、涨跌家数、成交额变化、情绪判断
2. **当前主线** — 核心主线（综合得分第1）+ 第二主线（综合得分第2），综合得分 = 二级行业涨幅排名分(20%) + 涨停集中度得分(80%)。区分"资金攻击型"（涨停>=3家）和"趋势/防御型"（涨停为0），含涨幅、涨停股数量、催化因素（最多3条）、资金态度
3. **次级热点** — 1个次级方向（优先选资金攻击型）
4. **核心锚点个股** — 5-8只（仅从核心主线和第二主线的涨停股中选取，排除新股），标注定位（情绪标的/趋势中军/补涨标的）
5. **当前情绪** — 阶段名称（冰点/调整/修复/主升/高潮）+ 一句话定性
6. **一句话交易结论** — 核心操作建议

## 文件结构

```
skill_a股主线识别/
├── skill.md                    # Skill 定义（分析框架和输出模板）
├── prompts.md                  # 本文件：使用说明
├── .gitignore
├── A股主线识别(auto)-*.md      # 生成的报告
├── A股主线识别(auto)-*_示例.md  # 示例报告
└── scripts/
    ├── .env.example            # 大模型配置模板
    ├── .env                    # 大模型配置（不提交）
    ├── requirements.txt        # Python 依赖
    ├── fetch_data.py           # 数据获取（含一级行业 + 二级行业涨跌幅）
    ├── analyze_data.py         # 数据分析（二级行业综合评分 + 涨停集中度）
    ├── generate_report.py      # 报告生成（调用大模型）
    └── data/                   # 中间数据（不提交）
```
