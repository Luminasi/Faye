# 电商 RAG 企业级知识库问答系统

**毕设项目** · 基于 **LangChain + FastAPI + Vue3** 的 RAG 架构，使用 **Ollama 本地大模型** 实现电商商品知识库的智能问答。

---

## ✨ 功能特性

| 模块 | 说明 |
|------|------|
| 🔐 用户系统 | 注册 / 登录（JWT） / 修改密码 / 管理员权限控制 |
| 💬 多会话管理 | 每个用户独立会话、历史消息永久保存、跨登录时段恢复 |
| 🧠 RAG 智能问答 | LangChain LCEL 链路 + 多库检索 + SSE 流式输出 + 引用来源可视化 |
| 📚 知识库管理 | 仅限管理员。知识库 CRUD、PDF/DOCX/MD/TXT/CSV/HTML 多格式文档上传、分块预览、向量化入库 |
| ⚡ 企业级优化 | 查询缓存（LRU+TTL）、Embedding 缓存、批量向量化、指数退避重试、异步文档处理、结构化日志 |
| 🎨 前端 | Vue3 + Pinia + Element Plus，对话区支持打字机流式、引用来源卡片展开 |

---

## 🏗️ 技术栈

| 层级 | 技术 |
|------|------|
| 大模型 / 嵌入 | Ollama 本地（LLM：`qwen2.5:7b`，嵌入：`nomic-embed-text`） |
| RAG 框架 | LangChain 0.3.x + LangChain-Ollama |
| 向量库 | ChromaDB 持久化 |
| 后端 | FastAPI + SQLAlchemy + SQLite + SSE + JWT |
| 前端 | Vue 3 + Pinia + Vue Router + Element Plus + Axios |
| 性能优化 | cachetools LRU+TTL、tenacity 重试、BackgroundTasks、结构化日志 |

---

## 🚀 快速开始（Windows）

### 0. 前置准备

1. **安装 Ollama**：[官网下载](https://ollama.com/) 并安装 Windows 版。安装完成后在 PowerShell 拉取两个模型：
   ```powershell
   ollama pull qwen2.5:7b          # 对话模型（7B 中文效果好，机器至少 16G 内存，推荐 32G）
   ollama pull nomic-embed-text    # 嵌入模型，约 274MB
   ```
   模型较大，首次拉取可能需要较长时间。Ollama 启动后默认监听 `http://localhost:11434`。

2. **Python ≥ 3.10**：命令行输入 `python --version` 确认；无则从 python.org 下载。
3. **Node.js ≥ 18**：命令行 `node -v` 确认；无则从 nodejs.org 下载 LTS。

---

### 1. 启动后端

双击 **`1-启动后端.bat`**（首次会自动检查 venv 与依赖）。

- 后端地址：
  - API 服务:   `http://localhost:8002`
  - Swagger UI: `http://localhost:8002/docs`

**首次自动完成：** 建库建表 + 创建管理员账号（用户名 `admin`，密码 `123456`，可在 `backend/.env` 修改）。

> 手动启动方式：
> ```powershell
> cd backend
> venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
> ```

---

### 2. 导入电商样例数据

后端运行中，另开一个终端，在项目根目录执行：

```powershell
backend\venv\Scripts\python.exe sample_data\load_data.py
```

会自动创建「电商商品知识库」并将 `sample_data/` 下 4 篇样例文档（智能手机 / 笔记本与平板 / 家电 / 平台服务政策）切分 + 向量化入库。等待"导入完成"提示即可。

> 💡 **机器内存不够？** 如果嵌入向量化过程中 Ollama 很慢，可以：
> 1. 在 `.env` 中把 `OLLAMA_LLM_MODEL` 换成更小的 `qwen2.5:3b`
> 2. 或者先用更小的嵌入模型：`ollama pull mxbai-embed-large`，并改 `.env` 中 `OLLAMA_EMBED_MODEL=mxbai-embed-large`

---

### 3. 启动前端

双击 **`2-启动前端.bat`**（首次会自动 `npm install`，依赖走国内 npmmirror 镜像加速）。

前端开发服务器地址：**http://localhost:5173**

---

## 🧪 使用流程

### 1. 管理员（admin / 123456）
- 登录后默认跳转「知识库管理」页面
- 左侧知识库列表可新建/编辑/删除
- 点击某个知识库 → 可以上传文档（PDF/DOCX/MD/TXT/CSV/HTML）、查看分块预览、删除文档

### 2. 普通用户
- 点击登录页「注册」或访问 http://localhost:5173/register 注册
- 登录后进入问答页：
  - 左侧可"新建对话"或切换历史会话（会话持久化，下次登录仍在）
  - 顶部可选择**参与检索的知识库**（不选则默认全部授权库）
  - 输入问题，Enter 发送 / Shift+Enter 换行
  - AI 回答后点击「📚 参考来源」卡片展开，直接查看知识库原文片段对比

### 3. 管理员授权知识库给普通用户
- 本项目演示版本：所有注册用户默认可见所有知识库的问答结果（如需严格授权请查看 `rag_service.py` 的 `_get_authorized_collections`）。

---

## 📁 项目结构

```
LangchainRAG/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口（CORS、路由、启动事件自动建管理员）
│   │   ├── config.py            # 设置（pydantic-settings 读 .env）
│   │   ├── database.py          # SQLAlchemy 引擎
│   │   ├── models.py            # ORM 模型（User/Session/Message/KB/Document）
│   │   ├── schemas.py           # Pydantic 请求/响应
│   │   ├── dependencies.py      # JWT 鉴权 + 管理员权限
│   │   ├── routers/             # API 路由
│   │   │   ├── auth.py          # 注册/登录/改密
│   │   │   ├── sessions.py      # 会话 CRUD + 消息历史
│   │   │   ├── chat.py          # 问答（SSE 流式）
│   │   │   └── admin_kb.py      # 知识库管理（admin 专属）
│   │   ├── services/            # 业务服务层（rag_service.py 为 RAG 核心）
│   │   ├── rag/                 # LangChain RAG 核心
│   │   │   ├── embeddings.py    # OllamaEmbedding + LRU 缓存 + 重试
│   │   │   ├── vector_store.py  # ChromaDB 封装（分 collection）
│   │   │   ├── file_loader.py   # 多格式加载 + Recursive 切分
│   │   │   ├── llm.py           # ChatOllama 封装 + 重试
│   │   │   └── prompts.py       # RAG Prompt 模板（防 prompt injection）
│   │   └── utils/               # 安全/缓存/日志
│   ├── data/                    # 运行时数据（app.db、uploads/、chroma/，gitignore）
│   ├── .env                     # 配置（含密钥，勿提交；.env.example 为模板）
│   └── requirements.txt
├── frontend/                    # Vue3 前端（Vite + Element Plus + Pinia）
│   ├── src/
│   │   ├── api/                 # Axios + SSE 流式解析封装
│   │   ├── views/               # 页面（Login/Register/Chat/ChangePassword/AdminKB）
│   │   ├── components/          # SessionList/MessageBubble/SourceCard
│   │   ├── stores/user.js       # Pinia 用户 store
│   │   └── router/              # 路由 + 权限守卫
│   └── .npmrc                   # npmmirror 国内镜像
├── sample_data/                 # 样例文档（4 篇）+ load_data.py 导入脚本
├── .claude/                     # skills 质量门禁体系（/gitcommit-save 等）
├── .githooks/                   # pre-commit 质量门禁 hook（strict/ask/off 三模式）
├── 1-启动后端.bat               # 后端启动（8002）
├── 2-启动前端.bat               # 前端启动（5173）
└── CLAUDE.md                    # Claude Code 开发指南
```

---

## 🛡️ 企业级优化点说明（毕设答辩可展开）

| 优化项 | 实现 |
|--------|------|
| **查询缓存** | `utils/cache.py` TTLCache：相同问题在 TTL 内命中直接返回，极大降低 LLM 调用与延迟 |
| **Embedding 缓存** | 对 `text+model` 的哈希做缓存，同一段文本不会重复计算向量 |
| **批量向量化** | `embed_documents` 按 64 条一批调用 Embedding 接口，失败自动退化成单条重试 |
| **重试机制** | Embedding / LLM 调用用 tenacity 做指数退避重试（最多 3 次） |
| **异步文档处理** | 文档上传立即返回，`BackgroundTasks` 后台异步切分+向量化，不阻塞请求 |
| **向量检索策略** | MMR 检索去重、多知识库并行检索后按内容指纹合并 |
| **流式输出** | SSE 协议，每个 token 实时推送到前端，打字机效果体验 |
| **引用来源解耦** | sources 字段由检索 docs 直接生成，不依赖 LLM 文本解析，保证来源真实准确 |
| **结构化日志** | structlog 彩色日志，可追踪每个请求的用户/耗时/错误 |
| **权限隔离** | JWT Bearer Token + 依赖注入；管理员接口强制校验 `role=='admin'` |
| **连接池** | SQLAlchemy 引擎启用连接池，Chroma 单例客户端避免反复初始化 |

---

## ✅ 质量门禁（Quality Gate）

项目内置了从记账APP 迁移的质量门禁体系，提交代码前会自动检查质量：

| 命令 | 作用 |
|------|------|
| `/gitcommit-save` | **推荐提交方式**：并行运行测试 + 质量审计，全部通过后提交并推送 |
| `/git-save` | 一键提交 + 推送（跳过质量检查，但 hook 仍会校验标记） |
| `/tester` / `/test` | 测试补全与执行（后端 pytest + 前端 Vitest） |
| `/quality-engineer` | 7 维度代码质量审计（安全/注释/规范/类型/错误处理/性能/可维护性） |
| `/security-check` | 安全审计（凭据泄露 / SQL注入 / 越权 / prompt injection） |
| `/comments-check` | 注释质量检查（覆盖率 ≥ 30%） |

`pre-commit` hook 校验通过标记与提交内容指纹（HEAD + DIFF_HASH）一致后才放行。未通过时按模式处理：

- **strict**：强制拦截 → `bash .githooks/gate.sh strict`
- **ask**（默认）：交互询问是否强制提交，非交互环境默认拒绝
- **off**：直接放行 → `bash .githooks/gate.sh off`

---

## 🔑 演示账号

| 账号 | 密码 | 角色 |
|------|------|------|
| `admin` | `123456` | 管理员（可管理知识库） |
| 任意注册用户 | 自定义 | 普通用户（仅可问答） |

---

## 🧩 毕设演示路线建议

1. **环境介绍**（30s）：指着项目结构说明 LangChain 是核心 RAG 框架，Ollama 跑本地模型，Chroma 存向量。
2. **管理员端**（2min）：登录 admin → 知识库管理 → 选「电商商品知识库」→ 打开某文档分块预览 → 直观展示切分策略。
3. **多用户与会话**（1min）：注册新用户 user1 → 登录 → 新建 2 个会话 → 分别提问 → 退出再登录仍可找回。
4. **RAG 问答核心**（3min）：
   - Q1："华为 Mate 70 Pro 多少钱？屏幕多大？" → 正确回答并展开引用卡片，对比原文《智能手机产品手册》。
   - Q2："寒御冰箱显示 E5 错误怎么办？" → 定位《家电产品手册》错误码表，引用原文。
   - Q3："ThinkPad 的电池保修多久？" → 展示跨知识库命中《笔记本与平板产品手册》售后政策章节。
5. **性能优化对比**（1min）：同一个问题问两次，第一次略慢，第二次立即回复（缓存命中），讲解 LRU+TTL 缓存。
6. **代码架构讲解**（2min）：打开 `rag_service.py` → 指 `LCEL chain`、`_retrieve_multi`、`docs_to_sources` 分别对应"检索-生成-引用"三段链路。

---

## 📝 License
仅供毕设参考。
