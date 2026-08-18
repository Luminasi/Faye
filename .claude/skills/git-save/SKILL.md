---
name: git-save
description: /git-save — 一键保存并推送代码。将工作区变更自动提交并推送到远程 GitHub，含智能 commit message 生成。
---

# /git-save — 一键保存并推送代码

## 描述
将当前工作区的代码变更自动保存到本地 git 仓库，并推送到远程 GitHub。包含智能 commit message 生成、冲突检测和推送状态反馈。

## 触发
- 用户输入 `/git-save`
- 用户说"保存代码"、"提交代码"、"push 到 GitHub"、"git 保存"、"上传代码"

## 参数
- `message`（可选）：自定义 commit message。如未提供，自动生成基于代码变更的摘要。
- `--push`（可选，默认开启）：推送至远程仓库。如只想本地提交，使用 `--no-push`。
- `--all`（可选）：使用 `git add -A` 添加所有变更（包括新增、修改、删除）。默认只添加已跟踪文件的修改和已知的新文件。
- `--dry-run`（可选）：试运行模式，展示将要执行的操作但不实际执行。

## 行为

### 1. 检查 Git 仓库状态
1. 运行 `git status --short` 查看当前工作区状态。
2. 如果没有变更：
   - 提示用户"当前工作区没有待保存的变更"
   - 检查是否有未推送的本地 commit（`git log @{u}..HEAD`），如有则询问是否仅执行推送
3. 如果有变更，继续下一步。

### 2. 确定提交范围
- 默认：`git add -u`（添加已跟踪文件的修改和删除）+ 新增的文件（通过 `git status` 识别出的新文件）
- `--all` 时：`git add -A`（添加所有变更，包括未跟踪文件）
- 如果存在不想提交的文件（如 `.env`、日志文件），提示用户并建议更新 `.gitignore`

### 3. 生成 Commit Message
1. **若用户提供了 `message`**：直接使用。
2. **若未提供，自动生成**：
   - 读取 `git diff --cached --stat` 了解变更概况（哪些文件、多少行增删）
   - 读取 `git diff --cached` 的摘要，识别变更类型：
     - `feat:` —— 新增功能、新增文件
     - `fix:` —— 修复 bug、错误处理
     - `refactor:` —— 重构、代码结构调整（无功能变化）
     - `docs:` —— 文档、注释更新
     - `test:` —— 测试相关
     - `style:` —— 代码格式、命名调整（无逻辑变化）
     - `chore:` —— 构建配置、依赖更新、杂项
   - 结合文件名和变更内容生成简洁的 commit message（中文，50字以内）
   - 示例：
     - `feat: 增加支出记录的四级金额分级功能`
     - `fix: 修复数据库查询结果为空时的崩溃问题`
     - `refactor: 提取 calcLevel 工具函数到独立模块`
     - `docs: 补充 db-core 模块的函数注释`

3. **向用户确认**：
   - 展示生成的 commit message
   - 展示将要提交的文件列表
   - 询问用户是否确认执行（用户可回复"确认"或提供新 message）
   - 若用户带有 `--yes`（可选参数），跳过确认直接执行

### 4. 执行本地提交
1. 运行 `git commit -m "{message}"`
2. 检查是否成功：
   - 成功：记录 commit hash
   - 失败：分析错误原因（如 hooks 失败、身份未配置等），提示用户解决

### 5. 推送到远程（默认开启）
1. 检查远程仓库配置：`git remote -v`
2. 检查当前分支的上游追踪：`git branch -vv`
3. 如果当前分支没有上游分支：
   - 询问用户是否首次推送该分支
   - 如是，执行 `git push -u origin {branch}`
4. 如果已有上游分支：
   - 先执行 `git fetch` 检查远程是否有更新
   - 如果远程领先本地（存在 divergence）：
     - 询问用户是否先执行 `git pull` 合并远程变更
     - 或建议用户手动处理冲突后再 push
   - 如果远程没有冲突或本地领先：
     - 执行 `git push origin {branch}`
5. 检查推送结果：
   - 成功：展示远程 commit URL（如 GitHub 仓库页面链接）
   - 失败：分析原因（权限、网络、分支保护等）

### 6. 结果汇报
向用户展示清晰的执行摘要：

```
✅ 代码保存成功
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 提交文件：X 个
   - modified: src/main/db.ts
   - new file: src/main/db-core.ts
   - deleted: src/old/utils.ts

📝 Commit：{hash}
   {commit message}

🚀 推送状态：已推送至 origin/{branch}
   查看：https://github.com/{user}/{repo}/commit/{hash}

📊 仓库状态：
   本地分支：{branch}
   远程同步：✅ 已同步
```

## 示例用法

```
/git-save
```
> 自动检测变更，生成 commit message，确认后提交并推送。

```
/git-save "feat: 完成支出统计图表组件"
```
> 使用自定义 message 提交并推送。

```
/git-save --no-push
```
> 仅本地提交，不推送到远程。

```
/git-save --all
```
> 添加所有变更（包括未跟踪的新文件），提交并推送。

```
/git-save --dry-run
```
> 试运行，展示将要提交的文件和生成的 message，但不实际执行。

## 注意事项
- **敏感文件检查**：提交前会自动检查是否包含 `.env`、密码、密钥等敏感文件。如发现，会警告用户并建议加入 `.gitignore`。
- **大文件警告**：如果新增文件超过 10MB，会提示用户是否应使用 Git LFS 或排除在版本控制外。
- **合并冲突**：如果远程有更新导致 push 失败，**不会自动强制推送**，而是引导用户安全地解决冲突。
- **身份配置**：如果 git 用户未配置（`user.name` / `user.email`），会提示用户先执行 `git config`。
- **网络问题**：推送失败时，会区分是网络问题、权限问题还是分支保护问题，并给出相应建议。
