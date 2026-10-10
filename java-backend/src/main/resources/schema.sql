-- ============================================================
-- 知伴AI 数据库初始化脚本
-- 数据库: zhiban_ai
-- ============================================================

CREATE DATABASE IF NOT EXISTS `zhiban_ai` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `zhiban_ai`;

-- -----------------------------------------------------------
-- 用户表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `username`    VARCHAR(64)  NOT NULL COMMENT '用户名',
    `password`    VARCHAR(128) NOT NULL COMMENT '加密密码（BCrypt）',
    `phone`       VARCHAR(20)  DEFAULT NULL COMMENT '手机号',
    `role`        VARCHAR(20)  NOT NULL DEFAULT 'USER' COMMENT '角色: USER / ADMIN',
    `avatar`      VARCHAR(512) DEFAULT NULL COMMENT '头像URL',
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`     TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0=未删除 1=已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- -----------------------------------------------------------
-- 用户配额表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `user_quota`;
CREATE TABLE `user_quota` (
    `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id`      BIGINT       NOT NULL COMMENT '用户ID',
    `quota_type`   VARCHAR(32)  NOT NULL COMMENT '配额类型: POLICY_QA / HELP_SEARCH 等',
    `total_amount` INT          NOT NULL DEFAULT 0 COMMENT '总配额',
    `used_amount`  INT          NOT NULL DEFAULT 0 COMMENT '已使用配额',
    `free_amount`  INT          NOT NULL DEFAULT 0 COMMENT '免费配额',
    `create_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_user_quota_type` (`user_id`, `quota_type`),
    INDEX `idx_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户配额表';

-- -----------------------------------------------------------
-- 政策文档表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `gov_policy_document`;
CREATE TABLE `gov_policy_document` (
    `id`                BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `doc_number`        VARCHAR(128)  DEFAULT NULL COMMENT '文号',
    `title`             VARCHAR(512) NOT NULL COMMENT '标题',
    `issuing_authority` VARCHAR(256)  DEFAULT NULL COMMENT '发文机关',
    `policy_type`       VARCHAR(64)  NOT NULL COMMENT '政策类型: 养老/旅游/政务 等',
    `effective_date`    DATE          DEFAULT NULL COMMENT '生效日期',
    `publish_date`     DATE          DEFAULT NULL COMMENT '发布日期',
    `region`            VARCHAR(128)  DEFAULT NULL COMMENT '适用地区',
    `status`            TINYINT      NOT NULL DEFAULT 1 COMMENT '状态: 0=失效 1=有效',
    `summary`           TEXT          DEFAULT NULL COMMENT '摘要',
    `full_text`         LONGTEXT      DEFAULT NULL COMMENT '全文内容',
    `key_points`        JSON          DEFAULT NULL COMMENT '要点列表（JSON数组）',
    `faq`               JSON          DEFAULT NULL COMMENT '常见问题（JSON数组）',
    `vector_id`         VARCHAR(128)  DEFAULT NULL COMMENT '向量库ID',
    `create_time`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`           TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0=未删除 1=已删除',
    PRIMARY KEY (`id`),
    INDEX `idx_policy_type` (`policy_type`),
    INDEX `idx_status` (`status`),
    INDEX `idx_region` (`region`),
    INDEX `idx_publish_date` (`publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='政策文档表';

-- -----------------------------------------------------------
-- 帮助内容表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `help_content`;
CREATE TABLE `help_content` (
    `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `title`        VARCHAR(256) NOT NULL COMMENT '标题',
    `content`      LONGTEXT     NOT NULL COMMENT '正文内容（富文本/Markdown）',
    `category`     VARCHAR(64)  NOT NULL COMMENT '分类: 老年人/政务/旅游 等',
    `cover_image`  VARCHAR(512)  DEFAULT NULL COMMENT '封面图URL',
    `video_url`    VARCHAR(512)  DEFAULT NULL COMMENT '视频URL',
    `tags`         VARCHAR(512)  DEFAULT NULL COMMENT '标签（逗号分隔）',
    `is_published` TINYINT      NOT NULL DEFAULT 0 COMMENT '是否发布: 0=未发布 1=已发布',
    `create_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`      TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0=未删除 1=已删除',
    PRIMARY KEY (`id`),
    INDEX `idx_category` (`category`),
    INDEX `idx_is_published` (`is_published`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='帮助内容表';

-- -----------------------------------------------------------
-- 分类表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `categories`;
CREATE TABLE `categories` (
    `id`          BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `name`        VARCHAR(64)  NOT NULL COMMENT '分类名称',
    `type`        VARCHAR(32)  NOT NULL COMMENT '类型: POLICY / HELP',
    `sort_order`  INT          NOT NULL DEFAULT 0 COMMENT '排序',
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    INDEX `idx_type` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='分类表';

-- -----------------------------------------------------------
-- 初始化数据
-- -----------------------------------------------------------

-- 默认管理员用户（密码: admin123 的BCrypt加密，生产环境请修改）
INSERT INTO `user` (`username`, `password`, `phone`, `role`) VALUES
('admin', '$2a$10$N.ZOn9G6/YLFixAobF4lqOJ4kFPQfHx3vRZQ6vJr2QpD2vD9wM0E', NULL, 'ADMIN');

-- 默认分类
INSERT INTO `categories` (`name`, `type`, `sort_order`) VALUES
('养老', 'POLICY', 1),
('旅游', 'POLICY', 2),
('政务', 'POLICY', 3),
('老年人', 'HELP', 1),
('政务指南', 'HELP', 2),
('旅游攻略', 'HELP', 3);
