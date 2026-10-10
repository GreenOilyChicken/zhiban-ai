package com.zhiban.ai.service;

/**
 * 语音服务接口
 * 附件一 §3.3：文字转语音、语音识别、发音人切换。
 *
 * @author zhiban
 */
public interface VoiceService {

    /**
     * 文本转语音
     *
     * @param text    文本（最长 500 字）
     * @param speaker 发音人（可为空，使用默认）
     * @return MP3 音频字节
     */
    byte[] textToSpeech(String text, String speaker);

    /**
     * 语音识别
     *
     * @param audio    音频字节
     * @param filename 原始文件名（用于推断格式）
     * @return 识别文本
     */
    String speechToText(byte[] audio, String filename);

    /**
     * 可用发音人列表（JSON 字符串）
     */
    String listSpeakers();

    /**
     * 切换默认发音人
     */
    void switchSpeaker(String speaker);

    /**
     * 当前发音人
     */
    String currentSpeaker();
}
