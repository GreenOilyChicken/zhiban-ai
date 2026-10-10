package com.zhiban.ai.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zhiban.ai.entity.ChatSession;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

/**
 * 对话会话 Mapper
 *
 * @author zhiban
 */
@Mapper
public interface ChatSessionMapper extends BaseMapper<ChatSession> {

    /**
     * 原子递增消息计数并更新最后一条消息摘要
     *
     * @param sessionId   会话ID
     * @param lastMessage 最后一条消息摘要
     * @return 受影响行数
     */
    @Update("""
        UPDATE chat_session
        SET message_count = message_count + 1,
            last_message = #{lastMessage},
            update_time = NOW()
        WHERE id = #{sessionId} AND deleted = 0
        """)
    int touchSession(@Param("sessionId") Long sessionId,
                     @Param("lastMessage") String lastMessage);
}
