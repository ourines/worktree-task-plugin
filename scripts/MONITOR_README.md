# Worktree Task Monitor & Auto-Retry

自动监控和重试停滞的 worktree 任务。

## 功能

- **自动检测停滞状态**：
  - 429 rate limit 错误
  - 重试循环卡住（attempt 5+/10）
  - 错误状态无进展
  - 长时间等待状态

- **自动重试**：发送 Enter 键触发重试
- **定时执行**：每 30 分钟自动检查
- **日志记录**：完整的操作日志

## Session 命名规范

从 v1.1 开始，session 名称包含项目标识符以避免冲突：

- **新格式**: `<project>-<branch>` (例如: `worktree-task-plugin-feature-add-dashboard`)
- **旧格式**: `<branch>` (例如: `feature-add-account-scheduler`)

监控脚本兼容两种格式。

## 快速开始

### 1. 安装定时任务

```bash
cd /Users/liubiao/code/claude/worktree-task-plugin/scripts
./setup_cron.sh
```

### 2. 手动测试

```bash
# 测试模式（不实际发送按键）
./monitor_and_retry.sh --dry-run --verbose

# 实际执行
./monitor_and_retry.sh --verbose
```

### 3. 查看日志

```bash
# 查看监控日志
tail -f /Users/liubiao/code/claude/worktree-task-plugin/scripts/../.monitor_retry.log

# 查看 cron 执行日志
tail -f /Users/liubiao/code/claude/worktree-task-plugin/scripts/../.monitor_cron.log
```

## 使用场景

### 场景 1: GitHub Copilot Token 限流

**问题**：任务遇到 429 错误后卡住
```
429 {"error":{"message":"Sorry, you have exceeded your Copilot token usage..."}}
Retrying in 0 seconds… (attempt 5/10)
```

**解决**：监控脚本检测到 "429" 或 "rate_limited"，自动发送 Enter 键重试

### 场景 2: 重试循环卡住

**问题**：任务在高次数重试中卡住（attempt 5-10）

**解决**：检测到 "Retrying in.*attempt [5-9]/10"，发送按键继续

### 场景 3: 错误状态无进展

**问题**：任务显示错误但没有后续活动

**解决**：检测到错误消息且最近 20 行无进展标记（⏺/✻/Done），触发重试

## 配置

### 修改检查间隔

编辑 crontab：
```bash
crontab -e
```

修改时间间隔（当前为 `*/30 * * * *` = 每 30 分钟）：
- 每 15 分钟：`*/15 * * * *`
- 每小时：`0 * * * *`
- 每 2 小时：`0 */2 * * *`

### 自定义 Session 匹配模式

默认情况下，监控脚本匹配以下模式的 session：
- `feature-*`
- `fix-*`
- `hotfix-*`
- `release-*`
- `worktree-*`
- `synergy-*`
- `<project>-feature-*`（新格式）

自定义匹配模式：
```bash
export WORKTREE_SESSION_PATTERN="^(myproject-|custom-)"
./monitor_and_retry.sh --verbose
```

### 自定义检测规则

编辑 `monitor_and_retry.sh` 中的 `check_session_stalled()` 函数，添加新的检测模式。

## 卸载

```bash
# 移除 cron 任务
crontab -l | grep -v 'monitor_and_retry.sh' | crontab -

# 删除脚本（可选）
rm /Users/liubiao/code/claude/worktree-task-plugin/scripts/monitor_and_retry.sh
rm /Users/liubiao/code/claude/worktree-task-plugin/scripts/setup_cron.sh
```

## 故障排查

### Cron 任务未执行

1. 检查 cron 服务是否运行：
   ```bash
   # macOS
   sudo launchctl list | grep cron
   ```

2. 检查脚本权限：
   ```bash
   ls -l /Users/liubiao/code/claude/worktree-task-plugin/scripts/monitor_and_retry.sh
   # 应该显示 -rwxr-xr-x
   ```

3. 查看 cron 日志：
   ```bash
   tail -f /Users/liubiao/code/claude/worktree-task-plugin/.monitor_cron.log
   ```

### 脚本检测不准确

- 使用 `--verbose` 模式查看详细检测过程
- 检查 `.monitor_retry.log` 中的 DEBUG 信息
- 调整 `check_session_stalled()` 中的检测阈值

### 按键发送失败

- 确认 tmux session 存在：`tmux list-sessions`
- 确认 session 名称匹配：检查 `get_worktree_sessions()` 的正则表达式
- 手动测试：`tmux send-keys -t <session-name> Enter`

## 技术细节

### 检测逻辑

脚本捕获每个 tmux session 的最后 50 行输出，使用以下模式匹配：

1. **429 错误**：`429.*rate_limited|exceeded.*token usage|rate limit`
2. **重试卡住**：`Retrying in.*attempt [5-9]/10|Retrying in.*attempt 10/10`
3. **错误无进展**：错误消息 + 最近 20 行无进展标记
4. **等待过久**：`Waiting…` 出现超过 10 次

### 日志轮转

- 日志文件超过 1MB 时自动轮转
- 旧日志保存为 `.monitor_retry.log.old`

### 安全性

- 使用 `set -euo pipefail` 确保错误时退出
- Dry-run 模式用于测试
- 所有操作记录到日志

## 示例输出

### Dry-run 模式
```
[INFO] Starting worktree task monitor (dry-run: true, verbose: true)
[DEBUG] Checking session: feature-add-account-scheduler
[WARN] Session feature-add-account-scheduler is stalled: 429 rate limit detected
[ACTION] [DRY-RUN] Would send Enter key to session: feature-add-account-scheduler
[INFO] Monitor complete: 4 sessions checked, 2 stalled, 2 retried
Summary: Checked 4 sessions, found 2 stalled, retried 2
```

### 实际执行
```
[ACTION] Sent retry keystroke to session: feature-add-account-scheduler (reason: 429 rate limit detected)
```
