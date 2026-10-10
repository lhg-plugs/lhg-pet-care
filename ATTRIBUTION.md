# 灵感来源与致谢（Attribution）

本插件的**方法论灵感**来自以下公开资料的高层思路，**所有实现代码、检测规则与文案均为原创**，未复制任何第三方的原文案与代码。

| 来源 | 说明 | 出处 | 借鉴了什么思路 |
|---|---|---|---|
| yimgao/hermes-skills-collection `lifestyle/pet-care-tracker` | 开源 Agent Skill（许可见其仓库） | https://github.com/yimgao/hermes-skills-collection/blob/HEAD/lifestyle/pet-care-tracker/SKILL.md | "多宠物登记 + 疫苗/驱虫/体重/就诊结构化记录 + 下次到期自动计算"的高层思路。**未复制其文案与代码** |
| Glumoo-ai/glumoo-pet-health-skill | 开源 Agent Skill，MIT 许可 | https://github.com/Glumoo-ai/glumoo-pet-health-skill | "安全第一：先做急诊红旗分诊、再给日常建议；回答附带安全校验"的高层思路。**未复制其文案与代码** |
| dungnotnull/pet-health-care-assessment-agent-skill | 开源 Agent Skill（许可见其仓库） | https://github.com/dungnotnull/pet-health-care-assessment-agent-skill | "按公认兽医框架（AAHA/WSAVA/五域模型）多维度评估养护"的框架思路。**未复制其文案与代码** |

## 声明

1. **借鉴思路，实现与文案均为原创**：以上来源的具体文案、原文表述、规则代码均未被复制。本插件的 skill 方法论文案、审计规则、命令流程、hook 脚本均为独立撰写。
2. **兽医知识口径**：本插件涉及的疫苗种类、驱虫频率、禁忌食物等常识性内容为公开兽医常识的独立整理，具体医疗方案请以执业兽医意见为准；本插件所有健康建议均附带"仅供参考，请遵医嘱"声明。
3. **未核实项**：未逐一核实各来源仓库的许可文本细节；引用链接以 2026-10-11 访问时为准。
4. **不编造**：本文件未编造任何数据、star 数、排名。

## 本插件自身的许可

本插件原创部分采用 MIT 许可（见 `LICENSE` 文件），版权所有：刘洪光（https://github.com/lhg-skills）。
