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
        SELECT id, username, password, phone, role, avatar, create_time, update_time
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
     * 根据手机号查询用户（用于手机号登录）
     *
     * @param phone 手机号
     * @return 用户实体
     */
    @Select("""
        SELECT id, username, password, phone, role, avatar, create_time, update_time
        FROM user
        WHERE phone = #{phone} AND deleted = 0
        LIMIT 1
        """)
    User selectByPhone(@Param("phone") String phone);
}
