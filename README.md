> **⚠️ 健康声明：本插件输出仅供日常养护参考，不是兽医诊断，不能替代专业诊疗；用药、疫苗、驱虫等医疗事项请遵医嘱，如有异常请及时咨询兽医。**

<!-- About 简介（推送后填写到仓库 About 栏）：
宠物养护专家：档案→驱虫/疫苗/饮食时间表→健康 checklist 一键生成 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-pet-care
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, pet-care, pets, veterinary -->

# lhg-pet-care：宠物养护专家

> **一句话介绍**：小白养宠不踩坑——宠物档案建档 → 驱虫/疫苗/饮食时间表 → 健康 checklist，一句话生成全年养护计划，49 条确定性规则 5 秒自检。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-pet-care
> /plugin install lhg-pet-care@lhg-plugs
> ```

**健康声明（再说一遍）**：本插件不是兽医，不做诊断、不开处方、不给具体用药剂量。急诊红旗（误食/抽搐/呼吸困难/血便/公猫尿闭）一律只写"立即就医"，不给家庭处理方案。

## 它是什么

`lhg-pet-care` 是一个 Claude Code 插件（plugin 为主、skill 为辅），专为"第一次养宠 / 多宠家庭记不住时间表"的人设计：

- **4 个命令**（小白入口）：`pet-care` 一键全流程（档案→时间表→饮食→checklist→自检）→ `pet-profile` 档案建档 → `pet-schedule` 时间表生成 → `pet-audit` 养护自检
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：宠物档案与生命周期、养护时间表、饮食与禁忌、自检流程
- **3 个专家 agent**：养护规划师、时间表审核员、独立安全评审（一票否决制）
- **1 个硬门 hook**：保存养护计划前自动检查健康声明（"仅供参考"+"遵医嘱"），缺失则拦截（可一键豁免，不骚扰）
- **49 条确定性自查规则**：禁忌食物 12、疫苗间隔 6、单位一致性 6、时间表冲突 6、急诊红旗 6、档案完整性 6、声明 3、饮食 4，纯 Python、零第三方依赖，5 秒出结果

工作流：`pet-care`（建档→排期→饮食→checklist）→ `pet-audit`（查一遍），也可以单独用 `pet-profile` 只建档。

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-pet-care:pet-care` | 养护一键生成：档案→时间表→饮食→checklist→自检 | `/lhg-pet-care:pet-care "3岁英短，4.5kg，已绝育"` |
| `/lhg-pet-care:pet-profile` | 宠物档案建档/更新，输出 profile.json | `/lhg-pet-care:pet-profile "金毛，5月龄，6kg"` |
| `/lhg-pet-care:pet-schedule` | 驱虫/疫苗/体检时间表生成，冲突自动告警 | `/lhg-pet-care:pet-schedule ./profile-doudou.json --year 2027` |
| `/lhg-pet-care:pet-audit` | 养护计划自检（脚本 + 人工评审清单） | `/lhg-pet-care:pet-audit ./plan/` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审清单（人）：

1. 先跑 `scripts/audit/pet_care_audit.py`（49 条规则），零 AI 成本；
2. 发现分三级：**blocker**（必须修：禁忌食物命中、疫苗间隔 <21 天、缺健康声明、急诊红旗无就医指引、同一天两种驱虫药；保存计划时 hook 会拦截缺声明的文件）、**warning**（修或写豁免理由）、**nit**（顺手修）；
3. 再按 `lhg-pc-audit` skill 第 5 节人工清单过一遍脚本抓不到的（日期与疫苗本对得上吗、禁忌表是否按物种打勾、剂量表述是否都是"遵医嘱"）。

blocker 清零才算做完；为清零改规则算作弊，不许。

## 目录结构

```
lhg-pet-care/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：pet-care / pet-profile / pet-schedule / pet-audit
├── skills/                  # 4 个平台中立 skill（档案/时间表/饮食/自检）
├── agents/                  # 3 个专家 agent（care-planner / schedule-reviewer / safety-reviewer）
├── hooks/                   # 1 个硬门（养护计划健康声明检查）+ 豁免说明
├── scripts/audit/           # 49 条确定性自查规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你刚养第一只猫/狗，不知道"疫苗什么时候打、驱虫多久一次"时 → 用 `/lhg-pet-care:pet-care`，一句话出全年计划
- 你家有两三只宠物，疫苗本、驱虫时间记混时 → 一宠一档 + 一宠一时间表，冲突自动告警
- 你想给宠物换粮/加零食，拿不准能不能吃时 → `lhg-pc-nutrition` 禁忌清单逐项打勾
- 你要把养护计划发给家人执行，想先过一遍安全检查时 → `pet-audit` + 独立安全评审一票否决

**什么时候不用：**

- 宠物正在生病、有明确症状（呕吐/拉稀/精神差/拒食）→ **直接去看兽医**，本插件不做诊断、不给治疗方案
- 你需要的是用药剂量、处方、疫苗品牌选择 → 超出本插件范围，请遵医嘱
- 出现急诊红旗（误食、抽搐、呼吸困难、血便、公猫排不出尿）→ **立即就医**，不要在网上查、不要等插件

**风险点诚实说明：**

- **疫苗/驱虫节拍是"常用做法"不是"医嘱"**：口径为公开兽医常识的独立整理，具体方案请以你的兽医为准
- **禁忌食物清单不可能穷尽**：清单会持续扩充；拿不准的食物一律按"先别喂、问兽医"处理
- **时间表依赖档案准确**：体重错一位、疫苗日期错一天，排期全错——输出前务必核对疫苗本
- **自检通过 ≠ 兽医认可**：49 条规则只检查计划的完整性与安全性表达，不替代专业判断

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-meal-plan](https://github.com/lhg-plugs/lhg-meal-plan) | 营养食谱专家：一周食谱与采购清单一键生成 | `/plugin install lhg-meal-plan@lhg-plugs` |
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频 | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-pet-care](https://github.com/lhg-plugs/lhg-pet-care) | 宠物养护专家：档案→时间表→健康 checklist 一键生成 | `/plugin install lhg-pet-care@lhg-plugs` |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、49 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-pet-care/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
