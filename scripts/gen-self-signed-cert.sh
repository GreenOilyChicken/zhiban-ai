#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# 知伴AI — 自签名 TLS 证书生成脚本
# ═══════════════════════════════════════════════════════
#
# 用途：为开发 / 内网 / 演示环境生成自签名证书，供 Nginx 443 使用。
#       【生产环境请使用受信任证书（Let's Encrypt 或商业 CA）】，
#       自签名证书会被浏览器/微信小程序判定为不受信任。
#
# 用法：
#   bash scripts/gen-self-signed-cert.sh                       # 默认 CN=localhost
#   bash scripts/gen-self-signed-cert.sh -d your-domain.com    # 指定域名
#   bash scripts/gen-self-signed-cert.sh -d 10.0.0.5 -i 10.0.0.5 -n 825
#   bash scripts/gen-self-signed-cert.sh --force               # 覆盖已有证书
#   bash scripts/gen-self-signed-cert.sh -h
#
# 产物（默认写入 <项目根>/certs/）：
#   certs/server.key   私钥（chmod 600，已被 .gitignore 忽略，切勿提交）
#   certs/server.crt   证书（含 SAN，自签名）
#
# 生成的证书与 docker-compose 的 ./certs:/etc/nginx/certs:ro 挂载约定一致。
# ═══════════════════════════════════════════════════════

set -euo pipefail

# ── 默认参数 ──────────────────────────────────────────
DOMAIN="localhost"
DAYS=825                 # 浏览器对自签名证书的宽限期上限（约 13 个月）
CERT_DIR=""
FORCE=0
EXTRA_IPS=()
EXTRA_DNS=()

# ── 定位项目根目录（脚本位于 <root>/scripts/ 下）────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
    sed -n '2,26p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
}

# ── 解析参数 ──────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--domain)  DOMAIN="${2:?--domain 需要一个值}"; shift 2 ;;
        -n|--days)    DAYS="${2:?--days 需要一个值}"; shift 2 ;;
        -o|--out-dir) CERT_DIR="${2:?--out-dir 需要一个值}"; shift 2 ;;
        -i|--ip)      EXTRA_IPS+=("${2:?--ip 需要一个值}"); shift 2 ;;
        -s|--san)     EXTRA_DNS+=("${2:?--san 需要一个值}"); shift 2 ;;
        -f|--force)   FORCE=1; shift ;;
        -h|--help)    usage ;;
        *) echo "未知参数：$1（用 -h 查看用法）" >&2; exit 2 ;;
    esac
done

# 默认输出目录：<项目根>/certs
[[ -n "$CERT_DIR" ]] || CERT_DIR="${PROJECT_ROOT}/certs"
KEY_FILE="${CERT_DIR}/server.key"
CRT_FILE="${CERT_DIR}/server.crt"

# ── 前置检查 ──────────────────────────────────────────
if ! command -v openssl >/dev/null 2>&1; then
    echo "❌ 未找到 openssl，请先安装（Debian/Ubuntu: apt-get install openssl）" >&2
    exit 1
fi

if [[ ! "$DAYS" =~ ^[0-9]+$ ]] || [[ "$DAYS" -lt 1 ]]; then
    echo "❌ --days 必须是正整数，当前为：${DAYS}" >&2
    exit 2
fi

mkdir -p "$CERT_DIR"
# 私钥保护：目录 700、文件 600（umask 在生成前后均生效）
chmod 700 "$CERT_DIR" 2>/dev/null || true

if [[ -e "$KEY_FILE" || -e "$CRT_FILE" ]]; then
    if [[ "$FORCE" -ne 1 ]]; then
        echo "❌ 已存在证书：${KEY_FILE} / ${CRT_FILE}" >&2
        echo "   如需覆盖请加 --force（会销毁现有私钥，请先确认已备份）" >&2
        exit 1
    fi
    echo "⚠️  --force 已指定，覆盖已有证书"
    rm -f "$KEY_FILE" "$CRT_FILE"
fi

# ── 组装 SAN（Subject Alternative Name）───────────────
# 现代浏览器/小程序不再看 CN，只看 SAN，因此必须写入。
# 用关联数组去重，避免 --ip 127.0.0.1 之类的重复项。
declare -A _SAN_SEEN=()
SAN_PARTS=()
add_san() {  # add_san <DNS|IP> <value>
    local entry="$1:$2"
    [[ -n "${_SAN_SEEN[$entry]:-}" ]] && return 0
    _SAN_SEEN[$entry]=1
    SAN_PARTS+=("$entry")
}

add_san DNS "$DOMAIN"
[[ "$DOMAIN" == "localhost" ]] || add_san DNS localhost
# 若 --domain 本身是 IP，则同时作为 IP SAN
if [[ "$DOMAIN" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
    add_san IP "$DOMAIN"
fi
for d in ${EXTRA_DNS[@]+"${EXTRA_DNS[@]}"}; do
    [[ -n "$d" ]] && add_san DNS "$d"
done
add_san IP 127.0.0.1
for ip in ${EXTRA_IPS[@]+"${EXTRA_IPS[@]}"}; do
    [[ -n "$ip" ]] && add_san IP "$ip"
done

SAN="$(IFS=,; echo "${SAN_PARTS[*]}")"

# ── 生成私钥 + 自签名证书（单条 openssl 命令，无需临时 CSR 文件）──
umask 077
openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CRT_FILE" \
    -days "$DAYS" \
    -sha256 \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=ZhibanAI-Development/CN=${DOMAIN}" \
    -addext "subjectAltName=${SAN}" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth" \
    -addext "basicConstraints=critical,CA:FALSE"

chmod 600 "$KEY_FILE"
chmod 644 "$CRT_FILE"

# ── 输出结果摘要 ──────────────────────────────────────
echo ""
echo "✅ 自签名证书已生成："
echo "   私钥：${KEY_FILE}"
echo "   证书：${CRT_FILE}"
echo ""
echo "── 证书信息 ──────────────────────────────────"
openssl x509 -in "$CRT_FILE" -noout -subject -issuer -dates -ext subjectAltName 2>/dev/null \
    | sed 's/^/   /'
echo ""
echo "── 下一步 ────────────────────────────────────"
echo "   1) 确认私钥未被提交：git status --short certs/   # 应为空（.gitignore 已忽略）"
echo "   2) 启用 HTTPS：docker compose -f docker-compose.yml -f docker-compose.https.yml up -d"
echo "   3) 验证：curl -k https://localhost/api/help/articles?page=1&size=1"
echo ""
echo "⚠️  自签名证书仅适用于开发/内网/演示；生产环境请改用受信任 CA 证书，"
echo "    并将 fullchain.pem/privkey.pem 放置为 certs/server.crt 与 certs/server.key。"
