#!/bin/bash
# ============================================================
# 知伴AI 服务统一管理脚本
# 用法:
#   ./zhibanctl.sh start    [java|python|frontend]   # 启动(不指定则全部)
#   ./zhibanctl.sh stop    [java|python|frontend]   # 停止
#   ./zhibanctl.sh restart [java|python|frontend]   # 重启(改完参数后执行)
#   ./zhibanctl.sh status                           # 查看所有服务状态
#   ./zhibanctl.sh logs     [java|python|frontend]  # 查看日志(实时)
#   ./zhibanctl.sh edit-env                        # 编辑环境变量配置
#   ./zhibanctl.sh build-frontend                  # 重新构建前端并部署
#   ./zhibanctl.sh health                          # 健康检查
# ============================================================
set -euo pipefail

BASE=/home/www/code/zhiban-ai/zhiban-ai
SERVICES=(zhiban-java zhiban-python zhiban-frontend)
declare -A SVC_PORT=( [zhiban-java]=8080 [zhiban-python]=8081 [zhiban-frontend]=8088 )

normalize() {
  case "$1" in
    java|zhiban-java) echo zhiban-java ;;
    python|zhiban-python) echo zhiban-python ;;
    frontend|zhiban-frontend|nginx) echo zhiban-frontend ;;
    *) echo "" ;;
  esac
}

do_start() {
  local svc="$1"
  if [ -z "$svc" ]; then
    for s in "${SERVICES[@]}"; do systemctl --user start "$s"; done
    echo "✓ 全部服务已启动"
  else
    systemctl --user start "$svc" && echo "✓ $svc 已启动"
  fi
}

do_stop() {
  local svc="$1"
  if [ -z "$svc" ]; then
    for s in "${SERVICES[@]}"; do systemctl --user stop "$s"; done
    echo "✓ 全部服务已停止"
  else
    systemctl --user stop "$svc" && echo "✓ $svc 已停止"
  fi
}

do_restart() {
  local svc="$1"
  if [ -z "$svc" ]; then
    # 全部重启时按依赖顺序
    for s in "${SERVICES[@]}"; do systemctl --user restart "$s" && echo "✓ $s 已重启"; done
    echo "✓ 全部服务已重启"
  else
    systemctl --user restart "$svc" && echo "✓ $svc 已重启"
  fi
}

do_status() {
  echo "══════════════════════════════════════════════════"
  printf "%-18s %-8s %-8s %s\n" "服务" "状态" "端口" "说明"
  echo "══════════════════════════════════════════════════"
  for s in "${SERVICES[@]}"; do
    local state=$(systemctl --user is-active "$s" 2>/dev/null)
    local port=${SVC_PORT[$s]}
    local desc=$(systemctl --user show -p Description --value "$s" 2>/dev/null | cut -d'(' -f1 | xargs)
    if [ "$state" = "active" ]; then
      printf "%-18s %-8s %-8s %s\n" "$s" "● 运行" "$port" "$desc"
    else
      printf "%-18s %-8s %-8s %s\n" "$s" "○ 停止" "$port" "$desc"
    fi
  done
  echo "══════════════════════════════════════════════════"
}

do_logs() {
  local svc=$(normalize "${1:-}")
  if [ -z "$svc" ]; then echo "用法: $0 logs [java|python|frontend]"; exit 1; fi
  local logfile="$BASE/.deploy/logs/$(echo $svc | sed 's/zhiban-//').log"
  echo "→ $svc 日志 (Ctrl+C 退出): $logfile"
  tail -f "$logfile"
}

do_edit_env() {
  local f="$BASE/.deploy/env"
  ${EDITOR:-vi} "$f"
  echo ""
  echo "环境变量已编辑。需重启服务生效:"
  echo "  $0 restart        # 全部重启"
  echo "  $0 restart java   # 只重启 Java(如改了 DB/JWT 等)"
  echo "  $0 restart python # 只重启 Python(如改了 LLM_PROVIDER)"
}

do_build_frontend() {
  echo "→ 构建前端..."
  cd "$BASE/vue-frontend" || exit 1
  npm run build || { echo "✗ 构建失败"; exit 1; }
  echo "→ 同步到部署目录..."
  local DEPLOY=$BASE/.deploy/web
  rm -rf "$DEPLOY/assets" && mkdir -p "$DEPLOY/assets"
  cp -r dist/* "$DEPLOY"/ && cp -r dist/assets/* "$DEPLOY/assets"/
  echo "✓ 前端已构建并部署到 $DEPLOY"
  echo "→ reload nginx 使资源生效..."
  systemctl --user reload zhiban-frontend 2>/dev/null || true
  echo "✓ 完成。浏览器 Ctrl+F5 刷新即可"
}

do_health() {
  echo "→ 健康检查..."
  local ok=0
  # Java
  local code=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://127.0.0.1:8080/api/health 2>/dev/null)
  if [ "$code" = "200" ]; then
    local body=$(curl -s -m 3 http://127.0.0.1:8080/api/health 2>/dev/null)
    echo "  Java(8080):  ✓ $body"
    ok=$((ok+1))
  else echo "  Java(8080):  ✗ HTTP $code"; fi
  # Python
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://127.0.0.1:8081/api/v1/health 2>/dev/null)
  if [ "$code" = "200" ]; then
    local body=$(curl -s -m 3 http://127.0.0.1:8081/api/v1/health 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(f'llm={d.get(\"llmProvider\")}, collections={d.get(\"collections\")}')" 2>/dev/null)
    echo "  Python(8081): ✓ $body"
    ok=$((ok+1))
  else echo "  Python(8081): ✗ HTTP $code"; fi
  # 前端
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://127.0.0.1:8088/ 2>/dev/null)
  if [ "$code" = "200" ]; then echo "  前端(8088):  ✓ HTTP 200"; ok=$((ok+1))
  else echo "  前端(8088):  ✗ HTTP $code"; fi
  echo ""
  if [ $ok -eq 3 ]; then echo "✓ 全部健康"; else echo "✗ $((3-ok)) 个服务异常"; fi
}

# ── 主入口 ──
cmd="${1:-status}"
target=$(normalize "${2:-}")

case "$cmd" in
  start)    do_start "$target" ;;
  stop)     do_stop "$target" ;;
  restart)  do_restart "$target" ;;
  status)   do_status ;;
  logs)     do_logs "${2:-}" ;;
  edit-env) do_edit_env ;;
  build-frontend) do_build_frontend ;;
  health)   do_health ;;
  *)
    cat <<'USAGE'
知伴AI 服务管理脚本
用法:
  ./zhibanctl.sh start    [java|python|frontend]   启动服务
  ./zhibanctl.sh stop    [java|python|frontend]   停止服务
  ./zhibanctl.sh restart [java|python|frontend]   重启服务(改完参数后执行)
  ./zhibanctl.sh status                           查看所有服务状态
  ./zhibanctl.sh logs     [java|python|frontend]  查看日志(实时)
  ./zhibanctl.sh edit-env                        编辑环境变量配置
  ./zhibanctl.sh build-frontend                  重新构建前端并部署
  ./zhibanctl.sh health                          健康检查
USAGE
    ;;
esac
