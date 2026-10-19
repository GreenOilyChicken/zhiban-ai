package com.zhiban.ai.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.zhiban.ai.dto.GovPolicyRequest;
import com.zhiban.ai.dto.GovPolicyQuery;
import com.zhiban.ai.dto.HelpArticleRequest;
import com.zhiban.ai.dto.PolicyAnswerVO;
import com.zhiban.ai.dto.PolicyQuestionRequest;
import com.zhiban.ai.entity.Category;
import com.zhiban.ai.entity.GovPolicyDocument;
import com.zhiban.ai.entity.HelpContent;
import com.zhiban.ai.entity.UserQuota;
import com.zhiban.ai.exception.BusinessException;
import com.zhiban.ai.mapper.CategoryMapper;
import com.zhiban.ai.mapper.GovPolicyDocumentMapper;
import com.zhiban.ai.mapper.HelpContentMapper;
import com.zhiban.ai.mapper.UserQuotaMapper;
import com.zhiban.ai.security.SecurityUtils;
import com.zhiban.ai.service.HelpCenterService;
import com.zhiban.ai.vo.CategoryVO;
import com.zhiban.ai.vo.GovPolicyVO;
import com.zhiban.ai.vo.HelpArticleVO;
import com.zhiban.ai.vo.QuotaVO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 帮助中心服务实现
 *
 * 关键设计：
 * 1. 政策问答：先原子扣减配额（deductQuota），再执行RAG检索生成回答
 * 2. 配额扣减：使用原子SQL UPDATE（WHERE used_amount < total_amount），避免并发超扣
 * 3. 所有异常使用 BusinessException，由全局异常处理器统一处理
 * 4. 所有接口返回类型化的 VO，不返回 Map<String, Object>
 *
 * @author zhiban
 */
@Service
public class HelpCenterServiceImpl implements HelpCenterService {

    private static final Logger log = LoggerFactory.getLogger(HelpCenterServiceImpl.class);

    /** 政策问答配额类型常量 */
    private static final String QUOTA_TYPE_POLICY_QA = "POLICY_QA";
    /** 新用户默认总配额 */
    private static final int DEFAULT_TOTAL_QUOTA = 100;
    /** 新用户默认免费配额 */
    private static final int DEFAULT_FREE_QUOTA = 10;

    private final HelpContentMapper helpContentMapper;
    private final GovPolicyDocumentMapper govPolicyMapper;
    private final UserQuotaMapper userQuotaMapper;
    private final CategoryMapper categoryMapper;
    private final RagService ragService;
    private final SecurityUtils securityUtils;
    private final ObjectMapper objectMapper;

    public HelpCenterServiceImpl(HelpContentMapper helpContentMapper,
                                 GovPolicyDocumentMapper govPolicyMapper,
                                 UserQuotaMapper userQuotaMapper,
                                 CategoryMapper categoryMapper,
                                 RagService ragService,
                                 SecurityUtils securityUtils,
                                 ObjectMapper objectMapper) {
        this.helpContentMapper = helpContentMapper;
        this.govPolicyMapper = govPolicyMapper;
        this.userQuotaMapper = userQuotaMapper;
        this.categoryMapper = categoryMapper;
        this.ragService = ragService;
        this.securityUtils = securityUtils;
        this.objectMapper = objectMapper;
    }

    // ==================== 帮助文章 ====================

    @Override
    public IPage<HelpArticleVO> getPublishedArticles(int page, int size, String category, String keyword) {
        Page<HelpContent> pageParam = new Page<>(page, size);
        IPage<HelpContent> contentPage = helpContentMapper.selectPublishedPage(pageParam, category, keyword);

        // 转换为VO
        Page<HelpArticleVO> voPage = new Page<>(page, size, contentPage.getTotal());
        List<HelpArticleVO> voList = contentPage.getRecords().stream()
                .map(this::convertToHelpArticleVO)
                .collect(Collectors.toList());
        voPage.setRecords(voList);
        return voPage;
    }

    @Override
    public HelpArticleVO getArticleById(Long id) {
        if (id == null || id <= 0) {
            throw new BusinessException(400, "文章ID无效");
        }
        HelpContent content = helpContentMapper.selectById(id);
        if (content == null || content.getDeleted() == 1) {
            throw new BusinessException(404, "文章不存在");
        }
        // 非管理员只能查看已发布的文章
        // 注意：此处不做角色判断，由Controller的公开/保护路由决定可见性
        return convertToHelpArticleVO(content);
    }

    /**
     * 获取相关推荐文章（附件一 §4.1 文章详情「相关推荐」）
     *
     * 策略：优先取同分类的其他已发布文章；不足 limit 时，
     * 用最新的其他已发布文章补齐，并去重。
     */
    @Override
    public List<HelpArticleVO> getRelatedArticles(Long id, int limit) {
        if (id == null || id <= 0) {
            throw new BusinessException(400, "文章ID无效");
        }
        HelpContent current = helpContentMapper.selectById(id);
        if (current == null || current.getDeleted() == 1) {
            throw new BusinessException(404, "文章不存在");
        }
        int size = limit <= 0 ? 5 : limit;

        List<HelpContent> related = new ArrayList<>();
        Set<Long> seen = new HashSet<>();
        seen.add(id);

        // 1. 同分类优先
        String category = current.getCategory();
        if (StringUtils.hasText(category)) {
            LambdaQueryWrapper<HelpContent> sameCategory = new LambdaQueryWrapper<>();
            sameCategory.eq(HelpContent::getDeleted, 0)
                        .eq(HelpContent::getIsPublished, 1)
                        .eq(HelpContent::getCategory, category)
                        .ne(HelpContent::getId, id)
                        .orderByDesc(HelpContent::getCreateTime)
                        .last("LIMIT " + size);
            for (HelpContent c : helpContentMapper.selectList(sameCategory)) {
                if (seen.add(c.getId())) {
                    related.add(c);
                }
            }
        }

        // 2. 不足则用最新文章补齐
        if (related.size() < size) {
            LambdaQueryWrapper<HelpContent> latest = new LambdaQueryWrapper<>();
            latest.eq(HelpContent::getDeleted, 0)
                  .eq(HelpContent::getIsPublished, 1)
                  .ne(HelpContent::getId, id)
                  .orderByDesc(HelpContent::getCreateTime)
                  .last("LIMIT " + (size * 2));
            for (HelpContent c : helpContentMapper.selectList(latest)) {
                if (related.size() >= size) {
                    break;
                }
                if (seen.add(c.getId())) {
                    related.add(c);
                }
            }
        }

        return related.stream()
                .limit(size)
                .map(this::convertToHelpArticleVO)
                .collect(Collectors.toList());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createArticle(HelpArticleRequest request) {
        HelpContent content = new HelpContent();
        content.setTitle(request.getTitle());
        content.setContent(request.getContent());
        content.setCategory(request.getCategory());
        content.setCoverImage(request.getCoverImage());
        content.setVideoUrl(request.getVideoUrl());
        content.setTags(request.getTags());
        content.setIsPublished(request.getIsPublished() != null ? request.getIsPublished() : 0);

        helpContentMapper.insert(content);
        log.info("创建帮助文章成功, id={}, title={}", content.getId(), content.getTitle());
        return content.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateArticle(Long id, HelpArticleRequest request) {
        HelpContent existing = helpContentMapper.selectById(id);
        if (existing == null || existing.getDeleted() == 1) {
            throw new BusinessException(404, "文章不存在");
        }

        existing.setTitle(request.getTitle());
        existing.setContent(request.getContent());
        existing.setCategory(request.getCategory());
        existing.setCoverImage(request.getCoverImage());
        existing.setVideoUrl(request.getVideoUrl());
        existing.setTags(request.getTags());
        if (request.getIsPublished() != null) {
            existing.setIsPublished(request.getIsPublished());
        }

        helpContentMapper.updateById(existing);
        log.info("更新帮助文章成功, id={}", id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteArticle(Long id) {
        HelpContent existing = helpContentMapper.selectById(id);
        if (existing == null || existing.getDeleted() == 1) {
            throw new BusinessException(404, "文章不存在");
        }
        helpContentMapper.deleteById(id); // 逻辑删除
        log.info("删除帮助文章成功, id={}", id);
    }

    // ==================== 政策文档 ====================

    @Override
    public IPage<GovPolicyVO> getGovPolicies(GovPolicyQuery query) {
        Page<GovPolicyDocument> pageParam = new Page<>(query.getPage(), query.getSize());
        IPage<GovPolicyDocument> docPage = govPolicyMapper.selectPolicyPage(
                pageParam,
                query.getPolicyType(),
                query.getKeyword(),
                query.getStatus(),
                query.getRegion()
        );

        Page<GovPolicyVO> voPage = new Page<>(query.getPage(), query.getSize(), docPage.getTotal());
        List<GovPolicyVO> voList = docPage.getRecords().stream()
                .map(this::convertToGovPolicyVO)
                .collect(Collectors.toList());
        voPage.setRecords(voList);
        return voPage;
    }

    @Override
    public GovPolicyVO getGovPolicyById(Long id) {
        if (id == null || id <= 0) {
            throw new BusinessException(400, "政策文档ID无效");
        }
        GovPolicyDocument doc = govPolicyMapper.selectById(id);
        if (doc == null || doc.getDeleted() == 1) {
            throw new BusinessException(404, "政策文档不存在");
        }
        return convertToGovPolicyVO(doc);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Long createGovPolicy(GovPolicyRequest request) {
        GovPolicyDocument doc = new GovPolicyDocument();
        doc.setDocNumber(request.getDocNumber());
        doc.setTitle(request.getTitle());
        doc.setIssuingAuthority(request.getIssuingAuthority());
        doc.setPolicyType(request.getPolicyType());
        doc.setEffectiveDate(request.getEffectiveDate());
        doc.setPublishDate(request.getPublishDate());
        doc.setRegion(request.getRegion());
        doc.setStatus(request.getStatus() != null ? request.getStatus() : 1);
        doc.setSummary(request.getSummary());
        doc.setFullText(request.getFullText());
        doc.setKeyPoints(request.getKeyPoints());
        doc.setFaq(request.getFaq());
        doc.setVectorId(request.getVectorId());

        govPolicyMapper.insert(doc);
        log.info("创建政策文档成功, id={}, title={}", doc.getId(), doc.getTitle());
        return doc.getId();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void updateGovPolicy(Long id, GovPolicyRequest request) {
        GovPolicyDocument existing = govPolicyMapper.selectById(id);
        if (existing == null || existing.getDeleted() == 1) {
            throw new BusinessException(404, "政策文档不存在");
        }

        existing.setDocNumber(request.getDocNumber());
        existing.setTitle(request.getTitle());
        existing.setIssuingAuthority(request.getIssuingAuthority());
        existing.setPolicyType(request.getPolicyType());
        existing.setEffectiveDate(request.getEffectiveDate());
        existing.setPublishDate(request.getPublishDate());
        existing.setRegion(request.getRegion());
        if (request.getStatus() != null) {
            existing.setStatus(request.getStatus());
        }
        existing.setSummary(request.getSummary());
        existing.setFullText(request.getFullText());
        existing.setKeyPoints(request.getKeyPoints());
        existing.setFaq(request.getFaq());
        if (request.getVectorId() != null) {
            existing.setVectorId(request.getVectorId());
        }

        govPolicyMapper.updateById(existing);
        log.info("更新政策文档成功, id={}", id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteGovPolicy(Long id) {
        GovPolicyDocument existing = govPolicyMapper.selectById(id);
        if (existing == null || existing.getDeleted() == 1) {
            throw new BusinessException(404, "政策文档不存在");
        }
        govPolicyMapper.deleteById(id); // 逻辑删除
        log.info("删除政策文档成功, id={}", id);
    }

    // ==================== 政策问答 ====================

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PolicyAnswerVO askPolicyQuestion(PolicyQuestionRequest request) {
        // 1. 获取当前用户ID
        Long userId = securityUtils.getCurrentUserId();
        log.info("政策问答请求: userId={}, question={}", userId, request.getQuestion());

        // 2. 关键步骤：先原子扣减配额，再执行问答
        // 这样确保不会在配额不足时仍执行昂贵的RAG检索
        boolean deducted = deductQuota(userId, QUOTA_TYPE_POLICY_QA);
        if (!deducted) {
            throw new BusinessException(429, "您的政策问答配额已用完，请明日再来或联系管理员");
        }

        // 3. 调用RAG服务检索并生成回答
        PolicyAnswerVO result = ragService.searchAndAnswer(
                request.getQuestion(),
                request.getPolicyType()
        );

        log.info("政策问答完成: userId={}, sources={}", userId,
                result.getSources() != null ? result.getSources().size() : 0);
        return result;
    }

    // ==================== FAQ ====================

    @Override
    public List<GovPolicyVO> getFaqList(String policyType) {
        List<GovPolicyDocument> docs = govPolicyMapper.selectFaqList(policyType);
        return docs.stream()
                .map(this::convertToGovPolicyVO)
                .collect(Collectors.toList());
    }

    // ==================== 配额管理 ====================

    @Override
    public QuotaVO getUserQuota(String quotaType) {
        Long userId = securityUtils.getCurrentUserId();
        return getQuotaByUserAndType(userId, quotaType);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean deductQuota(Long userId, String quotaType) {
        if (userId == null || quotaType == null) {
            throw new BusinessException(400, "用户ID和配额类型不能为空");
        }

        // 确保配额记录存在（如果首次使用，自动初始化）
        userQuotaMapper.initQuotaIfAbsent(userId, quotaType, DEFAULT_TOTAL_QUOTA, DEFAULT_FREE_QUOTA);

        // 原子扣减：SQL UPDATE WHERE used_amount < total_amount
        // 返回1=成功，0=配额不足
        int affected = userQuotaMapper.atomicDeductQuota(userId, quotaType);

        if (affected == 0) {
            log.warn("配额扣减失败（配额不足）: userId={}, quotaType={}", userId, quotaType);
            return false;
        }

        log.info("配额扣减成功: userId={}, quotaType={}", userId, quotaType);
        return true;
    }

    /**
     * 查询配额列表（管理端，附件一 §4.2 配额管理）
     */
    @Override
    public List<QuotaVO> listQuotas(Long userId, String quotaType) {
        LambdaQueryWrapper<UserQuota> wrapper = new LambdaQueryWrapper<>();
        if (userId != null) {
            wrapper.eq(UserQuota::getUserId, userId);
        }
        if (StringUtils.hasText(quotaType)) {
            wrapper.eq(UserQuota::getQuotaType, quotaType);
        }
        wrapper.orderByAsc(UserQuota::getUserId).orderByAsc(UserQuota::getQuotaType);
        return userQuotaMapper.selectList(wrapper).stream()
                .map(this::convertToQuotaVO)
                .collect(Collectors.toList());
    }

    /**
     * 调整用户配额（管理端，附件一 §4.2 配额管理「查看与调整」）
     *
     * 规则：
     *  - 记录不存在时按给定值初始化（默认总量 100 / 免费 10）
     *  - totalAmount / usedAmount / freeAmount 为 null 表示保持原值
     *  - 校验非负，且 usedAmount 不得超过 totalAmount
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public QuotaVO adjustQuota(Long userId, String quotaType,
                               Integer totalAmount, Integer usedAmount, Integer freeAmount) {
        if (userId == null || userId <= 0) {
            throw new BusinessException(400, "用户ID无效");
        }
        if (!StringUtils.hasText(quotaType)) {
            throw new BusinessException(400, "配额类型不能为空");
        }
        if (totalAmount != null && totalAmount < 0) {
            throw new BusinessException(400, "总配额不能为负数");
        }
        if (usedAmount != null && usedAmount < 0) {
            throw new BusinessException(400, "已用配额不能为负数");
        }
        if (freeAmount != null && freeAmount < 0) {
            throw new BusinessException(400, "免费配额不能为负数");
        }

        // 确保记录存在
        userQuotaMapper.initQuotaIfAbsent(userId, quotaType, DEFAULT_TOTAL_QUOTA, DEFAULT_FREE_QUOTA);

        LambdaQueryWrapper<UserQuota> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserQuota::getUserId, userId)
               .eq(UserQuota::getQuotaType, quotaType);
        UserQuota quota = userQuotaMapper.selectOne(wrapper);
        if (quota == null) {
            throw new BusinessException(500, "配额记录初始化失败");
        }

        int newTotal = totalAmount != null ? totalAmount : quota.getTotalAmount();
        int newUsed = usedAmount != null ? usedAmount : quota.getUsedAmount();
        if (newUsed > newTotal) {
            throw new BusinessException(400,
                    String.format("已用配额(%d)不能超过总配额(%d)", newUsed, newTotal));
        }

        quota.setTotalAmount(newTotal);
        quota.setUsedAmount(newUsed);
        if (freeAmount != null) {
            quota.setFreeAmount(freeAmount);
        }
        userQuotaMapper.updateById(quota);

        log.info("管理员调整配额: userId={}, quotaType={}, total={}, used={}, free={}",
                userId, quotaType, quota.getTotalAmount(), quota.getUsedAmount(), quota.getFreeAmount());
        return convertToQuotaVO(quota);
    }

    // ==================== 分类 ====================

    @Override
    public List<CategoryVO> getCategories(String type) {
        if (!StringUtils.hasText(type)) {
            // 返回所有分类
            LambdaQueryWrapper<Category> wrapper = new LambdaQueryWrapper<>();
            wrapper.orderByAsc(Category::getSortOrder);
            List<Category> categories = categoryMapper.selectList(wrapper);
            return categories.stream()
                    .map(this::convertToCategoryVO)
                    .collect(Collectors.toList());
        }
        List<Category> categories = categoryMapper.selectByType(type);
        return categories.stream()
                .map(this::convertToCategoryVO)
                .collect(Collectors.toList());
    }

    // ==================== 转换方法 ====================

    /**
     * HelpContent -> HelpArticleVO
     */
    private HelpArticleVO convertToHelpArticleVO(HelpContent content) {
        HelpArticleVO vo = new HelpArticleVO();
        vo.setId(content.getId());
        vo.setTitle(content.getTitle());
        vo.setContent(content.getContent());
        vo.setCategory(content.getCategory());
        vo.setCoverImage(content.getCoverImage());
        vo.setVideoUrl(content.getVideoUrl());
        vo.setTags(parseStringToList(content.getTags()));
        vo.setIsPublished(content.getIsPublished());
        vo.setCreateTime(content.getCreateTime());
        vo.setUpdateTime(content.getUpdateTime());
        return vo;
    }

    /**
     * GovPolicyDocument -> GovPolicyVO
     */
    private GovPolicyVO convertToGovPolicyVO(GovPolicyDocument doc) {
        GovPolicyVO vo = new GovPolicyVO();
        vo.setId(doc.getId());
        vo.setDocNumber(doc.getDocNumber());
        vo.setTitle(doc.getTitle());
        vo.setIssuingAuthority(doc.getIssuingAuthority());
        vo.setPolicyType(doc.getPolicyType());
        vo.setEffectiveDate(doc.getEffectiveDate());
        vo.setPublishDate(doc.getPublishDate());
        vo.setRegion(doc.getRegion());
        vo.setStatus(doc.getStatus());
        vo.setSummary(doc.getSummary());
        vo.setFullText(doc.getFullText());
        vo.setKeyPoints(parseJsonToStringList(doc.getKeyPoints()));
        vo.setFaq(parseJsonToFaqList(doc.getFaq()));
        vo.setCreateTime(doc.getCreateTime());
        vo.setUpdateTime(doc.getUpdateTime());
        return vo;
    }

    /**
     * Category -> CategoryVO
     */
    private CategoryVO convertToCategoryVO(Category category) {
        CategoryVO vo = new CategoryVO();
        vo.setId(category.getId());
        vo.setName(category.getName());
        vo.setType(category.getType());
        vo.setSortOrder(category.getSortOrder());
        return vo;
    }

    /**
     * 获取用户配额VO
     */
    private QuotaVO getQuotaByUserAndType(Long userId, String quotaType) {
        LambdaQueryWrapper<UserQuota> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(UserQuota::getUserId, userId)
               .eq(UserQuota::getQuotaType, quotaType);
        UserQuota quota = userQuotaMapper.selectOne(wrapper);

        if (quota == null) {
            // 自动初始化配额
            userQuotaMapper.initQuotaIfAbsent(userId, quotaType, DEFAULT_TOTAL_QUOTA, DEFAULT_FREE_QUOTA);
            quota = userQuotaMapper.selectOne(wrapper);
        }

        return convertToQuotaVO(quota);
    }

    /**
     * UserQuota -> QuotaVO
     */
    private QuotaVO convertToQuotaVO(UserQuota quota) {
        QuotaVO vo = new QuotaVO();
        if (quota == null) {
            return vo;
        }
        vo.setId(quota.getId());
        vo.setUserId(quota.getUserId());
        vo.setQuotaType(quota.getQuotaType());
        vo.setTotalAmount(quota.getTotalAmount());
        vo.setUsedAmount(quota.getUsedAmount());
        vo.setRemainingAmount(quota.getTotalAmount() - quota.getUsedAmount());
        vo.setFreeAmount(quota.getFreeAmount());
        return vo;
    }

    // ==================== JSON解析工具 ====================

    /**
     * 将逗号分隔的字符串解析为列表
     */
    private List<String> parseStringToList(String str) {
        if (str == null || str.isBlank()) {
            return Collections.emptyList();
        }
        return List.of(str.split(","));
    }

    /**
     * 将JSON字符串解析为字符串列表
     */
    private List<String> parseJsonToStringList(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            log.warn("解析JSON字符串列表失败: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * 将JSON字符串解析为FAQ列表
     */
    private List<GovPolicyVO.FaqItem> parseJsonToFaqList(String json) {
        if (json == null || json.isBlank()) {
            return Collections.emptyList();
        }
        try {
            return objectMapper.readValue(json, new TypeReference<List<GovPolicyVO.FaqItem>>() {});
        } catch (Exception e) {
            log.warn("解析FAQ列表失败: {}", e.getMessage());
            return Collections.emptyList();
        }
    }
}
