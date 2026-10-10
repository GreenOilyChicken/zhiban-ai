package com.zhiban.ai.controller;

import com.zhiban.ai.service.VoiceService;
import com.zhiban.ai.vo.Result;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

/**
 * 语音交互 Controller
 *
 * 附件一 §3.3：
 *   GET  /api/voice/tts       文本转语音
 *   POST /api/voice/asr       语音识别
 *   GET  /api/voice/speakers  发音人列表
 *
 * @author zhiban
 */
@Validated
@RestController
@RequestMapping("/voice")
public class VoiceController {

    private final VoiceService voiceService;

    public VoiceController(VoiceService voiceService) {
        this.voiceService = voiceService;
    }

    /**
     * 文本转语音，返回 MP3 音频流
     */
    @GetMapping("/tts")
    public ResponseEntity<byte[]> tts(
            @RequestParam @NotBlank(message = "文本不能为空") String text,
            @RequestParam(required = false) String speaker) {

        byte[] audio = voiceService.textToSpeech(text, speaker);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("audio/mpeg"));
        headers.setContentLength(audio.length);
        headers.set(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"tts.mp3\"");

        return ResponseEntity.ok().headers(headers).body(audio);
    }

    /**
     * 语音识别，返回识别文本
     */
    @PostMapping("/asr")
    public Result<String> asr(@RequestPart("file") MultipartFile file) throws IOException {
        if (file == null || file.isEmpty()) {
            return Result.error(400, "音频文件不能为空");
        }
        String text = voiceService.speechToText(file.getBytes(), file.getOriginalFilename());
        return Result.success(text);
    }

    /**
     * 获取可用发音人列表
     */
    @GetMapping("/speakers")
    public Result<Object> speakers() throws IOException {
        String json = voiceService.listSpeakers();
        // 直接透传 Python 侧的 speakers 数组
        com.fasterxml.jackson.databind.JsonNode root =
                new com.fasterxml.jackson.databind.ObjectMapper().readTree(json);
        return Result.success(root.get("speakers"));
    }

    /**
     * 切换发音人
     */
    @PostMapping("/speakers")
    public Result<Void> switchSpeaker(
            @RequestParam @NotBlank(message = "发音人不能为空") String speaker) {
        voiceService.switchSpeaker(speaker);
        return Result.success("切换成功", null);
    }

    /**
     * 当前发音人
     */
    @GetMapping("/speakers/current")
    public Result<String> currentSpeaker() {
        return Result.success(voiceService.currentSpeaker());
    }
}
