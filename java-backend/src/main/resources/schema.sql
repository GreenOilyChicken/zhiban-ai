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
    `phone`       VARCHAR(255) DEFAULT NULL COMMENT '手机号（AES-256-GCM 加密存储，附件一 §8.1）',
    `phone_hash`  VARCHAR(64)  DEFAULT NULL COMMENT '手机号盲索引（HMAC-SHA256），用于加密后的等值查询',
    `role`        VARCHAR(20)  NOT NULL DEFAULT 'USER' COMMENT '角色: USER / ADMIN',
    `avatar`      VARCHAR(512) DEFAULT NULL COMMENT '头像URL',
    `create_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `update_time` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted`     TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除: 0=未删除 1=已删除',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_user_phone_hash` (`phone_hash`)
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
('admin', '$2a$10$KqJA7uOT0CcRpebowhg45u/m3GQ3dqpf/HkTdgXzlF1Onsit34gAy', NULL, 'ADMIN');

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

-- -----------------------------------------------------------
-- 默认政策文档（附件一 §3.5 / §7：政策问答依赖向量检索后回查本表）
-- 说明：vector_id 必须与 python/knowledge_base/policies 下的源文档文件名一致，
--       否则 RAG 检索命中后无法回查正文，会静默降级为关键词检索。
--       内容为示例摘要，生产环境请替换为真实政策原文。
-- -----------------------------------------------------------
INSERT INTO `gov_policy_document`
(`doc_number`, `title`, `issuing_authority`, `policy_type`, `publish_date`, `region`, `status`, `summary`, `full_text`, `key_points`, `vector_id`) VALUES
('国发〔2026〕1号', '银发经济政策要点', '国务院', '银发经济', '2026-01-15', '全国', 1,
 '发展银发经济，增进老年人福祉，重点支持养老服务、老年用品、健康服务等产业。具体补贴标准以当地最新政策为准。',
 '发展银发经济是积极应对人口老龄化、推动高质量发展的重要举措。重点任务包括：扩大老年用品供给、发展智慧健康养老新业态、提升养老服务能力、培育银发经济产业集群。各地可结合实际出台配套扶持措施，具体标准以当地最新政策为准。',
 '["扩大老年用品供给","发展智慧健康养老","提升养老服务能力","培育产业集群"]',
 '银发经济政策.txt'),
('医保发〔2026〕2号', '医保报销指南', '国家医保局', '政务服务', '2026-02-01', '全国', 1,
 '职工医保与居民医保的报销范围、起付线、报销比例与异地就医备案流程说明，具体比例以参保地最新政策为准。',
 '参保人员在定点医疗机构发生的符合规定的医疗费用，可按参保地政策报销。异地就医需先办理备案。门诊慢特病待遇、住院起付线与报销比例因地区而异，请以参保地医保部门最新政策为准，或拨打医保服务热线 12393 咨询。',
 '["异地就医需备案","起付线与比例因地区而异","咨询热线12393"]',
 '医保报销指南.txt'),
('民政发〔2026〕3号', '长期护理保险政策', '民政部', '政务服务', '2026-03-01', '试点城市', 1,
 '长期护理保险为失能人员提供护理保障，需经失能等级评估，待遇形式与标准以试点城市政策为准。',
 '长期护理保险制度为长期失能人员的基本生活照料和医疗护理提供保障。申请流程一般包括：提交申请、失能等级评估、公示、享受待遇。待遇形式包括机构护理、居家护理等，具体标准与覆盖范围以试点城市最新政策为准，可拨打医保服务热线 12393 咨询。',
 '["需失能等级评估","待遇形式含机构与居家","咨询热线12393"]',
 '长期护理保险政策.txt'),
('民政发〔2026〕4号', '高龄津贴与优待政策', '民政部', '养老服务', '2026-03-20', '全国', 1,
 '高龄津贴面向达到规定年龄的老年人发放，年龄门槛与发放标准由各地自行确定，以当地最新政策为准。',
 '高龄津贴是国家面向高龄老年人发放的福利性补贴。多数地区以 80 周岁为起始年龄，部分地区降至 70 周岁。发放标准由各地根据经济社会发展水平确定，通常随年龄递增。符合条件的老年人可向户籍所在地社区（村）申请，具体以当地民政部门最新政策为准。',
 '["多数地区80周岁起","标准随年龄递增","向社区申请"]',
 '高龄津贴与优待政策.txt'),
('国办发〔2026〕5号', '惠民政策摘要', '国务院办公厅', '政务服务', '2026-04-01', '全国', 1,
 '汇总与老年人密切相关的政务惠民政策要点，包括养老、医疗、救助等方面，具体以当地最新政策为准。',
 '本摘要汇总与老年人日常生活密切相关的政务服务事项，涵盖养老保险待遇资格认证、医疗救助、临时救助、残疾人两项补贴等。各项政策的申请条件与办理材料因地区而异，建议通过当地政务服务热线 12345 或社区窗口咨询确认，以当地最新政策为准。',
 '["涵盖养老医疗救助","办理材料因地区而异","咨询热线12345"]',
 '惠民政策摘要.txt'),
('建城〔2026〕6号', '居家适老化改造与智慧养老', '住房城乡建设部', '养老服务', '2026-04-15', '全国', 1,
 '支持特殊困难老年人家庭实施居家适老化改造，并推广智慧养老设备应用，补贴标准以当地最新政策为准。',
 '居家适老化改造重点面向特殊困难老年人家庭，改造内容包括地面防滑、加装扶手、卫生间改造、配置助行器具等。智慧养老方面推广紧急呼叫、跌倒监测、智能水表等设备。符合条件的家庭可向社区申请，补贴比例与上限以当地最新政策为准。',
 '["面向特殊困难家庭","含防滑扶手改造","可向社区申请"]',
 '居家适老化改造与智慧养老.txt'),
('文旅发〔2026〕7号', '老年教育与银发文旅消费', '文化和旅游部', '文旅项目', '2026-05-01', '全国', 1,
 '鼓励发展老年教育和银发文旅消费，推动景区适老化改造与老年优待，具体优惠以景区最新公告为准。',
 '支持发展老年教育，扩大老年大学学位供给。鼓励开发适合老年人的文旅产品，推动景区开展适老化改造，完善无障碍设施、休息座椅与医疗点。多数景区对 60 或 65 周岁以上老年人实行门票优惠或免票，具体以景区最新公告为准。',
 '["景区适老化改造","老年门票优惠","以景区公告为准"]',
 '老年教育与银发文旅消费.txt'),
('发改〔2026〕8号', '银发经济产业扶持', '国家发展改革委', '银发经济', '2026-05-20', '全国', 1,
 '通过财税、金融、用地等政策支持银发经济产业发展，具体扶持力度以当地最新政策为准。',
 '支持银发经济产业发展的政策工具包括：税收优惠、专项债券支持、信贷投放倾斜、用地保障、人才培训补贴等。鼓励社会资本进入养老服务、康复辅具、智慧健康等领域。各项扶持政策的申报条件与额度以当地主管部门最新政策为准，谨防以补贴为名的诈骗，可拨打 96110 核实。',
 '["财税金融用地支持","鼓励社会资本进入","谨防补贴诈骗"]',
 '银发经济产业扶持.txt');

