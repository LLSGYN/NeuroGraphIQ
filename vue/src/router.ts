import { createRouter, createWebHistory } from 'vue-router';
import Home from './components/Home.vue';
import Login from './components/Login.vue';
import Register from './components/Register.vue'; // 导入Register组件
import store from './store';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', component: Login, meta: { requiresAuth: false } },
    { path: '/home', component: Home, meta: { requiresAuth: true } },
    { path: '/register', component: Register, meta: { requiresAuth: false } }, // 添加注册路由
    // other routes...
  ],
});

router.beforeEach((to, from, next) => {
  const isLoggedIn = store.state.isLoggedIn;
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isLoggedIn) {
      next('/login');
    } else {
      next();
    }
  } else {
    if (isLoggedIn && to.path === '/login') {
      next('/home');
    } else {
      next();
    }
  }
});

export default router;
