#!/usr/bin/env bash
# ============================================================
# 质量门禁模式切换脚本
# 用法：bash .githooks/gate.sh strict|ask|off
#   strict : 未通过质量检查时强制拦截提交
#   ask    : （默认）交互询问是否强制提交，非交互环境默认拦截
#   off    : 不拦截，直接放行
# ============================================================
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE_CONFIG="$DIR/gate.config"

case "${1:-}" in
  strict)
    echo "strict" > "$GATE_CONFIG"
    echo "🔒 门禁模式已切换为 [strict]：质量检查未通过时强制拦截提交"
    ;;
  ask)
    echo "ask" > "$GATE_CONFIG"
    echo "❓ 门禁模式已切换为 [ask]：质量检查未通过时交互询问（默认拒绝）"
    ;;
  off)
    echo "off" > "$GATE_CONFIG"
    echo "⏩ 门禁模式已切换为 [off]：不拦截提交（注意：质量门禁被绕过）"
    ;;
  *)
    echo "用法：bash .githooks/gate.sh strict|ask|off"
    echo "当前模式：$(cat "$GATE_CONFIG" 2>/dev/null || echo ask)"
    exit 1
    ;;
esac
