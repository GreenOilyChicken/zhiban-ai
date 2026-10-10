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
-- 对话会话表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `chat_session`;
CREATE TABLE `chat_session` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `user_id`       BIGINT       NOT NULL COMMENT '用户ID',
    `title`         VARCHAR(128) DEFAULT NULL COMMENT '会话标题',
    `agent_type`    VARCHAR(32)  NOT NULL DEFAULT 'elderly' COMMENT '智能体: elderly/govpolicy/tourism',
    `last_message`  VARCHAR(512) DEFAULT NULL COMMENT '最后一条消息摘要',
    `message_count` INT          NOT NULL DEFAULT 0 COMMENT '消息数量',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`       TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0=未删除 1=已删除',
    PRIMARY KEY (`id`),
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_user_update` (`user_id`, `update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';

-- -----------------------------------------------------------
-- 对话消息表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `chat_message`;
CREATE TABLE `chat_message` (
    `id`           BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `session_id`   BIGINT       NOT NULL COMMENT '会话ID',
    `user_id`      BIGINT       NOT NULL COMMENT '用户ID',
    `role`         VARCHAR(16)  NOT NULL COMMENT '角色: user/assistant/system',
    `content`      TEXT         NOT NULL COMMENT '消息内容',
    `message_type` VARCHAR(16)  NOT NULL DEFAULT 'text' COMMENT '消息类型: text/voice',
    `agent_type`   VARCHAR(32)  DEFAULT NULL COMMENT '处理该消息的智能体',
    `model`        VARCHAR(64)  DEFAULT NULL COMMENT '使用的模型',
    `token_usage`  INT          DEFAULT NULL COMMENT 'Token 消耗',
    `response_ms`  BIGINT       DEFAULT NULL COMMENT '响应耗时(毫秒)',
    `references`   TEXT         DEFAULT NULL COMMENT '引用的知识来源(JSON数组)',
    `create_time`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `deleted`      TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0=未删除 1=已删除',
    PRIMARY KEY (`id`),
    INDEX `idx_session_id` (`session_id`),
    INDEX `idx_session_create` (`session_id`, `create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话消息表';

-- -----------------------------------------------------------
-- 智能体人设表
-- -----------------------------------------------------------
DROP TABLE IF EXISTS `agent_persona`;
CREATE TABLE `agent_persona` (
    `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `agent_type`    VARCHAR(32)  NOT NULL COMMENT '智能体: elderly/govpolicy/tourism',
    `name`          VARCHAR(64)  NOT NULL COMMENT '智能体名称',
    `personality`   VARCHAR(1024) DEFAULT NULL COMMENT '人设描述',
    `greeting`      VARCHAR(512) DEFAULT NULL COMMENT '欢迎语',
    `description`   VARCHAR(512) DEFAULT NULL COMMENT '能力说明',
    `enabled`       TINYINT      NOT NULL DEFAULT 1 COMMENT '是否启用: 0=否 1=是',
    `sort_order`    INT          NOT NULL DEFAULT 0 COMMENT '排序',
    `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_agent_type` (`agent_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='智能体人设表';

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

-- 默认智能体人设（附件一 §6.2-6.4）
INSERT INTO `agent_persona` (`agent_type`, `name`, `personality`, `greeting`, `description`, `sort_order`) VALUES
('elderly', '银发康养助手',
 '你是知伴AI银发康养助手，用通俗易懂、耐心温和的语言服务老年用户。回答健康问题时必须说明信息仅供参考，并建议咨询医生或药师。遇到胸痛、卒中、意识障碍、自伤念头等紧急信号时，优先提示拨打 120 或心理援助热线 400-161-9995。',
 '您好，我是知伴AI康养助手。可以帮您查询用药注意事项、慢病护理建议、康复计划，或者了解长护险政策。请问有什么可以帮您？',
 '用药指导、护理建议、康复计划、长护险申请', 1),
('govpolicy', '政务政策助手',
 '你是知伴AI政务政策助手，基于知识库检索结果回答政策问题，回答中必须标注信息来源文件，确保可追溯。信息不确定时明确告知用户，并建议咨询相关政府部门。',
 '您好，我是知伴AI政策助手。您可以咨询惠民政策、养老补贴、医保等问题，我会标注政策来源供您核对。',
 '政策检索、培训台账生成', 2),
('tourism', '文旅导览助手',
 '你是知伴AI文旅导览助手，为游客介绍景点开放时间、门票、交通、看点，可以规划1-3天行程并按上下午晚间分段安排。介绍文化故事时兼顾老年人出行需求，提示休息点、无障碍通道与安全注意事项。',
 '您好，我是知伴AI文旅助手。可以为您介绍景点信息、规划行程路线，或者讲讲景点背后的文化故事。请问您想去哪里？',
 '景点导览、路线规划、文化故事', 3);
