package com.zhiban.ai.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zhiban.ai.entity.ChatMessage;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 对话消息 Mapper
 *
 * @author zhiban
 */
@Mapper
public interface ChatMessageMapper extends BaseMapper<ChatMessage> {

    /**
     * 查询会话的最近 N 条消息（按时间正序返回，用于构建上下文）
     *
     * @param sessionId 会话ID
     * @param limit     最大条数
     * @return 消息列表（时间正序）
     */
    @Select("""
        SELECT * FROM (
            SELECT id, session_id, user_id, role, content, message_type,
                   agent_type, model, token_usage, response_ms, `references`, create_time
            FROM chat_message
            WHERE session_id = #{sessionId} AND deleted = 0
            ORDER BY id DESC
            LIMIT #{limit}
        ) t ORDER BY t.id ASC
        """)
    List<ChatMessage> selectRecentMessages(@Param("sessionId") Long sessionId,
                                           @Param("limit") int limit);
}
