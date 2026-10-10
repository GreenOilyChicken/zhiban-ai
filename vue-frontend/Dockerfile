FROM node:20-alpine AS builder

WORKDIR /build

# 先复制 package.json，利用缓存
COPY package.json package-lock.json* ./
RUN npm install --registry https://registry.npmmirror.com

# 复制源码并构建
COPY . .
RUN npm run build

# ── 运行阶段：Nginx 静态服务 ─────────────

FROM nginx:1.25-alpine

LABEL maintainer="zhiban-ai"
LABEL description="知伴AI Vue.js前端 + Nginx"

# 复制构建产物
COPY --from=builder /build/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
