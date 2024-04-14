<template>
  <a-space direction="vertical" :style="{ width: '100%' }" :size="[0, 48]">
    <a-layout>
      <!-- <a-layout-header :style="headerStyle">Header</a-layout-header> -->
      <a-layout>
        <!-- <a-layout-sider :style="siderStyle">Sider</a-layout-sider> -->
        <a-layout-content :style="contentStyle">
            <a-flex>
                <div style="width: 50%;">
                  <div v-if="input_view">
                    <div>
                      <a-textarea v-model:value="query_str" placeholder="Query your graph here" :rows="6" />
                    </div>
                    <div>
                      <a-button @click="exec_query" style="margin-right: 5px;">RUN QUERY</a-button>
                      <a-button @click="reset_input">RESET</a-button>
                    </div>
                    <a-button @click="switch_input_view">graph input</a-button>
                  </div>
                  <div v-else>
                    <GraphInput/>
                    <a-button @click="switch_input_view">sparql input</a-button>
                  </div>
                <!-- <br /> -->
                <!-- <a-textarea :rows="4" placeholder="maxlength is 6" :maxlength="6" /> -->
                </div>
                <div style="width: 50%;">
                  <a-table :columns="columns" :data-source="entity_list" bordered>
                    <template #bodyCell="{ column, text }">
                      <template v-if="column.dataIndex === 'name'">
                        <a>{{ text }}</a>
                      </template>
                    </template>
                    <!-- <template #title>Results</template> -->
                  </a-table>
                </div>
            </a-flex>
        </a-layout-content>
      </a-layout>
      <a-layout-footer :style="footerStyle">Footer</a-layout-footer>
    </a-layout>
  </a-space>
</template>

<script lang="ts" setup>
import type { CSSProperties } from 'vue';
import { ref } from 'vue';
import axios from "axios"
import GraphInput from './components/GraphInput.vue';
// import useApiService from './services/apiService';

const query_str = ref<string>('foofoofoo');
// const { error, postUser, get_query } = useApiService();

const columns = [
  {
    title: 'Neural',
    dataIndex: 'ngdb',
  },
  {
    title: 'Symbolic',
    dataIndex: 'rdflib',
  },
  // {
  //   title: 'Cash Assets',
  //   className: 'column-money',
  //   dataIndex: 'money',
  // },
  // {
  //   title: 'Address',
  //   dataIndex: 'address',
  // },
];

const entity_list = ref([
  {
    ngdb: "",
    rdflib: ""
  },
  {
    ngdb: "",
    rdflib: "",
  },
  {
    ngdb: "",
    rdflib: ""
  },
])

const input_view = ref(true)

function switch_input_view() {
  input_view.value = !input_view.value;
};

function show_on_table(data: string[]): void {
  entity_list.value = data.map((item: string) => {
    return { ngdb: item[0],
             rdflib: item[1] };
  });
}

async function exec_query() {
  console.log(query_str)
  const params = {
    query_str: query_str.value
  };
  await axios.get('http://10.101.168.234:5000/exec_query', { params })
  .then(response => {
      // console.log(response.data);
      show_on_table(response.data)
  })
  .catch(error => {
      console.error(error);
  });
  // console.log("miaomiaomiao")
}

// TODO: 修改成论文需要的case
function reset_input() {
  query_str.value =  `SELECT ?o WHERE
{
  ?u :people.person.gender :m.05zppz .
  ?u :award.award_winner.awards_won..award.award_honor.honored_for ?o .
}
`
}

const headerStyle: CSSProperties = {
  textAlign: 'center',
  color: '#fff',
  height: 64,
  paddingInline: 50,
  lineHeight: '64px',
  backgroundColor: '#7dbcea',
};

const contentStyle: CSSProperties = {
  textAlign: 'center',
  minHeight: 120,
  lineHeight: '120px',
  color: '#fff',
  backgroundColor: '#f5f5f5',
}; 

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

