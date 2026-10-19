package com.zhiban.ai.service;

import java.util.List;

/**
 * Python AI 智能体服务客户端
 * 负责 Java 后端与 Python 智能体系统之间的 HTTP 通信。
 *
 * @author zhiban
 */
public interface AiAgentClient {

    /**
     * 智能体对话
     *
     * @param message  用户消息
     * @param agent    智能体类型: elderly / govpolicy / tourism
     * @param history  历史消息（role/content）
     * @return AI 回复文本
     */
    String chat(String message, String agent, List<HistoryItem> history);

    /**
     * 文本转语音，返回音频字节
     *
     * @param text    文本
     * @param speaker 发音人（可为空）
     * @return MP3 音频字节
     */
    byte[] tts(String text, String speaker);

    /**
     * 语音识别
     *
     * @param audio    音频字节
     * @param filename 原始文件名
     * @return 识别文本
     */
    String asr(byte[] audio, String filename);

    /**
     * 可用发音人列表（原始 JSON 数组字符串）
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

    /**
     * AI 服务健康检查
     *
     * @return true=可用
     */
    boolean isHealthy();

    /**
     * 重建/同步知识库向量索引（附件一 §4.2 政策管理「知识库同步」）
     *
     * @param collection 集合名（govpolicy / elderly / tourism）
     * @param rebuild    true=清库全量重建，false=增量更新
     * @return AI 服务返回的消息
     */
    String rebuildKnowledgeBase(String collection, boolean rebuild);

    /**
     * 上传知识库文档并同步索引（附件一 §4.2 政策管理「文档上传」）
     *
     * @param content    文件字节
     * @param filename   原始文件名
     * @param collection 目标集合
     * @param rebuild    是否上传后立即重建索引
     * @return AI 服务返回的消息
     */
    String uploadKnowledgeBaseDocument(byte[] content, String filename,
                                       String collection, boolean rebuild);

    /**
     * 对话历史条目
     */
    record HistoryItem(String role, String content) {
    }
}
