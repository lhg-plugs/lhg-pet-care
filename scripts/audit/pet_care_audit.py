#!/usr/bin/env python3
"""lhg-pet-care 确定性养护计划审计：49 条规则，零第三方依赖。

扫描交付目录（养护计划 *.md、profile*.json），输出 JSON 与人类可读报告；
有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

用法：
    python3 pet_care_audit.py --target <目录> [--format json|text] [--fail-on blocker|warning|nit]

规则文案均为本项目原创（详见仓库 ATTRIBUTION.md）。
兽医知识口径：疫苗种类、驱虫节拍、禁忌食物等为公开兽医常识的独立整理，
具体医疗方案请以执业兽医意见为准。

健康声明：本脚本输出仅供日常养护参考，不是兽医诊断；请遵医嘱。
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

VERSION = "1.0.0"
TOOL = "lhg-pet-care/pet-audit"

SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build"}

DISCLAIMER_RE = re.compile(r"仅供.*参考")
DOCTOR_RE = re.compile(r"遵医嘱|咨询兽医|问兽医")
NOT_VET_RE = re.compile(r"不是兽医诊断|不能替代.*诊疗|不能替代兽医")
CURE_PROMISE_RE = re.compile(r"保证治愈|包治|药到病除|百分百有效|100%有效")

# ---------------------------------------------------------------- 数据模型
class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line", "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line, snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError:
        return None
    except OSError:
        return ""


def collect(target):
    docs, profiles = [], []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            p = os.path.join(root, f)
            fl = f.lower()
            if fl.endswith(".md"):
                docs.append(p)
            elif fl.startswith("profile") and fl.endswith(".json"):
                profiles.append(p)
    return {"docs": sorted(docs), "profiles": sorted(profiles)}


# ---------------------------------------------------------------- 规则注册表
RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


def _mk(rule_id, path, line, snippet):
    r = _RULE_BY_ID[rule_id]
    return Finding(r["id"], r["severity"], r["category"], r["title"],
                   path, line, snippet[:160], r["detail"])


def _lines(text):
    return text.split("\n")


def _iter_hits(text, patterns):
    """yield (lineno, line, pattern) 命中行。patterns: [(name, compiled_re)]"""
    for i, ln in enumerate(_lines(text), 1):
        for name, rx in patterns:
            if rx.search(ln):
                yield i, ln, name


# ---------------------------------------------------------------- 自建表
# 禁忌食物：(rule_id, 级别, 关键词正则)
FOOD_BLOCKER = [
    ("PC-FOOD-001", re.compile(r"巧克力|可可(粉|脂|豆)?")),
    ("PC-FOOD-002", re.compile(r"咖啡|咖啡因|浓茶")),
    ("PC-FOOD-003", re.compile(r"酒精|白酒|啤酒|红酒")),
    ("PC-FOOD-004", re.compile(r"洋葱|大蒜|韭菜|葱(?!油饼)")),
    ("PC-FOOD-005", re.compile(r"木糖醇|代糖")),
    ("PC-FOOD-006", re.compile(r"葡萄(干)?")),
    ("PC-FOOD-007", re.compile(r"百合(花)?")),
    ("PC-FOOD-008", re.compile(r"布洛芬|对乙酰氨基酚|扑热息痛|阿司匹林")),
]
FOOD_WARNING = [
    ("PC-FOOD-009", re.compile(r"牛奶|奶酪|乳制品")),
    ("PC-FOOD-010", re.compile(r"熟骨头|骨头(?!汤)|啃骨头")),
    ("PC-FOOD-011", re.compile(r"火腿|咸菜|薯片|高盐")),
    ("PC-FOOD-012", re.compile(r"生肉|生鱼|生骨肉")),
]

VAX_RE = re.compile(r"(狂犬|犬瘟|细小|传染性肝炎|犬三联|犬四联|猫三联|猫瘟|猫鼻支|杯状病毒|猫白血病)")
DATE_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
VAX_LINE_RE = re.compile(r"疫苗")

RED_FLAGS = [
    ("PC-RED-001", re.compile(r"误食")),
    ("PC-RED-002", re.compile(r"抽搐|癫痫")),
    ("PC-RED-003", re.compile(r"呼吸困难|张口呼吸")),
    ("PC-RED-004", re.compile(r"血便|呕血|便血")),
    ("PC-RED-005", re.compile(r"频繁进出猫砂盆|尿闭|排不出尿")),
    ("PC-RED-006", re.compile(r"中毒")),
]
EMERGENCY_RE = re.compile(r"立即就医|急诊|送医|急救")

WEIGHT_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|公斤|lb|磅|斤)")
WEIGHT_BARE_RE = re.compile(r"体重[：:为是]?\s*(\d+(?:\.\d+)?)(?![\d.])(?!\s*(kg|公斤|lb|磅|斤))")

DOSE_GMG_RE = re.compile(r"\d+\s*g\b.*\d+\s*mg\b|\d+\s*mg\b.*\d+\s*g\b", re.I)
DOSE_ML_RE = re.compile(r"\d+\s*ml\b.*\d+\s*L\b|\d+\s*L\b.*\d+\s*ml\b", re.I)
TEMP_MIX_RE = re.compile(r"℃.*℉|℉.*℃")
AGE_MIX_RE = re.compile(r"\d+\s*岁.*\d+\s*(个)?月|\d+\s*(个)?月.*\d+\s*岁")

DEWORM_RE = re.compile(r"驱虫")
SURGERY_RE = re.compile(r"绝育手术|手术")
BATH_SPORT_RE = re.compile(r"洗澡|剧烈运动|跑步|游泳")


def _parse_date(s):
    m = DATE_RE.search(s)
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# ---------------------------------------------------------------- 规则实现
# ---- PC-DISC 声明类 ----
@rule("PC-DISC-001", "blocker", "声明", "缺健康声明",
      "计划文档缺少'仅供参考'+'遵医嘱/咨询兽医'健康声明。")
def _disc1(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        if not (DISCLAIMER_RE.search(text) and DOCTOR_RE.search(text)):
            out.append(_mk("PC-DISC-001", p, 1, _lines(text)[0] if text else ""))


@rule("PC-DISC-002", "warning", "声明", "缺'非兽医诊断'表述",
      "计划未声明'不是兽医诊断、不能替代专业诊疗'。")
def _disc2(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        if not NOT_VET_RE.search(text):
            out.append(_mk("PC-DISC-002", p, 1, _lines(text)[0] if text else ""))


@rule("PC-DISC-003", "blocker", "声明", "出现疗效承诺",
      "出现'保证治愈/包治/药到病除'类承诺，违反安全红线。")
def _disc3(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln, _ in _iter_hits(text, [("x", CURE_PROMISE_RE)]):
            out.append(_mk("PC-DISC-003", p, i, ln))


# ---- PC-FOOD 禁忌食物类 ----
def _food_rule(rule_id, severity, rx, title, detail):
    @rule(rule_id, severity, "禁忌食物", title, detail)
    def _f(ctx, out, _rx=rx, _rid=rule_id):
        for p in ctx["docs"]:
            text = read_text(p)
            if text is None:
                continue
            for i, ln, _ in _iter_hits(text, [("x", _rx)]):
                # 排除"禁忌""不能吃""避免"等否定语境（说明是在提醒，而非推荐）
                if re.search(r"禁忌|不能吃|不能喂|避免|禁食|危险|中毒", ln):
                    continue
                out.append(_mk(_rid, p, i, ln))
    _f.__name__ = rule_id.lower()
    return _f


_food_rule("PC-FOOD-001", "blocker", FOOD_BLOCKER[0][1], "含巧克力/可可", "饮食方案出现巧克力/可可（犬猫共有禁忌）。")
_food_rule("PC-FOOD-002", "blocker", FOOD_BLOCKER[1][1], "含咖啡因", "饮食方案出现咖啡/茶/咖啡因。")
_food_rule("PC-FOOD-003", "blocker", FOOD_BLOCKER[2][1], "含酒精", "饮食方案出现酒精类。")
_food_rule("PC-FOOD-004", "blocker", FOOD_BLOCKER[3][1], "含洋葱/大蒜/韭菜", "饮食方案出现洋葱/大蒜/韭菜。")
_food_rule("PC-FOOD-005", "blocker", FOOD_BLOCKER[4][1], "含木糖醇/代糖", "饮食方案出现木糖醇/代糖。")
_food_rule("PC-FOOD-006", "blocker", FOOD_BLOCKER[5][1], "含葡萄/葡萄干", "饮食方案出现葡萄/葡萄干（犬禁忌）。")
_food_rule("PC-FOOD-007", "blocker", FOOD_BLOCKER[6][1], "含百合", "饮食方案出现百合（猫禁忌）。")
_food_rule("PC-FOOD-008", "blocker", FOOD_BLOCKER[7][1], "含人用药物", "出现布洛芬/对乙酰氨基酚等人用药。")
_food_rule("PC-FOOD-009", "warning", FOOD_WARNING[0][1], "含牛奶/乳制品", "出现牛奶/乳制品（乳糖不耐受风险），建议标注或替换。")
_food_rule("PC-FOOD-010", "warning", FOOD_WARNING[1][1], "含熟骨头", "出现熟骨头（碎裂划伤风险）。")
_food_rule("PC-FOOD-011", "warning", FOOD_WARNING[2][1], "含高盐人类食物", "出现火腿/咸菜/薯片等高盐人类食物。")
_food_rule("PC-FOOD-012", "warning", FOOD_WARNING[3][1], "生肉生鱼无风险提示", "出现生肉/生鱼/生骨肉但无寄生虫风险提示。")


# ---- PC-VAX 疫苗类 ----
def _vax_entries(text):
    """提取 (行号, 疫苗名, 日期或None)。"""
    entries = []
    for i, ln in enumerate(_lines(text), 1):
        if not VAX_LINE_RE.search(ln):
            continue
        m = VAX_RE.search(ln)
        name = m.group(1) if m else None
        entries.append((i, ln, name, _parse_date(ln)))
    return entries


@rule("PC-VAX-001", "blocker", "疫苗", "同种疫苗间隔<21天",
      "同种疫苗两针间隔不足 21 天，违反首免间隔硬规则。")
def _vax1(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        by_name = {}
        for i, ln, name, dt in _vax_entries(text):
            if name and dt:
                by_name.setdefault(name, []).append((dt, i, ln))
        for name, lst in by_name.items():
            lst.sort()
            for (d1, i1, l1), (d2, i2, l2) in zip(lst, lst[1:]):
                if (d2 - d1).days < 21:
                    out.append(_mk("PC-VAX-001", p, i2, l2))


@rule("PC-VAX-002", "warning", "疫苗", "加强针间隔<10个月",
      "加强针距上针不足 10 个月（常规 11~12 个月），请确认是否为医嘱加密。")
def _vax2(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        by_name = {}
        for i, ln, name, dt in _vax_entries(text):
            if name and dt:
                by_name.setdefault(name, []).append((dt, i, ln))
        for name, lst in by_name.items():
            lst.sort()
            for (d1, i1, l1), (d2, i2, l2) in zip(lst, lst[1:]):
                gap = (d2 - d1).days
                if 21 <= gap < 300:
                    out.append(_mk("PC-VAX-002", p, i2, l2))


@rule("PC-VAX-003", "warning", "疫苗", "同一天接种≥3种疫苗",
      "同一天安排 3 种及以上疫苗，建议分开以便观察。")
def _vax3(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        by_date = {}
        for i, ln, name, dt in _vax_entries(text):
            if dt:
                by_date.setdefault(dt.date().isoformat(), []).append((i, ln))
        for d, lst in by_date.items():
            if len(lst) >= 3:
                i, ln = lst[0]
                out.append(_mk("PC-VAX-003", p, i, "%s 当天 %d 种疫苗" % (d, len(lst))))


@rule("PC-VAX-004", "warning", "疫苗", "疫苗条目日期无法解析",
      "含'疫苗'的行没有可解析的日期（需 YYYY-MM-DD）。")
def _vax4(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln, name, dt in _vax_entries(text):
            if dt is None and re.search(r"疫苗", ln) \
                    and not re.search(r"疫苗本|疫苗史|咨询兽医|遵医嘱", ln):
                out.append(_mk("PC-VAX-004", p, i, ln))


@rule("PC-VAX-005", "warning", "疫苗", "未识别的疫苗名称",
      "疫苗名称不在常见表，请核对拼写或确认是否为新型疫苗。")
def _vax5(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln, name, dt in _vax_entries(text):
            if name is None and VAX_LINE_RE.search(ln) and dt is not None:
                out.append(_mk("PC-VAX-005", p, i, ln))


@rule("PC-VAX-006", "blocker", "疫苗", "疫苗记录缺日期",
      "'接种/打针'类记录缺少日期，无法排加强针。")
def _vax6(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if re.search(r"接种|打针|注射疫苗", ln) and not DATE_RE.search(ln) \
                    and not re.search(r"疫苗本|咨询兽医", ln):
                out.append(_mk("PC-VAX-006", p, i, ln))


# ---- PC-UNIT 单位类 ----
@rule("PC-UNIT-001", "blocker", "单位", "体重单位混用",
      "同一文档混用 kg 与 lb/磅/斤，剂量基准混乱。")
def _unit1(ctx, out):
    for p in ctx["docs"] + ctx["profiles"]:
        text = read_text(p)
        if text is None:
            continue
        units = set()
        for m in WEIGHT_UNIT_RE.finditer(text):
            u = m.group(2)
            units.add("kg" if u in ("kg", "公斤") else "imperial")
        if "kg" in units and "imperial" in units:
            out.append(_mk("PC-UNIT-001", p, 1, _lines(text)[0] if text else ""))


@rule("PC-UNIT-002", "blocker", "单位", "体重数字无单位",
      "'体重'后跟数字但无单位。")
def _unit2(ctx, out):
    for p in ctx["docs"] + ctx["profiles"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if WEIGHT_BARE_RE.search(ln):
                out.append(_mk("PC-UNIT-002", p, i, ln))


@rule("PC-UNIT-003", "warning", "单位", "剂量 g/mg 混用",
      "同一行混用 g 与 mg，易看错剂量。")
def _unit3(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if DOSE_GMG_RE.search(ln):
                out.append(_mk("PC-UNIT-003", p, i, ln))


@rule("PC-UNIT-004", "warning", "单位", "容量 ml/L 混用",
      "同一行混用 ml 与 L。")
def _unit4(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if DOSE_ML_RE.search(ln):
                out.append(_mk("PC-UNIT-004", p, i, ln))


@rule("PC-UNIT-005", "nit", "单位", "温度单位混用",
      "同一行混用 ℃ 与 ℉。")
def _unit5(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if TEMP_MIX_RE.search(ln):
                out.append(_mk("PC-UNIT-005", p, i, ln))


@rule("PC-UNIT-006", "warning", "单位", "年龄单位混用无换算",
      "同一行混用'岁'与'月'且无换算说明。")
def _unit6(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if AGE_MIX_RE.search(ln) and not re.search(r"换算|约|≈", ln):
                out.append(_mk("PC-UNIT-006", p, i, ln))


# ---- PC-SCHED 时间表类 ----
def _dated_lines(text, keyword_re):
    items = []
    for i, ln in enumerate(_lines(text), 1):
        if keyword_re.search(ln):
            items.append((i, ln, _parse_date(ln)))
    return items


@rule("PC-SCHED-001", "blocker", "时间表", "同一天两种驱虫药",
      "同一天安排两种驱虫药。")
def _sched1(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        items = _dated_lines(text, DEWORM_RE)
        by_date = {}
        for i, ln, dt in items:
            if dt:
                by_date.setdefault(dt.date().isoformat(), []).append((i, ln))
        for d, lst in by_date.items():
            kinds = set()
            for i, ln in lst:
                m = re.search(r"(体内驱虫|体外驱虫|驱虫药[AB]?)", ln)
                kinds.add(m.group(1) if m else ln.strip()[:12])
            if len(kinds) >= 2 or (len(lst) >= 2 and len(set(l[1] for l in lst)) >= 2):
                i, ln = lst[0]
                out.append(_mk("PC-SCHED-001", p, i, "%s 当天 %d 项驱虫" % (d, len(lst))))


@rule("PC-SCHED-002", "warning", "时间表", "驱虫间隔<14天",
      "两次驱虫间隔不足 14 天。")
def _sched2(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        dts = sorted({dt for _, _, dt in _dated_lines(text, DEWORM_RE) if dt})
        for d1, d2 in zip(dts, dts[1:]):
            if 0 < (d2 - d1).days < 14:
                out.append(_mk("PC-SCHED-002", p, 1,
                               "驱虫间隔 %d 天（%s→%s）" % ((d2 - d1).days, d1.date(), d2.date())))


@rule("PC-SCHED-003", "blocker", "时间表", "时间表条目缺日期",
      "含日期关键词（疫苗/驱虫/体检）的条目缺少可解析日期。")
def _sched3(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if re.search(r"疫苗|驱虫|体检", ln) and not DATE_RE.search(ln) \
                    and not re.search(r"疫苗本|咨询兽医|每年|每月|每季度|每半年", ln):
                # 表头/说明行放行：含"日期|事项"表头特征
                if re.search(r"日期.*事项|事项.*备注", ln):
                    continue
                out.append(_mk("PC-SCHED-003", p, i, ln))


@rule("PC-SCHED-004", "warning", "时间表", "驱虫与疫苗同一天",
      "驱虫与疫苗安排在同一天，建议分开。")
def _sched4(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        vax_dates = {dt.date().isoformat() for _, _, dt in _dated_lines(text, VAX_LINE_RE) if dt}
        for i, ln, dt in _dated_lines(text, DEWORM_RE):
            if dt and dt.date().isoformat() in vax_dates:
                out.append(_mk("PC-SCHED-004", p, i, ln))


@rule("PC-SCHED-005", "warning", "时间表", "术后7天内安排洗澡/剧烈运动",
      "绝育/手术后 7 天内安排洗澡或剧烈运动。")
def _sched5(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        surgeries = [dt for _, _, dt in _dated_lines(text, SURGERY_RE) if dt]
        for i, ln, dt in _dated_lines(text, BATH_SPORT_RE):
            if dt and any(0 <= (dt - s).days <= 7 for s in surgeries):
                out.append(_mk("PC-SCHED-005", p, i, ln))


@rule("PC-SCHED-006", "warning", "时间表", "成年宠物无年度体检项",
      "时间表无'体检'项，成年宠物建议每年一体检。")
def _sched6(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        if "schedule" in os.path.basename(p).lower() or "时间表" in p:
            if not re.search(r"体检", text):
                out.append(_mk("PC-SCHED-006", p, 1, _lines(text)[0] if text else ""))


# ---- PC-RED 急诊红旗类 ----
def _red_rule(rule_id, rx, title):
    @rule(rule_id, "blocker", "急诊红旗", title,
          "出现急诊红旗词但无'立即就医/急诊/送医'指引。")
    def _r(ctx, out, _rx=rx, _rid=rule_id):
        for p in ctx["docs"]:
            text = read_text(p)
            if text is None:
                continue
            if EMERGENCY_RE.search(text):
                continue
            for i, ln, _ in _iter_hits(text, [("x", _rx)]):
                out.append(_mk(_rid, p, i, ln))
    _r.__name__ = rule_id.lower()
    return _r


_red_rule("PC-RED-001", RED_FLAGS[0][1], "误食无就医指引")
_red_rule("PC-RED-002", RED_FLAGS[1][1], "抽搐/癫痫无就医指引")
_red_rule("PC-RED-003", RED_FLAGS[2][1], "呼吸困难无就医指引")
_red_rule("PC-RED-004", RED_FLAGS[3][1], "血便/呕血无就医指引")
_red_rule("PC-RED-005", RED_FLAGS[4][1], "疑似尿闭无就医指引")
_red_rule("PC-RED-006", RED_FLAGS[5][1], "中毒无就医指引")


# ---- PC-ARCH 档案类 ----
def _profile_data(p):
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


@rule("PC-ARCH-001", "blocker", "档案", "档案缺体重",
      "profile.json 缺 weight_kg 或非数字。")
def _arch1(ctx, out):
    for p in ctx["profiles"]:
        d = _profile_data(p)
        if d is None:
            continue
        if not isinstance(d.get("weight_kg"), (int, float)):
            out.append(_mk("PC-ARCH-001", p, 1, "weight_kg 缺失或非数字"))


@rule("PC-ARCH-002", "blocker", "档案", "档案缺物种",
      "profile.json 缺 species。")
def _arch2(ctx, out):
    for p in ctx["profiles"]:
        d = _profile_data(p)
        if d is None:
            continue
        if not d.get("species"):
            out.append(_mk("PC-ARCH-002", p, 1, "species 缺失"))


@rule("PC-ARCH-003", "warning", "档案", "档案缺年龄",
      "profile.json 缺 age_years。")
def _arch3(ctx, out):
    for p in ctx["profiles"]:
        d = _profile_data(p)
        if d is None:
            continue
        if d.get("age_years") is None:
            out.append(_mk("PC-ARCH-003", p, 1, "age_years 缺失"))


@rule("PC-ARCH-004", "warning", "档案", "档案缺疫苗史",
      "profile.json 无 vaccine_history（含 unknown 标记也算有）。")
def _arch4(ctx, out):
    for p in ctx["profiles"]:
        d = _profile_data(p)
        if d is None:
            continue
        if "vaccine_history" not in d:
            out.append(_mk("PC-ARCH-004", p, 1, "vaccine_history 缺失"))


@rule("PC-ARCH-005", "nit", "档案", "档案缺绝育状态",
      "profile.json 无 neutered 字段。")
def _arch5(ctx, out):
    for p in ctx["profiles"]:
        d = _profile_data(p)
        if d is None:
            continue
        if "neutered" not in d:
            out.append(_mk("PC-ARCH-005", p, 1, "neutered 缺失"))


@rule("PC-ARCH-006", "nit", "档案", "档案缺紧急联系信息",
      "profile.json 无 emergency_vet（常去医院/急诊电话）。")
def _arch6(ctx, out):
    for p in ctx["profiles"]:
        d = _profile_data(p)
        if d is None:
            continue
        if not d.get("emergency_vet"):
            out.append(_mk("PC-ARCH-006", p, 1, "emergency_vet 缺失"))


# ---- PC-DIET 饮食类 ----
@rule("PC-DIET-001", "warning", "饮食", "换粮无过渡说明",
      "提到'换粮/转粮'但无 7 天过渡说明。")
def _diet1(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        if re.search(r"换粮|转粮", text) and not re.search(r"过渡|第 1~2 天|25%", text):
            out.append(_mk("PC-DIET-001", p, 1, "换粮无过渡说明"))


@rule("PC-DIET-002", "warning", "饮食", "幼年喂成年粮",
      "档案为幼年（<1 岁）但饮食出现成犬/成猫粮。")
def _diet2(ctx, out):
    young = False
    for p in ctx["profiles"]:
        d = _profile_data(p)
        if d and isinstance(d.get("age_years"), (int, float)) and d["age_years"] < 1:
            young = True
    if not young:
        # 无档案时从文档推断
        for p in ctx["docs"]:
            text = read_text(p) or ""
            if re.search(r"幼犬|幼猫|[0-9]+ ?月龄", text):
                young = True
                break
    if not young:
        return
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        for i, ln in enumerate(_lines(text), 1):
            if re.search(r"成犬粮|成猫粮", ln) and not re.search(r"禁忌|不要|避免", ln):
                out.append(_mk("PC-DIET-002", p, i, ln))


@rule("PC-DIET-003", "nit", "饮食", "未注明每日喂食次数",
      "饮食方案未注明每天喂几顿。")
def _diet3(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        if re.search(r"喂食|饲喂|吃饭", text) and not re.search(r"每天 ?[234] ?顿|一日 ?[234] ?餐", text):
            if "care-plan" in os.path.basename(p).lower() or "饮食" in p:
                out.append(_mk("PC-DIET-003", p, 1, "未注明每日喂食次数"))


@rule("PC-DIET-004", "nit", "饮食", "饮水说明缺失",
      "饮食方案无饮水说明。")
def _diet4(ctx, out):
    for p in ctx["docs"]:
        text = read_text(p)
        if text is None:
            continue
        if "care-plan" in os.path.basename(p).lower() or "饮食" in p:
            if not re.search(r"饮水|喝水|新鲜水", text):
                out.append(_mk("PC-DIET-004", p, 1, "饮水说明缺失"))


# ---------------------------------------------------------------- 主流程
def run_audit(target):
    ctx = collect(target)
    findings = []
    for r in RULES:
        try:
            r["check"](ctx, findings)
        except Exception as e:  # 单条规则失败不影响整体：fail-open
            findings.append(Finding(r["id"], "nit", r["category"],
                                    "规则执行异常（已跳过）", "", 0, "", str(e)))
    findings.sort(key=lambda f: ({"blocker": 0, "warning": 1, "nit": 2}[f.severity], f.rule_id))
    sev_count = {"blocker": 0, "warning": 0, "nit": 0}
    for f in findings:
        sev_count[f.severity] += 1
    summary = {
        "tool": TOOL, "version": VERSION, "target": os.path.abspath(target),
        "rules_run": len(RULES),
        "blocker": sev_count["blocker"], "warning": sev_count["warning"],
        "nit": sev_count["nit"], "total": len(findings),
    }
    return {"summary": summary, "findings": [f.to_dict() for f in findings]}


def format_text(report):
    s = report["summary"]
    lines = [
        "lhg-pet-care 审计报告 v%s" % s["version"],
        "目标：%s  规则：%d 条" % (s["target"], s["rules_run"]),
        "blocker=%d warning=%d nit=%d" % (s["blocker"], s["warning"], s["nit"]),
        "-" * 60,
    ]
    for f in report["findings"]:
        lines.append("[%s][%s] %s:%s %s" % (
            f["severity"], f["rule_id"], os.path.basename(f["file"]) or "(规则)",
            f["line"], f["title"]))
        if f["snippet"]:
            lines.append("    %s" % f["snippet"][:120])
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--format", default="text", choices=["json", "text"])
    ap.add_argument("--fail-on", default="blocker", choices=["blocker", "warning", "nit"])
    args = ap.parse_args()
    report = run_audit(args.target)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report))
    order = {"blocker": 0, "warning": 1, "nit": 2}
    thresh = order[args.fail_on]
    bad = any(order[f["severity"]] <= thresh for f in report["findings"])
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
