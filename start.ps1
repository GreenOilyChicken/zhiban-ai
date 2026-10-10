#Requires -Version 5.0
<#
.SYNOPSIS
    知伴AI 一键启动脚本 (Windows PowerShell)
.DESCRIPTION
    支持两种模式：
      1. Docker Compose 模式（推荐）：一键拉起全部 4 个服务
      2. 本地开发模式：分别启动 Python / Java / Vue 各模块
.PARAMETER Mode
    docker   - Docker Compose 一键部署（默认）
    dev      - 本地开发模式（需预先安装各环境）
    stop     - 停止所有 Docker 服务
    status   - 查看服务状态
    logs     - 查看日志
    build    - 仅构建镜像不启动
    clean    - 停止并清理所有容器和卷
.PARAMETER Service
    指定查看日志的服务名 (mysql/python-ai/java-backend/vue-frontend)
.EXAMPLE
    .\start.ps1                    # Docker 模式启动
    .\start.ps1 -Mode dev           # 本地开发模式
    .\start.ps1 -Mode stop          # 停止所有服务
    .\start.ps1 -Mode logs -Service java-backend  # 查看Java后端日志
    .\start.ps1 -Mode status        # 查看状态
    .\start.ps1 -Mode clean          # 清理所有
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("docker", "dev", "stop", "status", "logs", "build", "clean")]
    [string]$Mode = "docker",

    [string]$Service = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $ProjectRoot ".env.docker"
$EnvExample = Join-Path $ProjectRoot ".env.docker.example"

# ── 颜色输出 ─────────────────────────────────────────
function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Cyan }
function Write-OK    { Write-Host "[OK]    $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "[ERROR] $args" -ForegroundColor Red }
function Write-Step  { Write-Host ""; Write-Host "── $args ──" -ForegroundColor Magenta }

# ── 横幅 ─────────────────────────────────────────────
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║        知伴AI 一键启动脚本           ║" -ForegroundColor Cyan
    Write-Host "  ║        Zhiban AI Launcher             ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# ── 检查环境依赖 ──────────────────────────────────────
function Test-Dependencies {
    Write-Step "检查环境依赖"

    $missing = @()

    # Docker
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        $missing += "Docker"
    } else {
        Write-OK "Docker 已安装"
    }

    # Docker Compose
    try {
        $composeVersion = docker compose version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-OK "Docker Compose 已安装"
        } else {
            $missing += "Docker Compose"
        }
    } catch {
        $missing += "Docker Compose"
    }

    if ($missing.Count -gt 0) {
        Write-Err "缺少依赖: $($missing -join ', ')"
        Write-Host ""
        Write-Host "  请安装以下工具：" -ForegroundColor Yellow
        Write-Host "    Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}

# ── 检查 .env.docker ──────────────────────────────────
function Test-EnvFile {
    if (-not (Test-Path $EnvFile)) {
        Write-Warn "未找到 .env.docker 配置文件"

        if (Test-Path $EnvExample) {
            Write-Info "从模板创建 .env.docker ..."
            Copy-Item $EnvExample $EnvFile
            Write-OK ".env.docker 已创建"
            Write-Host ""
            Write-Warn "请编辑 .env.docker 填入实际配置："
            Write-Host "    - DEEPSEEK_API_KEY  : DeepSeek API Key（必填）" -ForegroundColor White
            Write-Host "    - DB_PASSWORD        : MySQL 密码（默认 zhiban123）" -ForegroundColor White
            Write-Host "    - JWT_SECRET         : JWT 密钥（默认值可用，生产环境务必修改）" -ForegroundColor White
            Write-Host ""
            $answer = Read-Host "是否现在编辑 .env.docker？(y/n)"
            if ($answer -eq "y" -or $answer -eq "Y") {
                Start-Process notepad $EnvFile -Wait
            } else {
                Write-Warn "使用默认配置启动，请确保已设置 API Key"
            }
        } else {
            Write-Err "模板文件 .env.docker.example 也不存在，无法继续"
            exit 1
        }
    } else {
        Write-OK ".env.docker 配置文件存在"
    }
}

# ── Docker Compose 启动 ───────────────────────────────
function Start-DockerCompose {
    Write-Step "Docker Compose 模式启动"

    Test-Dependencies
    Test-EnvFile

    Write-Info "构建并启动所有服务..."
    Write-Host ""
    Write-Host "  服务列表：" -ForegroundColor White
    Write-Host "    1. MySQL         (端口 3306) — 数据库" -ForegroundColor Gray
    Write-Host "    2. Python AI     (端口 8081) — RAG 检索服务" -ForegroundColor Gray
    Write-Host "    3. Java Backend  (端口 8080) — Spring Boot API" -ForegroundColor Gray
    Write-Host "    4. Vue Frontend  (端口 80)   — Nginx + 前端" -ForegroundColor Gray
    Write-Host ""

    Push-Location $ProjectRoot
    try {
        # 构建并启动
        docker compose --env-file .env.docker up -d --build

        if ($LASTEXITCODE -ne 0) {
            Write-Err "启动失败，请检查日志: docker compose --env-file .env.docker logs"
            exit 1
        }

        Write-Host ""
        Write-Step "服务启动状态"
        docker compose --env-file .env.docker ps
        Write-Host ""

        Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Green
        Write-Host "  ║          启动成功！                   ║" -ForegroundColor Green
        Write-Host "  ╠══════════════════════════════════════╣" -ForegroundColor Green
        Write-Host "  ║  前端:   http://localhost             ║" -ForegroundColor Green
        Write-Host "  ║  后端:   http://localhost:8080/api    ║" -ForegroundColor Green
        Write-Host "  ║  RAG:    http://localhost:8081        ║" -ForegroundColor Green
        Write-Host "  ║  MySQL:  localhost:3306               ║" -ForegroundColor Green
        Write-Host "  ╠══════════════════════════════════════╣" -ForegroundColor Green
        Write-Host "  ║  默认管理员: admin / admin123          ║" -ForegroundColor Yellow
        Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Green
        Write-Host ""
        Write-Host "  常用命令:" -ForegroundColor Cyan
        Write-Host "    .\start.ps1 -Mode status   # 查看状态" -ForegroundColor Gray
        Write-Host "    .\start.ps1 -Mode logs     # 查看日志" -ForegroundColor Gray
        Write-Host "    .\start.ps1 -Mode stop     # 停止服务" -ForegroundColor Gray
        Write-Host "    .\start.ps1 -Mode clean    # 清理所有" -ForegroundColor Gray
        Write-Host ""
    } finally {
        Pop-Location
    }
}

# ── 停止服务 ──────────────────────────────────────────
function Stop-Services {
    Write-Step "停止所有服务"
    Push-Location $ProjectRoot
    try {
        docker compose --env-file .env.docker down
        Write-OK "所有服务已停止"
    } catch {
        Write-Warn "停止时出现异常（可能服务未运行）"
    } finally {
        Pop-Location
    }
}

# ── 查看状态 ──────────────────────────────────────────
function Show-Status {
    Write-Step "服务状态"
    Push-Location $ProjectRoot
    try {
        docker compose --env-file .env.docker ps
    } finally {
        Pop-Location
    }
}

# ── 查看日志 ──────────────────────────────────────────
function Show-Logs {
    Write-Step "查看日志"
    Push-Location $ProjectRoot
    try {
        if ($Service) {
            Write-Info "服务: $Service (Ctrl+C 退出)"
            docker compose --env-file .env.docker logs -f $Service
        } else {
            Write-Info "所有服务日志 (Ctrl+C 退出)"
            docker compose --env-file .env.docker logs -f
        }
    } finally {
        Pop-Location
    }
}

# ── 仅构建 ────────────────────────────────────────────
function Build-Images {
    Write-Step "构建 Docker 镜像"
    Test-EnvFile
    Push-Location $ProjectRoot
    try {
        docker compose --env-file .env.docker build
        Write-OK "镜像构建完成"
    } finally {
        Pop-Location
    }
}

# ── 清理 ──────────────────────────────────────────────
function Clean-All {
    Write-Step "清理所有容器和数据卷"
    Write-Warn "此操作将删除所有容器和数据，不可恢复！"
    $answer = Read-Host "确认清理？输入 yes 继续"
    if ($answer -ne "yes") {
        Write-Info "已取消"
        return
    }
    Push-Location $ProjectRoot
    try {
        docker compose --env-file .env.docker down -v --rmi local
        Write-OK "清理完成"
    } finally {
        Pop-Location
    }
}

# ── 本地开发模式 ──────────────────────────────────────
function Start-DevMode {
    Write-Step "本地开发模式"
    Write-Host ""
    Write-Host "  本模式需要预先安装: JDK 17, Maven, Node.js, Python 3.10+, MySQL 8.0" -ForegroundColor Yellow
    Write-Host ""

    # 1. 检查 .env
    $PythonEnv = Join-Path $ProjectRoot "python\.env"
    if (-not (Test-Path $PythonEnv)) {
        $PythonExample = Join-Path $ProjectRoot "python\.env.example"
        if (Test-Path $PythonExample) {
            Write-Info "创建 python/.env ..."
            Copy-Item $PythonExample $PythonEnv
            Write-Warn "请编辑 python/.env 填入 API Key"
        }
    }

    Write-Host ""
    Write-Host "  请在不同终端窗口中分别执行以下命令：" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  ── 终端 1: Python RAG 服务 ──────────────" -ForegroundColor Magenta
    Write-Host "  cd python" -ForegroundColor White
    Write-Host "  python -m venv venv" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    Write-Host "  python rag_server.py" -ForegroundColor White
    Write-Host ""
    Write-Host "  ── 终端 2: Java 后端 ────────────────────" -ForegroundColor Magenta
    Write-Host "  `$env:DB_PASSWORD='your-mysql-password'" -ForegroundColor White
    Write-Host "  `$env:JWT_SECRET='your-jwt-secret-32-chars'" -ForegroundColor White
    Write-Host "  cd java-backend" -ForegroundColor White
    Write-Host "  mvn spring-boot:run" -ForegroundColor White
    Write-Host ""
    Write-Host "  ── 终端 3: Vue 前端 ─────────────────────" -ForegroundColor Magenta
    Write-Host "  cd vue-frontend" -ForegroundColor White
    Write-Host "  npm install" -ForegroundColor White
    Write-Host "  npm run dev" -ForegroundColor White
    Write-Host ""
    Write-Host "  访问地址：" -ForegroundColor Cyan
    Write-Host "    前端:   http://localhost:5173" -ForegroundColor Green
    Write-Host "    后端:   http://localhost:8080/api" -ForegroundColor Green
    Write-Host "    RAG:    http://localhost:8081" -ForegroundColor Green
    Write-Host ""
}

# ── 主入口 ────────────────────────────────────────────
Show-Banner

switch ($Mode) {
    "docker"  { Start-DockerCompose }
    "dev"     { Start-DevMode }
    "stop"    { Stop-Services }
    "status"  { Show-Status }
    "logs"    { Show-Logs }
    "build"   { Build-Images }
    "clean"   { Clean-All }
    default   { Start-DockerCompose }
}
