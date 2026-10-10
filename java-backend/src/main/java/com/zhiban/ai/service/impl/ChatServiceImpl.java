package com.zhiban.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.dto.ChatRequest;
import com.zhiban.ai.dto.ChatResponse;
import com.zhiban.ai.entity.ChatMessage;
import com.zhiban.ai.entity.ChatSession;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.mapper.ChatMessageMapper;
import com.zhiban.ai.mapper.ChatSessionMapper;
import com.zhiban.ai.service.AiAgentClient;
import com.zhiban.ai.service.ChatService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 对话服务实现
 *
 * 附件一 §3.2：文本对话、SSE 流式回复、会话管理与历史记录。
 * 附件一 §6.5：多轮对话须保留上下文（至少 10 轮）。
 *
 * @author zhiban
 */
@Service
public class ChatServiceImpl implements ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatServiceImpl.class);

    /**
     * 上下文保留轮数（1 轮 = 1 问 + 1 答）
     * 附件一 §6.5 要求至少 10 轮，这里取 10 轮 => 20 条消息。
     */
    private static final int CONTEXT_ROUNDS = 10;
    private static final int CONTEXT_MESSAGES = CONTEXT_ROUNDS * 2;

    /** 支持的智能体类型 */
    private static final Set<String> AGENT_TYPES = Set.of("elderly", "govpolicy", "tourism");
    private static final String DEFAULT_AGENT = "elderly";

    /** SSE 超时：10 分钟 */
    private static final long SSE_TIMEOUT_MS = 10 * 60 * 1000L;

    private final ChatSessionMapper sessionMapper;
    private final ChatMessageMapper messageMapper;
    private final AiAgentClient aiAgentClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** SSE 流式任务执行器（守护线程，避免阻塞请求线程） */
    private final ExecutorService streamExecutor = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "chat-sse");
        t.setDaemon(true);
        return t;
    });

    public ChatServiceImpl(ChatSessionMapper sessionMapper,
                           ChatMessageMapper messageMapper,
                           AiAgentClient aiAgentClient) {
        this.sessionMapper = sessionMapper;
        this.messageMapper = messageMapper;
        this.aiAgentClient = aiAgentClient;
    }

    // ── 同步对话 ────────────────────────────────────────

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ChatResponse send(Long userId, ChatRequest request) {
        long start = System.currentTimeMillis();

        ChatSession session = resolveSession(userId, request);
        String agentType = resolveAgentType(session, request);

        // 1. 保存用户消息
        saveMessage(session.getId(), userId, "user", request.getContent(),
                request.getMessageType(), agentType, null, null, null);

        // 2. 构建上下文（最近 10 轮）
        List<AiAgentClient.HistoryItem> history = loadHistory(session.getId());

        // 3. 调用 Python 智能体
        String reply = aiAgentClient.chat(request.getContent(), agentType, history);

        long elapsed = System.currentTimeMillis() - start;

        // 4. 保存助手回复
        ChatMessage assistant = saveMessage(session.getId(), userId, "assistant", reply,
                "text", agentType, null, null, elapsed);

        // 5. 更新会话
        sessionMapper.touchSession(session.getId(), truncate(reply, 200));

        ChatResponse response = new ChatResponse();
        response.setMessageId(assistant.getId());
        response.setSessionId(session.getId());
        response.setContent(reply);
        response.setAgentType(agentType);
        response.setResponseTime(elapsed);
        response.setReferences(new ArrayList<>());

        log.info("对话完成: userId={}, sessionId={}, agent={}, elapsed={}ms",
                userId, session.getId(), agentType, elapsed);
        return response;
    }

    // ── SSE 流式对话 ────────────────────────────────────

    @Override
    public SseEmitter sendStream(Long userId, ChatRequest request) {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT_MS);

        streamExecutor.execute(() -> {
            long start = System.currentTimeMillis();
            ChatSession session;
            String agentType;
            try {
                session = resolveSession(userId, request);
                agentType = resolveAgentType(session, request);
                saveMessage(session.getId(), userId, "user", request.getContent(),
                        request.getMessageType(), agentType, null, null, null);
            } catch (Exception e) {
                log.error("SSE 会话准备失败: {}", e.getMessage());
                completeWithError(emitter, e.getMessage());
                return;
            }

            // 发送会话信息，便于前端立即渲染
            try {
                emitter.send(SseEmitter.event().name("session")
                        .data(java.util.Map.of("sessionId", session.getId(), "agentType", agentType)));
            } catch (IOException e) {
                log.warn("SSE 发送会话事件失败: {}", e.getMessage());
                emitter.complete();
                return;
            }

            List<AiAgentClient.HistoryItem> history = loadHistory(session.getId());
            StringBuilder full = new StringBuilder();

            try {
                // Java 侧当前按「完整回复后分片下发」实现：
                // Python 侧 /api/v1/chat 返回完整文本，这里切成增量推给前端，
                // 保证 EventSource 兼容性与前端逐字渲染体验。
                String reply = aiAgentClient.chat(request.getContent(), agentType, history);
                for (String piece : chunk(reply)) {
                    full.append(piece);
                    emitter.send(SseEmitter.event().name("delta")
                            .data(java.util.Map.of("content", piece)));
                }

                long elapsed = System.currentTimeMillis() - start;
                ChatMessage assistant = saveMessage(session.getId(), userId, "assistant",
                        full.toString(), "text", agentType, null, null, elapsed);
                sessionMapper.touchSession(session.getId(), truncate(full.toString(), 200));

                emitter.send(SseEmitter.event().name("done").data(java.util.Map.of(
                        "messageId", assistant.getId(),
                        "sessionId", session.getId(),
                        "agentType", agentType,
                        "responseTime", elapsed)));
                emitter.complete();

                log.info("SSE 对话完成: userId={}, sessionId={}, elapsed={}ms",
                        userId, session.getId(), elapsed);
            } catch (Exception e) {
                log.error("SSE 对话失败: {}", e.getMessage());
                completeWithError(emitter, e.getMessage());
            }
        });

        return emitter;
    }

    // ── 会话管理 ────────────────────────────────────────

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ChatSession createSession(Long userId, String title, String agentType) {
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setTitle(title == null || title.isBlank() ? "新对话" : truncate(title, 120));
        session.setAgentType(normalizeAgent(agentType));
        session.setMessageCount(0);
        sessionMapper.insert(session);
        return session;
    }

    @Override
    public IPage<ChatSession> listSessions(Long userId, int page, int size) {
        Page<ChatSession> pageParam = new Page<>(page, size);
        return sessionMapper.selectPage(pageParam,
                new LambdaQueryWrapper<ChatSession>()
                        .eq(ChatSession::getUserId, userId)
                        .orderByDesc(ChatSession::getUpdateTime));
    }

    @Override
    public IPage<ChatMessage> listHistory(Long userId, Long sessionId, int page, int size) {
        requireOwnedSession(userId, sessionId);
        Page<ChatMessage> pageParam = new Page<>(page, size);
        return messageMapper.selectPage(pageParam,
                new LambdaQueryWrapper<ChatMessage>()
                        .eq(ChatMessage::getSessionId, sessionId)
                        .orderByAsc(ChatMessage::getId));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteSession(Long userId, Long sessionId) {
        ChatSession session = requireOwnedSession(userId, sessionId);
        sessionMapper.deleteById(session.getId());
        messageMapper.delete(new LambdaQueryWrapper<ChatMessage>()
                .eq(ChatMessage::getSessionId, sessionId));
    }

    // ── 内部方法 ────────────────────────────────────────

    /**
     * 解析会话：sessionId 存在则校验归属，否则新建
     */
    private ChatSession resolveSession(Long userId, ChatRequest request) {
        if (request.getSessionId() != null) {
            return requireOwnedSession(userId, request.getSessionId());
        }
        ChatSession session = new ChatSession();
        session.setUserId(userId);
        session.setTitle(truncate(request.getContent(), 30));
        session.setAgentType(normalizeAgent(request.getAgentType()));
        session.setMessageCount(0);
        sessionMapper.insert(session);
        return session;
    }

    /**
     * 校验会话归属，防止越权访问他人会话
     */
    private ChatSession requireOwnedSession(Long userId, Long sessionId) {
        ChatSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new BusinessException(404, "会话不存在");
        }
        if (!session.getUserId().equals(userId)) {
            throw new BusinessException(403, "无权访问该会话");
        }
        return session;
    }

    /**
     * 决定本次对话使用的智能体
     */
    private String resolveAgentType(ChatSession session, ChatRequest request) {
        if (request.getAgentType() != null && !request.getAgentType().isBlank()) {
            return normalizeAgent(request.getAgentType());
        }
        return normalizeAgent(session.getAgentType());
    }

    private String normalizeAgent(String agentType) {
        if (agentType == null || agentType.isBlank()) {
            return DEFAULT_AGENT;
        }
        String lower = agentType.trim().toLowerCase();
        return AGENT_TYPES.contains(lower) ? lower : DEFAULT_AGENT;
    }

    /**
     * 读取最近 N 条消息作为上下文（时间正序）
     */
    private List<AiAgentClient.HistoryItem> loadHistory(Long sessionId) {
        List<ChatMessage> recent = messageMapper.selectRecentMessages(sessionId, CONTEXT_MESSAGES);
        List<AiAgentClient.HistoryItem> history = new ArrayList<>();
        for (ChatMessage m : recent) {
            history.add(new AiAgentClient.HistoryItem(m.getRole(), m.getContent()));
        }
        return history;
    }

    private ChatMessage saveMessage(Long sessionId, Long userId, String role, String content,
                                    String messageType, String agentType, String model,
                                    Integer tokenUsage, Long responseMs) {
        ChatMessage msg = new ChatMessage();
        msg.setSessionId(sessionId);
        msg.setUserId(userId);
        msg.setRole(role);
        msg.setContent(content);
        msg.setMessageType(messageType == null ? "text" : messageType);
        msg.setAgentType(agentType);
        msg.setModel(model);
        msg.setTokenUsage(tokenUsage);
        msg.setResponseMs(responseMs);
        messageMapper.insert(msg);
        return msg;
    }

    /**
     * 把完整回复切成流式片段（在标点处断句，前端逐段渲染）
     */
    private List<String> chunk(String text) {
        List<String> pieces = new ArrayList<>();
        if (text == null || text.isEmpty()) {
            return pieces;
        }
        StringBuilder buf = new StringBuilder();
        for (char ch : text.toCharArray()) {
            buf.append(ch);
            if (buf.length() >= 12 && "。！？；\n，、：".indexOf(ch) >= 0) {
                pieces.add(buf.toString());
                buf.setLength(0);
            } else if (buf.length() >= 48) {
                pieces.add(buf.toString());
                buf.setLength(0);
            }
        }
        if (buf.length() > 0) {
            pieces.add(buf.toString());
        }
        return pieces;
    }

    private void completeWithError(SseEmitter emitter, String message) {
        try {
            emitter.send(SseEmitter.event().name("error")
                    .data(java.util.Map.of("message",
                            message == null ? "服务异常" : message)));
        } catch (Exception ignored) {
            // 客户端可能已断开
        }
        emitter.complete();
    }

    private String truncate(String s, int max) {
        if (s == null) {
            return null;
        }
        return s.length() <= max ? s : s.substring(0, max);
    }
}
