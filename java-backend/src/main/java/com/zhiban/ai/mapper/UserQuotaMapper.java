package com.zhiban.ai.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zhiban.ai.entity.UserQuota;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

/**
 * 用户配额 Mapper
 *
 * 关键设计：配额扣减使用原子性 SQL UPDATE（而非先读后写），
 * 避免并发场景下的超扣问题。
 *
 * @author zhiban
 */
@Mapper
public interface UserQuotaMapper extends BaseMapper<UserQuota> {

    /**
     * 原子扣减配额
     * 通过 SQL 条件 (used_amount + 1 <= total_amount) 保证不会超扣，
     * 返回受影响行数：1=扣减成功，0=配额不足。
     *
     * @param userId    用户ID
     * @param quotaType 配额类型
     * @return 受影响行数（1=成功，0=配额不足）
     */
    @Update("""
        UPDATE user_quota
        SET used_amount = used_amount + 1,
            update_time = NOW()
        WHERE user_id = #{userId}
          AND quota_type = #{quotaType}
          AND used_amount < total_amount
        """)
    int atomicDeductQuota(@Param("userId") Long userId,
                         @Param("quotaType") String quotaType);

    /**
     * 初始化用户配额（如果不存在则插入）
     *
     * @param userId      用户ID
     * @param quotaType   配额类型
     * @param totalAmount 总配额
     * @param freeAmount  免费配额
     * @return 受影响行数
     */
    @org.apache.ibatis.annotations.Insert("""
        INSERT IGNORE INTO user_quota (user_id, quota_type, total_amount, used_amount, free_amount, create_time, update_time)
        VALUES (#{userId}, #{quotaType}, #{totalAmount}, 0, #{freeAmount}, NOW(), NOW())
        """)
    int initQuotaIfAbsent(@Param("userId") Long userId,
                          @Param("quotaType") String quotaType,
                          @Param("totalAmount") Integer totalAmount,
                          @Param("freeAmount") Integer freeAmount);
}
