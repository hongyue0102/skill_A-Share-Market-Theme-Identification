# A股市场主线识别

每日 A股市场主线识别报告，包含三大指数行情、主线方向、核心个股、情绪周期。

## 处理流程

```
Step 1: fetch_data.py (取数 ~2min) → Step 2: analyze_data.py (分析 <1s) → Step 3: Agent LLM 自行生成报告
```

- `fetch_data.py` 和 `analyze_data.py` 由脚本自动完成
- `generate_report.py` 输出结构化 prompt（系统指令 + 分析数据 + 报告模板），由宿主环境的 Agent LLM 读取后自行生成报告，**不调用任何外部 LLM API**

## 快速开始

### 1. 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### 2. 配置数据源

从 https://yun.ccxe.com.cn/data/Skills 获取以下 skill 并安装到本地 `~/.openclaw/workspace/skills/wh/` 目录：

- `index-market-date`
- `stock-market-information`
- `stock-basic-information`
- `public-opinion-stock-index`

各 skill 的 `scripts/.env` 中需配置 `CXDA_USER_KEY`。

### 3. 运行

```bash
cd scripts

# Step 1: 数据获取
python fetch_data.py           # 不传日期则默认最近一个交易日
# python fetch_data.py 2026-04-17  # 或指定日期

# Step 2: 数据分析
python analyze_data.py

# Step 3: 报告生成
python generate_report.py      # 输出结构化 prompt，由 Agent LLM 读取后自行生成报告
```

### 4. 输出

- 中间数据：`scripts/data/*.json`
- 分析结果：`scripts/data/analysis.json`
- 最终报告：由 Agent LLM 生成

## 综合评分公式（v3.1）

```
综合得分 = 日涨幅排名分(30%) + 涨停集中度得分(30%) + 周涨幅趋势分(20%) + 月涨幅趋势分(20%)
```

- **日涨幅排名分**：二级行业涨幅排名，第1名100分，依次递减
- **涨停集中度**：涨停股最多的二级行业100分，其他按比例
- **周/月涨幅趋势分**：涨幅占全市场最高行业的比例
- 涨停≥3家标记为"资金攻击型"，涨停为0标记为"趋势/防御型"

## 报告结构（六段式）

| 段落 | 内容 |
|------|------|
| 1. 市场环境 | 三大指数行情表格 + 环境判断 + AI结论 |
| 2. 当前主线 | 核心主线 + 第二主线（四维综合评分），区分资金攻击型/趋势防御型，含涨停股、催化因素、资金态度 |
| 3. 次级热点 | 1个次级方向（优先选资金攻击型） |
| 4. 核心锚点个股 | 5-8只，仅从核心主线和第二主线的涨停股中选取，排除新股，标注情绪标的/情绪标的20cm/趋势中军/补涨标的 |
| 5. 情绪周期 | 冰点/调整/修复/主升/高潮 |
| 6. 一句话AI结论 | 核心操作建议 |
