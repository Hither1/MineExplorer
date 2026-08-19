# 三条 arm 在 strict 4-hop 场景上到底在做什么（轨迹分析，中文版）

英文正文见 [BEHAVIOR_helixon_4hop.md](BEHAVIOR_helixon_4hop.md)；分数见
[RESULTS_helixon_4hop.md](RESULTS_helixon_4hop.md) / [RESULTS_helixon_4hop_qwen35.md](RESULTS_helixon_4hop_qwen35.md)。
证据文件：`traj_analysis_4hop/`（逐步 digest、PRO-LONG 逐轮 transcript、指标表、7 份逐场景报告），
解析脚本 `scripts/analyze_4hop_traj.py`。目的不是重新排名（每 cell 一个 seed），而是找出每条 arm 的
**系统性**问题和它们指向的修复。

## 数据与方法

42 个 cell（default / hypothesis / prolong × 7 场景 × Qwen3.8 / Qwen3.5）。从 runner log 解析每一步的位置、
yaw、pitch、动作、thought、memory 和每个 milestone 的规则状态，并按场景 metadata 算出每一步到每个目标的
距离与朝向误差；PRO-LONG 另外解析 `logs.txt` 的程序和 codex 事件流里的分析器 briefing；hypothesis 解析
最终 DAG。之后 7 个 read-only 子代理逐场景对比 6 个 cell（`traj_analysis_4hop/scene_reports/`），关键论断再
对着原始数据核对（不成立的丢弃）。

## 总结论：分差小，行为差异大；丢 hop 的机制在三条 arm 里是同一批

按丢掉的 hop 数排序：

**1. 挖掘 / 工具 / 瞄准（三条 arm 都被卡，损失最大）**
- 42 个 cell 里 16 个（default 5、hypothesis 5、prolong 6）卡在第一个 `inventory_has` 类 hop；整个 campaign
  只有 **1 个 cell 挖到过东西**（q35-prolong-0603：地毯 step 42、石英 step 253）。没人挖到 magma / 苔石 /
  粉混凝土 / 6 块紫混凝土。
- 三个原因：**看不见 hotbar**（0763 镐子在第 3 格，c4h-prolong 看着物品栏截图选了 `hotbar.2`（栅栏门），砸紫
  混凝土砸了 ~170 步，step 231 才换到 slot 3 破一块；0182 q35-prolong 本来握着镐子，砸了 100 步没对准，然后把
  截图读成"slot1 是圆石、没有镐子"——那帧里镐子明明在 slot 1——于是主动换掉镐子去砍树想做石镐）；**瞄准无
  反馈**（c4h-prolong-0482 站在小屋里对着苔石左右两侧的石砖墙砸了 200 tick；c4h-prolong-0603 把红楼梯顶面
  当石英砸）；**攻击不连续**（直连 arm 通常按 1–3 步就重新决策；prolong 程序 5–20 tick 但轮间穿插转视角，
  进度归零）。
- 唯一成功的例子说明了要什么：地毯要 pitch 60°、离 1 格、`attack×5`；石英是停止调视角、`forward+attack×10`
  走到贴脸再 `attack×10`，第 8 个连续 tick 才碎。

**2. 罗盘 / yaw 混淆**
- 任务文本用 east / ahead / behind，checker 用绝对坐标，但没有任何 arm 被告知 Minecraft 的 yaw 约定
  （0=南、90=西、−90=东）。Qwen3.8 的 PRO-LONG 分析器在 briefing 里写了 24 次 yaw→方向，**23 次是错的**
  （它认为 0=北、90=东）。结果：0311 两个 checkpoint 的 prolong 和 c4h-hypothesis 全部**向西**走进天然森林
  找"东边的河"（q35-prolong 走出 43 格，还在森林里宣布 "Excellent! I can see the river now!"）；0182
  c4h-prolong "face north"（实际朝南）冲出 27 格，从旗帜旁 4 格处背对着经过。直连 arm 没有 yaw，只能靠 x/z
  增量猜方向；q35-default-0306 在 step 8 转了 90° 之后再没回到走廊轴线（3/4）。

**3. 假完成 + 信念锁死 + ESC 行为**
- checker 要"走近 + 朝向"或物品栏变化，agent 把"看见"或"发出了动作"当完成，且没有 per-hop 反馈纠正。
  q35-hypothesis-0306 在 step 13 就按 ESC（"I have visually confirmed all sub-goals"，离出生点 3 格），共 69 次
  被拒后 step 194 才走到橙旗；q35-default-0763 **一个 attack tick** 之后写下 "I have successfully mined the
  purple concrete block"，剩下 280 步去建圈；q35-hypothesis-0603 从 step 98 起按了 **202 次 ESC**，每步都读到
  "NOT verified" 却坚持 "visual evidence shows the block has broken"。
- 直连 arm 8 个挖掘场景 cell 里 9/16 在 memory 里写着 "mined X" 而物品栏为空；memory 字符串逐步复制把错误
  锁死；hypothesis 在 `on_esc_rejected` 把节点降级后**下一步就重新 confirm 到 1.0**。ESC 总计：default 152 次
  /151 拒，hypothesis 320/318，prolong 13/13。
- 另一种 ESC 是**放弃**（c4h-default-0311 从 step 172 起 84 次 "permanently stuck in this river channel"）。
- PRO-LONG 反过来：几乎不按 ESC，且**看不到已验证**——c4h-0306 在 step 52 已 4/4，[MILESTONE] "HAS
  verified" 行只写一次就滚出 `tail -40` 窗口，分析器从不 grep，于是在走廊里南北来回踱了 248 步（"I can see
  the orange banner ahead… let me continue forward to reach the chamber"）。q35-0306 是反例：turn 7 grep 到了
  MILESTONE，step 56 ESC。

**4. harness 自己的运动提示在"喊狼来了"（仅直连 arm）**
- "NOT moved… likely blocked" 在任何位移 <0.05 的 tick 都触发（包括每个纯转视角步），8 步 "circling" 警告在
  净位移 <1 格时触发（扫视、挖掘、水里都会）。实测 28 个直连 cell：circling 警告出现在 **56–62% 的步**，
  NOT-moved 20–36%，而真正被挡（移动动作却零位移）只占 5–13%。
- 模型信了：**44–71% 的纯转视角步之后下一步 thought 说"我卡住了"**；c4h 两条 arm 66% / 78% 的 thought 含
  stuck/blocked，其中 31% / 38% 发生在正常移动（≥0.15 格/tick）时（0306 c4h-default step 3–6："BARELY MOVING -
  only 0.3 blocks after 2 sprint steps. May be blocked" → 开始横移转向而不是沿走廊走）。在水里更糟：0311 岸边
  q35-hypothesis 把"8 步不到 1 格"读成"撞上垂直河岸"，退后、转身，然后相信自己"已经过河到了平原"（step 69，
  实际在 x=5.7 向西南走）。PRO-LONG 看到的是每 tick 的 `moved=`，只在天然森林里犯几次这种错。
- 另外没人被告知尺度（冲刺 0.28 格/tick），"moved 0.28" 被两边都当成失败。

**5. 决策粒度：逐 tick 重决策 vs 程序**
- PRO-LONG 的 `repeat` 让它到 hop1 / hop2 的中位步数是 **10.5 / 34.5**（default 29.5/108，hypothesis
  17.5/79.5，已剔除 0763 hop1 和 0603 假 hop）；0726 c4h prolong 用 `forward+sprint+jump` 块游过水道 4/4，而
  c4h 两条直连 arm 都没下水（default 沿岸向西漂到 x=−5.2 站了 220 步）。
- 代价：15–20 tick 的盲程序冲过房间（0306 c4h 每次冲出走廊到森林），转向粗（±45–90°），±22.5° 的朝向规则靠
  运气（0726 q35-prolong 在海草点 5 格内待了 107 步从没朝向它）；Qwen3.5 上分析器每 3–6 步就重规划（0482：
  92 轮，最后 19 轮逐字重复 "I've moved closer to the oak room…"）。

**6. benchmark 本身的缺陷（先修再加 seed）**
- **0603**：最后一条命令 `/tp @p ~0 ~1 ~5` 在记录 spawn 之前把玩家挪了 5 格，所以所有 position 目标整体偏南
  5 格：`find_purple_bed` 目标在卧室南墙外 3 格，而床就在出生点正前方 1 格（c4h-default step 3 "I can see a
  purple bed in the bottom center"，到目标距离 6.0）。三次"完成"都是站在南墙附近朝南的假阳性；只有两个挖掘
  hop 是真的。
- **0311**：平台西沿离出生点只有 5 格，天然森林 / 河充满视野；"河"是铺在 y=0 的一层水源（水面高于河岸、向
  两侧漫流），c4h-default 在 x≈9 处陷到 y≈−0.5 出不来 250 步（沙子塌陷或水流，推断）；hunt 两个 hop 预满足
  （已知）。没人到过平原。
- **0763**：`build_animal_pen` 数的是草地里 ≥6 块 **purple_concrete**，任务文本却说用栅栏；hop4 按文本做不可能
  拿到。
- **0726**：`find_seagrass` = 距水下一个点 ≤5 格且朝向 ±22.5°，直着游过去必然背对它。
- **0182**：hop3–4 要镐子、挖 magma、7 格熔岩桥，300 tick 里没有 cell 过得了挖掘。
- harness：每局第一帧是 128×128 的 reset 观测（之后 640×360）；milestone 提示只有任务级；`validate_action`
  把不带方向的 sprint/sneak 悄悄变成空动作（少见）。

## 三条 arm 各自的画像

| | default | hypothesis | prolong |
|---|---|---|---|
| milestones（/56） | 21 | 20 | 26 |
| hop1 / hop2 中位步 | 29.5 / 108 | 17.5 / 79.5 | **10.5 / 34.5** |
| 每 cell 中位路径长（格） | 36 | 41 | 20 |
| 动作构成 move/turn/turn+move/jump+move/attack (%) | 55/16/5/7/11 | 53/17/4/6/8 | 42/7/0/14/34 |
| ESC 按下 / 被拒 | 152/151 | 320/318 | 13/13 |
| "stuck" thought 占比（其中正常移动时的比例） | 66%（31%）c4h，41%（29%）q35 | 78%（38%），25%（25%） | 少 |
| 挖掘场景 cell 中有假 "mined X" 信念 | 4/8 | 5/8 | [PLAN] 里 0，briefing 里 0482 两次 |
| 分析器轮数（步/轮） | – | – | c4h 176（11.1），q35 320（5.8） |

- **default**：逐 tick 重决策、没有 yaw / 物品栏 / per-hop 反馈；memory 把 hop 列表记得不错，但把每个错信念
  一起带下去；被提示牵着"脱困"（跳、退、横移）反而离目标越来越远；认为完成或"永久卡死"就刷 ESC。
- **hypothesis**：和 default 同一个循环，DAG 从未改变过任何动作。DAG 内容 = step 1 建的 4 个 hop 脚手架 +
  大量马达层面的"有个低矮障碍挡着我"式假设 + 复述目标；置信度不随结果更新（0311 c4h "砍树能开路" 46 个
  attack tick 无进展仍 0.65）；Qwen3.8 上 26–75 节点、中位置信 0.1–0.3，Qwen3.5 上 4–37 节点、0.5–1.0，两种
  形态分数一样。唯一"帮到"的一处（0311 q35 诊断出 turn+move 耦合）是把 prompt 里的规则复述了一遍。代价：
  输出翻倍、Qwen3.5 上 ESC 刷得最凶。
- **prolong**：快、粗、有承诺；但论文里的"程序化记忆"没发生：14 个 workspace **0 个笔记文件**、6 次
  `view_image`、496 轮里 465 次 `tail` vs 20 次 `grep`、`grep MILESTONE` 只有 q35 的 3 轮。真正承载状态的是
  被 resume 的 codex 对话（历次 briefing + tail 输出），所以对话里一旦充满"chamber 在前面"就一直重复。加上
  yaw 标错、看不见 hotbar、盲瞄挖掘。

## 建议的修复（按能拿回的 hop 排序，每条都能在 1–2 个场景 × 1 seed 上先验）

1. **把 agent 看不见的游戏状态以文本给出**（runner 的 `info` 里都有）：hotbar 内容 + 选中格 + 手持物、物品栏
   增量（"+1 white_carpet"）、准星下方块及破坏进度（sandbox 若给不出，至少"同一方块连续攻击 n tick"）、数值
   yaw + 图例（"yaw −90 = 东(+x)"）。验证：0763 + 0603 上 default 与 prolong 是否 20 步内选到 slot 3、地毯是否
   挖到。
2. **hint 协议下给 per-hop 验证反馈**（"hop1 find_granite 已验证@10；hop2 未"）——直接消除"看见=找到""动作=
   结果"和绝大部分 ESC 刷屏。它改变了 benchmark 的"隐式"约定，算 protocol 变体而非补丁，但现在跑的 hint 协议
   本来就不是论文协议。
3. **重校运动提示**：只在移动动作之后报 NOT-moved；circling 阈值按动作构成缩放（最近 8 步多为转视角/攻击或人
   在水里时抑制）；写明尺度（冲刺 ≈0.28 格/步）。验证：0306 + 0726 default，纯转向步之后的 stuck 叙事应从
   ~65% 降到接近 0，水道应能过。
4. **机制一句话**进所有 prompt：挖一块要多少 tick、攻击键必须连续按住并对准；游泳 = forward+jump；脚下的方块
   要 pitch ~60°；"find" = 走到 3–5 格内并看着它。
5. **PRO-LONG 专项**：每轮 prompt 里直接放 milestone 状态 + 最近 N 条 [STATE] 的解析摘要（位置、yaw→方向、净
   位移、手持物），别指望它 grep；目标在几格内时限制 forward 的 repeat 或加 "turn to face (x,z)" 原语；第一次
   挖掘前强制读物品栏。验证：0306 c4h 应像 q35 一样 ~56 步 ESC；0311 应向东。
6. **hypothesis 专项**：要么去掉 DAG，要么让它干活——把每个 hop 节点绑到 (2) 的 per-hop 验证，环境否定的
   "confirmed" 强制转 refuted 并给理由，禁止下一步重新 confirm 到 1.0；任一 hop 节点未验证时禁止 ESC。
7. **场景**：0603 在 `/tp` 后重记 spawn（或去掉 tp）；0763 pen 规则改数栅栏；0311 / 0182 平台加宽、河做到地平
   面以下；0726 海草规则改 position-only 或放宽；静态 screen 加"重力方块 / 流体高于地面"检查。

(1)–(4) 对三条 arm 都有利，大概率不改变排序，但会抬高天花板：现在 42 个 cell 里 16 个停在挖掘、6 个停在
罗盘，两者都是 harness / prompt 层可修的，不是模型层。
