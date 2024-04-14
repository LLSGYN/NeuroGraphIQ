<template>
  <a-form
    @submit.prevent="handleSubmit"
    layout="basic"
    ref="registerForm"
    :model="registerForm"
    :rules="rules"
    :label-col="{ span: 8 }"
    :wrapper-col="{ span: 16 }"
  >
    <a-form-item
      label="Username"
      name="username"
      :rules="rules.username"
      :wrapper-col="{ span: 8 }"  
    >
      <a-input v-model:value="registerForm.username" placeholder="Username" />
    </a-form-item>
    <a-form-item
      label="Password"
      name="password"
      :rules="rules.password"
      :wrapper-col="{ span: 8 }"  
    >
      <a-input-password v-model:value="registerForm.password" placeholder="Password" />
    </a-form-item>
    <a-form-item
      label="Confirm Password"
      name="confirmPassword"
      :rules="rules.confirmPassword"
      :wrapper-col="{ span: 8 }"  
    >
      <a-input-password v-model:value="registerForm.confirmPassword" placeholder="Confirm Password" />
    </a-form-item>
    <a-form-item :wrapper-col="{ offset: 8, span: 8 }">
      <a-button type="primary" htmlType="submit">
        Submit
      </a-button>
    </a-form-item>
  </a-form>
</template>

<script lang="ts">
import { ref, defineComponent } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';

export default defineComponent({
  setup() {
    const router = useRouter();
    const store = useStore();
    const registerForm = ref({
      username: '',
      password: '',
      confirmPassword: '',
    });

    const confirmPasswordValidator = (_, value) => {
      if (value !== registerForm.value.password) {
        return Promise.reject(new Error('The two passwords do not match!'));
      }
      return Promise.resolve();
    };

    const rules = {
      username: [
        { required: true, message: 'Please input your username!', trigger: 'blur' },
      ],
      password: [
        { required: true, message: 'Please input your password!', trigger: 'blur' },
      ],
      confirmPassword: [
        { required: true, message: 'Please confirm your password!', trigger: 'blur' },
        { validator: confirmPasswordValidator, trigger: 'blur' },
      ],
    };

    const handleSubmit = async () => {
      const isSuccess = await store.dispatch('register', registerForm.value);
      if (isSuccess) {
        router.push('/home');
      } else {
        // Handle registration failure
      }
    };

    return {
      registerForm,
      rules,
      handleSubmit,
      confirmPasswordValidator,
    };
  },
});
</script>