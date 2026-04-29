#!/usr/bin/env python3
"""
A股主线识别 - 数据获取脚本
从财新数据 API 拉取分析所需的全部数据，保存为 JSON 文件。

使用方式：
    python fetch_data.py [日期]
    示例: python fetch_data.py 2026-04-20

输出目录：data/
"""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SKILL_BASE = Path.home() / ".openclaw/workspace/skills/wh"
SKILLS = {
    "market": SKILL_BASE / "stock-market-information/scripts/api_query.py",
    "basic": SKILL_BASE / "stock-basic-information/scripts/api_query.py",
    "opinion": SKILL_BASE / "public-opinion-stock-index/scripts/api_query.py",
    "index": SKILL_BASE / "index-market-date/scripts/api_query.py",
}

# 申万2021一级行业列表
SW_L1_INDUSTRIES = [
    "美容护理", "石油石化", "电子", "钢铁", "纺织服饰", "食品饮料", "公用事业",
    "计算机", "轻工制造", "通信", "煤炭", "汽车", "家用电器", "有色金属",
    "医药生物", "银行", "建筑材料", "电力设备", "环保", "非银金融", "商贸零售",
    "基础化工", "机械设备", "国防军工", "交通运输", "房地产", "社会服务",
    "传媒", "农林牧渔", "综合", "建筑装饰",
]

# 申万2021二级行业列表
SW_L2_INDUSTRIES = [
    "半导体", "光学光电", "消费电子", "元件", "电子化学品", "其他电子",
    "计算机设备", "IT服务", "软件开发", "计算机应用",
    "通信设备", "通信服务",
    "游戏", "影视院线", "数字媒体", "社交", "出版", "广告营销",
    "化学制药", "中药", "生物制品", "医药商业", "医疗器械", "医疗服务",
    "电池", "光伏设备", "风电设备", "电网设备",
    "通用设备", "专用设备", "仪器仪表", "自动化设备", "金属制品",
    "航空装备", "航天装备", "军工电子",
    "乘用车", "商用车", "汽车零部件", "摩托车及其他",
    "工业金属", "贵金属", "能源金属", "金属新材料",
    "化学制品", "塑料", "橡胶", "农化制品", "非金属材料", "化学原料",
    "火力发电", "水力发电", "光伏发电", "风力发电", "其他发电", "燃气", "环保",
    "煤炭开采", "焦炭",
    "油气开采", "炼化及贸易", "油服工程",
    "国有大型银行", "股份制银行", "城商行",
    "证券", "保险", "多元金融",
    "房地产开发", "房地产服务",
    "房屋建设", "装修装饰", "基建市政", "专业工程",
    "水泥", "玻璃玻纤", "装修建材",
    "普钢", "特钢",
    "种植业", "渔业", "饲料", "养殖", "农产品加工",
    "白酒", "非白酒", "饮料乳品", "零食", "调味品",
    "白色家电", "黑色家电", "小家电",
    "纺织制造", "服装家纺", "饰品",
    "造纸", "家居", "包装印刷", "文娱用品",
    "一般零售", "专业连锁", "贸易", "互联网电商",
    "酒店餐饮", "旅游及景区", "教育", "专业服务",
    "铁路公路", "航空机场", "航运港口", "物流",
    "个护用品", "化妆品", "医疗美容",
    "综合",
    "环境治理", "环保设备", "水务",
]


def safe_float(val, default=0.0):
    if val in (None, "", "NaN"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=0):
    return int(safe_float(val, default))


def call_api(skill_key: str, api_id: str, params: dict) -> dict:
    script = SKILLS[skill_key]
    args = [sys.executable, str(script), api_id]
    for k, v in params.items():
        args.append(f"{k}={v}")
    result = subprocess.run(args, capture_output=True, text=True, cwd=str(script.parent))
    if result.returncode != 0:
        print(f"  [ERROR] {api_id}: {result.stderr.strip()}")
        return {"code": "error", "result": [], "totalCount": 0}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  [ERROR] {api_id}: JSON解析失败")
        return {"code": "error", "result": [], "totalCount": 0}


def fetch_all_pages(skill_key: str, api_id: str, params: dict, show_progress: bool = False) -> list:
    """自动分页拉取全部数据（每页10000条）。"""
    all_results = []
    page = 1
    total = None
    while True:
        params_copy = {**params, "pageNum": str(page), "pageSize": "10000"}
        data = call_api(skill_key, api_id, params_copy)
        results = data.get("result", [])
        if not results:
            break
        all_results.extend(results)
        if page == 1:
            tc = data.get("totalCount")
            if tc is not None:
                total = int(tc)
                total_pages = -(total // -10000) if total > 0 else 1
                print(f"    totalCount={total}, 分{total_pages}页拉取")
        if show_progress and total and page % 2 == 0:
            print(f"    ... 已拉取 {len(all_results)}/{total}")
        if total is not None and len(all_results) >= total:
            break
        page += 1
        time.sleep(0.1)
    return all_results


def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        from datetime import datetime, timedelta
        today = datetime.now()
        if today.weekday() == 5:
            today -= timedelta(days=1)
        elif today.weekday() == 6:
            today -= timedelta(days=2)
        date = today.strftime("%Y-%m-%d")

    t_start = time.time()

    print(f"=== A股主线识别数据获取 ===")
    print(f"目标日期: {date}")

    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    def save(filename: str, data):
        with open(output_dir / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [OK] {filename} ({len(data)} 条)")

    # ========================================
    # 0/8 三大指数日线行情
    # ========================================
    print("[0/8] 三大指数行情...")
    INDEX_NAMES = ["上证指数", "深证成指", "创业板指"]
    index_quotes = []
    for idx_name in INDEX_NAMES:
        data = call_api("index", "getDIndDayQuoByCond-G",
                        {"indShortName": idx_name, "tradeDate": date, "pageNum": "1", "pageSize": "1"})
        results = data.get("result", [])
        if results:
            index_quotes.append(results[0])
    save("index_quotes.json", index_quotes)

    # ========================================
    # 1/8 市场情绪温度
    # ========================================
    print("\n[1/8] 市场情绪温度...")
    heat = fetch_all_pages("market", "getStkHotMarketByCond-G", {"endDate": date})
    save("market_heat.json", heat)

    # ========================================
    # 2/8 申万一级行业涨跌幅（并发查询）
    # ========================================
    print("[2/8] 申万一级行业涨跌幅（31个行业，并发）...")

    def query_industry(name):
        data = call_api("market", "getInduDayQuoByCond-G",
                        {"induClassName": name, "pageNum": "1", "pageSize": "10"})
        return [r for r in data.get("result", [])
                if r.get("INDU_LEVEL") == "1"
                and r.get("REST_TYPE_PAR") == "后复权"
                and r.get("WEIGH_TYPE_PAR") == "流通市值加权"]

    industry_quotes = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(query_industry, name): name for name in SW_L1_INDUSTRIES}
        for f in as_completed(futures):
            industry_quotes.extend(f.result())
    industry_quotes.sort(key=lambda x: float(x.get("INDU_LIMIT_DAY", 0) or 0), reverse=True)
    save("industry_quotes.json", industry_quotes)

    # ========================================
    # 2b/8 申万二级行业涨跌幅（并发查询）
    # ========================================
    print("[2b/8] 申万二级行业涨跌幅（并发）...")

    def query_industry_l2(name):
        data = call_api("market", "getInduDayQuoByCond-G",
                        {"induClassName": name, "pageNum": "1", "pageSize": "10"})
        return [r for r in data.get("result", [])
                if r.get("INDU_LEVEL") == "2"
                and r.get("REST_TYPE_PAR") == "后复权"
                and r.get("WEIGH_TYPE_PAR") == "流通市值加权"]

    industry_l2_quotes = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(query_industry_l2, name): name for name in SW_L2_INDUSTRIES}
        for f in as_completed(futures):
            industry_l2_quotes.extend(f.result())
    industry_l2_quotes.sort(key=lambda x: float(x.get("INDU_LIMIT_DAY", 0) or 0), reverse=True)
    save("industry_l2_quotes.json", industry_l2_quotes)

    # ========================================
    # 3/8 全市场个股日线行情（分页拉取全部）
    # ========================================
    print("[3/8] 全市场个股日线行情...")
    all_quotes = fetch_all_pages("market", "getStkDayQuoByCond-G", {"tradeDate": date}, show_progress=True)
    valid_quotes = [r for r in all_quotes if r.get("PRICE_LIMIT") not in (None, "", "NaN")]
    valid_quotes.sort(key=lambda x: float(x.get("PRICE_LIMIT", 0)), reverse=True)

    save("stock_top_rise.json", valid_quotes[:100])
    save("stock_top_drop.json", valid_quotes[-50:] if len(valid_quotes) > 100 else [])

    limit_up_10 = [r for r in valid_quotes if 9.9 <= float(r.get("PRICE_LIMIT", 0)) < 19.9]
    limit_up_20 = [r for r in valid_quotes if float(r.get("PRICE_LIMIT", 0)) >= 19.9]
    limit_down_10 = [r for r in valid_quotes if -19.9 < float(r.get("PRICE_LIMIT", 0)) <= -9.9]
    limit_down_20 = [r for r in valid_quotes if float(r.get("PRICE_LIMIT", 0)) <= -19.9]

    all_limit_up = limit_up_10 + limit_up_20
    all_limit_down = limit_down_10 + limit_down_20
    print(f"  总成交: {len(valid_quotes)}家")
    print(f"  涨停: {len(all_limit_up)}家 (10%:{len(limit_up_10)}, 20%:{len(limit_up_20)})")
    print(f"  跌停: {len(all_limit_down)}家 (10%:{len(limit_down_10)}, 20%:{len(limit_down_20)})")

    # ========================================
    # 4/8 异动披露
    # ========================================
    print("[4/8] 异动披露...")
    abnormal = fetch_all_pages("market", "getStatTradeDateMainByCond-G", {"endDate": date})
    save("abnormal_trade.json", abnormal)

    # ========================================
    # 5/8 涨停股市值（并发查询）
    # ========================================
    print("[5/8] 涨停股市值...")

    def query_stock_value(r):
        val = call_api("market", "getDStkValueMidByCond-G",
                       {"stkCode": r["STK_CODE"], "endDate": date, "pageNum": "1", "pageSize": "1"})
        return val.get("result", [])

    stock_value = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(query_stock_value, r) for r in all_limit_up[:30]]
        for f in as_completed(futures):
            stock_value.extend(f.result())
    save("stock_value.json", stock_value)

    # ========================================
    # 6/8 涨停股行业分类 + 舆情（并发查询）
    # ========================================
    print("[6/8] 涨停股行业分类 + 舆情...")

    def query_stock_detail(r):
        code = r.get("STK_CODE", "")
        name = r.get("STK_SHORT_NAME", "")
        # 行业分类
        ind_data = call_api("basic", "getDPubComInfo1ByCond-G",
                            {"stkCode": code, "pageNum": "1", "pageSize": "1"})
        ind_res = ind_data.get("result", [{}])
        info = ind_res[0] if ind_res else {}
        # 正面舆情
        pos_data = call_api("opinion", "getIndexLyricalList2ByCond-G",
                            {"code": code, "indexDate": date, "pageNum": "1", "pageSize": "5"})
        # 负面舆情
        neg_data = call_api("opinion", "getIndexLyricalList1ByCond-G",
                            {"code": code, "indexDate": date, "pageNum": "1", "pageSize": "5"})

        pos_results = pos_data.get("result", [])
        neg_results = neg_data.get("result", [])
        pos_count = sum(safe_int(p.get("ALL_REPORT_COUNT")) for p in pos_results)
        neg_count = sum(safe_int(p.get("ALL_REPORT_COUNT")) for p in neg_results)
        pos_index = max((safe_float(p.get("TODAY_INDEX")) for p in pos_results), default=0)
        neg_index = max((safe_float(p.get("TODAY_INDEX")) for p in neg_results), default=0)

        return {
            "code": code,
            "name": name,
            "sw_industry_s": info.get("INDU_CLASS_NAME_S", ""),
            "sw_industry_q": info.get("INDU_CLASS_NAME_Q", ""),
            "sw_industry_z": info.get("INDU_CLASS_NAME_Z", ""),
            "pos_count": pos_count,
            "neg_count": neg_count,
            "pos_index": pos_index,
            "neg_index": neg_index,
            "pos_titles": [p.get("REGULA_TITLE", "") or p.get("TITLE", "") for p in pos_results if p.get("REGULA_TITLE") or p.get("TITLE")],
            "neg_titles": [p.get("REGULA_TITLE", "") or p.get("TITLE", "") for p in neg_results if p.get("REGULA_TITLE") or p.get("TITLE")],
        }

    stock_detail = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(query_stock_detail, r) for r in all_limit_up]
        for f in as_completed(futures):
            stock_detail.append(f.result())
    save("stock_detail.json", stock_detail)

    # ========================================
    # 7/8 大宗交易
    # ========================================
    print("[7/8] 大宗交易...")
    block = fetch_all_pages("market", "getDStkBlockTradeByCond-G", {"tradeDate": date})
    save("block_trade.json", block)

    # 元数据
    meta = {
        "date": date,
        "total_stocks": len(valid_quotes),
        "limit_up_count": len(all_limit_up),
        "limit_down_count": len(all_limit_down),
    }
    save("meta.json", [meta])

    elapsed = time.time() - t_start
    print(f"\n=== 完成！日期: {date}, 总成交: {len(valid_quotes)}, 涨停: {len(all_limit_up)}, 跌停: {len(all_limit_down)} ===")
    print(f"总耗时: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
