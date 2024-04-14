<template>
  <a-select
      ref="select_gmode"
      v-model:value="value1"
      style="width: 120px"
      :dropdown-match-select-width="false"
      @change="handleChange"
    >
    <a-select-option value="default">Default mode</a-select-option>
    <a-select-option value="addNode">Add Node (by clicking canvas)</a-select-option>
    <a-select-option value="addEdge">Add Edge (by clicking two end nodes)</a-select-option>
    <a-select-option value="addData">Add Graph Data (by clicking nodes or edges)</a-select-option>
  </a-select>

  <a-select v-if="showSelect" v-model="selectedValue" :style="{ position: 'absolute', left: `${selectPosition.x}px`, top: `${selectPosition.y}px` }" @change="handleSelectChange">
    <a-select-option v-for="option in options" :key="option" :value="option">{{ option }}</a-select-option>
  </a-select>

  <a-button @click="graphQuery">RUN QUERY</a-button>
  <div id="mountNode" style="border: 1px solid #000; background-color:white;"></div>
</template>

<!-- <script lang="ts" setup>
import { GraphWithSelection } from './GraphWithSelection'

import { onMounted, nextTick } from 'vue';
onMounted(async () => {
  await nextTick();
  const graphWithSelection = new GraphWithSelection('mountNode');
});
</script> -->

<script lang="ts">
import { defineComponent, onMounted, ref } from 'vue';
import { GraphWithSelection } from './GraphWithSelection'; // Adjust the import based on your file structure

const graphWithSelection = ref<GraphWithSelection | null>(null);
const value1 = ref<string>('default');

const showSelect = ref(false);
const selectPosition = ref({ x: 0, y: 0 });
const selectedValue = ref(undefined);
const options = ref(['Option 1', 'Option 2', 'Option 3']);
export default defineComponent({
  setup() {

    onMounted(() => {
      graphWithSelection.value = new GraphWithSelection('mountNode', (type, model, position) => {
        showSelect.value = true;
        selectPosition.value = position;
        // 根据类型设置不同的选项
        options.value = type === 'node' ? ['Node Option 1', 'Node Option 2'] : ['Edge Option 1', 'Edge Option 2'];
        console.log(model)
      });
    });

    const handleChange = (value: string) => {
      if (graphWithSelection.value) {
        graphWithSelection.value.handleChange(value);
      }
    };

    const graphQuery = () => {

    };

    return {
      value1,
      handleChange,
      graphQuery
    };
  },
});
</script>

<style>
  /* 提示框的样式 */
  .g6-tooltip {
    border: 1px solid #e2e2e2;
    border-radius: 4px;
    font-size: 12px;
    color: #545454;
    background-color: rgba(255, 255, 255, 0.9);
    padding: 10px 8px;
    box-shadow: rgb(174, 174, 174) 0px 0px 10px;
  }
</style>