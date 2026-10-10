package com.zhiban.ai.service;

import com.zhiban.ai.entity.AgentPersona;

import java.util.List;

/**
 * 智能体人设服务接口
 * 附件一 §3.4：获取人设、切换智能体（康养/政务/文旅）。
 *
 * @author zhiban
 */
public interface AgentService {

    /**
     * 获取全部启用的智能体人设
     */
    List<AgentPersona> listPersonas();

    /**
     * 获取指定智能体的人设
     *
     * @param agentType elderly / govpolicy / tourism
     */
    AgentPersona getPersona(String agentType);

    /**
     * 校验智能体类型是否合法
     */
    boolean isValidAgent(String agentType);

    /**
     * 默认智能体类型
     */
    String defaultAgent();
}
