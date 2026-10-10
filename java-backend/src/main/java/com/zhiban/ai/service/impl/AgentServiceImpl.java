package com.zhiban.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.zhiban.ai.entity.AgentPersona;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.mapper.AgentPersonaMapper;
import com.zhiban.ai.service.AgentService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 智能体人设服务实现
 *
 * @author zhiban
 */
@Service
public class AgentServiceImpl implements AgentService {

    private static final Logger log = LoggerFactory.getLogger(AgentServiceImpl.class);

    /** 附件一 §6：三大智能体方向 */
    private static final Set<String> AGENT_TYPES = Set.of("elderly", "govpolicy", "tourism");
    private static final String DEFAULT_AGENT = "elderly";

    /** 数据库不可用时的兜底人设（保证接口始终可用） */
    private static final Map<String, AgentPersona> FALLBACK = Map.of(
            "elderly", fallback("elderly", "银发康养助手",
                    "你是知伴AI银发康养助手，用通俗易懂、耐心温和的语言服务老年用户。"
                            + "回答健康问题时必须说明信息仅供参考，并建议咨询医生或药师。"
                            + "遇到胸痛、卒中、意识障碍、自伤念头等紧急信号时，"
                            + "优先提示拨打 120 或心理援助热线 400-161-9995。",
                    "您好，我是知伴AI康养助手。可以帮您查询用药注意事项、慢病护理建议、"
                            + "康复计划，或者了解长护险政策。请问有什么可以帮您？",
                    "用药指导、护理建议、康复计划、长护险申请"),
            "govpolicy", fallback("govpolicy", "政务政策助手",
                    "你是知伴AI政务政策助手，基于知识库检索结果回答政策问题，"
                            + "回答中必须标注信息来源文件，确保可追溯。",
                    "您好，我是知伴AI政策助手。您可以咨询惠民政策、养老补贴、医保等问题，"
                            + "我会标注政策来源供您核对。",
                    "政策检索、培训台账生成"),
            "tourism", fallback("tourism", "文旅导览助手",
                    "你是知伴AI文旅导览助手，为游客介绍景点信息、规划行程、讲述文化故事，"
                            + "并关注老年人出行需求。",
                    "您好，我是知伴AI文旅助手。可以为您介绍景点信息、规划行程路线，"
                            + "或者讲讲景点背后的文化故事。请问您想去哪里？",
                    "景点导览、路线规划、文化故事")
    );

    private final AgentPersonaMapper personaMapper;

    public AgentServiceImpl(AgentPersonaMapper personaMapper) {
        this.personaMapper = personaMapper;
    }

    @Override
    public List<AgentPersona> listPersonas() {
        try {
            List<AgentPersona> list = personaMapper.selectList(
                    new LambdaQueryWrapper<AgentPersona>()
                            .eq(AgentPersona::getEnabled, 1)
                            .orderByAsc(AgentPersona::getSortOrder));
            if (list != null && !list.isEmpty()) {
                return list;
            }
        } catch (Exception e) {
            log.warn("查询智能体人设失败，使用内置兜底数据: {}", e.getMessage());
        }
        return List.of(FALLBACK.get("elderly"), FALLBACK.get("govpolicy"), FALLBACK.get("tourism"));
    }

    @Override
    public AgentPersona getPersona(String agentType) {
        String type = normalize(agentType);
        try {
            AgentPersona persona = personaMapper.selectOne(
                    new LambdaQueryWrapper<AgentPersona>()
                            .eq(AgentPersona::getAgentType, type)
                            .last("LIMIT 1"));
            if (persona != null) {
                return persona;
            }
        } catch (Exception e) {
            log.warn("查询智能体人设失败，使用内置兜底数据: {}", e.getMessage());
        }
        return FALLBACK.get(type);
    }

    @Override
    public boolean isValidAgent(String agentType) {
        return agentType != null && AGENT_TYPES.contains(agentType.trim().toLowerCase());
    }

    @Override
    public String defaultAgent() {
        return DEFAULT_AGENT;
    }

    private String normalize(String agentType) {
        if (!isValidAgent(agentType)) {
            throw new BusinessException(400,
                    "未知智能体: " + agentType + "，可用值: elderly / govpolicy / tourism");
        }
        return agentType.trim().toLowerCase();
    }

    private static AgentPersona fallback(String type, String name, String personality,
                                         String greeting, String description) {
        AgentPersona p = new AgentPersona();
        p.setAgentType(type);
        p.setName(name);
        p.setPersonality(personality);
        p.setGreeting(greeting);
        p.setDescription(description);
        p.setEnabled(1);
        return p;
    }
}
