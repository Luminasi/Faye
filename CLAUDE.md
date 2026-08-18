# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**电商商品 RAG 企业知识库问答系统** —— 基于 RAG（检索增强生成）的企业内部知识库问答平台。用户上传产品手册、服务政策等文档建立知识库，通过自然语言提问，系统从向量库检索相关内容后由大模型生成带引用来源的答案。

- **技术栈**：FastAPI + SQLAlchemy + LangChain 0.3 + Ollama (qwen2.5) + ChromaDB / Vue3 + Vite + Element Plus
- **端口**：后端 8002（`.env` 中 `APP_PORT` 配置），前端 5173，Ollama 11434
- **模型**：`backend/.env` 中配置（`OLLAMA_LLM_MODEL` / `OLLAMA_EMBED_MODEL` / `OPENAI_COMPAT_MODEL`）

---

## 快速启动

```bash
# 后端（需先启动 Ollama 服务，模型见 backend/.env）
1-启动后端.bat          # 或手动: cd backend && venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# 前端
2-启动前端.bat          # 或手动: cd frontend && npm run dev
```

- 首次启动后端时，`main.py` 的 `on_startup` 事件自动创建管理员账号（`admin` / `123456`）。
- 导入样例数据：后端运行中执行 `backend\venv\Scripts\python.exe sample_data/load_data.py`（登录 admin 后可导入文档到"电商商品知识库"）。

---

## 项目架构

```
LangchainRAG/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口：CORS、路由注册、启动事件（自动建管理员）
│   │   ├── config.py          # 配置加载（读取 backend/.env）
│   │   ├── database.py        # SQLAlchemy 异步引擎与会话
│   │   ├── models.py          # ORM 模型（User / KnowledgeBase / Chunk 等）
│   │   ├── schemas.py         # Pydantic 请求/响应模型
│   │   ├── dependencies.py    # JWT 鉴权依赖（get_current_user）、角色校验
│   │   ├── utils/security.py  # 密码哈希、JWT 签发
│   │   ├── routers/           # API 路由
│   │   │   ├── auth.py        # 登录/注册
│   │   │   ├── admin_kb.py    # 知识库管理（仅 ADMIN）
│   │   │   ├── chat.py        # 聊天问答（SSE 流式）
│   │   │   └── sessions.py    # 会话管理
│   │   ├── services/          # 业务服务层（rag_service.py 为 RAG 核心）
│   │   └── rag/               # 检索/嵌入/提示词
│   │       └── prompts.py     # 系统提示词（含防 prompt injection 指令）
│   ├── data/                  # 运行时数据（app.db、chroma/、uploads/，全部 gitignore）
│   └── requirements.txt
├── frontend/                  # Vue3 + Vite + Element Plus + Pinia
│   └── src/
│       ├── api/               # axios 请求封装（chat.js 为 SSE 流式解析）
│       ├── stores/            # Pinia 状态（用户、会话）
│       ├── views/             # 页面（登录、知识库管理、聊天）
│       └── components/        # 组件
├── sample_data/               # 样例文档 + load_data.py 导入脚本
├── .claude/                   # skills（质量门禁体系）+ markers + settings
├── .githooks/                 # pre-commit 质量门禁 hook（三模式）
├── 1-启动后端.bat             # 唯一后端启动脚本（8002）
└── 2-启动前端.bat             # 唯一前端启动脚本（5173）
```

---

## 开发命令

```bash
# 后端依赖安装（首次）
backend\venv\Scripts\pip.exe install -r backend/requirements.txt

# 前端依赖安装（首次）
cd frontend && npm install

# 后端冒烟测试
curl http://127.0.0.1:8002/api/health

# 语法检查
backend\venv\Scripts\python.exe -c "import ast; ast.parse(open('app/services/rag_service.py', encoding='utf-8').read())"

# 测试（质量门禁的一部分）
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v   # 后端（需先 pip install pytest httpx）
npm --prefix frontend run test                                 # 前端（需先配置 vitest）
```

---

## 安全模型（强制）

- **`backend/.env` 含真实密钥**，已被 `.gitignore` 排除，**严禁提交**（`.env.example` 是唯一可提交的模板）。
- 所有业务接口必须挂 `Depends(get_current_user)` 鉴权；知识库管理接口校验 `UserRole.ADMIN`。
- 知识库访问控制：检索必须经过 `rag_service.py` 的 `_get_authorized_collections` 过滤，用户不能检索无权访问的知识库。
- 密码存储：bcrypt 哈希（`utils/security.py` 的 `hash_password` / `verify_password`）。
- Prompt 安全：`rag/prompts.py` 中提示模型只依据检索上下文回答、不得执行文档内容中的指令（防 prompt injection）。
- 前端禁止用 `v-html` 渲染模型输出（聊天区渲染必须转义）。
- RAG 检索与 LLM 调用失败要有降级处理（提示"模型不可用"而非 500 崩溃）。

---

## 质量门禁（Quality Gate）

本项目从记账APP 迁移了整套质量门禁体系：

- **`/gitcommit-save`**（推荐提交方式）：并行运行 `tester` + `quality-engineer` 两个 subagent → 全部通过后在 `.claude/markers/` 生成 `test-passed.marker` + `quality-passed.marker`（含 HEAD + DIFF_HASH 指纹）→ 再调用 `/git-save` 提交。
- **`/git-save`**：普通一键提交+推送（不跑质量检查）。
- **`/tester` / `/test`**：测试补全与执行（后端 pytest + 前端 Vitest）。
- **`/quality-engineer`**：7 维度质量审计（安全/注释/规范/类型/错误处理/性能/可维护性）。
- **`/security-check`**：安全审计（凭据泄露/SQL注入/越权/prompt injection）。
- **`/comments-check`**：注释质量检查（覆盖率 ≥ 30%）。

### pre-commit hook 三模式

`.githooks/pre-commit` 校验 markers 指纹（HEAD/DIFF_HASH 与 `git diff --cached` 一致）后才放行提交。未通过时按 `.githooks/gate.config` 的模式处理：

| 模式 | 行为 | 适用场景 |
|------|------|----------|
| `strict` | 强制拦截（exit 1） | CI / 严格质量要求 |
| `ask`（默认） | 交互询问是否强制提交（非交互环境默认拒绝） | 个人开发 |
| `off` | 直接放行 | 临时绕过 |

切换模式：`bash .githooks/gate.sh strict|ask|off`。绕过检查可直接 `git commit --no-verify`。

---

## 开发原则

- **中文注释**：注释覆盖率 ≥ 30%，函数用 docstring（Python）或 JSDoc（前端），解释"为什么"而非"做了什么"，适合小白阅读。
- **防御式编程**：用户输入必须经 Pydantic 校验（长度/类型/范围）；文件上传校验扩展名/大小；聊天 `question` 长度限制。
- **分层清晰**：路由层（routers）只管 HTTP 语义，业务逻辑在服务层（services），RAG 逻辑集中在 `rag_service.py`。
- **性能意识**：embedding 模型/向量库连接复用单例；多知识库并行检索合并去重；检索限 top_k；避免 N+1 查询。
- **版本兼容**：绝对路径、端口、模型名不硬编码，统一走 `backend/.env` / `app/config.py`。
- **提交规范**：conventional commits 中文风格（feat/fix/docs/refactor/chore），由 `/git-save` 自动生成。
