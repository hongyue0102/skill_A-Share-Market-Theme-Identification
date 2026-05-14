# A股主线识别 Skill — 使用说明

## 功能

每日自动生成 A股市场主线识别报告，包含市场环境、主线方向、核心个股、情绪周期。

## 处理流程

```
Step 1: fetch_data.py (取数 ~2min) → Step 2: analyze_data.py (分析 <1s) → Step 3: Agent LLM 自行生成报告
```

## 使用方式

### 1. 环境准备

```bash
# 安装依赖
pip install -r scripts/requirements.txt
```

### 2. 执行步骤

```bash
cd scripts

# Step 1: 数据获取
python fetch_data.py           # 不传日期则默认最近一个交易日
# python fetch_data.py 2026-04-20  # 或指定日期

# Step 2: 数据分析
python analyze_data.py

# Step 3: 报告生成
python generate_report.py      # 输出结构化 prompt，由 Agent LLM 读取后自行生成报告
```

### 3. 输出

- 中间数据：`scripts/data/*.json`
- 分析结果：`scripts/data/analysis.json`
- 最终报告：由 Agent LLM 生成并保存到 skill 根目录

## 数据源依赖

本 skill 依赖财新数据平台取数 skill 集合，从 https://yun.ccxe.com.cn/data/Skills 获取。
若运行 fetch_data.py 时提示"数据源 skill 未安装"，请前往上述地址下载。

实际用到的 skill（4个）：

| Skill | 用途 | 调用的 API |
|-------|------|-----------|
| stock-market-information | 行情、行业涨跌（一级+二级）、情绪温度、异动、市值、大宗交易 | getStkHotMarketByCond-G, getInduDayQuoByCond-G, getStkDayQuoByCond-G, getStatTradeDateMainByCond-G, getDStkValueMidByCond-G, getDStkBlockTradeByCond-G |
| stock-basic-information | 个股行业分类（申万三级） | getDPubComInfo1ByCond-G |
| public-opinion-stock-index | 正面/负面舆情指数 | getIndexLyricalList1ByCond-G, getIndexLyricalList2ByCond-G |
| index-market-date | 三大指数日线行情 | getDIndDayQuoByCond-G |

各 skill 的 `scripts/.env` 中需配置 `CXDA_USER_KEY`。

## 报告模板（六段式）

1. **市场环境** — 指数强弱、涨跌家数、成交额变化、情绪判断
2. **当前主线** — 核心主线（综合得分第1）+ 第二主线（综合得分第2），综合得分 = 日涨幅排名分(30%) + 涨停集中度得分(30%) + 周涨幅趋势分(20%) + 月涨幅趋势分(20%)。区分"资金攻击型"（涨停>=3家）和"趋势/防御型"（涨停为0），含涨幅、涨停股数量、催化因素（最多3条）、资金态度
3. **次级热点** — 1个次级方向（优先选资金攻击型）
4. **核心锚点个股** — 5-8只（仅从核心主线和第二主线的涨停股中选取，排除新股），标注定位（情绪标的/趋势中军/补涨标的）
5. **当前情绪** — 阶段名称（冰点/调整/修复/主升/高潮）+ 一句话定性
6. **一句话交易结论** — 核心操作建议

## 文件结构

```
skill_a股主线识别/
├── SKILL.md                    # Skill 定义（分析框架、执行步骤和输出模板）
├── prompts.md                  # 本文件：使用说明
├── .gitignore
├── A股主线识别(auto)-*.md      # 生成的报告
├── A股主线识别(auto)-*_示例.md  # 示例报告
└── scripts/
    ├── requirements.txt        # Python 依赖
    ├── fetch_data.py           # 数据获取（含前置检查 + 一二级行业涨跌幅）
    ├── analyze_data.py         # 数据分析（二级行业综合评分 + 涨停集中度）
    ├── generate_report.py      # 输出结构化 prompt（供 Agent LLM 使用）
    └── data/                   # 中间数据（不提交）
```
