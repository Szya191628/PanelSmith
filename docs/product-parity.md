# 产品能力与演进路线

> 状态：Phase 0–5a + LangGraph + redesign **已完成**；**仅保留 3 个常用简单 Skill**（厚 directives/template/pipeline），拉片等复杂流下线；Review 局部重做已修目标推断与清理范围
> 原则：只做能跑通的 **产品原语**，不做 1:1 的界面临摹，不追闭源模型护城河；复杂实验流不做。

## 能力清单

| 原语 | 现状 | 下一步 |
|------|------|--------|
| Agent 流水线 | Outline / Plan / Render / Compose / Critic 五段接力 | 扩展场景、艺术总监角色 |
| 无限画布 | tldraw comic-workflow，节点随流程投影 | 选中绑定对话 + 局部重做 |
| Skill 库 | 3 个厚工作流（directives + 模板 + 管线提示） | 只增可跑通的工作流，不做薄壳陈列 |
| 视频拉片 | **不做**（产品面已移除） | 近端明确非目标 |
| 创作模式 | review（逐步审批）/ quick（自动跑完） | 文案与入口产品化 |
| 资产复用 | Universe + Asset + StyleTemplate | 强化跨项目继承 |
| 成片输出 | 逐镜视频 → 拼接 → 配音混音 → 条漫 / PDF | 导出规格与批量任务 |

## 分阶段

| Phase | 范围 | 状态 |
|-------|------|------|
| 0 | 能力盘点 + 设计对齐 | ✅ |
| 1 | 首页 Skill 墙 + 项目页导演台布局 + token 收紧 | ✅ |
| 2 | 画布选中 ↔ Agent 上下文 + feedback_entity feedback | ✅ |
| 3 | Skill schema + catalog API 驱动编排入口 | ✅ **深度**：`Project.skill_id` 持久化、directives 注入 outline/plan、默认镜头数/模式 |
| 4 | 视频拉片 | ❌ **产品下线**：catalog/UI/API 已卸；仅保留历史 DB 字段与遗留 service |
| 5a | 九宫格分镜 + 单格重做 | ✅ **深度**：多选批量重做、排序重排 order、`entity_ids` 多格反馈 |
| 宇宙 | IP 宇宙章节 + 共享角色 | ✅ **深度**：自动导入共享卡司、outline/render 宇宙上下文、提升/导入/编辑 UI |
| 5b | 场景 Agent / 真视频上传多模态 / 画布图编 | 默认不做 |

### LangGraph 架构（2026 对齐）

- HITL：`interrupt()` in approval nodes + `Command(resume=…)` only
- Driver：`app/orchestration/driver.py` 抽出 interrupt 循环
- State：`skill_id` / `focus_entity_*` 写入 Phase2State
- Skills（仅 3 个常用简单流）：`story-anime` / `character-design` / `quick-short`
  - 每 skill：`directives` + `story_template` + `pipeline_hints` + 入口 stage/agent
  - 注入 outline/plan system prompt；创建时回填默认 style/镜头数/模式
  - Review：自由文本可解析角色名/镜头号为 target_ids；局部清理不误伤未选实体

- Selection：review `target_ids` → orchestrator cleanup/render 局部重跑
  - 反馈语义路由：对白/设定 → plan；画面/光色 → render；运镜/视频 → compose
  - resume 继承 `project.skill_id`；compose/render 注入实体反馈

## 明确不做（近端）

- 像素级临摹同类产品的界面
- 自建闭源视频模型供应链与积分体系
- 运营级 200+ 风格 / 全量行业 Skill 库存
- 完整移动端导演台
- **拉片复刻 / 真视频上传 / 产品广告等复杂实验工作流**
- 只有 catalog 名、没有 directives/template 的薄壳 Skill

## 前端信息架构（Phase 1）

```
Home
  导演问候 + 一句话开工
  Skill / 模板墙（配置驱动）
  最近入口：项目 / 资产 / 宇宙

Project（导演台）
  TopBar + StagePipeline
  ┌ Agent Rail │ Canvas │ Workspace Sidebar ┐
  │ 任务/阶段   │ tldraw │ Chat / Inspector  │
  │ 选中上下文  │        │ Assets            │
  └────────────┴────────┴───────────────────┘
```

## Design Read

- **Page kind:** 创意生产工具（canvas-first product UI）
- **Audience:** 独立漫剧创作者
- **Vibe:** Comic Workbench（印刷工位 × 导演台）
- **Dials:** VARIANCE 6 / MOTION 4 / DENSITY 6
- **Anti-slop:** 禁止紫渐变 AI 默认、禁止冷灰 SaaS 三栏照搬
