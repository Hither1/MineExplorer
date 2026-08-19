# 我们的 `prolong` arm 是不是论文里的 PRO-LONG？——实现保真度审计（中文版）

英文完整版见 [PROLONG_FIDELITY_AUDIT.md](PROLONG_FIDELITY_AUDIT.md)；轨迹分析见
[BEHAVIOR_helixon_4hop.md](BEHAVIOR_helixon_4hop.md)。对照材料：论文 arXiv 2607.20064
（Fox, Wang, Rosu, Dhingra，原始在 ARC-AGI-3 上）、上游代码 github.com/alexisfox7/PRO-LONG
（2026-08-19 的 main）、上游公开的一条 Fable-5 完整 episode 日志（`release_logs/fable5/ar25/rep1`），
以及我们 14 个跑完的 prolong cell（`outputs/{c4h,q35}-prolong-codex-*`）。

## 一句话结论

**"外壳"移植是忠实的**——actions.json 计划队列、同一分隔符的 append-only 日志、AGENTS.md 系统提示、
`codex exec resume` 会话与溢出冷启动、沙箱工具面（含 Python）、log-window / stateless 消融——
**但论文归功的那套机制没有被用起来**，原因有三层叠加：

1. 论文的日志里每步都有**完整的文本观测**（无损的 64×64 棋盘）；我们的日志每步只有 5 个数
   （`pos/pitch/yaw/moved`）和一个 PNG 路径——日志里几乎没有值得"程序化解析"的东西。
2. 上游三个让**进度显眼、能打断陈旧计划**的机制没有移植：每个 action 表头的 `Score:`、分数变化时
   **清空队列并立即重新分析**、以及把 agent 自己的 briefing 写进日志。
3. 27B 模型根本不去碰论文收益来源的那些工具：497 个 analyzer turn 里 **Python 0 次、笔记文件 0 个、
   grep/sed/awk 24 次、`tail` 463 次**，70 个 turn 连日志都没读就写了计划；论文 Table 3 里 PRO-LONG 的
   工具分布是 Python 60.6% / 日志解析 20.3% / workspace 19.1%，Fable-5 公开 episode 22 个 turn 里 Python 45 次
   还维护着 notes.md。

所以我们这条 arm 实测的是"**带滑动文本窗口和续接对话的计划队列 agent**"，它相对直接 arm 的优势
（26 vs 20–21 / 56）来自计划粒度（BEHAVIOR §3.5），不是程序化记忆。

## 1. 论文/上游的机制清单（可核对项）

| # | 机制 | 上游位置 |
|---|---|---|
| M1 | 完整结构化日志：每个 action 一段，表头 `Action N \| Level \| Attempt \| Plan Step i/T \| Score: S`，agent 的 `[PLAN]`，`Tool Call`，以及**完整文本观测** `[POST-ACTION BOARD STATE]`（公开 episode 里 266 个 action 对应 266 个棋盘） | `runner.py:322-330, 488-513`；`swarm.py:58,280` |
| M2 | 编码 agent 被要求**程序化解析**日志，工具 Read/Write/Edit/Bash/Grep/Glob + Python。Table 1：只读 23.1% → +grep 27.2% → +Python 38.3% → +Write/Edit 41.2% | `prompts.py:52-58` |
| M3 | 持久 workspace 存笔记/脚本。Table 2：清空 workspace 只让 PRO-LONG 掉 0.5 分，no-log 掉 4 分——记忆在日志里，不在笔记里 | `codex_agent.py:449-460` |
| M4 | 计划队列：1–15 个 action；"测新假设时用 1–2 个，验证过的序列再放大"；队列空了才调 analyzer；5 次带提示重试后无限退避 | `prompts.py:74`；`runner.py:106-135, 270-296` |
| M5 | **进度打断计划**：表头有 `Score:`；分数变化**清空剩余队列**并立即重新分析；WIN 结束游戏 | `action_queue.py:55-62`；`runner.py:113-114, 335-375` |
| M6 | **agent 的分析写进日志**：briefing 写一次，2–3 句 plan 写进它管辖的**每一段**，直到下一次分析 | `game_state.py:26-62`；`runner.py:457-458, 497-508` |
| M7 | 每局一个 codex 会话，之后 `codex exec resume`；溢出→丢会话、在 logs.txt 上冷启动 | `codex_agent.py:207-221, 381-406, 476-486` |
| M8 | 消融：`--log-window N` 把截断日志拷进独立沙箱；`-1` = **无日志、当前棋盘进 prompt**（论文的 No-Log 对照）；stateless | `base.py:33-51`；`codex_agent.py:295-333, 336-380, 417-424, 449-460` |
| M9 | 论文的对照是**同一个编码 agent 去掉日志**（+18.0 pp），成本对照公开 harness（少 4.2–5.8× token） | 论文结果节 |
| M10 | 适用域：前沿模型、无损文本观测、"当前棋盘不能决定动态"的游戏收益最大 | 论文分析节 |

## 2. 逐项对照（上游 / 我们 / 我们跑出来的证据 / 结论）

| 项 | 上游 | 我们 | 证据 | 结论 |
|---|---|---|---|---|
| M1 日志内容 | 每步完整文本观测 | `[STATE] pos pitch yaw moved` + `[FRAME]` 路径；没有背包、快捷栏、手持物、生命、水中、准星方块（`info` 里有 inventory，`inventory_has` 规则就是靠它评分） | analyzer 只 `tail` 10–30 行（中位 20 = 最近 2–3 段）再看那一张附图；16/42 死在挖掘 hop 的 cell 从不知道手里拿的是什么 | 领域所迫的偏离，但**欠移植**：`info` 里能文本化的都没写。修 R1 |
| M1 表头 | 每段有 `Score:` 和 `Plan Step i/T` | `Action N \| Step S`，无进度字段 | 300 段的日志里 `[MILESTONE]` 只出现两次（c4h-0306：第 17 行 NOT、第 387 行 HAS）；没有 cell grep 过它 | **缺失**。修 R2 |
| M5 进度打断 | 分数变化清队列、立即重析；WIN 结束 | 不清队列；`[MILESTONE]` 只在变化时写；episode 只靠 agent 的 ESC 结束 | c4h-0306 第 52 步 4/4 完成后继续把计划跑到 300（又 21 个 turn）；下一个 turn 的 `tail -20` 离"HAS verified"那行差约 10 段 | **缺失**。修 R2 |
| M6 分析入日志 | briefing 一次 + `[PLAN]` 每段 | 只写 `[PLAN]`（或末 400 字符）一次 | 推理只活在续接的 codex 对话里，溢出重置就没了；`grep PLAN` 只能得到 2–3 句 plan | **缺失、便宜**。修 R3 |
| M2 工具 | 同 + Python | 同样工具面，沙箱内 Python 有自检 | **0 python / 0 笔记 / 24 grep / 463 tail / 503 次写 actions.json / 6 次 view_image；70 个 turn（63 个 Qwen3.5）不读日志** | 表面忠实，机制未用（§3） |
| M4 队列 | 1–15 个单 tick action；5 次重试+退避 | 1–15 条 × `repeat`≤20，每计划 ≤40 tick；3 次重试后**空操作一步** | 每 turn 11.1 步（3.8）/ 5.8 步（3.5）；repeat=20 冲刺对 4 格目标过冲 | 适配合理；重试语义不同（R6） |
| M7 会话 | resume + 溢出冷启动 | 同 + compaction 计数须为 0 | 14 个 cell overflow_resets 0、compactions 0 | **忠实** |
| M8 消融 | 窗口 / `-1` No-Log / stateless | 窗口与 stateless 已强制执行；**没有 `-1`** | 本轮没跑 | 0/N/stateless 忠实；**论文的对照 arm 缺失**（R5） |
| M9 对照 | 同一 agent ± 日志 | `prolong×codex` vs `default×vllm`（不同 agent 循环、不同通道；`default×codex` 任何帧数都卡死） | — | **不是论文的对照**；R5 补上 |
| 给 analyzer 的观测 | 只有日志 | 每 turn 附当前帧 | frames_attached == turns | 有意的偏离（finding #30），合理 |
| 沙箱 | docker + full-access | bwrap + workspace-write + SAFE_CODEX_FLAGS | 自检 43 项 | 威胁模型忠实、更严 |
| M10 适用域 | 前沿模型、文本棋盘、依赖历史 | 27B、像素+5 个数、下一步几乎由当前画面和位置决定 | 失败在挖掘/瞄准、指南针、假完成（BEHAVIOR §3.1–3.3），没有一个是检索失败 | 三个轴都在论文域外 |

## 3. 为什么机制无处着力

1. **日志不是观测**。ARC 里棋盘就是世界且是无损文本；论文的论点是编码 agent 搜索完整文本历史比塞进
   context 更好。我们的日志每步信息是 `pos/pitch/yaw/moved`，世界在 `frames/*.png` 里，不可 grep，
   而 analyzer 497 个 turn 只回看了 6 次旧帧。`tail -20` 已经穷尽日志对近期的全部描述——用 `tail`
   是理性的，不是懒，是日志薄。这与 finding #30（这条 arm 曾经盲走）是同一件事的另一面：强制附帧之后，
   像素负责感知，日志只剩里程计。
2. **`info` 里能文本化的部分是有意不写的**。移植设计成与 baseline 信息对齐（"arm B 不增加信息"），
   于是 baseline 只能从像素读的背包/快捷栏/手持物没有进日志。作为对 `default` 的**单变量比较**这是对的；
   作为对论文的**保真**这是错的——论文前提就是"环境返回什么就以文本记什么"。两者冲突，只能由用户排序。
3. **日志里没有任何一处说"你有进展了/你完成了"**。论文 agent 每次 tail 都看到 `Score:`，runner 一有分数
   变化就砍掉计划；我们把任务级 yes/no 埋在一条每局只变两次的 `[MILESTONE]` 里，还让 40 tick 的程序在
   环境已验证完成之后继续跑完。逐 hop 进度没写在任何地方（harness 的 `milestone_status` 有，但没有任何
   arm 收到——BEHAVIOR §5.2）。
4. **模型**。Qwen3.5 在 320 个 turn 里 63 次不读日志就写计划、每 5.8 步重规划；Qwen3.8 每 turn 都读尾。
   两个都没写过脚本或笔记。论文的消融说笔记对**它们的模型**可有可无；对 27B 是否该强迫写笔记没测过。
   托管 gpt-5.6 arm 是分离"移植问题"和"模型问题"的手段（task findings #19、#34：无提示协议下 0313/0802 3/3），
   但没在 4-hop 上跑过。

## 4. 对 claim 的含义

- prolong 在 4-hop 上的领先（26/56 vs 21、20）作为观察是真的，但**不是"程序化记忆"的证据**：机制没被用。
  领先来自计划粒度和更少的逐 tick 决策（BEHAVIOR §3.5），代价是过冲和踱步。
- 忠实移植也修不了主要失败：挖掘/瞄准（16/42）、指南针（prolong 三个 0311 全往西）、假完成，都是感知、
  机制、校准问题，搜日志救不了。保真能买到的是有界的：R2 去掉完成后的浪费步并给出 hop 进度；R1 给挖掘 hop
  它缺的那一个事实（手里有什么）；R3 让记忆熬过溢出。
- 想 claim"PRO-LONG 的记忆在 MineExplorer 上有没有用"，论文式的比较是 `prolong` vs
  `prolong --log-window -1`（同一 codex agent、同一张帧、无日志）——R5，而不是 `prolong×codex` vs
  `default×vllm`（同时换了 agent 循环、通道和帧数）。现在的配对回答的是"我们的计划队列 codex arm 能否胜过
  20 帧 vLLM baseline"，是个好问题，但不是同一个问题。

## 5. 建议的改动（按顺序）

都很小；测试是 1–2 个场景 × 1 seed（2026-08-19 12:40 每张卡上都跑着别的训练任务，下面没有一项对模型跑过）。
**本次提交已落地并被 `prolong_mc/selftest.py`（167 项）覆盖：R2 任务级版本、R3、R5、R6。**
R1、逐 hop 的 R2、R7 等待下面点名的决策。

- **R1 —— 把能文本化的观测全部写进 `[STATE]`**（上游 M1）：快捷栏内容+选中槽+手持物、背包 `name:count`、
  每步背包增量（`+1 white_carpet`），`info` 有的话还有生命/饥饿/是否在水中。保真收益：这就是"棋盘"。
  代价：打破与 `default` 的信息对等（default 只能从像素看快捷栏）——是决策，不是补丁。测试：0763、0603，
  analyzer 会不会在第一个挖掘程序前选镐子槽，挖到的地毯会不会出现在下一个计划里。
- **R2 —— 让进度显眼并能打断**（上游 M5）：每段表头写验证状态（提示协议下 `| Verified: yes/no`；协议允许
  的话写逐 hop），**状态变化时清空队列、立即重析**。任务级版本无需决策（同一个 bit，写到 `tail` 看得见的
  地方）；逐 hop 版本就是 BEHAVIOR §5.2 的协议决策。测试：c4h-0306 应在第 52 步后一个 turn 内 ESC。
  **已落地（任务级）**：表头 `Action N | Step S | Plan Step i/T | Verified: yes/no`、变化即 flush+重析、
  `prolong_vision_audit.json` 里的 `plan_flushes`、系统提示里的标记说明。
- **R3 —— briefing 写一次、`[PLAN]` 写进每段**（上游 M6）。无需决策。**已落地**：
  `EpisodeLog.set_plan(plan, briefing)`、`CodexTurn.split_briefing`。
- **R4 —— 不要替 agent 做解析**。BEHAVIOR §5.5 建议在每个 turn 的 prompt 里放最近 N 条 `[STATE]` 的
  runner 端摘要——那是论文没有的"辅助"（论文 agent 自己算，Table 1 把功劳记给了"算"）；要加就叫
  `prolong-assisted`，不能与忠实 arm 合并。建议等 R1–R3、R5 测完再说。
- **R5 —— 移植论文的 No-Log 对照**（`--prolong-log-window -1`，上游 M8/M9）：无 `logs.txt`；当前 `[STATE]`
  行和当前帧进 prompt；workspace 持久；会话语义不变。这样记忆架构效应 = `prolong` − `prolong-nolog`，
  同通道同模型，是论文自己的对比；`default×vllm` 仍是外部 baseline。**已落地**：`SYSTEM_PROMPT_NOLOG` +
  `NOLOG_*_PROMPT`，`EpisodeLog.publish(window=-1)` 删掉日志和除当前帧外的所有帧，
  `ProlongAgent._state_text` 把 `[STATE]`、`Verified:`、动作数、上一动作放进 prompt。
- **R6 —— 重试语义**：5 次带提示重试（上游 M4 是无限退避，在这里会挂死 episode，所以之后仍是空操作一步）。
  **已落地**：`analyzer_retries=5`。
- **R7 —— 跑一次托管 gpt-5.6 的 prolong 七场景**作为能力上限：它若用 Python/grep/笔记并读到 `[MILESTONE]`，
  差距在模型；若也只 `tail`，问题在日志。代价：API 费用与 150 KB/s 出口（纯文本，够用）；是决策。
- 保持原样（已验证忠实或有理由）：会话/续接/溢出处理、沙箱与工具面、消融强制执行、强制附当前帧、
  `repeat`/步数上限、ESC/验证措辞（finding #28 有意选择的协议）。

不建议：放弃 codex 通道或直接对 `/v1/chat/completions` 重写循环（task plan 里的兜底）。通道是忠实的；
日志薄和模型习惯才是发现，R1–R5 都在同一 harness 内解决。

## 6. 数字来源

工具分布：`outputs/{c4h,q35}-prolong-codex-*/**/codex_turns/turn_*.events.jsonl` 里每个
`item.completed`/`command_execution` 事件（去掉 timeout），按正则分类。497 turn、1001 条命令：写 actions.json 503、
tail 463、head/cat 10、grep/sed/awk 24、ls 1、python 0。`tail -N` 的 N：10 60 次、15 79、20 126、25 38、30 112、
40 29、≥50 19。不读日志的 turn 70（c4h 7、q35 63）。workspace 文件来自 `prolong_workspace_files.txt`；view_image、
overflow 来自 `prolong_vision_audit.json`。上游 episode 的分布来自 `release_logs/fable5/ar25/rep1/logs_analyzer.txt`
的 `[TOOL USE: …]` 块与 `workspace/notes.md`。论文数字引自 arXiv 2607.20064v2（Table 1–3、方法节）。
