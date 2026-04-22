#!/usr/bin/env python3
"""
A股主线识别 - 报告生成脚本
读取 analyze_data.py 的分析结果 JSON，调用大模型按 skill.md 分析框架生成报告。

使用方式：
    python generate_report.py [日期]
    示例: python generate_report.py 2026-04-20

配置：
    复制 .env.example 为 .env，填入 API 配置
    cp .env.example .env
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).parent / ".env")

DATA_DIR = Path(__file__).parent / "data"
REPORT_DIR = Path(__file__).parent.parent  # skill_a股主线识别/

SYSTEM_PROMPT = """你是一名中国A股顶级市场结构研究员，拥有15年以上市场交易与盘面分析经验，深度理解以下体系：

- A股题材炒作与主线演化逻辑
- 游资、机构、量化资金的典型行为特征
- 涨停板、连板梯队、趋势中军、补涨股之间的联动关系
- 情绪阶段的冰点、调整、修复、主升、高潮等阶段特征
- 资金抱团、分歧转一致、一致转分歧、强趋势与弱轮动的盘口差异
- 政策驱动、产业催化、事件刺激、海外映射对A股主线形成的影响

你的任务是：基于提供的市场数据和分析结果，识别当前A股市场真正的交易主线，并输出具备交易指导意义的结构化结论。

输出要求：
- 使用专业交易语言，但避免堆砌术语
- 必须先判断结构，再给观点
- 每个结论都要给理由
- 不要写空洞的大而全宏观评论
- 不要把所有热点都说成机会
- 如果市场没有明确主线，要明确指出"主线不清、轮动为主、降低预期"
- 结论必须服务于交易决策，而不是写成新闻摘要

## 严格禁止事项（红线）

- **禁止编造个股名称**：报告中出现的每一只股票必须存在于 limit_up_details 或 anchors 数据中
- **禁止编造事件和数据**：不得虚构海外市场数据（如美股、港股行情）、财报数据（如一季报利润）、机构持仓等数据中不存在的信息
- **催化因素必须来自舆情**：催化因素只能从 pos_titles / neg_titles 中提取，无舆情时标注"数据中无明确催化"即可，不得自行推测编造"""

REPORT_TEMPLATE = """请根据以下市场数据，按照八段式模板生成A股市场主线识别报告。

## 固定输出模板（八段式）

【1.市场环境】先用表格列出三大指数当日行情（指数名称、收盘点位、涨跌幅、成交额），再判断市场整体环境（强势/震荡偏强/震荡偏弱/弱势），给出操作建议（主动进攻/精选参与/控制仓位/观望）
【2.当前主线】严格按 main_lines 中行业涨幅排序输出：涨幅第1名为"核心主线"，涨幅第2名为"第二主线"。行业名称必须使用 main_lines 中的原始名称，不得替换为细分概念。每条主线包含：涨幅数据（取 main_lines 中的 day_change/week_change）、涨停表现（从 limit_up_by_industry 中找对应行业的个股）、催化因素（必须且只能从 limit_up_by_industry 中对应行业的 pos_titles 提取，每条主线最多列3条，内容不得重复，无舆情则标注"数据中无明确催化"）、资金态度（根据成交额和涨停数量判断）
【3.次级热点】列出1个次级热点方向，代表股必须是 limit_up_details 中存在的个股
【4.核心锚点个股】用表格列出5-8只核心个股（排除新股/次新股），列：股票、板块、涨跌幅(%)、成交额(亿)、定位（情绪标的/情绪标的20cm/趋势中军/补涨标的）
【5.当前情绪】只输出阶段名称和一句话定性描述，阶段必须使用 analysis 数据中 emotion.phase 的值（冰点/调整/修复/主升/高潮），不得输出评分维度、打分逻辑等判断过程
【6.主线持续性评估】对每条主线分别评估，基于 analysis 中 sustainability 数据：周涨幅趋势（✅/⚠️）、月线方向（✅/⚠️）、日涨幅强度（✅/⚠️）、正面舆情（✅/⚠️），给出持续性等级（强/较强/一般/弱）
【7.明日观察重点】给出4-5条具体可操作的观察点（看什么、怎么判断）
【8.一句话交易结论】加粗，一段话总结当日核心结论

## 格式要求
- 标题：## 【A 股市场主线识别报告】{date}
- 每段用 ### 【N. 段名】 标题
- 段与段之间用 --- 分隔
- 结尾加风险提示（列出2-3条具体风险），最后加免责声明："以上分析基于公开市场数据推演，不构成任何投资建议，据此操作风险自担。"

## 市场数据和分析结果

```json
{data}
```

请直接输出 Markdown 报告，不要输出其他内容。"""


def generate_report(analysis: dict) -> str:
    date = analysis.get("date", datetime.now().strftime("%Y-%m-%d"))
    data_str = json.dumps(analysis, ensure_ascii=False, indent=2)

    prompt = REPORT_TEMPLATE.format(date=date, data=data_str)

    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    model = os.environ.get("LLM_MODEL", "glm-5.1")

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    return response.choices[0].message.content


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else None

    if not os.environ.get("LLM_API_KEY"):
        print("[ERROR] 请在 .env 中配置 LLM_API_KEY")
        print("  cp .env.example .env")
        sys.exit(1)

    with open(DATA_DIR / "analysis.json", encoding="utf-8") as f:
        analysis = json.load(f)

    if date:
        analysis["date"] = date

    report_date = analysis.get("date", datetime.now().strftime("%Y-%m-%d"))
    model = os.environ.get("LLM_MODEL", "glm-5.1")
    print(f"正在调用 {model} 生成 {report_date} 报告...")

    report = generate_report(analysis)

    filename = f"A股主线识别(auto)-{report_date.replace('-', '')}.md"
    filepath = REPORT_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"=== 报告已生成：{filepath} ===")
    print(f"文件名：{filename}")


if __name__ == "__main__":
    main()
