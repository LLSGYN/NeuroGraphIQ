<template>
  <a-form
    :model="formState"
    name="basic"
    :label-col="{ span: 8 }"
    :wrapper-col="{ span: 16 }"
    autocomplete="off"
    @finish="onFinish"
    @finishFailed="onFinishFailed"
  >
    <a-form-item
      label="Username"
      name="username"
      :rules="[{ required: true, message: 'Please input your username!' }]"
      :wrapper-col="{ span: 8 }"  
    >
      <a-input v-model:value="formState.username" />
    </a-form-item>

    <a-form-item
      label="Password"
      name="password"
      :rules="[{ required: true, message: 'Please input your password!' }]"
      :wrapper-col="{ span: 8 }"  
    >
      <a-input-password v-model:value="formState.password" />
    </a-form-item>

    <a-form-item :wrapper-col="{ offset: 8, span: 8 }"> 
      <a-button type="primary" html-type="submit" style="margin-right: 5px;">Login</a-button>
      <router-link to="/register">
        <a-button type="default">
          Register
        </a-button>
      </router-link>
    </a-form-item>
  </a-form>
</template>

<script lang="ts">
import { reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';

interface FormState {
  username: string;
  password: string;
  remember: boolean;
}

export default {
  setup() {
    const router = useRouter();
    const store = useStore();
    
    const formState = reactive<FormState>({
      username: '',
      password: '',
      remember: false,
    });

    const onFinish = async () => {
      console.log('Success:', formState);
      const isSuccess = await store.dispatch('login', {
        username: formState.username,
        password: formState.password
      });

      if (isSuccess) {
        router.push('/home');
      } else {
        alert('Incorrect username or password!');
      }
    };

    const onFinishFailed = (errorInfo: any) => {
      console.log('Failed:', errorInfo);
    };

    return {
      formState,
      onFinish,
      onFinishFailed
    };
  }
};
</script>
