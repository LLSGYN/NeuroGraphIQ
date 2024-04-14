<template>
  <a-select v-if="showSelectNode"
    v-model:value="selectedNodeVal"
    show-search
    placeholder="Select node data"
    :style="{ position: 'absolute', left: `${selectPosition.x}px`, top: `${selectPosition.y}px`, width: '250px'}" 
    :options="node_options"
    :dropdown-match-select-width="true"
    @change="handleSelectChange"
    @search="debouncedSearch"
  ></a-select>

  <a-select v-if="showSelectEdge"
    v-model:value="selectedEdgeVal"
    show-search
    placeholder="Select edge data"
    :style="{ position: 'absolute', left: `${selectPosition.x}px`, top: `${selectPosition.y}px`, width: '250px'}" 
    :options="edge_options"
    :dropdown-match-select-width="true"
    @change="handleSelectChange"
    @search="debouncedSearch"
  ></a-select>

  <div id="mountNode" style="border: 1px solid #000; background-color:white;"></div>
  <a-select
      v-model:value="value1"
      style="width: 120px"
      :dropdown-match-select-width="false"
      @change="handleModeChange"
    >
    <a-select-option value="default">Default mode</a-select-option>
    <a-select-option value="addNode">Add Node (by clicking canvas)</a-select-option>
    <a-select-option value="addEdge">Add Edge (by clicking two end nodes)</a-select-option>
    <a-select-option value="addData">Add Graph Data (by clicking nodes or edges)</a-select-option>
  </a-select>

  <a-button @click="graphQuery">RUN QUERY</a-button>
  <a-button @click="setDefault">EXAMPLE</a-button>
</template>

<script lang="ts" setup>
import { defineComponent, onMounted, ref, nextTick, defineEmits } from 'vue';
import { GraphWithSelection } from './GraphWithSelection';
import debounce from './debounce';
import type { SelectProps } from 'ant-design-vue';
import type { Item, NodeConfig } from '@antv/g6';
import axios from 'axios';

// export default defineComponent({
  // setup() {
    // const mountNode = ref(null);
    const graphWithSelection = ref<GraphWithSelection | null>(null);
    const value1 = ref<string>('default');
    const showSelect = ref(false);
    const selectPosition = ref({ x: 0, y: 0 });
    const selectedValue = ref('');
    // const options = ref(['Option 1', 'Option 2', 'Option 3']);

    const showSelectNode = ref(false);
    const showSelectEdge = ref(false);

    const defaultNodeOptions = [
      { value : "Variable" },
      { value : "Target" },
    ];
    const defaultEdgeOptions = [
      { value : "Intersection" },
      { value : "Union" },
      { value : "Negation" },
    ];

    const node_options = ref<SelectProps['options']>(defaultNodeOptions);
    const edge_options = ref<SelectProps['options']>(defaultEdgeOptions);
    const selectedNodeVal = ref('');
    const selectedEdgeVal = ref('');

    let lastClickedItem: Item | null = null;

    const resetOptions = () => {
      node_options.value = defaultNodeOptions;
      edge_options.value = defaultEdgeOptions;
    };

    const handleSearch = async (query: string) => {
      if (query) {
        if (showSelectNode.value) {
          try {
            const response = await axios.get('http://10.101.168.234:5000/search_options', { params: { query:query, type:'node' } });
            // const response = await axios.get('http://localhost:5000/search_options', { params: { query:query, type:'node' } });
            node_options.value = response.data.map((item: string) => {
              return { value: item }
            });
          } catch (error) {
            console.error('Search request failed:', error);
          }
        }
        else if (showSelectEdge.value) {
          try {
            // const response = await axios.get('http://localhost:5000/search_options', { params: { query:query, type:'edge' } });
            const response = await axios.get('http://10.101.168.234:5000/search_options', { params: { query:query, type:'edge' } });
            edge_options.value = response.data.map((item: string) => {
              return { value: item }
            }); 
          } catch (error) {
            console.error('Search request failed:', error);
          }
        }
      }
    };
    const debouncedSearch = debounce(handleSearch, 500);

    onMounted(async() => {
      await nextTick();
      graphWithSelection.value = new GraphWithSelection('mountNode', (type, item, position) => {
        if (position) {
          selectPosition.value = position;
        }
        if (type === 'node') {
          showSelectNode.value = true;
          lastClickedItem = item;
        }
        else if (type === 'edge') {
          showSelectEdge.value = true;
          lastClickedItem = item;
        }
        else {
          showSelectEdge.value = false;
          showSelectNode.value = false;
          lastClickedItem = null;
          resetOptions();
        }
        console.log("!!!!!!!!!!!");
        console.log(type);
        if (item)
          console.log(item.getModel());
      });
    });

    const handleModeChange = (value: string) => {
      if (graphWithSelection.value) {
        graphWithSelection.value.handleModeChange(value);
      }
    };

    const filterOption = (input: string, option: any) => {
      return option.value.toLowerCase().indexOf(input.toLowerCase()) >= 0;
    };

    const handleSelectChange = (value: string) => {
      // Add logic here to handle the change from a-select
      console.log("Selected Option:", value);
      if (graphWithSelection.value && lastClickedItem) {
        if (showSelectNode.value) {
          let nodeModel = lastClickedItem.getModel();

          if (value === 'Variable') {
            nodeModel.type = 'circle';
            nodeModel.style.fill = 'grey';
            nodeModel.label = 'Var';
          }
          else if (value === 'Target') {
            nodeModel.type = 'star';
            nodeModel.size = 20;
            nodeModel.style.fill = '#ffa500';
            nodeModel.label = 'Target';
          }
          else {
            nodeModel.type = 'ellipse';
            nodeModel.label = selectedNodeVal.value;
            nodeModel.style.fill = '#F7FAFF';
          }

          graphWithSelection.value.graph.updateItem(
            lastClickedItem,
            nodeModel
          );
          selectedNodeVal.value = '';
        }
        else {
          let edgeModel = lastClickedItem.getModel();

          if (value === 'Intersection') {
            edgeModel.label = 'i';
            edgeModel.style.lineDash = [5];
          }
          else if (value === 'Union') {
            edgeModel.label = 'u';
            edgeModel.style.lineDash = [5];
          }
          else if (value === 'Negation') {
            edgeModel.label = 'n';
            edgeModel.style.lineDash = [5];
          }
          else {
            edgeModel.label = selectedEdgeVal.value;
            edgeModel.style.lineDash = null;
          }

          graphWithSelection.value.graph.updateItem(
            lastClickedItem,
            edgeModel
          );
          selectedEdgeVal.value = '';
        }
      }
      // Optionally close the select box after selection
      showSelectNode.value = false;
      showSelectEdge.value = false;
      resetOptions();
    };
    const emit = defineEmits(['updateValue'])
    const graphQuery = async() => {
      // Logic for running query goes here
      // pack the triples and send it to the backend
      if (graphWithSelection.value?.graph) {
        let data:any = {
          target: null,
          triples: []
        };
        const nodes = graphWithSelection.value.graph.getNodes();
        let id2label:any = {};
        for (let node of nodes) {
          let nodeconf = node.getModel();
          if (nodeconf.label === 'Target') {
            if (data.target) {
              alert("Multiple target nodes detected!");
              return;
            }
            data.target = nodeconf.id;
          }
          if (nodeconf.id) {
            id2label[nodeconf.id] = nodeconf.label;
          }
          else {
            alert("some internal errors happen during the query.");
          }
        }
        console.log(id2label);
        if (data.target == null) {
          alert("Query graph should have a target node!");
          return;
        }

        const nodedata = (id:any) => {
          if (id2label[id] != 'Var' && id2label[id] != 'Target') {
            // variable node
            return { type: 'anchor', id: id2label[id] }
          }
          else {
            return { type: 'variable', id: id }
          }
        };

        const edges = graphWithSelection.value.graph.getEdges();
        for(let e of edges) {
          console.log(e.getModel());
          const edgeconf = e.getModel();
          data.triples.push({
            src: nodedata(edgeconf.source),
            dst: nodedata(edgeconf.target),
            // rel: edgeconf.label =
            rel: (() => {
              if (edgeconf.label === 'i') {
                return 'INTERSECTION';
              }
              else if (edgeconf.label === 'u') {
                return 'UNION';
              }
              else if (edgeconf.label === 'n') {
                return 'NEGATION';
              }
              else {
                return edgeconf.label;
              }
            })()
          });
        }

        console.log(data);
        // await axios.get('http://localhost:5000/exec_graph_query', 
        await axios.get('http://10.101.168.234:5000/exec_graph_query', 
          { params: { data: JSON.stringify(data) } })
        .then(response => {
            console.log(response.data);
            emit('updateValue', response.data)
            // show_on_table(response.data)
        })
        .catch(error => {
            console.error(error);
        });
      }
    };
    const setDefault = () => {
      if (graphWithSelection.value) {
        graphWithSelection.value.setDefault();
      }
    };

    // return {
    //   value1,
    //   handleModeChange,
    //   handleSelectChange,
    //   graphQuery,
    //   showSelect,
    //   selectPosition,
    //   selectedValue,
    //   // options,
    //   // mountNode // Ensure the ref is returned if you need to access it in the template
    //   showSelectNode,
    //   showSelectEdge,
    //   node_options,
    //   edge_options,
    //   selectedNodeVal,
    //   selectedEdgeVal,
    //   filterOption,
    //   debouncedSearch,
    //   setDefault
    // };
  // },
// });
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