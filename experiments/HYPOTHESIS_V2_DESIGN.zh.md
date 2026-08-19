# Hypothesis agent v2：让图真的干活（中文版）

英文完整版见 [HYPOTHESIS_V2_DESIGN.md](HYPOTHESIS_V2_DESIGN.md)。配套：
[BEHAVIOR_helixon_4hop.md](BEHAVIOR_helixon_4hop.md)（§3.3、§3.6、§5.6）、
[PROLONG_FIDELITY_AUDIT.md](PROLONG_FIDELITY_AUDIT.md)。分工：`default` 是固定 baseline，不动；
`prolong` 往论文靠；`hypothesis` 是我们在开发的方法——本文说它错在哪、v2.0 改了什么（已落地、有单测、
还没对模型跑过）、v2.1 需要什么决策、先跑什么。

## 1. 4-hop 轨迹对 hypothesis agent 的判断

14 个 cell（7 场景 × Qwen3.8/3.5），20/56 个 milestone，对 `default` 的 21：DAG 没改变任何可测的东西，轨迹说明了为什么。

1. **图是笔记本，不是信念状态。** 节点 = 每局第 1 步建的 4 个 hop 脚手架 + 运动层面的说法
   （"前方地面有个矮方块挡路"，0482）+ 复述目标；置信度从不对照任何东西。0311（Qwen3.8）`h12`
   "打断树干就能开路"在 46 个 attack tick 毫无进展期间一直 0.65。没有一个 cell 里 DAG 选出了纯记忆
   agent 不会选的动作。
2. **目标完成是自封的，而且自封压过环境。** q35-hypothesis-0603：模型在第 98 步把 `h4`"挖到石英"标为
   confirmed 1.0 并按 ESC；harness 拒绝（什么都没挖到——地毯、楼梯、石英三个 hop 都没触发），
   `on_esc_rejected` 把目标降到 0.5；**第 99 步模型把 h1–h4 全部重新 confirmed 1.0 再按 ESC，然后每一步
   都这样直到 300 步**（202 次拒绝）。它的理由："环境状态明确说任务 NOT verified……我必须重发 ESC……
   估计验证系统需要特定触发或延迟"。记忆串（"Mined white carpet (h2). Mined … stairs (h3). …
   Successfully mined the quartz block (h4)"）就是锁，图再把它当既定事实回显。
3. **没有东西给测试设上限。** 计划是自由文本；没人知道某个动作在测哪个假设、测了多久，于是错误的
   机制信念一直跑到模型碰巧改主意为止（按第 1 条，它不会）。
4. 直接 arm 共有的问题——没有 yaw、没有背包、没有逐 hop 验证、"喊狼来了"的移动提示（BEHAVIOR §3.4）、
   挖掘/瞄准盲区（§3.1）——它全有；320 次 ESC（default 152）说明 DAG 让"假完成"更**黏**了。

## 2. v2 的原则

把 DAG 从笔记本变成**harness 能问责的信念状态**：每个节点有 kind；能被检查的 kind 就检查；环境拥有的
东西（目标完成）模型不得宣布；测试中不再动的信念替它退役。动作仍由模型选——图对"做什么"仍是建议——
但对"什么是真的"不再只是建议。

## 3. v2.0 —— 已落地（无需决策，不新增信息通道）

文件：`mc_agent/hypothesis.py`、`mc_agent/hypothesis_agent.py`、`mc_agent/hypothesis_selftest.py`
（32 项，`python -m mc_agent.hypothesis_selftest`）。`default` agent、`mc_agent/context.py`、
`mc_agent/agent.py` 未动；hypothesis 的 prompt 有意改变，所以 `scripts/prompt_layout_check.py --golden`
会报 hypothesis 用例 DIFFERENT——给它们重写 golden，并确认 default 用例仍 IDENTICAL。

| 规则 | harness 做什么 | 针对 |
|---|---|---|
| **kind** | 每个假设带 `kind ∈ {goal, location, mechanism, state, other}`；第一轮回复的脚手架即便忘写也按 `goal`；prompt 里 goal 排最前 | §1.1——把"这是哪一类断言"显式化，规则才有抓手 |
| **目标由环境确认** | 状态行说 NOT verified 时，goal 上的 `confirmed` 被回退成 `active`、置信度 ≤0.9，并写一条 `[harness]` 证据说明原因 | §1.2 前半 |
| **ESC 门 + 锁** | NOT verified 时的 ESC 在到达游戏前被丢弃（harness 本来也会拒），并把模型*自认为已完成*的所有 goal（confirmed 或 ≥0.5）和任何 confirmed 的 `state` 断言压到 0.5 并**上锁**；锁住的节点在环境验证前不能升过 0.5、不能 confirmed；prompt 在节点上标 "locked"，并有一段 *Harness notices*（"你试图结束 episode N 次……；上锁的目标：h1、h2——逐个实地复核，物品只有在快捷栏/背包里才算挖到"） | §1.2 后半——1.0 重确认循环不可能发生；ESC 刷屏只花掉被丢弃的那一步 |
| **测试预算** | 回复里写 `testing: <id>`；非 goal 假设在测试中 25 步（`TEST_BUDGET_STEPS`）置信度不变（±0.05）就标 `stale`、清空计划并在 prompt 里说明；置信度变化或换 id 都重置计时；goal 豁免（找 hop 2 找 40 步是工作，不是执念） | §1.3——0.65 信念上的 46 个 attack tick 最多变 25 |
| **无提示协议** | 没有状态行（`milestone_hint == ""`）时以上都不触发，ESC 放行——论文协议不变 | 两种协议下 arm 都可比 |
| **记录** | 图旁边多一个 `hypothesis_discipline.json`：回退的 confirm、被压的升幅、丢弃的 ESC、上锁事件、预算 stale 的次数、上锁集合 | v2 的 cell 能连着分数一起读 |

Prompt：一段两种 response style 共用的块（`_HYP_DISCIPLINE`）陈述规则并要求 `kind` 与 `testing`；
codex 通道的回复 schema（`hypothesis_reply_schema`）两者都接受。`on_esc_rejected` 保留（走同一个锁），
以防 harness 出于自身理由拒绝 ESC。

v2.0 **不做**的：不告诉 agent 是*哪个* goal 没完成（只有任务级 bit）、不读背包或位姿、不改共享提示。
所以预期效果有界：0603 型 cell 不再把 200 步烧在 ESC 上、被要求去复核，但之后能不能*找到*缺的那件东西，
取决于 §4。

## 4. v2.1 —— 落地到地面（需要信息通道的决策）

这些让 kind 可检验，是真正收益应在的地方；每一项都给了 hypothesis arm 一些 `default` 不渲染的信息，
所以是**声明的方法组件**，不是补丁。harness 的 `info`/`milestone_status` 里全有；改动是给 hypothesis 模式也传
`_agent_extra` 再渲染。

- **位姿落地的 `location` 假设**：位置断言带出生点相对目标或方位（`"at": [dx, dz]` 或
  `"bearing": "west"`）；harness 用真实位置与 yaw 渲染"h3：约 12 格外、方位西；你面朝南（yaw 0）——
  转 +90 面向它"。这是在方法内部做的指南针修复（BEHAVIOR §3.2：prolong 三个 0311 和 c4h-hyp 都把东走成西），
  并给 `location` 节点一段 harness 可评分的真实距离史（在接近/在远离）。代价：baseline 看不到的 yaw + 方位计算。
- **背包落地的 `state` 假设**："地毯在我的快捷栏里"对照 `info["inventory"]` 自动确认/否定并附计数；
  16/42 死在挖掘 hop 的 cell 得到它们缺的那一个事实。代价：文本化背包——与 PRO-LONG R1 同一个对等性问题。
- **`goal` 节点的逐 hop 验证**：有了逐 hop 状态，目标规则就精确了：hop 1 触发那一步 harness 直接 confirm 它的
   节点，被拒的 ESC 只锁*未完成*的 hop。这是对所有 arm 生效的协议改动（BEHAVIOR §5.2），最有价值、也最需要用户拍板。

建议：三项都给 hypothesis arm 用，把 arm 命名为 `hypothesis-v2`（kind + 纪律 + 落地）；以后若要把功劳归到 DAG
本身，再跑一个 `default+grounding` 消融，而不是现在把落地从方法里扣掉。这样 `default` 仍是用户要的固定 baseline，
比较从"prompt 对 prompt"变成"方法对 baseline"。

## 5. v2.2 —— 之后

- **假设驱动的动作程序**：计划步 = 带 `repeat` 的动作程序（PRO-LONG hop-1 速度的来源，BEHAVIOR §3.5），
  每个程序绑定它测试的假设与预期 `[STATE]` 特征；预测失败 harness 提前终止程序。改动更大（逐步接口），放在 4 之后。
- **compact style**：分支的 `--response-style compact` 已覆盖 hypothesis agent；v2 的规则在共用块里，直接适用。

## 6. 先跑什么（等有卡——2026-08-19 每张卡上都跑着别的训练任务）

`hypothesis` v2.0 vs 已跑完的 `hypothesis` cell，1 seed，Qwen3.5-27B（失败最响的 checkpoint），场景 **0603、0763、0306**：

- 0603：第一次 ESC 之后 `esc_dropped` > 0、出现锁；之后的步花在移动/检查而不是按 ESC（对比 202 步纯 ESC）；
  看它会不会回查快捷栏或走回地毯处。
- 0763：镐子/围栏 cell——目标规则能否挡住"挖到围栏"的宣称，测试预算能否退役"就在这儿打"的机制假设。
- 0306：sanity cell（4/4 可达）——hop 数和到 hop 的步数不倒退。

v2.0 的成功标准是行为的（ESC 刷屏消失、锁被执行、预算生效），不是分数 claim；分数问题等 v2.1 和多 seed。
每 cell 成本 ≈ 300 步 × 4–14 s。

## 7. 非目标

`default` agent 及其 prompt；共享的移动/相机提示；场景修复（BEHAVIOR §4）；prolong arm（见审计）。
这里没有任何东西改变论文无提示协议允许 agent 做的事。
