# /tester — 智能测试助手

## 描述
当用户有单元测试需求时，自动启动名为 `tester` 的专用 subagent 完成测试分析、用例生成、测试执行和结果报告。tester 是 `/test` skill 的增强版，具备更深的代码分析和自主决策能力。适配双栈：后端 FastAPI（pytest + TestClient），前端 Vue3（Vitest）。

## 触发
- 用户输入 `/tester`
- 用户表达单元测试相关需求，如：
  - "写测试"、"补测试"、"测试覆盖"
  - "帮我测试这个模块"
  - "给 xxx 加单元测试"
  - "运行测试"、"看看测试有没有过"

## 参数
- `target`（可选）：指定要测试的文件路径或模块名。如未提供，自动检测当前工作区中修改/新增的源文件。
- `--coverage`（可选）：同时生成覆盖率报告。
- `--create`（可选）：强制为没有测试的文件创建基础测试模板。
- `--fix`（可选）：测试失败时，尝试自动修复测试代码（而非被测代码）。

## 行为

### 1. 需求分析
1. 解析用户提供的 `target`。
2. 若未提供，查看 git 工作区中 `M`（已修改）和 `A`（新增）的源文件：
   - 后端：`.py`（排除 `venv/`、`__pycache__/`、启动文件）
   - 前端：`.ts` / `.js` / `.vue` / `.tsx` / `.jsx`
   - 过滤掉测试文件（含 `__tests__`、`.test.`、`.spec.`、`test_`、`tests/`）和配置文件。
3. 若仍无目标，提示用户指定文件。

### 2. 启动 tester subagent
使用 `Agent` 工具启动一个 subagent，分配以下任务：

```
你是 tester，一个专业的测试工程师助手。请按以下流程工作：

## 阶段一：理解被测代码
1. 读取用户指定的 target 源文件。
2. 分析其导出结构：函数、类、接口、默认导出。
3. 记录关键函数的参数类型和返回值类型。

## 阶段二：调用 test skill（如果适用）
1. 使用 Skill 工具调用 `test` skill，传入 target 和用户的 flags（--coverage / --create）。
2. 让 test skill 完成初步的测试检测和补全。

## 阶段三：深度测试设计与补全
1. 检查现有测试文件是否完整覆盖了所有导出函数：
   - 每个函数至少一个正常路径测试
   - 边界值测试（如空值、0、极大值、负值）
   - 异常路径测试（如非法输入、数据库异常）
2. 如有缺失，手动编写并补充测试用例。
3. 后端（Python）测试规范：
   - 框架：pytest + fastapi.testclient.TestClient
   - 纯函数（RAG 检索、文本处理、权限判断）直接断言输入→输出
   - 涉及数据库的测试：使用独立测试数据库，`beforeEach`/fixture 中初始化，`afterEach` 中清理，**禁止污染真实 app.db**
   - LLM/ChromaDB 等重依赖用 `unittest.mock` 或 `pytest-mock` mock，不真实调用 Ollama
   - 测试文件放 `backend/tests/test_<module>.py`
4. 前端（Vue3）测试规范：
   - 框架：Vitest + @vue/test-utils
   - 纯函数直接断言；组件测试挂载后断言渲染与交互
   - Pinia store 用 `createPinia` + 独立实例
   - 测试文件放 `frontend/src/__tests__/{name}.test.js` 或同目录

## 阶段四：执行与验证
1. 运行测试：
   - 后端常规：`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v`
   - 后端带覆盖率：`backend\venv\Scripts\python.exe -m pytest backend/tests/ -v --cov=app --cov-report=term-missing`
   - 前端常规：`npm --prefix frontend run test`
   - 前端带覆盖率：`npm --prefix frontend run test:coverage`
   - 若 pytest/vitest 未安装或未配置，先提示用户安装（pytest+httpx / vitest+@vue/test-utils），得到确认后再执行
2. 分析失败原因：
   - 若测试代码逻辑错误 → 修复测试
   - 若被测代码有明显 bug → 报告给用户，不擅自修改被测代码（除非用户带有 `--fix` 且明确授权）
3. 确保所有测试通过后再返回结果。

## 阶段五：报告
向用户返回结构化报告，包括：
- 被测文件列表
- 测试文件列表（新建 / 修改）
- 测试结果摘要（通过数 / 失败数 / 跳过数）
- 覆盖率概要（若启用 --coverage）
- 仍建议补充的测试场景（如有）

## 阶段六：生成测试通过标记
1. **先删除旧标记（如有）**：
   ```bash
   rm -f .claude/markers/test-passed.marker
   ```
2. 如果阶段四中所有测试全部通过（0 失败、0 错误），则生成新的测试通过标记文件：
   ```bash
   mkdir -p .claude/markers
   if git rev-parse --verify HEAD >/dev/null 2>&1; then
     AGAINST=HEAD
   else
     AGAINST=$(git hash-object -t tree /dev/null)
   fi
   DIFF_HASH=$(
     (
       git diff "$AGAINST"
       git ls-files --others --exclude-standard | while read -r f; do
         echo "UNTRACKED:$f"
         cat "$f" 2>/dev/null
       done
     ) | sha256sum | cut -d' ' -f1
   )
   cat > .claude/markers/test-passed.marker <<EOF
   HEAD=$(git rev-parse HEAD 2>/dev/null || echo "initial")
   DIFF_HASH=$DIFF_HASH
   TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
   EOF
   ```
   （此 DIFF_HASH 算法必须与 `.githooks/pre-commit` 中的一致，否则 hook 无法放行。）
3. 如果测试存在任何失败，**不生成标记文件**，并在最终报告中明确告知用户："存在测试失败，未生成 commit 放行标记。请修复后重新运行 /tester 或 /gitcommit-save。"

## 约束
- 后端测试框架：pytest + TestClient；前端测试框架：Vitest + @vue/test-utils
- 后端语言：Python；前端语言：JavaScript/TypeScript
- 禁止修改 `node_modules/`、`venv/`、`dist/` 下的文件
- 禁止直接操作生产数据库文件（`backend/data/app.db`）
```

### 3. 结果汇总与呈现
Subagent 返回后，将其报告以清晰、简洁的格式呈现给用户，突出：
- 关键数字（测试通过率、覆盖率）
- 需要用户关注的警告或建议
- 新建/修改的文件路径（可点击）

## 示例用法

```
/tester
```
> 自动检测最近修改的源文件，启动 tester subagent 补全测试并执行。

```
/tester backend/app/services/rag_service.py --coverage
```
> 针对 RAG 服务进行深度测试分析，补全用例，执行并输出覆盖率报告。

```
/tester --create
```
> 为所有缺少测试的源文件自动创建基础测试模板。

```
/tester frontend/src/api/chat.js --fix
```
> 为 API 模块生成测试，若测试失败则尝试修复测试代码。

## 注意事项
- tester subagent 运行在独立上下文中，拥有完整的文件读写权限。
- 若被测代码存在复杂依赖（如 Ollama、ChromaDB、FastAPI 全栈依赖注入），tester 会建议如何 mock 或隔离测试，但不会强行修改被测代码的架构。
- 覆盖率报告生成后，会提示用户查看 `coverage/` / `htmlcov/` 目录下的 HTML 报告。
- 如果项目没有配置 pytest/vitest，tester 会先检查依赖与 package.json scripts，并建议正确的测试命令。
