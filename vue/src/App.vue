
<template>
  <div id="app" class="main-container">
    <!-- 头部导航 -->
    <a-layout-header :style="headerStyle">
    <!-- <header> -->
      <!-- <nav>
        <router-link to="/home">Home</router-link>
        <router-link v-if="!isLoggedIn" to="/login">Login</router-link>
        <router-link v-if="!isLoggedIn" to="/register">Register</router-link>
        <a v-if="isLoggedIn" href="#" @click="logout">Logout</a>
      </nav> -->
      NeuroGraphIQ Demo
      <!-- <a-menu v-if="isLoggedIn"
        v-model:selectedKeys="current" 
        mode="horizontal" 
        :items="items" 
        :style="{ lineHeight: '64px' }"
      /> -->
    </a-layout-header>
    
    <!-- </header> -->
    <!-- 主内容区，根据路由显示不同的组件 -->
    <main>
      <!-- <router-view></router-view> -->
      <Home/>
    </main>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, computed } from 'vue';
// import { useStore } from 'vuex';
// import { useRouter } from 'vue-router';
import type { CSSProperties } from 'vue';
import Home from './components/Home.vue'

import { h, ref } from 'vue';
import { FileTextOutlined, RadarChartOutlined, UserOutlined } from '@ant-design/icons-vue';
import type { MenuProps } from 'ant-design-vue';
const current = ref<string[]>(['sparql']);
const items = ref<MenuProps['items']>([
  {
    key: 'sparql',
    icon: () => h(FileTextOutlined),
    label: 'SPARQL Input',
    title: 'SPARQL Input',
  },
  {
    key: 'graph',
    icon: () => h(RadarChartOutlined),
    label: 'Graph Input',
    title: 'Graph Input',
  },
  {
    key: 'sub1',
    icon: () => h(UserOutlined),
    label: 'User',
    title: 'User',
    children: [
      {
        label: 'Option 1',
        key: 'setting:1',
      },
      {
        label: 'Option 2',
        key: 'setting:2',
      }
    ],
  },
  // {
  //   key: 'alipay',
  //   label: h('a', { href: 'https://antdv.com', target: '_blank' }, 'Navigation Four - Link'),
  //   title: 'Navigation Four - Link',
  // },
]);


// const store = useStore();
// const router = useRouter();

// const isLoggedIn = computed(() => store.state.isLoggedIn);

// const logout = () => {
//   store.dispatch('logout');
//   router.push('/login');
// };
const headerStyle: CSSProperties = {
  textAlign: 'left',            // 文字靠左，看起来更加专业
  color: '#fff',
  height: 64,
  padding: '0 50px',            // 水平内边距保持50px，垂直方向使用0
  lineHeight: '64px',
  backgroundColor: '#5d8eb6',   // 深一点的蓝色背景
  boxShadow: '0 2px 8px 0 rgba(0,0,0,0.2)', // 在底部增加轻微阴影
  borderBottom: '1px solid #5d8eb6', // 增加与背景同色的边界线，根据喜好可调整
  fontSize: '20px',             // 增大字体大小以提高可读性
  fontFamily: 'Arial, sans-serif', // 使用常见的字体家族
};
// const headerStyle: CSSProperties = {
//   textAlign: 'center',
//   color: '#fff',
//   height: 64,
//   paddingInline: 50,
//   lineHeight: '64px',
//   backgroundColor: '#7dbcea',
// };
</script>

<style>
html, body {
  height: 100%;
  margin: 0;
}

.main-container {
  min-height: 100vh;
}
</style>