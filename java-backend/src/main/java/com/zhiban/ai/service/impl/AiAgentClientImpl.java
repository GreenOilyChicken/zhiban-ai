package com.zhiban.ai.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.config.AiServiceConfig;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.service.AiAgentClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Python AI 智能体服务客户端实现
 *
 * @author zhiban
 */
@Service
public class AiAgentClientImpl implements AiAgentClient {

    private static final Logger log = LoggerFactory.getLogger(AiAgentClientImpl.class);

    private final RestTemplate restTemplate;
    private final AiServiceConfig config;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AiAgentClientImpl(@Qualifier("aiRestTemplate") RestTemplate restTemplate,
                             AiServiceConfig config) {
        this.restTemplate = restTemplate;
        this.config = config;
    }

    // ── 对话 ────────────────────────────────────────────

    @Override
    public String chat(String message, String agent, List<HistoryItem> history) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("message", message);
        body.put("agent", agent == null ? "elderly" : agent);
        if (history != null && !history.isEmpty()) {
            List<Map<String, String>> items = new ArrayList<>();
            for (HistoryItem h : history) {
                items.add(Map.of("role", h.role(), "content", h.content()));
            }
            body.put("history", items);
        }

        String url = config.getBaseUrl() + config.getChatPath();
        try {
            ResponseEntity<String> resp = restTemplate.postForEntity(
                    url, new HttpEntity<>(body, jsonHeaders()), String.class);

            JsonNode root = objectMapper.readTree(resp.getBody());
            JsonNode content = root.get("content");
            if (content == null || content.isNull()) {
                throw new BusinessException(502, "AI 服务返回内容为空");
            }
            return content.asText();
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("调用 AI 对话接口失败: url={}, err={}", url, e.getMessage());
            throw new BusinessException(502, "AI 智能体服务暂时不可用，请稍后重试");
        }
    }

    // ── 语音 ────────────────────────────────────────────

    @Override
    public byte[] tts(String text, String speaker) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("text", text);
        if (speaker != null && !speaker.isBlank()) {
            body.put("speaker", speaker);
        }

        String url = config.getBaseUrl() + config.getTtsPath();
        try {
            ResponseEntity<byte[]> resp = restTemplate.postForEntity(
                    url, new HttpEntity<>(body, jsonHeaders()), byte[].class);
            byte[] audio = resp.getBody();
            if (audio == null || audio.length == 0) {
                throw new BusinessException(502, "TTS 未返回音频数据");
            }
            return audio;
        } catch (BusinessException e) {
            throw e;
        } catch (Exception e) {
            log.error("调用 TTS 接口失败: url={}, err={}", url, e.getMessage());
            throw new BusinessException(502, "语音合成服务暂时不可用");
        }
    }

    @Override
    public String asr(byte[] audio, String filename) {
        String url = config.getBaseUrl() + config.getAsrPath();
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            if (config.getApiKey() != null && !config.getApiKey().isBlank()) {
                headers.set("X-API-Key", config.getApiKey());
            }

            MultiValueMap<String, Object> form = new LinkedMultiValueMap<>();
            form.add("file", new ByteArrayResource(audio) {
                @Override
                public String getFilename() {
                    return filename == null || filename.isBlank() ? "audio.wav" : filename;
                }
            });

            ResponseEntity<String> resp = restTemplate.postForEntity(
                    url, new HttpEntity<>(form, headers), String.class);

            JsonNode root = objectMapper.readTree(resp.getBody());
            JsonNode text = root.get("text");
            return text == null ? "" : text.asText();
        } catch (Exception e) {
            log.error("调用 ASR 接口失败: url={}, err={}", url, e.getMessage());
            throw new BusinessException(502, "语音识别服务暂时不可用");
        }
    }

    @Override
    public String listSpeakers() {
        String url = config.getBaseUrl() + config.getSpeakersPath();
        try {
            ResponseEntity<String> resp = restTemplate.getForEntity(url, String.class);
            return resp.getBody();
        } catch (Exception e) {
            log.warn("获取发音人列表失败: {}", e.getMessage());
            return "{\"speakers\":[]}";
        }
    }

    @Override
    public void switchSpeaker(String speaker) {
        // 发音人状态由 Python 侧持有；Java 侧通过 TTS 请求参数透传
        log.info("发音人切换请求: {}", speaker);
    }

    @Override
    public String currentSpeaker() {
        try {
            JsonNode root = objectMapper.readTree(listSpeakers());
            JsonNode speakers = root.get("speakers");
            if (speakers != null && speakers.isArray()) {
                for (JsonNode s : speakers) {
                    if (s.path("selected").asBoolean(false)) {
                        return s.path("id").asText();
                    }
                }
            }
        } catch (Exception e) {
            log.warn("解析发音人列表失败: {}", e.getMessage());
        }
        return "";
    }

    @Override
    public boolean isHealthy() {
        String url = config.getBaseUrl() + "/api/v1/health";
        try {
            ResponseEntity<String> resp = restTemplate.getForEntity(url, String.class);
            return resp.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.warn("AI 服务健康检查失败: {}", e.getMessage());
            return false;
        }
    }

    // ── 内部工具 ─────────────────────────────────────────

    private HttpHeaders jsonHeaders() {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (config.getApiKey() != null && !config.getApiKey().isBlank()) {
            headers.set("X-API-Key", config.getApiKey());
        }
        return headers;
    }
}
