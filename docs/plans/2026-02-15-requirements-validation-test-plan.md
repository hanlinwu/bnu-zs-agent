# 招生智能体需求逐条验证测试计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按《docs/需求分析.md》逐条验证当前实现状态，执行自动化测试，发现并修复阻断性缺陷。

**Architecture:** 采用“需求矩阵 + 多层测试”方法：先做静态实现核对（接口/服务/页面），再跑自动化命令（后端单测、前端构建），最后形成逐条结论（通过/部分通过/不通过）与缺口清单。

**Tech Stack:** Vue 3 + Vite + TypeScript, FastAPI + SQLAlchemy + Redis + Celery, Pytest

---

## 范围与准入
- 文档基线：`docs/需求分析.md`
- 代码基线：`client/` + `server/`
- 测试目标：
  - 功能正确性（核心流程可用）
  - 需求覆盖度（逐条映射）
  - 构建可交付性（后端测试、前端构建）

## 测试策略
1. 静态验证：用代码证据验证需求是否有对应实现。
2. 自动化验证：运行现有后端单元测试与前端构建/类型检查。
3. 缺陷处理：遇到失败先定位根因，再最小改动修复并回归。
4. 结论分级：
   - `PASS`：有实现且已有自动化验证通过。
   - `PARTIAL`：有实现但验证不足/存在流程缺口。
   - `FAIL`：未实现或明显不符合需求。

## 需求逐条测试矩阵
1. 用户注册登录（手机号+短信）
- 检查点：`/api/v1/auth/sms/send`、`/api/v1/auth/login`、短信 mock、管理员登录链路。
- 命令/证据：静态核对 `server/app/api/v1/auth.py`、`server/app/services/sms_service.py`、`server/app/api/v1/admin_auth.py`。
- 通过标准：用户短信登录可用；管理员采用用户名密码(+可选MFA)登录。

2. 智能对话主体功能
- 检查点：聊天接口、风险兜底转人工、角色差异化提示词。
- 命令/证据：`server/app/services/chat_service.py`、`server/app/api/v1/chat.py`。
- 通过标准：对话链路具备敏感词/风险判断、角色提示、流式返回。

3. AI 幻觉防控
- 检查点：风险分级、双模型审查、敏感词过滤、引用溯源。
- 命令/证据：`test_chat_services.py`、`chat_service.py`、`review_service.py`、`admin_sensitive.py`。
- 通过标准：风险与敏感词有效；审查闭环可执行；来源引用可返回。

4. 模糊意图识别与追问引导
- 检查点：动态追问推荐2-3条、上下文记忆。
- 命令/证据：`SuggestQuestions.vue`、`chat_service.py`。
- 通过标准：推荐问题与上下文为动态生成而非静态模板。

5. 知识库与内容管理
- 检查点：多格式上传、审核流、切片+embedding、可追溯字段。
- 命令/证据：`knowledge.py`、`file_parser_service.py`、`tasks/*.py`。
- 通过标准：上传/审核/解析入库完整可运行。

6. 多媒体内容集成
- 检查点：官方素材上传、审批、检索并嵌入对话。
- 命令/证据：`media.py`、`Media.vue`、聊天服务是否注入媒体检索。
- 通过标准：媒体全流程可用，且对话中支持媒体结果融合。

7. 时间感知与话术调整
- 检查点：按月份切换策略。
- 命令/证据：`calendar_service.py`、`test_chat_services.py::test_default_period_mapping`。
- 通过标准：月份分段符合需求文档。

8. 人文关怀与情绪支持
- 检查点：情绪识别与安慰前缀。
- 命令/证据：`emotion_service.py`、`test_chat_services.py`。
- 通过标准：焦虑/迷茫/挫败识别命中并触发话术。

9. 多模态输入支持
- 检查点：用户侧上传图片/PDF/DOC并用于问答。
- 命令/证据：用户聊天输入组件、后端用户上传接口。
- 通过标准：用户端上传->解析->问答闭环可用。

10. 系统管理与运维
- 检查点：多模型接入、日志审计、RBAC。
- 命令/证据：`admin_model.py`、`admin_log.py`、`core/seed.py`、`admin_role.py`。
- 通过标准：配置/日志/权限链路完整。

11. 前端体验与设计
- 检查点：首页高频问题、对话历史、标题编辑与自动生成、响应式、无障碍、夜间模式字体调节。
- 命令/证据：`HotQuestions.vue`、`AppHeader.vue`、`conversation.ts`、`theme.ts`、`useAccessibility.ts`。
- 通过标准：交互与需求一致且类型/构建通过。

12. 性能与非功能
- 检查点：首屏<1.5s、响应<2s、离线缓存、HTTPS与合规。
- 命令/证据：代码与配置静态核对；需补充压测与浏览器审计。
- 通过标准：有可复现的性能/安全测试报告。

## 执行命令（自动化）
- `cd server && .venv/bin/pytest -q`
- `cd client && npm run build`
- `rg`/`sed` 静态证据扫描（需求映射）

## 缺陷处理策略
- 先复现：保存失败命令与报错。
- 再定位：仅针对失败点相关文件分析。
- 后修复：最小改动，避免连带回归。
- 回归：至少重跑失败命令 + 全量基线命令。

## 交付输出
- 测试计划：`docs/plans/2026-02-15-requirements-validation-test-plan.md`
- 执行报告：`docs/plans/2026-02-15-requirements-validation-report.md`
- 缺陷修复清单：git diff + 回归结果
