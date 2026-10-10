FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /build

# 先复制 pom.xml，利用 Docker 缓存加速依赖下载
COPY pom.xml .
RUN mvn dependency:resolve -B

# 复制源码并构建
COPY src ./src
RUN mvn clean package -DskipTests -B

# ── 运行阶段 ──────────────────────────────

FROM eclipse-temurin:17-jre

LABEL maintainer="zhiban-ai"
LABEL description="知伴AI Spring Boot后端"

WORKDIR /app

COPY --from=builder /build/target/zhiban-ai-backend-1.0.0.jar app.jar

# 环境变量默认值
ENV DB_HOST=mysql
ENV DB_PORT=3306
ENV DB_NAME=zhiban_ai
ENV DB_USERNAME=root
ENV DB_PASSWORD=""
ENV JWT_SECRET=""
ENV RAG_VECTOR_API_URL=http://python-ai:8081/api/v1/search
ENV RAG_API_KEY=""

EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/help/articles?page=1\&size=1 || exit 1

ENTRYPOINT ["java", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-jar", "app.jar"]
