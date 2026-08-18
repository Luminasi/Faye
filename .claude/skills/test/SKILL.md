# /test — 测试自动化

## 描述
自动为项目中的模块创建单元测试、执行测试并生成报告。支持一键补全缺失的测试用例。适配双栈：后端 FastAPI（pytest + TestClient），前端 Vue3（Vitest）。

## 触发
当用户在对话中输入 `/test` 时触发。

## 参数
- `target`（可选）：指定要测试的文件路径或模块名。如未提供，则自动检测当前修改或最近编辑的文件。
- `--coverage`（可选）：同时生成覆盖率报告。
- `--create`（可选）：强制为没有测试的文件创建测试。

## 行为

### 1. 检测目标
如果用户没有提供 `target`，执行以下逻辑：
1. 查看当前 git 工作区中 `M`（已修改）和 `A`（新增）的源文件：
   - 后端：`.py`（排除 `venv/`、`__pycache__/`、`app/main.py` 等启动文件）
   - 前端：`.ts` / `.js` / `.vue` / `.tsx` / `.jsx`
2. 过滤掉测试文件（路径包含 `__tests__`、`.test.`、`.spec.`、`test_`、`tests/`）和配置文件。
3. 如果仍无目标，提示用户指定文件。

### 2. 查找/创建测试文件
对每个目标源文件：
1. 根据项目约定推导测试文件路径：
   - 后端：`backend/tests/test_<module>.py`（与 `backend/app/` 目录结构对应，如 `app/services/rag_service.py` → `tests/test_rag_service.py`）
   - 前端：`frontend/src/__tests__/{name}.test.js` 或同目录 `{name}.test.js`
2. 若测试文件已存在：
   - 读取现有测试，检查是否覆盖了目标文件的导出函数/类。
   - 如有缺失覆盖，追加或补齐测试用例。
3. 若测试文件不存在且用户带有 `--create` 或未指定参数：
   - 自动创建基础测试文件，包含导入和至少一个占位测试。

### 3. 编写测试规范
- **后端（pytest + FastAPI TestClient）**：
  - 测试框架优先使用 **pytest**（未安装时提示：`backend\venv\Scripts\pip.exe install pytest httpx`，httpx 是 TestClient 依赖）。
  - 使用 `fastapi.testclient.TestClient` 测试 API 路由（app 从 `app.main` 导入）。
  - 数据库隔离：优先使用独立测试数据库（如 `sqlite:///./test.db`）或在 fixture 中清理数据，**禁止污染真实 `app.db`**。
  - 纯函数（RAG 检索逻辑、文本处理、权限判断）优先写单元测试（输入 → 输出断言）。
  - LLM/向量库等重依赖在测试中 mock（`unittest.mock` 或 `pytest-mock`），不真实调用 Ollama。
  - 每个测试函数 `test_*` 对应一个被测函数或一个业务场景。
  - 必须包含边界值测试和异常路径测试。
- **前端（Vitest）**：
  - 测试框架优先使用 **Vitest**（未配置时提示：`cd frontend && npm install -D vitest @vue/test-utils`，并在 `package.json` scripts 中添加 `"test": "vitest run"`）。
  - 纯函数（格式化、工具函数）优先写单元测试。
  - 组件测试使用 `@vue/test-utils` 挂载组件，断言渲染结果与交互行为。
  - Pinia store 测试使用 `createPinia` + 独立 store 实例。
  - 每个 `describe` 对应一个被测函数或一个业务场景。

### 4. 执行测试
运行后端测试：
```bash
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```
若用户带有 `--coverage`：
```bash
backend\venv\Scripts\python.exe -m pytest backend/tests/ -v --cov=app --cov-report=term-missing
```
运行前端测试：
```bash
npm --prefix frontend run test
```
若用户带有 `--coverage`：
```bash
npm --prefix frontend run test:coverage
```
若某个栈没有测试文件，告知用户"该栈暂无测试"，不要执行失败的命令。

### 5. 生成报告
测试执行后，向用户展示：
- 测试通过 / 失败数量
- 失败的详细信息和文件位置
- 覆盖率概要（若启用 `--coverage`）
- 新创建或修改的测试文件列表

## 示例用法

```
/test
```
> 自动检测最近修改的文件，补全测试，执行并生成报告。

```
/test backend/app/services/rag_service.py --coverage
```
> 为 RAG 服务创建/补全测试，执行并输出覆盖率。

```
/test --create
```
> 为所有没有测试的源文件自动创建基础测试模板。

## 注意事项
- 禁止直接修改 `node_modules`、`venv/` 或 `dist/` 下的文件。
- 创建测试前，先读取源文件以了解导出结构和函数签名。
- 若测试执行失败，优先修复测试代码而非被测代码（除非被测代码明显有 bug）。
- 后端测试文件用 Python + pytest 风格，前端测试文件用 JavaScript/TypeScript + Vitest 风格，不要混用。
- 本项目未配置 pytest/vitest 时，先提示用户安装依赖和添加 scripts，得到确认后再执行。
