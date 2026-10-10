import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/api/index'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue')
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/help',
    name: 'HelpCenter',
    component: () => import('@/views/user/HelpCenter.vue')
  },
  {
    path: '/help/policies',
    name: 'PolicyList',
    component: () => import('@/views/user/PolicyList.vue')
  },
  {
    path: '/help/qa',
    name: 'PolicyQA',
    component: () => import('@/views/user/PolicyQA.vue')
  },
  {
    path: '/help/articles',
    name: 'ArticleList',
    component: () => import('@/views/user/ArticleList.vue')
  },
  {
    path: '/help/article/:id',
    name: 'ArticleDetail',
    component: () => import('@/views/user/ArticleDetail.vue')
  },
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    redirect: '/admin/articles',
    children: [
      {
        path: 'articles',
        name: 'AdminArticle',
        component: () => import('@/views/admin/AdminArticle.vue')
      },
      {
        path: 'policies',
        name: 'AdminPolicy',
        component: () => import('@/views/admin/AdminPolicy.vue')
      },
      {
        path: 'quota',
        name: 'AdminQuota',
        component: () => import('@/views/admin/AdminQuota.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：管理端需要登录
router.beforeEach((to, from, next) => {
  if (to.path.startsWith('/admin')) {
    const token = getToken()
    if (!token) {
      next('/login')
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
