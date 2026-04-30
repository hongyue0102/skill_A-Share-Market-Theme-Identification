# A股市场主线识别

每日自动生成 A股市场主线识别报告，包含三大指数行情、主线方向、核心个股、情绪周期、持续性评估和明日观察重点。

## 处理流程

```
fetch_data.py (取数) → analyze_data.py (分析) → generate_report.py (大模型生成报告)
      ~2min                  <1s                         ~10s
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### 2. 配置数据源

从 https://yun.ccxe.com.cn/data/Skills 获取以下 skill 并安装到本地：

- `index-market-date`
- `stock-market-information`
- `stock-basic-information`
- `public-opinion-stock-index`

各 skill 的 `scripts/.env` 中需配置 `CXDA_USER_KEY`。

### 3. 配置大模型

```bash
cp scripts/.env.example scripts/.env
# 编辑 .env 填入 LLM_API_KEY
```

### 4. 运行

```bash
cd scripts

# 指定日期
python fetch_data.py 2026-04-17
python analyze_data.py 2026-04-17
python generate_report.py 2026-04-17

# 不传日期则默认取最近一个交易日
python fetch_data.py
python analyze_data.py
python generate_report.py
```

### 5. 输出

- 中间数据：`scripts/data/*.json`
- 分析结果：`scripts/data/analysis.json`
- 最终报告：`A股主线识别(auto)-YYYYMMDD.md`

## 报告结构（六段式）

| 段落 | 内容 |
|------|------|
| 1. 市场环境 | 三大指数行情表格 + 环境判断 + 操作建议 |
| 2. 当前主线 | 1-2条主线（基于二级行业涨幅+涨停集中度综合评分），区分资金攻击型/趋势防御型，含涨停股、催化因素、资金态度 |
| 3. 次级热点 | 1个次级方向 |
| 4. 核心锚点个股 | 5-8只，仅从核心主线和第二主线的涨停股中选取，排除新股，标注情绪标的/情绪标的20cm/趋势中军/补涨标的 |
| 5. 情绪周期 | 冰点/调整/修复/主升/高潮 |
| 6. 一句话交易结论 | 核心操作建议 |

## 大模型配置

支持 OpenAI 兼容接口，在 `scripts/.env` 中配置：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | 是 | - | API Key |
| `LLM_BASE_URL` | 否 | 智谱 | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 否 | `glm-5.1` | 模型名称 |

支持任何 OpenAI 兼容接口的大模型，配置 `LLM_BASE_URL` 和 `LLM_MODEL` 即可。常见选择：
- 智谱：`glm-5.1`、`glm-4-plus`
- DeepSeek：`deepseek-chat`（base_url 改为 `https://api.deepseek.com/v1`）
- 通义：`qwen-plus`（base_url 改为 `https://dashscope.aliyuncs.com/compatible-mode/v1`）
- OpenAI：`gpt-4o`（base_url 改为 `https://api.openai.com/v1`）
- Claude：`claude-sonnet-4-6`（通过 OpenAI 兼容代理）
