#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# 知伴AI 一键启动脚本 (Linux / macOS)
# ═══════════════════════════════════════════════════════
#
# 使用方法:
#   ./start.sh              # Docker 模式启动（默认）
#   ./start.sh docker       # Docker Compose 一键部署
#   ./start.sh dev          # 本地开发模式（打印启动指令）
#   ./start.sh stop         # 停止所有 Docker 服务
#   ./start.sh status       # 查看服务状态
#   ./start.sh logs         # 查看日志（全部）
#   ./start.sh logs java    # 查看指定服务日志
#   ./start.sh build        # 仅构建镜像
#   ./start.sh clean        # 停止并清理所有容器和卷
#   ./start.sh init-kb      # 构建知识库（Docker 内执行）
# ═══════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.docker"
ENV_EXAMPLE="${PROJECT_ROOT}/.env.docker.example"

# ── 颜色输出 ─────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()  { echo -e "\n${MAGENTA}── $* ──${NC}\n"; }

# ── 横幅 ─────────────────────────────────────────────
show_banner() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════╗"
    echo "  ║        知伴AI 一键启动脚本           ║"
    echo "  ║        Zhiban AI Launcher             ║"
    echo "  ╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

# ── 检查依赖 ──────────────────────────────────────────
check_dependencies() {
    step "检查环境依赖"

    local missing=()

    if ! command -v docker &>/dev/null; then
        missing+=("Docker")
    else
        ok "Docker 已安装: $(docker --version)"
    fi

    if ! docker compose version &>/dev/null 2>&1; then
        missing+=("Docker Compose v2")
    else
        ok "Docker Compose 已安装"
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        err "缺少依赖: ${missing[*]}"
        echo ""
        echo "  请安装以下工具："
        echo "    Docker: https://docs.docker.com/get-docker/"
        echo ""
        exit 1
    fi
}

# ── 检查 .env.docker ──────────────────────────────────
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        warn "未找到 .env.docker 配置文件"

        if [ -f "$ENV_EXAMPLE" ]; then
            info "从模板创建 .env.docker ..."
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            ok ".env.docker 已创建"
            echo ""
            warn "请编辑 .env.docker 填入实际配置："
            echo "    - DEEPSEEK_API_KEY  : DeepSeek API Key（必填）"
            echo "    - DB_PASSWORD        : MySQL 密码（默认 zhiban123）"
            echo "    - JWT_SECRET         : JWT 密钥（默认值可用，生产环境务必修改）"
            echo ""
            read -p "是否现在编辑 .env.docker？(y/n) " answer
            if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
                ${EDITOR:-nano} "$ENV_FILE"
            else
                warn "使用默认配置启动，请确保已设置 API Key"
            fi
        else
            err "模板文件 .env.docker.example 也不存在，无法继续"
            exit 1
        fi
    else
        ok ".env.docker 配置文件存在"
    fi
}

# ── Docker Compose 命令封装 ───────────────────────────
dc() {
    docker compose --env-file "$ENV_FILE" "$@"
}

# ── Docker 启动 ───────────────────────────────────────
start_docker() {
    step "Docker Compose 模式启动"

    check_dependencies
    check_env_file

    info "构建并启动所有服务..."
    echo ""
    echo "  服务列表："
    echo "    1. MySQL         (端口 3306) — 数据库"
    echo "    2. Python AI     (端口 8081) — RAG 检索服务"
    echo "    3. Java Backend  (端口 8080) — Spring Boot API"
    echo "    4. Vue Frontend  (端口 80)   — Nginx + 前端"
    echo ""

    cd "$PROJECT_ROOT"
    dc up -d --build

    echo ""
    step "服务启动状态"
    dc ps
    echo ""

    echo -e "${GREEN}"
    echo "  ╔══════════════════════════════════════╗"
    echo "  ║          启动成功！                  ║"
    echo "  ╠══════════════════════════════════════╣"
    echo "  ║  前端:   http://localhost            ║"
    echo "  ║  后端:   http://localhost:8080/api    ║"
    echo "  ║  RAG:    http://localhost:8081        ║"
    echo "  ║  MySQL:  localhost:3306               ║"
    echo "  ╠══════════════════════════════════════╣"
    echo "  ║  默认管理员: admin / admin123          ║"
    echo "  ╚══════════════════════════════════════╝"
    echo -e "${NC}"
    echo "  常用命令:"
    echo "    ./start.sh status   # 查看状态"
    echo "    ./start.sh logs     # 查看日志"
    echo "    ./start.sh stop     # 停止服务"
    echo "    ./start.sh clean    # 清理所有"
    echo "    ./start.sh init-kb  # 构建知识库"
    echo ""
}

# ── 停止服务 ──────────────────────────────────────────
stop_services() {
    step "停止所有服务"
    cd "$PROJECT_ROOT"
    dc down
    ok "所有服务已停止"
}

# ── 查看状态 ──────────────────────────────────────────
show_status() {
    step "服务状态"
    cd "$PROJECT_ROOT"
    dc ps
}

# ── 查看日志 ──────────────────────────────────────────
show_logs() {
    local svc="${1:-}"
    step "查看日志"
    cd "$PROJECT_ROOT"
    if [ -n "$svc" ]; then
        info "服务: $svc (Ctrl+C 退出)"
        dc logs -f "$svc"
    else
        info "所有服务日志 (Ctrl+C 退出)"
        dc logs -f
    fi
}

# ── 仅构建 ────────────────────────────────────────────
build_images() {
    step "构建 Docker 镜像"
    check_env_file
    cd "$PROJECT_ROOT"
    dc build
    ok "镜像构建完成"
}

# ── 清理 ──────────────────────────────────────────────
clean_all() {
    step "清理所有容器和数据卷"
    warn "此操作将删除所有容器和数据，不可恢复！"
    read -p "确认清理？输入 yes 继续 " answer
    if [ "$answer" != "yes" ]; then
        info "已取消"
        return
    fi
    cd "$PROJECT_ROOT"
    dc down -v --rmi local
    ok "清理完成"
}

# ── 构建知识库 ────────────────────────────────────────
init_kb() {
    step "构建知识库（在 Python 容器内执行）"
    cd "$PROJECT_ROOT"

    info "构建政务政策知识库..."
    docker exec zhiban-python-ai python govpolicy_agent/main.py --build-kb --rebuild 2>/dev/null || \
        warn "政务知识库构建失败或已存在"

    info "构建银发康养知识库..."
    docker exec zhiban-python-ai python elderly_agent/main.py --build-kb --rebuild 2>/dev/null || \
        warn "康养知识库构建失败或已存在"

    info "构建文旅导览知识库..."
    docker exec zhiban-python-ai python tourism_agent/main.py --build-kb --rebuild 2>/dev/null || \
        warn "文旅知识库构建失败或已存在"

    ok "知识库构建流程结束"
    info "验证向量库状态..."
    curl -s http://localhost:8081/api/v1/health | python3 -m json.tool 2>/dev/null || \
        echo "  RAG 服务健康检查: http://localhost:8081/api/v1/health"
}

# ── 本地开发模式 ──────────────────────────────────────
start_dev() {
    step "本地开发模式"
    echo ""
    echo "  本模式需要预先安装: JDK 17, Maven, Node.js, Python 3.10+, MySQL 8.0"
    echo ""

    # 检查 .env
    local python_env="${PROJECT_ROOT}/python/.env"
    if [ ! -f "$python_env" ]; then
        local example="${PROJECT_ROOT}/python/.env.example"
        if [ -f "$example" ]; then
            info "创建 python/.env ..."
            cp "$example" "$python_env"
            warn "请编辑 python/.env 填入 API Key"
        fi
    fi

    echo ""
    echo "  请在不同终端窗口中分别执行以下命令："
    echo ""
    echo -e "${MAGENTA}  ── 终端 1: Python RAG 服务 ──────────────${NC}"
    echo "  cd python"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo "  python rag_server.py"
    echo ""
    echo -e "${MAGENTA}  ── 终端 2: Java 后端 ────────────────────${NC}"
    echo "  export DB_PASSWORD=your-mysql-password"
    echo "  export JWT_SECRET=your-jwt-secret-32-chars"
    echo "  cd java-backend"
    echo "  mvn spring-boot:run"
    echo ""
    echo -e "${MAGENTA}  ── 终端 3: Vue 前端 ─────────────────────${NC}"
    echo "  cd vue-frontend"
    echo "  npm install"
    echo "  npm run dev"
    echo ""
    echo "  访问地址："
    echo "    前端:   http://localhost:5173"
    echo "    后端:   http://localhost:8080/api"
    echo "    RAG:    http://localhost:8081"
    echo ""
}

# ── 主入口 ────────────────────────────────────────────
show_banner

case "${1:-docker}" in
    docker)    start_docker ;;
    dev)       start_dev ;;
    stop)      stop_services ;;
    status)    show_status ;;
    logs)      show_logs "${2:-}" ;;
    build)     build_images ;;
    clean)     clean_all ;;
    init-kb)   init_kb ;;
    help|--help|-h)
        echo "用法: $0 [docker|dev|stop|status|logs [service]|build|clean|init-kb]"
        echo ""
        echo "命令:"
        echo "  docker     Docker Compose 一键启动（默认）"
        echo "  dev        本地开发模式（打印启动指令）"
        echo "  stop       停止所有服务"
        echo "  status     查看服务状态"
        echo "  logs [s]   查看日志（可选指定服务名）"
        echo "  build      仅构建镜像"
        echo "  clean      停止并清理所有容器和卷"
        echo "  init-kb    构建知识库（容器内执行）"
        echo ""
        ;;
    *)
        err "未知命令: $1"
        echo "运行 $0 help 查看帮助"
        exit 1
        ;;
esac
