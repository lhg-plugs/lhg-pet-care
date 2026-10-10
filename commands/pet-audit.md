---
description: 养护计划自检：49 条确定性规则（禁忌食物/疫苗间隔/单位一致/时间表冲突/声明缺失/急诊红旗），blocker 清零才算过。
argument-hint: [计划目录] [--fail-on blocker]
---

# /lhg-pet-care:pet-audit —— 养护计划自检

用户输入在 `$ARGUMENTS` 中：`[计划目录] [--fail-on 级别]`，缺省 blocker。

先跑脚本、再过人工清单（见 `lhg-pc-audit` skill）。

## 流程

### 1. 确定性脚本（零 AI 成本先行）
```bash
python3 scripts/audit/pet_care_audit.py --target <计划目录> --format text
```
- 49 条规则分 8 类：声明 3、禁忌食物 12、疫苗 6、单位 6、时间表 6、急诊红旗 6、档案 6、饮食 4。
- 发现分三级：**blocker**（必须修：禁忌食物命中、疫苗间隔 <21 天、缺健康声明、急诊红旗无就医指引）、**warning**（修或写豁免理由）、**nit**（顺手修）。
- blocker 清零才算做完；为清零改规则算作弊，不许。

### 2. 人工评审清单（脚本抓不到的）
- 时间表上的日期是未来的吗？疫苗本上的末次日期对得上吗？
- 禁忌食物检查是否按"这只宠物的物种"打的勾（猫狗表不一样）？
- 剂量相关表述是否都写了"遵医嘱按体重核算"，没有出现具体 mg/kg 数字？
- 急诊红旗清单是否置顶、是否每条都写了"立即就医"？

### 3. 输出
- 审计报告（blocker/warning/nit 清单 + 修复建议），存 `audit-report.md`。
