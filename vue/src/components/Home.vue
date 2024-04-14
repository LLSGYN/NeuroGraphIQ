<template>
  <a-space direction="vertical" :style="{ width: '100%' }" :size="[0, 48]">
    <a-layout>
      <!-- <a-layout-header :style="headerStyle">Header</a-layout-header> -->
      <a-menu
        v-model:selectedKeys="current" 
        mode="horizontal" 
        :items="items" 
        :style="{ lineHeight: '64px' }"
      />
      <a-layout>
        <!-- <a-layout-sider :style="siderStyle">Sider</a-layout-sider> -->
        <a-layout-content :style="contentStyle">
            <a-flex>
                <div style="width: 50%;">
                  <div>
                    <a-spin v-if="isLoading"></a-spin>
                    
                    <label for="graph-select">Graph: </label>
                    <a-select
                      id="graph-select"
                      v-model:value="graph"
                      style="width: 120px; margin-right: 8px;"
                      :options="graphData.map(gra => ({ value: gra }))"
                    ></a-select>

                    <label for="model-select">Model: </label>
                    <a-select
                      id="model-select"
                      v-model:value="model"
                      style="width: 120px"
                      :options="models.map(qp => ({ 
                        value: (() => {
                          if (qp == null) {
                            return null;
                          } else if (qp === 'Query2Box') {
                            return 'box';
                          } else {
                            return 'betae';
                          }
                        })(), 
                        label: qp 
                      }))"
                    ></a-select>
                    <div v-if="current[0]==='graph'" style="display: inline; margin-left: 5px;">
                      <label for="limit-number"> LIMIT: </label>
                      <a-input id="limit-number" v-model:value="n_limit" placeholder="limit count" style="width: 75px" />
                    </div>
                  </div>
                  <div v-if="current[0] === 'sparql'">
                    <div>
                      <a-textarea v-model:value="query_str" placeholder="Query your graph here" :rows="6" style="font-family: 'Consolas', monospace;" />
                    </div>
                  </div>
                  <!-- <div v-else> -->
                  <div v-if="current[0] === 'graph'">
                    <GraphInput @update-value="handleGraphResult"/>
                  </div>
                  <div>
                    <a-button v-if="current[0] === 'sparql'" @click="exec_query" style="margin: 5px;" :disabled="isLoading">RUN QUERY</a-button>
                    <a-button v-if="current[0] === 'sparql'" @click="reset_input" style="margin-right: 5px;">RESET</a-button>
                  </div>
                  <div v-if="current[0] === 'sparql'">
                    <h2>Query Plan</h2>
                    <PlotQueryPlan :graphData="queryGraphData" />
                  </div>
                </div>
                <div style="width: 50%;">
                  <h2>
                    Results
                  </h2>
                  <div v-if="current[0] === 'sparql'">
                    <a-table 
                      :columns="columns" 
                      :data-source="entity_list" 
                      bordered
                    >
                      <template #bodyCell="{ column, record }">
                        <template v-if="column.key === 'tags'">
                          <span>
                            <a-tag
                              v-for="tag in record.tags"
                              :key="tag"
                              :color="tag ? 'green' : null"
                            >
                              {{ tag.toUpperCase() }}
                            </a-tag>
                          </span>
                        </template>
                      </template>
                      <!-- <template #title>Results</template> -->
                    </a-table>
                  </div>
                  <div v-else>
                    <a-table 
                      :columns="columns_graph" 
                      :data-source="entity_list_graph" 
                      bordered
                    >
                    </a-table>
                  </div>
                </div>
            </a-flex>
        </a-layout-content>
      </a-layout>
      <!-- <a-layout-footer :style="footerStyle"></a-layout-footer> -->
    </a-layout>
  </a-space>
</template>

<script lang="ts" setup>
import type { CSSProperties } from 'vue';
import { h, ref, watch, computed } from 'vue';
import axios from "axios"
import GraphInput from './GraphInput.vue';
import PlotQueryPlan from './PlotQueryPlan.vue'
import { FileTextOutlined, RadarChartOutlined, UserOutlined } from '@ant-design/icons-vue';
import type { MenuProps, SelectProps } from 'ant-design-vue';
// import { useStore } from 'vuex';
// import { useRouter } from 'vue-router';

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
  // {
  //   key: 'sub1',
  //   icon: () => h(UserOutlined),
  //   label: 'User',
  //   title: 'User',
  //   children: [
  //     {
  //       label: 'Option 1',
  //       key: 'setting:1',
  //     },
  //     {
  //       label: 'Logout',
  //       key: 'logout',
  //     }
  //   ],
  // },
]);

const graphData = ['FB15k', 'NELL'];
const modelData = {
  FB15k: ['Query2Box', 'BetaE'],
  NELL: ['Query2Box', 'BetaE'],
};
const graph = ref(graphData[0]);
const model = ref(modelData[graph.value][0]);
const models = computed(() => {
  return modelData[graph.value];
});

const n_limit = ref("0");

watch(graph, val => {
  // model.value = modelData[val][0];
  model.value = null;
});

watch(model, val => {
  console.log("Model changed to");
  console.log(val);
  if (val != null)
    // console.log(val);
    handleGraphChange();
  else
    console.log("nullnull");
});

function handleGraphResult(value) {
  console.log("graph value update");
  show_on_table_graph(value);
}

const query_str = ref<string>('');

const columns = [
  {
    title: 'Neural',
    dataIndex: 'ngdb',
  },
  {
    title: 'Tags',
    key: 'tags',
    dataIndex: 'tags',
  },
  {
    title: 'Symbolic',
    dataIndex: 'rdflib',
  },
];

const columns_graph = [
  {
    title: 'Neural',
    dataIndex: 'ngdb',
  }
];

const entity_list = ref([
])

const entity_list_graph = ref([
])

const isLoading = ref(false);
const selectedGraph = ref('FB15k');
const defaultGraphOptions = [
  { value: 'FB15k', label: 'FB15k (Default)'},
  { value : 'FB15k-237', label: 'FB15k-237 (Default)'},
];
const graph_options = ref<SelectProps['options']>(defaultGraphOptions);
const avail_graphs = async () => {
  let options = defaultGraphOptions;
  // const token = store.state.token;
  await axios.get('http://10.101.168.234:5000/get_user_graphs').then(response => {
  // await axios.get('http://localhost:5000/get_user_graphs').then(response => {
    for (let x of response.data) {
      options.push({ value: x, label: `${x} (User)`});
    }
  })
  .catch(error => {
    console.error(error);
  });
  return options;
}

const handleGraphChange = async () => {
  isLoading.value = true;
  // let params = {
  //   graph: selectedgraph.value
  // }
  // const token = store.state.token;
  // console.log(token);
  console.log("processing model change");
  await axios.post('http://10.101.168.234:5000/set_graph', {
  // await axios.post('http://localhost:5000/set_graph', {
    graph: graph.value,
    processor: model.value
  })
  .then(response => {
    console.log(response.data);
  })
  .catch(error => {
    console.error(error);
  });
  isLoading.value = false;
};

function show_on_table(data: any): void {
  let result_data = data['result_table']
  entity_list.value = result_data.map((item) => {
    if (item[0] != null) {
      return { ngdb: item[0][0],
              tags: (item[0][1] === 1 ? ['success'] : null),
              rdflib: item[1] };
    }
    else {
      return {
        ngdb: null,
        tags: null,
        rdflib: item[1]
      };
    }
  });
}

function show_on_table_graph(data: any): void {
  if (parseInt(n_limit.value) == 0) {
    let result_data = data['result_table']
    entity_list_graph.value = result_data.map((item) => {
      return { ngdb: item };
    });
  }
  else {
    let result_data = data['result_table'].slice(0, parseInt(n_limit.value))
    entity_list_graph.value = result_data.map((item) => {
      return { ngdb: item };
    });
  }
}

async function exec_query() {
  console.log(query_str)
  const params = {
    query_str: query_str.value
  };
  await axios.get('http://10.101.168.234:5000/exec_query', { params })
  // await axios.get('http://localhost:5000/exec_query', { params })
  .then(response => {
      console.log(response.data);
      show_on_table(response.data)
      queryGraphData.value = response.data['query_plan']
  })
  .catch(error => {
      console.error(error);
  });
}

function reset_input() {
  query_str.value =  `SELECT ?o WHERE
{
  ?u :people.person.gender :m.05zppz .
  ?u :award.award_winner.awards_won..award.award_honor.honored_for ?o .
}
`
}


const queryGraphData = ref({
  nodes: [],
  edges: [],
});


const headerStyle: CSSProperties = {
  textAlign: 'center',
  color: '#fff',
  height: 64,
  paddingInline: 50,
  lineHeight: '64px',
  backgroundColor: '#7dbcea',
};

const contentStyle: CSSProperties = {
  textAlign: 'left',       // 文字对齐改为靠左
  minHeight: '120px',      // 保证最小高度为120px
  padding: '24px',         // 添加内填充，确保文本不会紧贴边缘
  color: '#333',           // 深色文字通常更易于阅读
  backgroundColor: '#f5f5f5',
  borderRadius: '4px',     // 添加圆角边框使得元素更加现代化和柔和
  boxShadow: '0 2px 4px rgba(0,0,0,0.1)', // 添加轻微的阴影，提升层次感
  fontSize: '16px',        // 设置适当的字体大小
  fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', // 使用常见的字体栈，确保跨平台的一致性
};

// const contentStyle: CSSProperties = {
//   textAlign: 'center',
//   minHeight: 120,
//   lineHeight: '120px',
//   color: '#000',
//   backgroundColor: '#f5f5f5',
// }; 

const siderStyle: CSSProperties = {
  textAlign: 'center',
  lineHeight: '120px',
  color: '#fff',
  backgroundColor: '#3ba0e9',
};

const footerStyle: CSSProperties = {
  textAlign: 'center',
  color: '#fff',
  backgroundColor: '#7dbcea',
};
</script>

