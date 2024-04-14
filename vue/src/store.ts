// import { createStore } from 'vuex';
// import axios from 'axios';

// const apiClient = axios.create({
//   baseURL: 'http://localhost:5000', 
//   headers: {
//     'Content-Type': 'application/json'
//   }
// });

// const store = createStore({
//   state: {
//     isLoggedIn: false
//   },
//   mutations: {
//     setLoggedIn(state, payload) {
//       state.isLoggedIn = payload;
//     }
//   },
//   actions: {
//     async login({ commit }, credentials) {
//       try {
//         const response = await apiClient.post('/login', credentials);
//         if (response.data.success) {
//           commit('setLoggedIn', true);
//           return true;
//         }
//         return false;
//       } catch (error) {
//         console.error(error);
//         return false;
//       }
//     },
//     logout({ commit }) {
//       commit('setLoggedIn', false);
//     },
//     async register({ commit }, userInfo) {
//       try {
//         const response = await apiClient.post('/register', userInfo);
//         if (response.data.success) {
//           commit('setLoggedIn', true);
//           return true;
//         }
//         return false;
//       } catch (error) {
//         console.error(error);
//         return false;
//       }
//     }
//   }
// });

// export default store;

import { createStore } from 'vuex';
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:5000', 
  headers: {
    'Content-Type': 'application/json'
  }
});

const store = createStore({
  state: {
    isLoggedIn: false,
    token: null,  // 添加token字段
  },
  mutations: {
    setLoggedIn(state, payload) {
      state.isLoggedIn = payload;
    },
    setToken(state, token) {
      state.token = token;
    }
  },
  actions: {
    async login({ commit }, credentials) {
      try {
        const response = await apiClient.post('/login', credentials);
        if (response.data.success) {
          commit('setLoggedIn', true);
          commit('setToken', response.data.access_token);  // 保存token
          return true;
        }
        return false;
      } catch (error) {
        console.error(error);
        return false;
      }
    },
    logout({ commit }) {
      commit('setLoggedIn', false);
      commit('setToken', null);  // 清空token
    },
    async register({ commit }, userInfo) {
      try {
        const response = await apiClient.post('/register', userInfo);
        if (response.data.success) {
          commit('setLoggedIn', true);
          return true;
        }
        return false;
      } catch (error) {
        console.error(error);
        return false;
      }
    }
  }
});

export default store;
