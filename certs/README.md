# TLS 证书目录

本目录用于存放 Nginx 443 所需的证书，通过 compose 以只读方式挂载到容器
`/etc/nginx/certs/`。

## 文件约定

| 文件名 | 内容 | 说明 |
|--------|------|------|
| `server.key` | 私钥 | **绝不提交仓库**（`.gitignore` 已忽略）；权限 `600` |
| `server.crt` | 证书（含证书链） | 自签名证书直接用；Let's Encrypt 用 `fullchain.pem` 改名为 `server.crt` |

> 若使用商业 CA 签发的证书，通常会得到 `your-domain.crt` + `ca-bundle.crt`，
> 需要按「服务器证书 → 中间证书」顺序合并为 `server.crt`：
> `cat your-domain.crt ca-bundle.crt > certs/server.crt`

## 生成自签名证书（开发 / 内网）

```bash
bash scripts/gen-self-signed-cert.sh -d your-domain.com
```

## 使用 Let's Encrypt（生产，推荐）

```bash
# 1) 先确保 80 端口可达（HTTP-01 校验）
sudo certbot certonly --standalone -d your-domain.com

# 2) 复制到本目录并规范命名
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem certs/server.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem   certs/server.key
sudo chown "$(id -u):$(id -g)" certs/server.key certs/server.crt
chmod 600 certs/server.key

# 3) 续期后需重载 Nginx（证书有效期 90 天）
#    续期钩子示例：docker compose exec vue-frontend nginx -s reload
```

## 启用与验证

```bash
# 启用 HTTPS（叠加 https 覆盖文件）
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d

# 验证
curl -I  http://localhost/          # 期望 301 → https://...
curl -kI https://localhost/         # 期望 200 + Strict-Transport-Security
```

详细说明见 [`DEPLOYMENT.md`](../DEPLOYMENT.md) §11「HTTPS / TLS 部署」。
