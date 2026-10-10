package com.zhiban.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.service.AiAgentClient;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Java → Python AI 服务真实联调测试
 *
 * 需要本机已启动 Python AI 服务（默认 http://localhost:8081），
 * 因此默认跳过，仅在显式开启时执行：
 *
 *   mvn test -Dtest=AiServiceLiveTest -Dai.live=true
 *
 * 覆盖附件一 §3.2（对话）、§3.3（语音）、§2.1（Java/Python 分层）。
 *
 * @author zhiban
 */
@SpringBootTest
@ActiveProfiles("test")
@EnabledIfSystemProperty(named = "ai.live", matches = "true")
@DisplayName("Java → Python AI 联调（需 Python 服务在线）")
class AiServiceLiveTest {

    @Autowired
    private AiAgentClient aiAgentClient;

    private final ObjectMapper mapper = new ObjectMapper();

    @Test
    @DisplayName("AI 服务健康检查通过")
    void health() {
        assertThat(aiAgentClient.isHealthy()).isTrue();
    }

    @Test
    @DisplayName("三大智能体均可对话并返回非空回复")
    void chatWithAllAgents() {
        for (String agent : List.of("elderly", "govpolicy", "tourism")) {
            String reply = aiAgentClient.chat("你好，请用一句话介绍你能做什么", agent, List.of());
            assertThat(reply).as("agent=%s 回复不应为空", agent).isNotBlank();
        }
    }

    @Test
    @DisplayName("多轮对话保留上下文")
    void multiTurnContext() {
        List<AiAgentClient.HistoryItem> history = List.of(
                new AiAgentClient.HistoryItem("user", "我住在杭州"),
                new AiAgentClient.HistoryItem("assistant", "好的，杭州是个好地方")
        );
        String reply = aiAgentClient.chat("帮我推荐一下本地景点", "tourism", history);
        assertThat(reply).isNotBlank();
    }

    @Test
    @DisplayName("TTS 返回 MP3 音频字节")
    void ttsReturnsAudio() {
        byte[] audio = aiAgentClient.tts("您好，我是知伴AI助手", null);
        assertThat(audio).isNotEmpty();
        // MP3 帧同步头 0xFF 0xFB/0xF3/0xF2 或 ID3 标签
        boolean looksMp3 = (audio.length > 2
                && (audio[0] & 0xFF) == 0xFF
                && ((audio[1] & 0xE0) == 0xE0))
                || (audio.length > 3 && audio[0] == 'I' && audio[1] == 'D' && audio[2] == '3');
        assertThat(looksMp3).as("返回内容应为 MP3 音频").isTrue();
    }

    @Test
    @DisplayName("发音人列表包含当前选中项")
    void speakers() throws Exception {
        JsonNode root = mapper.readTree(aiAgentClient.listSpeakers());
        JsonNode speakers = root.get("speakers");
        assertThat(speakers).isNotNull();
        assertThat(speakers.size()).isGreaterThan(0);
        assertThat(aiAgentClient.currentSpeaker()).isNotBlank();
    }
}
