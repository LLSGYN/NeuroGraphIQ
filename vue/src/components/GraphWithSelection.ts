import G6, { Graph } from '@antv/g6';
import type { IG6GraphEvent, Item } from '@antv/g6';

// 用于生成节点ID
let addedCount = 0;

// 注册添加边的行为
G6.registerBehavior('click-add-edge', {
  getEvents() {
    return {
      'node:click': 'onClick',
      'mousemove': 'onMousemove',
      'edge:click': 'onEdgeClick',
    };
  },
  onClick(ev: IG6GraphEvent) {
    console.log('Canvas clicked, adding node');
    const node = ev.item as Item;
    const graph = this.graph as Graph;
    const point = {
      x: ev.x,
      y: ev.y,
    };
    const model = node.getModel();
    if (this.addingEdge && this.edge) {
      graph.updateItem(this.edge, {
        target: model.id,
      });
      this.edge = null;
      this.addingEdge = false;
    } else {
      this.edge = graph.addItem('edge', {
        source: model.id,
        target: point,
      });
      this.addingEdge = true;
    }
  },
  onMousemove(ev: IG6GraphEvent) {
    const point = {
      x: ev.x,
      y: ev.y,
    };
    if (this.addingEdge && this.edge) {
      this.graph.updateItem(this.edge, {
        target: point,
      });
    }
  },
  onEdgeClick(ev: IG6GraphEvent) {
    const currentEdge = ev.item as Item;
    if (this.addingEdge && this.edge === currentEdge) {
      this.graph.removeItem(this.edge);
      this.edge = null;
      this.addingEdge = false;
    }
  }
});

// 注册添加节点的行为
G6.registerBehavior('click-add-node', {
  getEvents() {
    return {
      'canvas:click': 'onClick',
    };
  },
  onClick(ev: IG6GraphEvent) {
    const graph = this.graph as Graph;
    graph.addItem('node', {
      x: ev.canvasX,
      y: ev.canvasY,
      id: `node-${addedCount}`, // 生成唯一的ID
    });
    addedCount++;
  }
});

export class GraphWithSelection {
  public graph: Graph;
  // private selectElement: HTMLSelectElement | null = null;
  private mode: string = 'default';// 添加一个回调函数属性
  private onSelectItem: (type: 'node' | 'edge' | 'canvas', item: any, position: { x: number; y: number; } | null) => void;
  // public lastClickedItem: Item | null = null;

  constructor(containerId: string, onSelectItem: (type: 'node' | 'edge' | 'canvas', item: any, position: { x: number; y: number; } | null) => void) {
    this.graph = new G6.Graph({
      container: containerId,
      width: 800,
      height: 600,
      modes: {
        default: ['drag-node', 'click-select'],
        addNode: ['click-add-node', 'click-select'],
        addEdge: ['click-add-edge', 'click-select'],
        addData: ['click-select']
      },
      nodeStateStyles: {
        selected: {
          stroke: '#666',
          lineWidth: 2,
          fill: 'steelblue',
        },
      },
      // 其他图形配置
      defaultEdge: {
        // ...                 // 边的其他配置
        // 边样式配置
        style: {
          opacity: 0.6, // 边透明度
          stroke: 'grey', // 边描边颜色
          endArrow: true
        },
        // 边上的标签文本配置
        labelCfg: {
          autoRotate: true, // 边上的标签文本根据边的方向旋转
        },
      }
    });
    this.onSelectItem = onSelectItem; // 设置回调函数

    this.initializeGraph();
  }

  private initializeGraph(): void {
    this.graph.data({
      nodes: [],
      edges: []
    });
    // this.graph.data({
    //   nodes: [
    //     { id: 'node1', label: 'Node 1', x: 100, y: 100 },
    //     { id: 'node2', label: 'Node 2', x: 300, y: 200 }
    //     // 更多节点数据
    //   ],
    //   edges: [
    //     // 示例边
    //     { source: 'node1', target: 'node2', label: 'Edge 1' }
    //   ]
    // });

    this.graph.render();

    // 监听节点点击事件
    this.graph.on('node:click', (evt) => this.handleNodeClick(evt));
    // 监听边点击事件
    this.graph.on('edge:click', (evt) => this.handleEdgeClick(evt));
    // 监听画布点击事件，用于移除选择框
    this.graph.on('canvas:click', () => this.removeSelectElement());
  }

  public setDefault(): void {
    this.graph.data({
      nodes: [
        { id: 'node1', label: 'Target', x: 450, y: 100, type: 'star', size: 20, style: { fill: '#ffa500' } },
        { id: 'node2', label: 'Var', x: 100, y: 200, fill: 'grey'},
        { id: 'node3', label: '/m/05zppz', x: 450, y: 300, type: 'ellipse', style: { fill: '#F7FAFF' } }
        // { id: 'node1', label: 'Target', type: 'star', size: 20, style: { fill: '#ffa500' } },
        // { id: 'node2', label: 'Var', fill: 'grey'},
        // { id: 'node3', label: '/m/05zppz', type: 'ellipse', style: { fill: '#F7FAFF' } }
      ],
      edges: [
        { source: 'node2', target: 'node1', label: "/award/award_winner/awards_won./award/award_honor/award_winner" },
        { source: 'node2', target: 'node3', label: '/people/person/gender' },
      ]
    });
    this.graph.render();
  }

  private removeSelectElement(): void {
    this.onSelectItem('canvas', null, null);
  }

  private handleNodeClick(evt: IG6GraphEvent): void {
    if (this.mode !== 'addData') return;
    // this.lastClickedItem = evt.item;
    const item: any = evt.item;
    const model:any = item.getModel();
    const { x, y } = this.graph.getClientByPoint(model.x, model.y);
    this.onSelectItem('node', item, { x, y });
  }

  private handleEdgeClick(evt: IG6GraphEvent): void {
    if (this.mode !== 'addData') return;
    // this.lastClickedItem = evt.item;
    const item: any = evt.item;
    const model:any = item.getModel();
    // 使用边的中点作为位置
    const { x, y } = this.graph.getClientByPoint((model.startPoint.x + model.endPoint.x) / 2, (model.startPoint.y + model.endPoint.y) / 2);
    this.onSelectItem('edge', item, { x, y });
  }

  public handleModeChange = (value: string): void => {
    console.log(`selected ${value}`);
    this.mode = value; // 更新当前模式
    this.graph.setMode(value);
  };
}