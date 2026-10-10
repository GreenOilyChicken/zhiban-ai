package com.zhiban.ai.websocket;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.service.AiAgentClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 对话 WebSocket 处理器
 *
 * 附件一 §3.2：WS /ws/chat 全双工实时对话通道。
 * 附件一 §3.6：WebSocket 须支持心跳检测和断线重连机制。
 *
 * 协议（JSON 文本帧）：
 *   客户端 -> 服务端
 *     {"type":"chat","content":"你好","agent":"elderly"}
 *     {"type":"ping"}                        心跳
 *   服务端 -> 客户端
 *     {"type":"delta","content":"..."}        增量文本
 *     {"type":"done","sessionId":1}
 *     {"type":"pong"}                         心跳应答
 *     {"type":"error","message":"..."}
 *
 * @author zhiban
 */
@Component
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(ChatWebSocketHandler.class);

    private final AiAgentClient aiAgentClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 会话上下文：sessionId -> 历史消息 */
    private final Map<String, List<AiAgentClient.HistoryItem>> contexts = new ConcurrentHashMap<>();

    public ChatWebSocketHandler(AiAgentClient aiAgentClient) {
        this.aiAgentClient = aiAgentClient;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        log.info("WebSocket 连接建立: sessionId={}", session.getId());
        contexts.put(session.getId(), new java.util.concurrent.CopyOnWriteArrayList<>());
        send(session, Map.of("type", "connected", "sessionId", session.getId()));
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        log.info("WebSocket 连接关闭: sessionId={}, status={}", session.getId(), status);
        contexts.remove(session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        String payload = message.getPayload();
        try {
            JsonNode node = objectMapper.readTree(payload);
            String type = node.path("type").asText("chat");

            switch (type) {
                case "ping" -> send(session, Map.of("type", "pong",
                        "ts", System.currentTimeMillis()));
                case "chat" -> handleChat(session, node);
                default -> send(session, Map.of("type", "error",
                        "message", "未知消息类型: " + type));
            }
        } catch (Exception e) {
            log.warn("WebSocket 消息处理失败: {}", e.getMessage());
            send(session, Map.of("type", "error", "message", "消息格式错误"));
        }
    }

    /**
     * 处理对话消息：流式下发增量文本
     */
    private void handleChat(WebSocketSession session, JsonNode node) {
        String content = node.path("content").asText("");
        String agent = node.path("agent").asText("elderly");

        if (content.isBlank()) {
            send(session, Map.of("type", "error", "message", "消息内容不能为空"));
            return;
        }

        List<AiAgentClient.HistoryItem> history =
                contexts.computeIfAbsent(session.getId(),
                        k -> new java.util.concurrent.CopyOnWriteArrayList<>());

        try {
            String reply = aiAgentClient.chat(content, agent, history);

            // 增量下发，模拟打字机效果
            for (String piece : chunk(reply)) {
                send(session, Map.of("type", "delta", "content", piece));
            }

            // 更新上下文（保留最近 10 轮）
            history.add(new AiAgentClient.HistoryItem("user", content));
            history.add(new AiAgentClient.HistoryItem("assistant", reply));
            while (history.size() > 20) {
                history.remove(0);
            }

            send(session, Map.of("type", "done", "agent", agent));
        } catch (Exception e) {
            log.error("WebSocket 对话失败: {}", e.getMessage());
            send(session, Map.of("type", "error",
                    "message", e.getMessage() == null ? "服务异常" : e.getMessage()));
        }
    }

    private List<String> chunk(String text) {
        List<String> pieces = new java.util.ArrayList<>();
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

    private void send(WebSocketSession session, Map<String, Object> data) {
        if (!session.isOpen()) {
            return;
        }
        try {
            session.sendMessage(new TextMessage(
                    objectMapper.writeValueAsString(data)));
        } catch (Exception e) {
            log.warn("WebSocket 发送失败: {}", e.getMessage());
        }
    }
}
