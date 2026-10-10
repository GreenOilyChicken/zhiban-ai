package com.zhiban.ai.controller;

import com.zhiban.ai.entity.AgentPersona;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.service.AgentService;
import com.zhiban.ai.vo.Result;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 智能体人设 Controller
 *
 * 附件一 §3.4：
 *   GET  /api/agent/persona           获取当前智能体人设配置
 *   POST /api/agent/switch/{agentType} 切换康养/政务/文旅智能体
 *
 * @author zhiban
 */
@RestController
@RequestMapping("/agent")
public class AgentController {

    private final AgentService agentService;

    public AgentController(AgentService agentService) {
        this.agentService = agentService;
    }

    /**
     * 获取智能体列表（供前端展示三大方向入口）
     */
    @GetMapping("/list")
    public Result<List<AgentPersona>> list() {
        return Result.success(agentService.listPersonas());
    }

    /**
     * 获取当前智能体人设配置
     *
     * @param agentType 可选，默认返回 elderly
     */
    @GetMapping("/persona")
    public Result<AgentPersona> persona(
            @org.springframework.web.bind.annotation.RequestParam(required = false) String agentType) {
        String type = (agentType == null || agentType.isBlank())
                ? agentService.defaultAgent() : agentType;
        return Result.success(agentService.getPersona(type));
    }

    /**
     * 切换智能体（返回目标智能体的人设配置）
     */
    @PostMapping("/switch/{agentType}")
    public Result<AgentPersona> switchAgent(@PathVariable String agentType) {
        if (!agentService.isValidAgent(agentType)) {
            throw new BusinessException(400,
                    "未知智能体: " + agentType + "，可用值: elderly / govpolicy / tourism");
        }
        return Result.success("切换成功", agentService.getPersona(agentType));
    }
}
