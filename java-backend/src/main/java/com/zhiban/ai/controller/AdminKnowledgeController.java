package com.zhiban.ai.controller;

import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.service.AiAgentClient;
import com.zhiban.ai.vo.Result;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Set;

/**
 * 管理端知识库 Controller
 *
 * 附件一 §4.2 政策管理：政策文档「上传」与「知识库同步」。
 * 所有接口均需要 ADMIN 角色。
 *
 * @author zhiban
 */
@RestController
@RequestMapping("/admin/kb")
@PreAuthorize("hasRole('ADMIN')")
public class AdminKnowledgeController {

    /** 可用集合（与 Python 侧 COLLECTION_MAP 对齐） */
    private static final Set<String> COLLECTIONS = Set.of("govpolicy", "elderly", "tourism");

    /** 上传文件大小上限：5MB */
    private static final long MAX_UPLOAD_BYTES = 5L * 1024 * 1024;

    /** 允许的文档扩展名 */
    private static final Set<String> ALLOWED_SUFFIXES = Set.of(".txt", ".md", ".markdown");

    private final AiAgentClient aiAgentClient;

    public AdminKnowledgeController(AiAgentClient aiAgentClient) {
        this.aiAgentClient = aiAgentClient;
    }

    /**
     * 同步（重建）指定集合的知识库索引
     *
     * @param collection 集合名，默认 govpolicy
     * @param rebuild    true=清库全量重建，false=增量更新
     */
    @PostMapping("/sync")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<String> sync(@RequestParam(defaultValue = "govpolicy") String collection,
                               @RequestParam(defaultValue = "true") boolean rebuild) {
        String normalized = normalizeCollection(collection);
        String message = aiAgentClient.rebuildKnowledgeBase(normalized, rebuild);
        return Result.success(message);
    }

    /**
     * 上传知识库文档并同步索引
     *
     * @param file       文档文件（.txt / .md，UTF-8，≤5MB）
     * @param collection 目标集合，默认 govpolicy
     * @param rebuild    上传后是否立即重建索引，默认 true
     */
    @PostMapping("/upload")
    @PreAuthorize("hasRole('ADMIN')")
    public Result<String> upload(@RequestParam("file") MultipartFile file,
                                 @RequestParam(defaultValue = "govpolicy") String collection,
                                 @RequestParam(defaultValue = "true") boolean rebuild) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(400, "上传文件不能为空");
        }
        if (file.getSize() > MAX_UPLOAD_BYTES) {
            throw new BusinessException(400, "文件过大，上限 5MB");
        }

        String filename = file.getOriginalFilename();
        if (filename == null || filename.isBlank()) {
            throw new BusinessException(400, "文件名不能为空");
        }
        // 仅取文件名，剥离任何路径成分（防目录穿越）
        filename = filename.replace("\\", "/");
        int slash = filename.lastIndexOf('/');
        if (slash >= 0) {
            filename = filename.substring(slash + 1);
        }
        String lower = filename.toLowerCase();
        boolean suffixOk = ALLOWED_SUFFIXES.stream().anyMatch(lower::endsWith);
        if (!suffixOk) {
            throw new BusinessException(400, "仅支持 .txt / .md 文档");
        }

        byte[] content;
        try {
            content = file.getBytes();
        } catch (IOException e) {
            throw new BusinessException(400, "读取上传文件失败: " + e.getMessage());
        }

        String normalized = normalizeCollection(collection);
        String message = aiAgentClient.uploadKnowledgeBaseDocument(
                content, filename, normalized, rebuild);
        return Result.success(message);
    }

    /**
     * 校验并归一化集合名
     */
    private String normalizeCollection(String collection) {
        String value = (collection == null || collection.isBlank()) ? "govpolicy" : collection.trim();
        if (!COLLECTIONS.contains(value)) {
            throw new BusinessException(400,
                    "未知集合: " + value + "，可用值: govpolicy / elderly / tourism");
        }
        return value;
    }
}
