package com.zhiban.ai.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.zhiban.ai.dto.ChatRequest;
import com.zhiban.ai.dto.ChatResponse;
import com.zhiban.ai.dto.SessionCreateRequest;
import com.zhiban.ai.entity.ChatMessage;
import com.zhiban.ai.entity.ChatSession;
import com.zhiban.ai.security.SecurityUtils;
import com.zhiban.ai.service.ChatService;
import com.zhiban.ai.vo.Result;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * 对话 Controller
 * 附件一 §3.2：文本消息、SSE 流式回复、会话管理与历史记录。
 *
 * @author zhiban
 */
@Validated
@RestController
@RequestMapping("/chat")
public class ChatController {

    private final ChatService chatService;
    private final SecurityUtils securityUtils;

    public ChatController(ChatService chatService, SecurityUtils securityUtils) {
        this.chatService = chatService;
        this.securityUtils = securityUtils;
    }

    /**
     * 发送文本消息，返回 AI 回复
     */
    @PostMapping("/send")
    public Result<ChatResponse> send(@Valid @RequestBody ChatRequest request) {
        Long userId = securityUtils.getCurrentUserId();
        return Result.success(chatService.send(userId, request));
    }

    /**
     * SSE 流式返回 AI 回复
     * 兼容浏览器 EventSource：事件名 session / delta / done / error
     */
    @PostMapping(value = "/send/stream", produces = "text/event-stream;charset=UTF-8")
    public SseEmitter sendStream(@Valid @RequestBody ChatRequest request) {
        Long userId = securityUtils.getCurrentUserId();
        return chatService.sendStream(userId, request);
    }

    /**
     * 创建新的对话会话
     */
    @PostMapping("/session")
    public Result<ChatSession> createSession(@Valid @RequestBody SessionCreateRequest request) {
        Long userId = securityUtils.getCurrentUserId();
        ChatSession session = chatService.createSession(
                userId, request.getTitle(), request.getAgentType());
        return Result.success(session);
    }

    /**
     * 获取用户所有会话列表
     */
    @GetMapping("/sessions")
    public Result<IPage<ChatSession>> listSessions(
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size) {
        Long userId = securityUtils.getCurrentUserId();
        return Result.success(chatService.listSessions(userId, page, size));
    }

    /**
     * 获取指定会话的历史消息
     */
    @GetMapping("/history")
    public Result<IPage<ChatMessage>> history(
            @RequestParam Long sessionId,
            @RequestParam(defaultValue = "1") @Min(1) int page,
            @RequestParam(defaultValue = "50") @Min(1) @Max(200) int size) {
        Long userId = securityUtils.getCurrentUserId();
        return Result.success(chatService.listHistory(userId, sessionId, page, size));
    }

    /**
     * 删除会话
     */
    @DeleteMapping("/session/{sessionId}")
    public Result<Void> deleteSession(@PathVariable Long sessionId) {
        Long userId = securityUtils.getCurrentUserId();
        chatService.deleteSession(userId, sessionId);
        return Result.success();
    }
}
