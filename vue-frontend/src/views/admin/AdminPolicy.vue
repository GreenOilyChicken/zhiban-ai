<template>
  <div class="admin-policy">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>政策管理</span>
          <el-button type="primary" @click="openDialog()">
            <el-icon class="el-icon--left"><Plus /></el-icon>
            新建政策
          </el-button>
        </div>
      </template>

      <el-table :data="policies" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="政策标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="documentNumber" label="文号" width="140" />
        <el-table-column prop="issuingAuthority" label="发文机关" width="120" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="publishDate" label="发布日期" width="120" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadPolicies"
        />
      </div>
    </el-card>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑政策' : '新建政策'" width="70%">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="政策标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入政策标题" />
        </el-form-item>
        <el-form-item label="文号" prop="documentNumber">
          <el-input v-model="form.documentNumber" placeholder="例如：国发〔2026〕1号" />
        </el-form-item>
        <el-form-item label="发文机关" prop="issuingAuthority">
          <el-input v-model="form.issuingAuthority" placeholder="请输入发文机关" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="选择分类" style="width: 100%">
            <el-option label="政务服务" value="政务服务" />
            <el-option label="银发经济" value="银发经济" />
            <el-option label="文旅项目" value="文旅项目" />
          </el-select>
        </el-form-item>
        <el-form-item label="发布日期" prop="publishDate">
          <el-date-picker
            v-model="form.publishDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择发布日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="生效日期" prop="effectiveDate">
          <el-date-picker
            v-model="form.effectiveDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择生效日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="有效期至" prop="expiryDate">
          <el-date-picker
            v-model="form.expiryDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="留空表示长期有效"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="政策内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="8"
            placeholder="请输入政策正文内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getGovPolicies,
  createGovPolicy,
  updateGovPolicy,
  deleteGovPolicy
} from '@/api/help'

const policies = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const dialogVisible = ref(false)
const editingId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({
  title: '',
  documentNumber: '',
  issuingAuthority: '',
  category: '',
  publishDate: '',
  effectiveDate: '',
  expiryDate: '',
  content: ''
})

const rules = {
  title: [{ required: true, message: '请输入政策标题', trigger: 'blur' }],
  documentNumber: [{ required: true, message: '请输入文号', trigger: 'blur' }],
  issuingAuthority: [{ required: true, message: '请输入发文机关', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入政策内容', trigger: 'blur' }]
}

// 首次加载
loadPolicies()

async function loadPolicies() {
  loading.value = true
  try {
    const res = await getGovPolicies({ page: currentPage.value - 1, size: pageSize.value })
    policies.value = res.data?.content || res.data?.records || []
    total.value = res.data?.totalElements || res.data?.total || 0
  } catch {
    // 错误已由拦截器处理
  } finally {
    loading.value = false
  }
}

function openDialog(row) {
  if (row) {
    editingId.value = row.id
    Object.assign(form, {
      title: row.title || '',
      documentNumber: row.documentNumber || '',
      issuingAuthority: row.issuingAuthority || '',
      category: row.category || '',
      publishDate: row.publishDate || '',
      effectiveDate: row.effectiveDate || '',
      expiryDate: row.expiryDate || '',
      content: row.content || ''
    })
  } else {
    editingId.value = null
    Object.assign(form, {
      title: '',
      documentNumber: '',
      issuingAuthority: '',
      category: '',
      publishDate: '',
      effectiveDate: '',
      expiryDate: '',
      content: ''
    })
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const data = { ...form }
      if (editingId.value) {
        await updateGovPolicy(editingId.value, data)
        ElMessage.success('更新成功')
      } else {
        await createGovPolicy(data)
        ElMessage.success('创建成功')
      }
      dialogVisible.value = false
      await loadPolicies()
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除政策"${row.title}"吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await deleteGovPolicy(row.id)
    ElMessage.success('删除成功')
    await loadPolicies()
  } catch (e) {
    if (e !== 'cancel') {
      // 错误已由拦截器处理
    }
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
