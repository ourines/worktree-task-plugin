# Worktree Task Monitor & Auto-Retry

自动监控和重试停滞的 worktree 任务。

## 功能

- 自动检测停滞状态（429 rate limit、重试循环、错误无进展）
- 自动重试：发送 Enter 键触发重试
- 定时执行：每 30 分钟自动检查

## 快速开始

```bash
# 安装定时任务
./setup_cron.sh

# 手动测试
./monitor_and_retry.sh --dry-run --verbose

# 实际执行
./monitor_and_retry.sh --verbose
```

## 使用场景

| 问题 | 解决方案 |
|------|----------|
| 429 rate limit | 检测到后自动发送 Enter 键重试 |
| 重试循环卡住 (attempt 5+) | 发送按键继续 |
| 错误状态无进展 | 触发重试 |

## Session 命名规范

- **新格式**: `<project>-<branch>` (例如: `myproject-feature-auth`)
- **旧格式**: `<branch>` (例如: `feature-new-api`)

## 配置

修改 crontab 调整检查间隔：

```bash
crontab -e
# 默认: */30 * * * * (每 30 分钟)
```

## 卸载

```bash
crontab -l | grep -v 'monitor_and_retry.sh' | crontab -
```
