<template>
  <div ref="graphContainer" style="border: 1px solid #000; background-color:white;"></div>
</template>

<script lang="ts">
import { defineComponent, onMounted, ref, watch } from 'vue';
import G6 from '@antv/g6';

export default defineComponent({
  name: 'PlotQueryPlan',
  props: {
    graphData: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    const graphContainer = ref<HTMLElement | null>(null);

    let graph:any = null;
    onMounted(() => {
      if (graphContainer.value) {
        graph = new G6.Graph({
          container: graphContainer.value,
          width: 600,
          height: 800,
          // fitView: true,
          defaultEdge: {
            style: {
              opacity: 0.6, // 边透明度
              stroke: 'grey', // 边描边颜色
              endArrow: true
            },
            // 边上的标签文本配置
            labelCfg: {
              autoRotate: true, // 边上的标签文本根据边的方向旋转
            },
          },
          layout: {
            type: 'force', // 指定为力导向布局
            preventOverlap: true, // 防止节点重叠
            linkDistance: function(edge, source, target) {
              // 返回边长值，可以基于边的标签长度动态计算
              const labelLength = edge.label ? Math.max(edge.label.length * 8, 50) : 50;
              return labelLength;
            },
          },
          modes: {
            default: ['drag-node'],
          },
        });

        // 使用 props.graphData 来绘制图形
        graph.data(props.graphData);
        graph.render();
      }
    });

    watch(
      () => props.graphData,
      (newData) => {
        // 当图数据更新时重新渲染图形
        if (graphContainer.value && graph) {
          graph.read(newData)
          // graph = new G6.Graph({
          //   container: graphContainer.value,
          //   width: 300,
          //   height: 300,
          //   defaultEdge: {
          //     style: {
          //       opacity: 0.6, // 边透明度
          //       stroke: 'grey', // 边描边颜色
          //       endArrow: true
          //     },
          //     // 边上的标签文本配置
          //     labelCfg: {
          //       autoRotate: true, // 边上的标签文本根据边的方向旋转
          //     },
          //   },
          //   layout: {
          //     type: 'force', // 指定为力导向布局
          //     preventOverlap: true, // 防止节点重叠
          //   },
          // });
          // graph.data(newData);
          // graph.render();
        }
      }
    );

    return {
      graphContainer,
    };
  },
});
</script>
