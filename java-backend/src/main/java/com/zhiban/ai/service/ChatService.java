package com.zhiban.ai.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.zhiban.ai.dto.ChatRequest;
import com.zhiban.ai.dto.ChatResponse;
import com.zhiban.ai.entity.ChatMessage;
import com.zhiban.ai.entity.ChatSession;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * 对话服务接口
 *
 * @author zhiban
 */
public interface ChatService {

    /**
     * 发送消息并同步获取回复
     */
    ChatResponse send(Long userId, ChatRequest request);

    /**
     * 发送消息并以 SSE 流式返回回复
     */
    SseEmitter sendStream(Long userId, ChatRequest request);

    /**
     * 创建新会话
     *
     * @param userId    用户ID
     * @param title     标题（可空）
     * @param agentType 智能体类型（可空，默认 elderly）
     * @return 会话实体
     */
    ChatSession createSession(Long userId, String title, String agentType);

    /**
     * 获取用户的会话列表
     */
    IPage<ChatSession> listSessions(Long userId, int page, int size);

    /**
     * 获取指定会话的历史消息
     *
     * @param userId    用户ID（用于归属校验）
     * @param sessionId 会话ID
     * @param page      页码
     * @param size      每页数量
     */
    IPage<ChatMessage> listHistory(Long userId, Long sessionId, int page, int size);

    /**
     * 删除会话（逻辑删除）
     */
    void deleteSession(Long userId, Long sessionId);
}
