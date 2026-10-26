---
name: lhg-pc-audit
description: 养护计划自检方法论：49 条确定性规则分类解读、安全红线、人工评审清单。适用于发布养护计划前的最后一道检查。
license: MIT
compatibility: 平台中立（Claude Code / 豆包 / Workbuddy 等 agent 平台通用）
metadata:
  version: 1.0.0
  domain: pet-care
---

# lhg-pc-audit：养护计划自检

> **健康声明**：自检通过不等于兽医认可；本 skill 只检查计划的完整性与安全性表达，不替代专业诊疗判断。

## 1. 何时使用

- 养护计划（profile.json / schedule-*.md / care-plan.md）写完、交付用户之前的最后一道检查。
- 收到一份别人写的养护计划，想验它靠不靠谱时。
- `/lhg-pet-care:pet-audit` 命令全程按本 skill 执行。

**检查哲学**：机器先行（49 条确定性规则，零 AI 成本），人工补漏（脚本抓不到的 10 项）。blocker 清零才算做完；为清零改规则算作弊。

## 2. 健康声明模板（每个 md 文件顶部必须带）

```markdown
> **健康声明**：本计划仅供日常养护参考，不是兽医诊断，不能替代专业诊疗；
> 用药、疫苗、驱虫等医疗事项请遵医嘱，如有异常请及时咨询兽医。
```

必须同时含"仅供参考"与"遵医嘱/咨询兽医"两层意思，缺一层即判 PC-DISC-001。

## 3. 49 条规则分类解读

脚本：`scripts/audit/pet_care_audit.py`（用法见第 4 节）。规则分 8 类：

### PC-DISC 声明类（3 条）
| 规则 | 含义 | 级别 |
|---|---|---|
| PC-DISC-001 | 任一计划文档缺健康声明（"仅供参考"+"遵医嘱"） | blocker |
| PC-DISC-002 | 缺"不是兽医诊断/不能替代诊疗"表述 | warning |
| PC-DISC-003 | 出现"保证治愈/包治/药到病除"类承诺 | blocker |

### PC-FOOD 禁忌食物类（12 条）
按 lhg-pc-nutrition 第 4 节清单命中即告警：
- blocker：巧克力/可可（001）、咖啡因（002）、酒精（003）、洋葱大蒜韭菜（004）、木糖醇（005）、葡萄/葡萄干（006，犬）、百合（007，猫）、人用药布洛芬等（008）
- warning：牛奶（009）、熟骨头（010）、高盐人类食物（011）、生肉生鱼无风险提示（012）

### PC-VAX 疫苗类（6 条）
| 规则 | 含义 | 级别 |
|---|---|---|
| PC-VAX-001 | 同种疫苗两针间隔 <21 天 | blocker |
| PC-VAX-002 | 加强针距上针 <10 个月（遵医嘱加密除外） | warning |
| PC-VAX-003 | 同一天接种 ≥3 种疫苗 | warning |
| PC-VAX-004 | 疫苗条目日期格式无法解析 | warning |
| PC-VAX-005 | 疫苗名称不在常见表（狂犬/犬瘟/细小/猫三联/猫瘟…） | warning（请核对拼写） |
| PC-VAX-006 | 疫苗记录缺日期 | blocker |

### PC-UNIT 单位类（6 条）
| 规则 | 含义 | 级别 |
|---|---|---|
| PC-UNIT-001 | 同一文档 kg 与 lb/斤混用 | blocker |
| PC-UNIT-002 | 体重数字无单位 | blocker |
| PC-UNIT-003 | 剂量 g/mg 混用 | warning |
| PC-UNIT-004 | 容量 ml/L 混用 | warning |
| PC-UNIT-005 | 温度 ℃/℉ 混用 | nit |
| PC-UNIT-006 | 年龄"岁/月"混用无换算说明 | warning |

### PC-SCHED 时间表类（6 条）
| 规则 | 含义 | 级别 |
|---|---|---|
| PC-SCHED-001 | 同一天两种驱虫药 | blocker |
| PC-SCHED-002 | 两次驱虫间隔 <14 天 | warning |
| PC-SCHED-003 | 时间表条目缺日期 | blocker |
| PC-SCHED-004 | 驱虫与疫苗同一天 | warning |
| PC-SCHED-005 | 绝育/手术 7 天内安排洗澡或剧烈运动 | warning |
| PC-SCHED-006 | 成年宠物时间表无年度体检项 | warning |

### PC-RED 急诊红旗类（6 条）
文档中出现以下词、但**无"立即就医/急诊/送医"指引**时触发（均为 blocker）：
- PC-RED-001 误食（老鼠药/巧克力大量/异物）
- PC-RED-002 抽搐/癫痫
- PC-RED-003 呼吸困难/张口呼吸
- PC-RED-004 血便/呕血
- PC-RED-005 频繁进出猫砂盆（公猫尿闭信号）
- PC-RED-006 中毒

### PC-ARCH 档案类（6 条）
| 规则 | 含义 | 级别 |
|---|---|---|
| PC-ARCH-001 | 档案缺体重 | blocker |
| PC-ARCH-002 | 档案缺物种 | blocker |
| PC-ARCH-003 | 档案缺年龄 | warning |
| PC-ARCH-004 | 档案缺疫苗史（连 unknown 都没标） | warning |
| PC-ARCH-005 | 档案缺绝育状态 | nit |
| PC-ARCH-006 | 档案缺紧急联系人/常去医院 | nit |

### PC-DIET 饮食类（4 条）
| 规则 | 含义 | 级别 |
|---|---|---|
| PC-DIET-001 | 换粮无 7 天过渡说明 | warning |
| PC-DIET-002 | 幼年宠物喂成犬/成猫粮 | warning |
| PC-DIET-003 | 每日喂食次数未注明 | nit |
| PC-DIET-004 | 饮水说明缺失 | nit |

## 4. 脚本用法

```bash
# 人类可读报告
python3 scripts/audit/pet_care_audit.py --target <计划目录> --format text
# JSON（供 hook / CI）
python3 scripts/audit/pet_care_audit.py --target <计划目录> --format json
# exit code：0=无 blocker，2=有 blocker
```

## 5. 人工评审清单（脚本抓不到的 10 项）

1. [ ] 时间表日期是未来的吗？与疫苗本末次日期对得上吗？
2. [ ] 禁忌检查是否按"这只宠物的物种"打的勾（猫狗表不同）？
3. [ ] 剂量相关表述是否都是"遵医嘱按体重核算"，无具体 mg/kg 数字？
4. [ ] 急诊红旗清单是否置顶、每条都有"立即就医"？
5. [ ] 多宠家庭：档案与计划是否一一对应、无张冠李戴？
6. [ ] 疫苗史 unknown 的宠物，时间表是否未排具体加强日期？
7. [ ] 饮食方案有无品牌推荐、疗效承诺？
8. [ ] 换粮/转粮是否有 7 天过渡说明？
9. [ ] 老年宠物是否有半年体检项？
10. [ ] 用户是否已确认档案摘要与时间表？

## 6. 反模式

1. **为过而改阈值**：把"21 天"改成"14 天"让 blocker 消失——作弊，不许。
2. **warning 当没看见**：warning 需要"修或写豁免理由"，不能静默忽略。
3. **只跑脚本不看清单**：脚本是底稿，第 5 节人工清单必须过一遍。
4. **声明贴了但藏在文末**：健康声明必须在文件顶部，藏文末等于没有。
5. **拿不准就放行**：禁忌食物拿不准 → 按"先别写进方案、问兽医"处理，不许放行。

## 7. 自检与反馈

### 质检门（本 skill 自查）
- [ ] 49 条规则分类解读是否与脚本实现一致（rule_id 一一对应）？
- [ ] 健康声明模板是否同时含"仅供参考"与"遵医嘱"？
- [ ] 人工清单 10 项是否覆盖脚本盲区（日期真实性、物种表匹配、剂量表述）？

### 标准冒烟用例
对 `fixtures/pet-bad` 跑脚本：期望 20 个埋点规则全命中、exit code 为 2；对 `fixtures/pet-good` 跑：期望零 blocker、exit code 为 0。

### 一键反馈
发现规则误报/漏报，以 `[QC] lhg-pc-audit <rule_id> <一句话>` 为标题提交到 https://github.com/lhg-plugs/lhg-pet-care/issues，正文写清"触发文本 → 实际判定 → 期望判定"。

## 出品：刘洪光

本 skill 由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
