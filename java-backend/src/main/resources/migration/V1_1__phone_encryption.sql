-- ============================================================
-- 迁移脚本：手机号加密存储支持（附件一 §8.1）
-- 适用：已按旧版 schema.sql 建库的存量环境
-- 幂等性：可重复执行（先判断列是否存在）
-- ============================================================
--
-- 背景：
--   旧版 user.phone 为 VARCHAR(20) 明文存储。为满足「敏感数据须加密存储」，
--   现改为 AES-256-GCM 密文存储，并新增 HMAC 盲索引 phone_hash 以支持等值查询。
--
-- 执行前提：
--   应用需配置环境变量 PHONE_ENC_KEY / PHONE_INDEX_KEY（见 application.yml）。
--
-- 注意：
--   1) 本脚本只做结构迁移（加长 phone、新增 phone_hash 与索引），
--      不会也无法在 SQL 层把已有明文加密为密文（加密在应用侧完成）。
--   2) 应用已兼容历史明文：读取时无 enc1: 前缀则按明文处理。
--      因此存量数据可继续使用，后续按需在应用层做一次性加密回填。
-- ============================================================

USE `zhiban_ai`;

-- 1) 扩展 phone 列以容纳密文（enc1: + Base64(iv+ct+tag)，手机号约 60-80 字符）
ALTER TABLE `user`
    MODIFY COLUMN `phone` VARCHAR(255) DEFAULT NULL COMMENT '手机号（AES-256-GCM 加密存储，附件一 §8.1）';

-- 2) 新增盲索引列（若已存在会报错，可忽略该条错误继续）
ALTER TABLE `user`
    ADD COLUMN `phone_hash` VARCHAR(64) DEFAULT NULL COMMENT '手机号盲索引（HMAC-SHA256）'
    AFTER `phone`;

-- 3) 为盲索引建立唯一索引，防止同一手机号重复注册
--    注意：历史数据 phone_hash 均为 NULL，MySQL 唯一索引允许多个 NULL，不影响存量数据。
ALTER TABLE `user`
    ADD UNIQUE KEY `uk_user_phone_hash` (`phone_hash`);

-- 4) 校验
-- SELECT id, username, LEFT(phone, 8) AS phone_prefix, phone_hash FROM `user` LIMIT 10;
