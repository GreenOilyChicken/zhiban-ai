package com.zhiban.ai.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zhiban.ai.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

/**
 * 用户 Mapper
 *
 * @author zhiban
 */
@Mapper
public interface UserMapper extends BaseMapper<User> {

    /**
     * 根据用户名查询用户（用于登录认证）
     *
     * @param username 用户名
     * @return 用户实体
     */
    @Select("""
        SELECT id, username, password, phone, phone_hash, role, avatar, create_time, update_time
        FROM user
        WHERE username = #{username} AND deleted = 0
        """)
    User selectByUsername(@Param("username") String username);

    /**
     * 检查用户名是否已存在
     *
     * @param username 用户名
     * @return 数量
     */
    @Select("""
        SELECT COUNT(*)
        FROM user
        WHERE username = #{username} AND deleted = 0
        """)
    int countByUsername(@Param("username") String username);

    /**
     * 根据手机号盲索引查询用户（用于手机号登录）
     *
     * 附件一 §8.1：手机号加密存储后无法按明文等值查询，
     * 因此使用 HMAC 盲索引 phone_hash 做等值匹配。
     *
     * @param phoneHash 手机号盲索引
     * @return 用户实体
     */
    @Select("""
        SELECT id, username, password, phone, phone_hash, role, avatar, create_time, update_time
        FROM user
        WHERE phone_hash = #{phoneHash} AND deleted = 0
        LIMIT 1
        """)
    User selectByPhoneHash(@Param("phoneHash") String phoneHash);
}
