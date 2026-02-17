<template>
  <div class="workflow-graph">
    <svg
      :width="svgWidth"
      :height="svgHeight"
      :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="8"
          markerHeight="6"
          refX="8"
          refY="3"
          orient="auto"
        >
          <polygon points="0 0, 8 3, 0 6" fill="#909399" />
        </marker>
      </defs>

      <!-- Edges -->
      <g v-for="edge in layoutEdges" :key="`${edge.from}-${edge.action}-${edge.to}`">
        <path
          :d="edge.path"
          fill="none"
          stroke="#909399"
          stroke-width="1.5"
          marker-end="url(#arrowhead)"
        />
        <text
          :x="edge.labelX"
          :y="edge.labelY"
          class="edge-label"
          text-anchor="middle"
          dominant-baseline="middle"
        >
          {{ edge.label }}
        </text>
      </g>

      <!-- Nodes -->
      <g
        v-for="node in layoutNodes"
        :key="node.id"
        :transform="`translate(${node.x}, ${node.y})`"
      >
        <rect
          :width="nodeWidth"
          :height="nodeHeight"
          :rx="8"
          :ry="8"
          :fill="node.fill"
          :stroke="node.stroke"
          :stroke-width="node.id === activeNode ? 2.5 : node.strokeWidth"
          :class="{ 'node-active': node.id === activeNode }"
        />
        <text
          :x="nodeWidth / 2"
          :y="nodeHeight / 2"
          text-anchor="middle"
          dominant-baseline="central"
          :fill="node.textColor"
          class="node-label"
        >
          {{ node.name }}
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { WorkflowNode, WorkflowAction, WorkflowTransition, WorkflowDefinition } from '@/api/admin/workflow'

const props = defineProps<{
  nodes?: WorkflowNode[]
  actions?: WorkflowAction[]
  transitions?: WorkflowTransition[]
  definition?: WorkflowDefinition
  activeNode?: string
}>()

// Support both separate props and a combined definition prop
const resolvedNodes = computed(() => props.nodes ?? props.definition?.nodes ?? [])
const resolvedActions = computed(() => props.actions ?? props.definition?.actions ?? [])
const resolvedTransitions = computed(() => props.transitions ?? props.definition?.transitions ?? [])

const nodeWidth = 120
const nodeHeight = 40
const paddingX = 40
const paddingY = 30
const colGap = 160
const rowGap = 70

function getNodeStyle(node: WorkflowNode) {
  if (node.type === 'start') {
    return { fill: '#003DA5', textColor: '#FFFFFF', stroke: '#003DA5', strokeWidth: 1.5 }
  }
  if (node.type === 'terminal') {
    if (node.id.includes('approved')) {
      return { fill: '#67C23A', textColor: '#FFFFFF', stroke: '#67C23A', strokeWidth: 1.5 }
    }
    if (node.id.includes('rejected')) {
      return { fill: '#F56C6C', textColor: '#FFFFFF', stroke: '#F56C6C', strokeWidth: 1.5 }
    }
    return { fill: '#909399', textColor: '#FFFFFF', stroke: '#909399', strokeWidth: 1.5 }
  }
  // intermediate
  return { fill: '#F4F6FA', textColor: '#1A1A2E', stroke: '#E2E6ED', strokeWidth: 1.5 }
}

// Build adjacency list and perform topological sort to assign columns
const layout = computed(() => {
  const nodeMap = new Map<string, WorkflowNode>()
  resolvedNodes.value.forEach(n => nodeMap.set(n.id, n))

  // Build adjacency and in-degree
  const adj = new Map<string, string[]>()
  const inDegree = new Map<string, number>()
  resolvedNodes.value.forEach(n => {
    adj.set(n.id, [])
    inDegree.set(n.id, 0)
  })
  resolvedTransitions.value.forEach(t => {
    adj.get(t.from_node)?.push(t.to_node)
    inDegree.set(t.to_node, (inDegree.get(t.to_node) || 0) + 1)
  })

  // Kahn's algorithm — assign layer (column) based on longest path
  const layer = new Map<string, number>()
  const queue: string[] = []
  resolvedNodes.value.forEach(n => {
    if ((inDegree.get(n.id) || 0) === 0) {
      queue.push(n.id)
      layer.set(n.id, 0)
    }
  })

  while (queue.length > 0) {
    const curr = queue.shift()!
    const currLayer = layer.get(curr) || 0
    for (const next of adj.get(curr) || []) {
      // Use longest path for layer assignment
      const existingLayer = layer.get(next) ?? -1
      if (currLayer + 1 > existingLayer) {
        layer.set(next, currLayer + 1)
      }
      inDegree.set(next, (inDegree.get(next) || 0) - 1)
      if (inDegree.get(next) === 0) {
        queue.push(next)
      }
    }
  }

  // Handle nodes not reached by topo sort (cycles or disconnected)
  resolvedNodes.value.forEach(n => {
    if (!layer.has(n.id)) {
      layer.set(n.id, 0)
    }
  })

  // Group nodes by column
  const columns = new Map<number, string[]>()
  layer.forEach((col, nodeId) => {
    if (!columns.has(col)) columns.set(col, [])
    columns.get(col)!.push(nodeId)
  })

  const maxCol = Math.max(0, ...layer.values())

  // Assign x, y positions
  const positions = new Map<string, { x: number; y: number }>()
  for (let col = 0; col <= maxCol; col++) {
    const nodesInCol = columns.get(col) || []
    nodesInCol.forEach((nodeId, rowIdx) => {
      positions.set(nodeId, {
        x: paddingX + col * (nodeWidth + colGap),
        y: paddingY + rowIdx * (nodeHeight + rowGap),
      })
    })
  }

  // Build action name lookup
  const actionNameMap = new Map<string, string>()
  resolvedActions.value.forEach(a => actionNameMap.set(a.id, a.name))

  // Compute total width/height
  const maxNodesInAnyCol = Math.max(1, ...Array.from(columns.values()).map(c => c.length))
  const totalWidth = paddingX * 2 + (maxCol + 1) * nodeWidth + maxCol * colGap
  const totalHeight = paddingY * 2 + maxNodesInAnyCol * nodeHeight + (maxNodesInAnyCol - 1) * rowGap

  // Build layout nodes
  const layoutNodes = resolvedNodes.value.map(n => {
    const pos = positions.get(n.id)!
    const style = getNodeStyle(n)
    return {
      id: n.id,
      name: n.name,
      x: pos.x,
      y: pos.y,
      ...style,
    }
  })

  // Build layout edges with paths
  const layoutEdges = resolvedTransitions.value.map(t => {
    const fromPos = positions.get(t.from_node)
    const toPos = positions.get(t.to_node)
    if (!fromPos || !toPos) {
      return null
    }

    const x1 = fromPos.x + nodeWidth
    const y1 = fromPos.y + nodeHeight / 2
    const x2 = toPos.x
    const y2 = toPos.y + nodeHeight / 2

    // Simple cubic bezier for smooth curves
    const dx = (x2 - x1) * 0.4
    const path = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`

    const labelX = (x1 + x2) / 2
    const labelY = (y1 + y2) / 2 - 8

    return {
      from: t.from_node,
      to: t.to_node,
      action: t.action,
      path,
      labelX,
      labelY,
      label: actionNameMap.get(t.action) || t.action,
    }
  }).filter(Boolean)

  return { layoutNodes, layoutEdges, totalWidth, totalHeight }
})

const layoutNodes = computed(() => layout.value.layoutNodes)
const layoutEdges = computed(() => layout.value.layoutEdges)
const svgWidth = computed(() => Math.max(300, layout.value.totalWidth))
const svgHeight = computed(() => Math.max(100, layout.value.totalHeight))
</script>

<style lang="scss" scoped>
.workflow-graph {
  overflow-x: auto;
  padding: 8px;

  svg {
    display: block;
  }
}

.node-label {
  font-size: 12px;
  font-weight: 500;
  pointer-events: none;
  user-select: none;
}

.edge-label {
  font-size: 10px;
  fill: #606266;
  pointer-events: none;
  user-select: none;
}

.node-active {
  filter: drop-shadow(0 0 4px rgba(0, 61, 165, 0.5));
  stroke: #003DA5;
}
</style>
