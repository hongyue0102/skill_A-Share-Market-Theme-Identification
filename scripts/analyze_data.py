#!/usr/bin/env python3
"""
A股主线识别 - 数据分析脚本
读取 fetch_data.py 拉取的 JSON 数据，按主线识别框架进行结构化分析，
输出分析结果 JSON 供 generate_report.py 使用。

使用方式：
    python analyze_data.py [日期]
"""

import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load(name: str) -> list:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def safe_float(val, default=0.0):
    if val in (None, "", "NaN"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def analyze_market_environment(heat, industry_quotes, meta):
    """第一步：判断市场整体环境"""
    h = heat[0] if heat else {}
    up_ratio = safe_float(h.get("UP_NUM_PER"))
    pe_mid = safe_float(h.get("PE_MID"))
    pe_index = h.get("PE_INDEX", "未知")
    up_down_index = h.get("UP_DOWN_INDEX", "未知")
    hot_comment = h.get("HOT_INDEX_COS", "")
    hot_index = safe_float(h.get("HOT_INDEX"))

    total_stocks = meta.get("total_stocks", 0)
    limit_up = meta.get("limit_up_count", 0)
    limit_down = meta.get("limit_down_count", 0)

    # 行业涨跌分布
    rising_industries = [i for i in industry_quotes if safe_float(i.get("INDU_LIMIT_DAY")) > 0]
    falling_industries = [i for i in industry_quotes if safe_float(i.get("INDU_LIMIT_DAY")) < 0]

    # 判断市场状态
    if up_ratio >= 65 and limit_up >= 80:
        status = "强势"
        action = "主动进攻"
    elif up_ratio >= 55 and limit_up >= 40:
        status = "震荡偏强" if hot_index > 50 else "震荡"
        action = "精选参与"
    elif up_ratio >= 40:
        status = "震荡偏弱"
        action = "控制仓位"
    else:
        status = "弱势"
        action = "观望"

    return {
        "status": status,
        "action": action,
        "up_ratio": up_ratio,
        "pe_mid": pe_mid,
        "pe_index": pe_index,
        "up_down_index": up_down_index,
        "hot_comment": hot_comment,
        "hot_index": hot_index,
        "total_stocks": total_stocks,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "rising_industries": len(rising_industries),
        "falling_industries": len(falling_industries),
    }


def analyze_main_lines(industry_quotes, stock_top_rise, abnormal_trade):
    """第二步：识别主线与次级热点"""
    # 行业按日涨幅排序（已排好）
    top_industries = industry_quotes[:5]  # 前5行业
    bottom_industries = industry_quotes[-3:]  # 后3行业

    # 涨停股按板块归类
    limit_up_stocks = [s for s in stock_top_rise
                       if safe_float(s.get("PRICE_LIMIT")) >= 9.9]

    # 从异动数据提取活跃方向
    active_directions = {}
    for r in abnormal_trade:
        name = r.get("STK_SHORT_NAME", "")
        rise = safe_float(r.get("RISE_DROP_RANGE"))
        if rise >= 5:
            active_directions[name] = {
                "code": r.get("STK_CODE", ""),
                "rise": rise,
                "abnorm_type": r.get("ABNORM_TYPE_PAR", ""),
                "amount": safe_float(r.get("TRADE_AMUT")),
            }

    main_lines = []
    for ind in top_industries[:2]:
        day_limit = safe_float(ind.get("INDU_LIMIT_DAY"))
        week_limit = safe_float(ind.get("INDU_LIMIT_1W"))
        name = ind.get("INDU_CLASS_NAME", "")

        main_lines.append({
            "name": name,
            "day_change": day_limit,
            "week_change": week_limit,
            "month_change": safe_float(ind.get("INDU_LIMIT_1M")),
            "compo_num": int(safe_float(ind.get("INDU_COMPO_NUM"))),
        })

    secondary_hot = []
    for ind in top_industries[2:5]:
        secondary_hot.append({
            "name": ind.get("INDU_CLASS_NAME", ""),
            "day_change": safe_float(ind.get("INDU_LIMIT_DAY")),
            "week_change": safe_float(ind.get("INDU_LIMIT_1W")),
        })

    return {
        "main_lines": main_lines,
        "secondary_hot": secondary_hot,
        "bottom_industries": [{"name": i.get("INDU_CLASS_NAME"), "day_change": safe_float(i.get("INDU_LIMIT_DAY"))} for i in bottom_industries],
        "limit_up_stocks": limit_up_stocks,
        "active_directions": active_directions,
    }


def analyze_anchor_stocks(stock_top_rise, stock_value, limit_up_count):
    """第三步：识别龙头、中军、补涨 — 只选最有辨识度的核心锚点（排除新股）"""
    limit_ups = [s for s in stock_top_rise
                 if safe_float(s.get("PRICE_LIMIT")) >= 9.9
                 and safe_float(s.get("PRICE_LIMIT")) < 100]

    # 市值数据转dict
    value_map = {}
    for v in stock_value:
        code = v.get("STK_CODE", "")
        value_map[code] = {
            "total_value": safe_float(v.get("TOT_VALUE_S")),
            "float_value": safe_float(v.get("FLOAT_VALUE_S")),
        }

    # 构建所有涨停股信息
    all_info = []
    for s in limit_ups:
        code = s.get("STK_CODE", "")
        rise = safe_float(s.get("PRICE_LIMIT"))
        amount = safe_float(s.get("TRADE_AMUT"))
        val = value_map.get(code, {})
        total_val = val.get("total_value", 0)

        if total_val > 500e8:
            role = "趋势中军"
        elif rise >= 19.9:
            role = "情绪标的（20cm）"
        else:
            role = "情绪标的" if amount > 10e8 else "补涨标的"

        all_info.append({
            "code": code,
            "name": s.get("STK_SHORT_NAME", ""),
            "rise": rise,
            "amount": amount,
            "total_value": total_val,
            "role": role,
        })

    all_info.sort(key=lambda x: x["amount"], reverse=True)

    # 按角色各取代表性个股，总共 5-8 只
    leaders = [s for s in all_info if s["role"] in ("情绪标的", "情绪标的（20cm）")]
    mid_trend = [s for s in all_info if s["role"] == "趋势中军"]
    followers = [s for s in all_info if s["role"] == "补涨标的"]

    anchors = []
    # 情绪标的取成交额前 3
    anchors.extend(leaders[:3])
    # 趋势中军取前 2
    anchors.extend(mid_trend[:2])
    # 补涨标的取成交额前 2（且不与已选重复）
    anchors.extend(followers[:2])

    anchors.sort(key=lambda x: x["rise"], reverse=True)
    return anchors


def analyze_emotion_cycle(meta, stock_top_rise, abnormal_trade, market_heat):
    """第四步：判断当前情绪（三维加权：广度40%+强度35%+量能25%）"""
    limit_up = meta.get("limit_up_count", 0)
    limit_down = meta.get("limit_down_count", 0)

    # 涨停股列表（排除新股）
    limit_ups = [s for s in stock_top_rise
                 if safe_float(s.get("PRICE_LIMIT")) >= 9.9
                 and safe_float(s.get("PRICE_LIMIT")) < 100]

    h = market_heat[0] if market_heat else {}
    up_ratio = safe_float(h.get("UP_NUM_PER"))

    # === 1. 广度维度（40%）===
    if limit_up >= 90 and limit_down <= 5 and up_ratio >= 65:
        breadth_score = 4
    elif limit_up >= 70 and limit_down <= 10 and up_ratio >= 55:
        breadth_score = 3
    elif limit_up >= 40 and limit_down <= 15 and up_ratio >= 50:
        breadth_score = 2
    elif limit_up >= 20:
        breadth_score = 1
    else:
        breadth_score = 0

    # === 2. 强度维度（35%）===
    broken = 0
    sealed = 0
    for s in limit_ups:
        close = safe_float(s.get("CLOSE_PRICE"))
        high = safe_float(s.get("HIGH_PRICE"))
        if high > 0 and close < high * 0.999:
            broken += 1
        else:
            sealed += 1
    total_limit_up = broken + sealed
    broken_rate = round(broken / total_limit_up * 100, 1) if total_limit_up > 0 else 0

    if broken_rate <= 15:
        strength_score = 4
    elif broken_rate <= 25:
        strength_score = 3
    elif broken_rate <= 40:
        strength_score = 2
    elif broken_rate <= 55:
        strength_score = 1
    else:
        strength_score = 0

    # === 3. 量能维度（25%）===
    hot_index = safe_float(h.get("HOT_INDEX"))
    up_down_index = h.get("UP_DOWN_INDEX", "")

    if hot_index >= 70 and "偏热" in up_down_index:
        volume_score = 4
    elif hot_index >= 55:
        volume_score = 3
    elif hot_index >= 40:
        volume_score = 2
    elif hot_index >= 25:
        volume_score = 1
    else:
        volume_score = 0

    # === 综合加权评分 ===
    weighted = (breadth_score * 0.40 + strength_score * 0.35 + volume_score * 0.25)

    # 映射情绪阶段
    if weighted >= 3.5:
        phase = "高潮"
    elif weighted >= 2.8:
        phase = "主升"
    elif weighted >= 2.0:
        phase = "修复"
    elif weighted >= 1.2:
        phase = "调整"
    else:
        phase = "冰点"

    return {
        "phase": phase,
        "weighted_score": round(weighted, 2),
        "breadth": {"score": breadth_score, "limit_up": limit_up, "limit_down": limit_down, "up_ratio": round(up_ratio, 1)},
        "strength": {"score": strength_score, "sealed": sealed, "broken": broken, "broken_rate": broken_rate},
        "volume": {"score": volume_score, "hot_index": round(hot_index, 1), "sentiment": up_down_index},
    }


def analyze_sustainability(industry_quotes, stock_detail):
    """第五步：评估主线持续性"""
    # 构建行业 → 舆情总量的映射（用证监会行业名匹配）
    industry_sentiment = {}
    for d in stock_detail:
        ind = d.get("sw_industry_q", "")
        if ind:
            if ind not in industry_sentiment:
                industry_sentiment[ind] = {"pos": 0, "neg": 0}
            industry_sentiment[ind]["pos"] += d.get("pos_count", 0)
            industry_sentiment[ind]["neg"] += d.get("neg_count", 0)

    results = []
    for ind in industry_quotes[:3]:
        name = ind.get("INDU_CLASS_NAME", "")
        day = safe_float(ind.get("INDU_LIMIT_DAY"))
        week = safe_float(ind.get("INDU_LIMIT_1W"))
        month = safe_float(ind.get("INDU_LIMIT_1M"))

        score = 0
        reasons = []
        if week > 5:
            score += 1
            reasons.append("周涨幅强势")
        if month > 0:
            score += 1
            reasons.append("月线趋势向上")
        if day > 2:
            score += 1
            reasons.append("日涨幅领先")

        # 舆情匹配（遍历证监会行业寻找包含关系）
        for ind_q, sent in industry_sentiment.items():
            if ind_q and (name in ind_q or ind_q in name):
                if sent["pos"] > 0:
                    score += 1
                    reasons.append(f"正面舆情{sent['pos']}条")
                break

        if score >= 3:
            level = "强"
        elif score >= 2:
            level = "较强"
        elif score >= 1:
            level = "一般"
        else:
            level = "弱"

        results.append({
            "name": name,
            "score": score,
            "level": level,
            "reasons": reasons,
            "day_change": day,
            "week_change": week,
        })

    return results


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else "latest"

    print(f"=== A股主线识别数据分析 ===")

    # 加载数据
    heat = load("market_heat.json")
    index_quotes = load("index_quotes.json")
    industry_quotes = load("industry_quotes.json")
    stock_top_rise = load("stock_top_rise.json")
    abnormal_trade = load("abnormal_trade.json")
    stock_value = load("stock_value.json")
    stock_detail = load("stock_detail.json")
    meta_data = load("meta.json")
    meta = meta_data[0] if meta_data else {}

    # 六步分析
    print("[1/6] 市场环境...")
    env = analyze_market_environment(heat, industry_quotes, meta)

    print("[2/6] 主线识别...")
    lines = analyze_main_lines(industry_quotes, stock_top_rise, abnormal_trade)

    print("[3/6] 核心锚点...")
    anchors = analyze_anchor_stocks(stock_top_rise, stock_value, meta.get("limit_up_count", 0))

    print("[4/6] 情绪周期...")
    emotion = analyze_emotion_cycle(meta, stock_top_rise, abnormal_trade, heat)

    print("[5/6] 持续性评估...")
    sustainability = analyze_sustainability(industry_quotes, stock_detail)

    print("[6/6] 明日观察重点...")

    # 保存分析结果（精简字段，减少大模型 token 消耗）
    slim_industries = []
    for i in industry_quotes:
        slim_industries.append({
            "name": i.get("INDU_CLASS_NAME", ""),
            "day": safe_float(i.get("INDU_LIMIT_DAY")),
            "week": safe_float(i.get("INDU_LIMIT_1W")),
            "month": safe_float(i.get("INDU_LIMIT_1M")),
            "compo_num": int(safe_float(i.get("INDU_COMPO_NUM"))),
        })

    slim_limit_ups = []
    for s in lines.get("limit_up_stocks", []):
        slim_limit_ups.append({
            "code": s.get("STK_CODE", ""),
            "name": s.get("STK_SHORT_NAME", ""),
            "rise": safe_float(s.get("PRICE_LIMIT")),
            "amount": round(safe_float(s.get("TRADE_AMUT")) / 1e8, 2),
        })

    # 按三级行业归类涨停股 + 舆情
    detail_map = {r["code"]: r for r in stock_detail}
    industry_groups = {}
    total_pos = 0
    total_neg = 0
    hot_stocks = []
    for s in slim_limit_ups:
        info = detail_map.get(s["code"], {})
        ind = info.get("sw_industry_s") or info.get("sw_industry_q") or "未知"
        if ind not in industry_groups:
            industry_groups[ind] = []
        industry_groups[ind].append({**s, "pos_count": info.get("pos_count", 0), "neg_count": info.get("neg_count", 0),
                                      "pos_titles": info.get("pos_titles", []), "neg_titles": info.get("neg_titles", [])})
        total_pos += info.get("pos_count", 0)
        total_neg += info.get("neg_count", 0)
        if info.get("pos_count", 0) >= 3 or info.get("pos_index", 0) >= 5:
            hot_stocks.append({"name": s["name"], "code": s["code"],
                               "pos_count": info.get("pos_count", 0), "pos_index": info.get("pos_index", 0),
                               "pos_titles": info.get("pos_titles", [])})
    sorted_industry_groups = sorted(industry_groups.items(), key=lambda x: len(x[1]), reverse=True)
    limit_up_by_industry = [{"industry": ind, "count": len(stocks), "stocks": stocks}
                            for ind, stocks in sorted_industry_groups]

    slim_abnormal = {}
    for k, v in lines.get("active_directions", {}).items():
        slim_abnormal[k] = {
            "code": v.get("code", ""),
            "rise": v.get("rise", 0),
            "type": v.get("abnorm_type", ""),
        }

    slim_index = []
    for idx in index_quotes:
        slim_index.append({
            "name": idx.get("IND_SHORT_NAME", ""),
            "close": safe_float(idx.get("CLOSE_PRICE")),
            "pre_close": safe_float(idx.get("PRE_CLOSE_PRICE")),
            "change_pct": safe_float(idx.get("PRI_LIMIT")),
            "open": safe_float(idx.get("OPEN_PRICE")),
            "high": safe_float(idx.get("HIGH_PRICE")),
            "low": safe_float(idx.get("LOW_PRICE")),
            "amount": round(safe_float(idx.get("TRADE_AMUT")) / 1e8, 1),
        })

    analysis = {
        "date": meta.get("date", date),
        "index_quotes": slim_index,
        "environment": env,
        "main_lines": {
            "main_lines": lines["main_lines"],
            "secondary_hot": lines["secondary_hot"],
            "bottom_industries": lines["bottom_industries"],
        },
        "anchors": anchors,
        "emotion": emotion,
        "sustainability": sustainability,
        "industry_quotes_all": slim_industries,
        "limit_up_details": slim_limit_ups,
        "limit_up_by_industry": limit_up_by_industry,
        "abnormal_summary": slim_abnormal,
        "opinion": {
            "total_pos": total_pos,
            "total_neg": total_neg,
            "hot_stocks": hot_stocks,
        },
    }

    output = DATA_DIR / "analysis.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    print(f"\n=== 分析完成！结果已保存到 {output} ===")
    print(f"市场状态: {env['status']}, 操作建议: {env['action']}")
    print(f"情绪周期: {emotion['phase']}, 综合评分: {emotion['weighted_score']}, 涨停: {emotion['breadth']['limit_up']}家")


if __name__ == "__main__":
    main()
