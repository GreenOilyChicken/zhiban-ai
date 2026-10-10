package com.zhiban.ai.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.service.AiAgentClient;
import com.zhiban.ai.service.VoiceService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * 语音服务实现
 *
 * 语音能力统一由 Python AI 服务提供（edge-tts / whisper，可切换阿里云 NLS），
 * Java 侧只做参数校验与转发，避免重复实现。
 *
 * @author zhiban
 */
@Service
public class VoiceServiceImpl implements VoiceService {

    private static final Logger log = LoggerFactory.getLogger(VoiceServiceImpl.class);

    /** 单次 TTS 文本上限（附件一 §3.3 接口约定） */
    private static final int MAX_TTS_LENGTH = 500;

    private final AiAgentClient aiAgentClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public VoiceServiceImpl(AiAgentClient aiAgentClient) {
        this.aiAgentClient = aiAgentClient;
    }

    @Override
    public byte[] textToSpeech(String text, String speaker) {
        if (text == null || text.isBlank()) {
            throw new BusinessException(400, "文本内容不能为空");
        }

        String content = text.trim();
        if (content.length() > MAX_TTS_LENGTH) {
            log.warn("TTS 文本超长（{}字），已截断至 {} 字", content.length(), MAX_TTS_LENGTH);
            content = content.substring(0, MAX_TTS_LENGTH);
        }

        return aiAgentClient.tts(content, speaker);
    }

    @Override
    public String speechToText(byte[] audio, String filename) {
        if (audio == null || audio.length == 0) {
            throw new BusinessException(400, "音频数据不能为空");
        }
        // 单次上传上限 10MB，防止资源滥用
        if (audio.length > 10 * 1024 * 1024) {
            throw new BusinessException(400, "音频文件过大，最大支持 10MB");
        }
        return aiAgentClient.asr(audio, filename);
    }

    @Override
    public String listSpeakers() {
        return aiAgentClient.listSpeakers();
    }

    @Override
    public void switchSpeaker(String speaker) {
        if (speaker == null || speaker.isBlank()) {
            throw new BusinessException(400, "发音人不能为空");
        }
        // 校验发音人是否在可用列表中
        String speakersJson = aiAgentClient.listSpeakers();
        try {
            JsonNode root = objectMapper.readTree(speakersJson);
            JsonNode speakers = root.get("speakers");
            if (speakers != null && speakers.isArray()) {
                for (JsonNode s : speakers) {
                    if (speaker.equals(s.path("id").asText())) {
                        aiAgentClient.switchSpeaker(speaker);
                        return;
                    }
                }
            }
        } catch (Exception e) {
            log.warn("解析发音人列表失败: {}", e.getMessage());
        }
        throw new BusinessException(400, "未知发音人: " + speaker);
    }

    @Override
    public String currentSpeaker() {
        return aiAgentClient.currentSpeaker();
    }
}
