---
name: gitcommit-save
description: /gitcommit-save — 一键检查并保存代码。并行执行测试与质量检查，全部通过后提交并推送。
---

# /gitcommit-save — 一键检查并保存代码

## 描述
并行执行测试检查与质量检查，全部通过后自动保存并推送代码到 GitHub。是 `/git-save` 的增强版，内置质量门禁系统。

## 触发
- 用户输入 `/gitcommit-save`
- 用户说"保存并检查"、"检查完提交"、"质量门禁提交"

## 参数
- `message`（可选）：自定义 commit message。如未提供，由 `/git-save` 自动生成。
- `--no-push`（可选）：仅本地提交，不推送到远程。
- `--all`（可选）：添加所有变更（包括未跟踪文件）。
- `--yes`（可选）：跳过 git-save 的确认步骤，直接提交。

## 行为

### 1. 清理旧标记文件
在开始新一轮检查前，先清理 `.claude/markers/` 目录下所有旧的通过标记，确保不会受到上一次运行残留结果的干扰：
```bash
rm -f .claude/markers/test-passed.marker .claude/markers/quality-passed.marker
```

### 2. 检查代码变更
运行 `git status --short`，查看是否有未提交的更改。
- 如果工作区干净（无改动），告知用户"当前没有可提交的更改"。
- 如果有变更，继续下一步。

### 2. 并行执行检查
使用 `Agent` 工具并行启动两个 subagent：

**Subagent A — tester**
- 调用 `Skill` 执行 `tester`，自动检测修改的文件，补全/执行测试
- 测试全部通过后，会在 `.claude/markers/` 下生成 `test-passed.marker`

**Subagent B — quality-engineer**
- 调用 `Skill` 执行 `quality-engineer`，自动检测修改的文件，执行质量审计
- 不带 `--fix` 参数，避免与 tester 可能产生的文件修改发生冲突
- 无阻塞问题后，会在 `.claude/markers/` 下生成 `quality-passed.marker`

等待两个 subagent 都完成。

### 3. 验证标记文件
两个 skill 调用完成后，检查以下标记文件：
- `.claude/markers/test-passed.marker`
- `.claude/markers/quality-passed.marker`

验证方式：
- 检查文件是否存在
- 读取文件中的 `HEAD` 和 `DIFF_HASH`，与当前代码状态比对
- 如果任一标记缺失或过期，视为检查未通过

**结果处理：**
- 如果两个标记都有效：继续下一步
- 如果有任一缺失或无效：
  - 向用户展示具体哪个检查未通过
  - 提示用户修复问题后重新运行 `/gitcommit-save`
  - **终止流程，不调用 git-save**

### 4. 调用 git-save
使用 `Skill` 工具调用 `git-save` skill，传入用户提供的参数：
- `message`（如有）
- `--no-push`、`--all`、`--yes` 等标志

`git-save` 执行流程：
1. `git add` 添加变更文件
2. `git commit -m "..."` 触发 `pre-commit` hook
3. hook 验证标记文件的有效性，通过后删除标记并放行 commit
4. 继续推送到远程（如未禁用 `--no-push`）

### 5. 失败处理
如果 `git-save` 因 hook 验证失败（如用户在检查完成后又修改了代码），`git-save` 会返回失败信息。此时：
- 标记文件仍保留在 `.claude/markers/` 中（因为 hook 只在通过后才删除）
- 向用户说明失败原因
- 建议用户重新运行 `/gitcommit-save`

## 示例用法

```
/gitcommit-save
```
> 自动并行执行测试检查与质量检查，通过后保存并推送。

```
/gitcommit-save "feat: 新增支出统计图表"
```
> 使用自定义 message，执行检查后提交并推送。

```
/gitcommit-save --no-push
```
> 执行检查，仅本地提交，不推送。

```
/gitcommit-save --yes
```
> 执行检查后直接提交，不询问确认。

## 注意事项
- `/gitcommit-save` 是推荐的提交方式，能确保门禁系统完整生效。
- 完整执行时间 = max(测试时间, 质量检查时间)，通常比串行执行更快。
- 如果只想快速提交而不触发检查，请直接使用 `/git-save`（但 pre-commit hook 仍会拦截，除非使用 `git commit --no-verify`）。
- 并行执行时 `quality-engineer` 不带 `--fix`，如需自动修复质量问题，建议先单独运行 `/quality-engineer --fix`，再运行 `/gitcommit-save`。
