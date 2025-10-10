<template>
	<div
		class="editor-viewport"
		tabindex="0"
		ref="viewportElement"
		@wheel.stop.prevent="onWheel"
		@fullscreenchange="onFullscreenChange"
		@contextmenu.capture="onViewportContextMenu"
	>
		<MiniMapComponent v-if="settingsStore.showMinimap" :graph="props.graph" ref="minimap" />

		<div
			class="editor-scaler"
			:style="scalerStyles"
			@transitionstart="onScalerTransitionStart"
			@transitionend="onScalerTransitionEnd"
		>
			<div class="editor-background" :style="editorBackgroundStyles" v-if="graph.ui.scale > 0.2"></div>
			<div
				class="editor-backdrop"
				:style="editorBackdropStyles"
				ref="backdropElement"
				@mousedown="props.graph.ui.onMouseDown"
				@mouseup="props.graph.ui.onMouseUp"
				@dblclick.stop.prevent="onDoubleClick"
				@click="graph.ui.onClick"
				@mousemove="graph.ui.onMouseMove"
				@mouseleave="graph.ui.onMouseUp"
				@dragover.prevent="onDragOver"
				@drop.prevent="onDrop"
			>
				<div class="editor-contents" :style="editorContentsStyles" ref="contentElement">
					<template v-for="node in graph.getNodes()" :key="node.id + '-' + node.renderKey">
						<NodeComponent :node="node" :tab-id="props.tabId" :disabled="editorStore.isResolvingMergeConflict" />
					</template>

					<FreeformEdgeComponent v-if="grabbedEdge" v-bind="grabbedEdge" />
					<div class="editor-selection-area" :style="selectionAreaStyles" v-if="props.graph.ui.selectionArea"></div>
				</div>
			</div>
		</div>

		<div class="controls-container">
			<span class="zoom-amount no-select" @click="graph.ui.resetZoom" title="Reset Zoom"
				>{{ Math.round(graph.ui.scale * 100) }}%</span
			>
			<span class="controls-icon material-icons" title="Zoom in" @click="graph.ui.zoomIn">zoom_in</span>
			<span class="controls-icon material-icons" title="Zoom out" @click="graph.ui.zoomOut">zoom_out</span>
			<span class="controls-icon material-icons" title="Toggle Fullscreen" @click="toggleFullscreen">{{
				isFullscreen ? 'fullscreen_exit' : 'fullscreen'
			}}</span>
		</div>

		<!-- 
			Each graph needs its own context menu since transforms within the graph will
			make the root context menu unusable in certain situations (e.g. fullscreen).
		-->
		<ContextMenu :ref="(el) => contextmenuStore.setContextMenu(props.tabId, el)" />
	</div>
</template>

<script setup lang="ts">
	import ContextMenu from '@/components/ContextMenu.vue';
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
	import type { GraphEdge } from '@/editor/graph/edges/FreeformEdgeComponent.vue';
	import FreeformEdgeComponent from '@/editor/graph/edges/FreeformEdgeComponent.vue';
	import NodeComponent from '@/editor/graph/nodes/NodeComponent.vue';
	import MiniMapComponent from '@/editor/MiniMapComponent.vue';
	import type { Graph, NodeMetadata } from '@/graph';
	import { useContextmenuStore, useEditorStore, useMetadataStore, useSettingsStore } from '@/stores';
	import { computed, nextTick, onMounted, ref, watch, type ComputedRef } from 'vue';

	const props = defineProps<{
		tabId: string;
		graph: Graph;
	}>();

	const metadataStore = useMetadataStore();
	const contextmenuStore = useContextmenuStore();
	const editorStore = useEditorStore();
	const settingsStore = useSettingsStore();

	const viewportElement = ref<HTMLDivElement>();
	const backdropElement = ref<HTMLDivElement>();
	const contentElement = ref<HTMLDivElement>();
	const minimap = ref<InstanceType<typeof MiniMapComponent> | null>(null);
	const isFullscreen = ref<boolean>(false);

	onMounted(() => {
		props.graph.ui.setElements(viewportElement.value, backdropElement.value, contentElement.value);
		contextmenuStore.getContextMenu(props.tabId).addHook(backdropElement.value!, openContextMenu, false);
		minimap.value?.requestUpdateMinimap();
	});

	function onDragOver(ev: DragEvent) {
		if (!ev.dataTransfer) return;
		ev.dataTransfer.dropEffect = 'move';
	}

	function onDrop(ev: DragEvent) {
		if (!ev.dataTransfer) return;

		const contentPositions = props.graph.ui.contentPositions();
		const backdropPositions = props.graph.ui.backdropPositions();
		const cursorX =
			(ev.clientX - backdropPositions.left - (contentPositions.left - backdropPositions.left)) / props.graph.ui.scale;
		const cursorY =
			(ev.clientY - backdropPositions.top - (contentPositions.top - backdropPositions.top)) / props.graph.ui.scale;

		const nodeData = ev.dataTransfer.getData('addNode');
		if (nodeData) {
			const metadata: NodeMetadata = JSON.parse(nodeData);
			const addedNode = props.graph.addNode(metadata, cursorX - 20, cursorY - 20);
			nextTick(() => addedNode.centerPosition());
		}
	}

	function onWheel(event: WheelEvent) {
		if (event.deltaY > 0) {
			props.graph.ui.zoomIn();
		}
		if (event.deltaY < 0) {
			props.graph.ui.zoomOut();
		}
	}

	function onDoubleClick(event: MouseEvent) {
		if (event.button == 0) {
			props.graph.ui.deselectAllNodes();
		}
	}

	function onViewportContextMenu(event: MouseEvent) {
		props.graph.ui.grabSocket(null);

		if (event.ctrlKey && event.altKey) {
			// Allow for normal context menu when ctrl+alt is held down
			return;
		}

		event.preventDefault();
	}

	function onScalerTransitionStart() {
		props.graph.ui.setIsScaling(true);
	}

	function onScalerTransitionEnd() {
		props.graph.ui.setIsScaling(false);
		props.graph.ui.handleScaleFrames();
	}

	/**
	 * Internally checks if this lowercase string matches the metadata store
	 * @param nodeName the name of the node to match (forced lowercase)
	 */
	async function addNode(nodeName: string) {
		const addedNode = props.graph.addNode(
			metadataStore.getNode(nodeName),
			props.graph.ui.cursor.x,
			props.graph.ui.cursor.y
		);
		nextTick(() => addedNode.centerPosition());
	}

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];
		const copiedNodes = editorStore.copiedNodes;
		const selectedNodes = props.graph.ui.selectedNodes;

		if (copiedNodes.length) {
			let description = `Paste copied node: '${copiedNodes[0].serialized.name}' (Ctrl+V)`;
			if (copiedNodes.length > 1) {
				description = `Paste all copied nodes: '${copiedNodes[0].serialized.name}' and ${
					copiedNodes.length - 1
				} more... (Ctrl+V)`;
			}

			entries.push({
				label: copiedNodes.length > 1 ? 'Paste Nodes' : 'Paste Node',
				description: description,
				callback: () => {
					const addedNodes = props.graph.addNodeStates(copiedNodes, {
						x: props.graph.ui.cursor.x,
						y: props.graph.ui.cursor.y,
						connect: 'group'
					});

					if (addedNodes.length > 1) {
						props.graph.ui.deselectAllNodes();
						for (const addedNode of addedNodes) {
							props.graph.ui.selectNode(addedNode);
						}
					}
				},
				divider: true
			});
		}

		entries.push({
			label: 'Select all',
			description: 'Select all nodes (Ctrl+A)',
			callback: async () => {
				props.graph.ui.selectAllNodes();
			}
		});

		entries.push({
			label: 'Add Comment Node',
			description: 'Create a comment node',
			callback: () => {
				addNode('comment');
			}
		});

		// New Primitive Node
		const newPrimNodesSubmenu: Array<MenuItem> = [];

		newPrimNodesSubmenu.push({
			label: 'New String',
			description: "Create a 'New String' node",
			callback: () => {
				addNode('new string');
			}
		});

		newPrimNodesSubmenu.push({
			label: 'New Number',
			description: "Create a 'New Number' node",
			callback: () => {
				addNode('new number');
			}
		});

		newPrimNodesSubmenu.push({
			label: 'New Boolean',
			description: "Create a 'New Boolean' node",
			callback: () => {
				addNode('new boolean');
			}
		});

		entries.push({
			label: 'Add Primitive Data',
			description: 'Create a data node',
			submenu: { items: newPrimNodesSubmenu },
			divider: false
		});
		// // //

		// New Log Node
		const newLogNodesSubmenu: Array<MenuItem> = [];

		newLogNodesSubmenu.push({
			label: 'Log (Print)',
			description: "Create a 'Log (Print)' node",
			callback: () => {
				addNode('log (print)');
			}
		});

		newLogNodesSubmenu.push({
			label: 'Log (Print) List',
			description: "Create a 'Log (Print) List' node",
			callback: () => {
				addNode('log (print) list');
			}
		});

		newLogNodesSubmenu.push({
			label: 'Debug Breakpoint (Log)',
			description: "Create a 'Debug Breakpoint (Log)' node",
			callback: () => {
				addNode('debug breakpoint (log)');
			}
		});

		entries.push({
			label: 'Add Logging Node',
			description: 'Create a logging node',
			submenu: { items: newLogNodesSubmenu },
			divider: false
		});
		// // //

		// New Loops
		const newLoopNodesSubmenu: Array<MenuItem> = [];

		newLoopNodesSubmenu.push({
			label: 'For Each',
			description: "Create a 'For Each' node",
			callback: () => {
				addNode('for each');
			}
		});

		newLoopNodesSubmenu.push({
			label: 'For Loop',
			description: "Create a 'For Loop' node",
			callback: () => {
				addNode('For Loop');
			}
		});

		newLoopNodesSubmenu.push({
			label: 'Ranged For Loop',
			description: "Create a 'Ranged For Loop' node",
			callback: () => {
				addNode('Ranged For Loop');
			}
		});

		newLoopNodesSubmenu.push({
			label: 'Infinite Loop',
			description: "Create a 'Infinite Loop' node",
			callback: () => {
				addNode('Infinite Loop');
			}
		});

		newLoopNodesSubmenu.push({
			label: 'List Compression Loop',
			description: "Create a 'List Compression Loop' node",
			callback: () => {
				addNode('List Compression Loop');
			}
		});

		newLoopNodesSubmenu.push({
			label: 'Retry Loop',
			description: "Create a 'Retry Loop' node",
			callback: () => {
				addNode('Retry Loop');
			}
		});

		newLoopNodesSubmenu.push({
			label: 'Loop Break',
			description: "Create a 'Loop Break' node",
			callback: () => {
				addNode('Loop Break');
			}
		});

		newLoopNodesSubmenu.push({
			label: 'Loop Continue',
			description: "Create a 'Loop Continue' node",
			callback: () => {
				addNode('Loop Continue');
			}
		});

		entries.push({
			label: 'Add Loop',
			description: 'Create a loop node',
			submenu: { items: newLoopNodesSubmenu },
			divider: false
		});
		// // //

		// New Branching
		const newBranchingNodesSubmenu: Array<MenuItem> = [];

		newBranchingNodesSubmenu.push({
			label: 'If / Else',
			description: "Create a 'If / Else' node",
			callback: () => {
				addNode('If / Else');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'If / Else / Finally',
			description: "Create a 'If / Else / Finally' node",
			callback: () => {
				addNode('If / Else / Finally');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'If True',
			description: "Create a 'If True' node",
			callback: () => {
				addNode('If True');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'If True / Finally',
			description: "Create a 'If True / Finally' node",
			callback: () => {
				addNode('If True / Finally');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'If False',
			description: "Create a 'If False' node",
			callback: () => {
				addNode('If False');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'If False / Finally',
			description: "Create a 'If False / Finally' node",
			callback: () => {
				addNode('If False / Finally');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'Sequence (2)',
			description: "Create a 'Sequence (2)' node",
			callback: () => {
				addNode('Sequence (2)');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'Sequence (3)',
			description: "Create a 'Sequence (3)' node",
			callback: () => {
				addNode('Sequence (3)');
			}
		});

		newBranchingNodesSubmenu.push({
			label: 'Sequence (4)',
			description: "Create a 'Sequence (4)' node",
			callback: () => {
				addNode('Sequence (4)');
			}
		});

		entries.push({
			label: 'Add Branching',
			description: 'Create a branching node',
			submenu: { items: newBranchingNodesSubmenu },
			divider: false
		});
		// // //

		// New Graph Control
		const newStartEndNodesSubmenu: Array<MenuItem> = [];

		newStartEndNodesSubmenu.push({
			label: 'Graph Start',
			description: "Create a 'Graph Start' node",
			callback: () => {
				addNode('Graph Start');
			}
		});

		newStartEndNodesSubmenu.push({
			label: 'End',
			description: "Create a 'End' node",
			callback: () => {
				addNode('End');
			}
		});

		newStartEndNodesSubmenu.push({
			label: 'Execute Graph',
			description: "Create a 'Execute Graph' node",
			callback: () => {
				addNode('Execute Graph');
			}
		});

		entries.push({
			label: 'Add Graph Control',
			description: 'Create a node that controls graph flow',
			submenu: { items: newStartEndNodesSubmenu },
			divider: false
		});

		// Exception Handling
		const exceptionsSubmenu: Array<MenuItem> = [];

		exceptionsSubmenu.push({
			label: 'Try / Catch',
			description: "Create a 'Try / Catch' node",
			callback: () => { addNode('Try / Catch'); }
		});

		exceptionsSubmenu.push({
			label: 'Try / Catch / Finally',
			description: "Create a 'Try / Catch / Finally' node",
			callback: () => { addNode('Try / Catch / Finally'); }
		});

		exceptionsSubmenu.push({
			label: 'Try / Finally',
			description: "Create a 'Try / Finally' node",
			callback: () => { addNode('Try / Finally'); }
		});

		exceptionsSubmenu.push({
			label: 'Raise Exception',
			description: "Create a 'Raise Exception' node",
			callback: () => { addNode('Raise Exception'); }
		});

		exceptionsSubmenu.push({
			label: 'Defer Exception',
			description: "Create a 'Defer Exception' node",
			callback: () => { addNode('Defer Exception'); }
		});

		exceptionsSubmenu.push({
			label: 'Retry Loop',
			description: "Create a 'Retry Loop' node",
			callback: () => { addNode('Retry Loop'); }
		});

		entries.push({
			label: 'Add Exception Handling',
			description: 'Create a node that handles exceptions',
			submenu: { items: exceptionsSubmenu },
			divider: false
		});
		// // //

		// Selected node operations
		if (selectedNodes.length) {
			const selectedNodesSubmenu: Array<MenuItem> = [];

			selectedNodesSubmenu.push({
				label: 'De-select All',
				description: 'De-select all nodes (Double Click)',
				callback: async () => {
					props.graph.ui.deselectAllNodes();
				}
			});

			selectedNodesSubmenu.push({
				label: 'Cut',
				description: 'Cut (Copy & Delete) all selected nodes (Ctrl+X)',
				callback: () => {
					editorStore.storeCopiedNodes(selectedNodes);
					props.graph.deleteNodes(selectedNodes);
				}
			});

			selectedNodesSubmenu.push({
				label: 'Copy',
				description: 'Copy all selected nodes (Ctrl+C)',
				callback: () => {
					editorStore.storeCopiedNodes(selectedNodes);
				}
			});

			selectedNodesSubmenu.push({
				label: 'Delete',
				description: 'Delete the selected node',
				callback: () => {
					props.graph.deleteNodes(selectedNodes);
				},
				divider: true
			});

			selectedNodesSubmenu.push({
				label: 'Replace with Comments',
				description: 'Replaces selected nodes with comments',
				callback: () => {
					editorStore.replaceMultipleNodesWithComments(selectedNodes, props.graph);
				},
				divider: false
			});

			selectedNodesSubmenu.push({
				label: 'Uncomment Nodes',
				description: 'Uncomments nodes previously commented via this menu',
				callback: async () => {
					editorStore.replaceMultipleCommentsWithNodes(selectedNodes, props.graph);
				},
				divider: true
			});

			selectedNodesSubmenu.push({
				label: 'Duplicate',
				description: 'Duplicate all selected nodes',
				callback: () => {
					// Find the right-most node of the selection
					const rightMostNode = selectedNodes.reduce((prev, curr) => (prev.x > curr.x ? prev : curr));

					// Duplicate
					const addedNodes = props.graph.addNodeStates(
						selectedNodes.map((node) => node.getStateObject()),
						{
							x: rightMostNode.x + rightMostNode.width() + 50,
							connect: 'group'
						}
					);

					if (addedNodes.length > 1) {
						props.graph.ui.deselectAllNodes();
						for (const addedNode of addedNodes) {
							props.graph.ui.selectNode(addedNode);
						}
					}
				}
			});

			selectedNodesSubmenu.push({
				label: 'Clear Connections',
				description: 'Clears the connections on selected nodes',
				callback: () => {
					for (const node of selectedNodes) {
						node.clearConnections();
					}
				}
			});

			if (selectedNodes.find((node) => node.metadata.dynamic)) {
				selectedNodesSubmenu.push({
					label: 'Refresh',
					description: 'Refresh the selected nodes',
					callback: () => {
						for (const node of selectedNodes) {
							if (node.metadata.dynamic) {
								node.requestRefreshMetadata(0, true);
							}
						}
					}
				});
			}

			selectedNodesSubmenu[selectedNodesSubmenu.length - 1].divider = true;

			selectedNodesSubmenu.push({
				label: 'Top-Align',
				description: 'Align the top of all selected nodes.',
				callback: () => {
					const topY = selectedNodes.reduce((y, node) => Math.min(y, node.y), Infinity);
					for (const node of selectedNodes) {
						node.y = topY;
					}
				}
			});

			selectedNodesSubmenu.push({
				label: 'Left-Align',
				description: 'Align the left side of all selected nodes.',
				callback: () => {
					const leftX = selectedNodes.reduce((x, node) => Math.min(x, node.x), Infinity);
					for (const node of selectedNodes) {
						node.x = leftX;
					}
				}
			});

			const spaceHorizontal = (amount: number) => {
				const sorted = selectedNodes.sort((a, b) => a.x - b.x);

				let nextX = sorted[0].x + sorted[0].width() + amount;
				for (const node of sorted.slice(1)) {
					node.x = nextX;
					nextX += node.width() + amount;
				}
			};

			const spaceVertical = (amount: number) => {
				const sorted = selectedNodes.sort((a, b) => a.y - b.y);

				let nextY = sorted[0].y + sorted[0].height() + amount;
				for (const node of sorted.slice(1)) {
					node.y = nextY;
					nextY += node.height() + amount;
				}
			};

			selectedNodesSubmenu.push({
				label: 'Space Evenly (Horizontal)',
				description: 'Space selected nodes evenly on the X-axis.',
				submenu: {
					items: [
						{
							label: '25',
							callback: () => spaceHorizontal(25)
						},
						{
							label: '50',
							callback: () => spaceHorizontal(50)
						},
						{
							label: '75',
							callback: () => spaceHorizontal(75)
						},
						{
							label: '100',
							callback: () => spaceHorizontal(100)
						}
					]
				}
			});

			selectedNodesSubmenu.push({
				label: 'Space Evenly (Vertical)',
				description: 'Space selected nodes evenly on the Y-axis.',
				submenu: {
					items: [
						{
							label: '0',
							callback: () => spaceVertical(0)
						},
						{
							label: '25',
							callback: () => spaceVertical(25)
						},
						{
							label: '50',
							callback: () => spaceVertical(50)
						},
						{
							label: '75',
							callback: () => spaceVertical(75)
						},
						{
							label: '100',
							callback: () => spaceVertical(100)
						}
					]
				}
			});

			// Add the main entry for selected nodes

			entries.push({
				label: `Selected Nodes (${selectedNodes.length})`,
				description:
					selectedNodes.length > 1
						? `'${selectedNodes[0].metadata.name}' and ${selectedNodes.length - 1} more...`
						: `'${selectedNodes[0].metadata.name}'`,
				submenu: { items: selectedNodesSubmenu }
			});
		}

		return { items: entries };
	}

	function toggleFullscreen() {
		if (document.fullscreenElement) {
			document.exitFullscreen();
		} else {
			viewportElement.value?.requestFullscreen();
		}
	}

	function onFullscreenChange() {
		isFullscreen.value = !!document.fullscreenElement;
	}

	// Watch for changes in the grabbed edge
	const grabbedSocket = computed(() => props.graph.ui.grabbed.socket);
	const grabbedSocketPositions = ref<{ top: number; right: number; bottom: number; left: number } | null>(null);

	const grabbedEdge: ComputedRef<GraphEdge | null> = computed(() => {
		const grabbedSocket = props.graph.ui.grabbed.socket;
		if (!grabbedSocketPositions.value || !grabbedSocket || editorStore.isResolvingMergeConflict) {
			return null;
		}

		const { top, right, bottom, left } = grabbedSocketPositions.value;

		if (grabbedSocket.metadata.datatype && grabbedSocket.metadata.isInput) {
			return {
				startX: props.graph.ui.cursor.x,
				startY: props.graph.ui.cursor.y,
				endX: left,
				endY: top + (bottom - top) / 2,
				color: metadataStore.getDataType(grabbedSocket.metadata.datatype).color
			};
		}

		if (grabbedSocket.metadata.datatype && !grabbedSocket.metadata.isInput) {
			return {
				startX: right,
				startY: top + (bottom - top) / 2,
				endX: props.graph.ui.cursor.x,
				endY: props.graph.ui.cursor.y,
				color: metadataStore.getDataType(grabbedSocket.metadata.datatype).color
			};
		}

		if (grabbedSocket.metadata.isInput) {
			return {
				startX: props.graph.ui.cursor.x,
				startY: props.graph.ui.cursor.y,
				endX: left,
				endY: top + (bottom - top) / 2,
				color: 'var(--color-editor-link-socket-edge)'
			};
		}

		if (!grabbedSocket.metadata.isInput) {
			return {
				startX: right,
				startY: top + (bottom - top) / 2,
				endX: props.graph.ui.cursor.x,
				endY: props.graph.ui.cursor.y,
				color: 'var(--color-editor-link-socket-edge)'
			};
		}
		return null;
	});

	// Selection area
	const selectionAreaStyles = computed(() => {
		if (editorStore.isResolvingMergeConflict) {
			return {};
		}
		const selectionArea = props.graph.ui.selectionArea;
		if (!selectionArea) {
			return {};
		}

		const dX = props.graph.ui.cursor.x - selectionArea.x;
		const dY = props.graph.ui.cursor.y - selectionArea.y;

		const anchorX = dX >= 0 ? selectionArea.x : props.graph.ui.cursor.x;
		const anchorY = dY >= 0 ? selectionArea.y : props.graph.ui.cursor.y;

		return {
			transform: `translate(${anchorX}px, ${anchorY}px)`,
			width: Math.abs(dX) + 'px',
			height: Math.abs(dY) + 'px'
		};
	});

	// Editor styles
	const scalerStyles = computed(() => {
		return {
			transform: `scale(${props.graph.ui.scale})`
		};
	});

	const editorBackdropStyles = computed(() => {
		return {
			cursor: props.graph.ui.cursor.button === 0 && !props.graph.ui.cursor.keys ? 'grabbing' : 'default'
		};
	});

	const editorBackgroundStyles = computed(() => {
		return {
			transform: `translate(${props.graph.ui.offsets.x % 40}px, ${props.graph.ui.offsets.y % 40}px)`
		};
	});

	const editorContentsStyles = computed(() => {
		return {
			transform: `translate(${props.graph.ui.offsets.x}px, ${props.graph.ui.offsets.y}px)`
		};
	});

	watch(
		grabbedSocket,
		() => {
			const grabbedSocket = props.graph.ui.grabbed.socket;
			if (!grabbedSocket || !grabbedSocket.element) {
				grabbedSocketPositions.value = null;
				return;
			}
			grabbedSocketPositions.value = grabbedSocket.getPositions();
		},
		{ immediate: true }
	);

	/**
	 * Track the nodes to call the graph.onNodesChanged function whenever any node changes its serialized state.
	 */
	const nodesChangedDependencies = computed(() => {
		const deps = Array.from(props.graph.getNodes()).map((n) => n.serialize());
		return deps;
	});

	watch(
		nodesChangedDependencies,
		() => {
			if (minimap.value) {
				minimap.value.requestUpdateMinimap();
			}

			props.graph.onNodesChanged();
		},
		{ deep: true }
	);
</script>

<style scoped>
	.editor-viewport {
		flex: 1 0;
		overflow: clip;
		position: relative;
		background-color: var(--color-foreground-primary);
		border-radius: 10px;
	}

	.editor-scaler {
		width: 100%;
		height: 100%;
		position: absolute;
		top: 0px;
		left: 0px;
		z-index: 1;
		overflow: visible;
		transition: transform 70ms linear;
		transform-origin: center;
	}

	.editor-backdrop {
		width: 1000vw;
		height: 1000vh;
		position: absolute;
		top: -500vh;
		left: -500vw;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.editor-background {
		/** Note: It is slightly more performant to use a dedicated background element, rather than including the background as part of the backdrop */
		width: 1000vw;
		height: 1000vh;
		position: absolute;
		top: -500vh;
		left: -500vw;
		background-image: linear-gradient(var(--color-editor-grid) 2px, transparent 2px),
			linear-gradient(90deg, var(--color-editor-grid) 2px, transparent 2px);
		background-size: 40px 40px, 40px 40px;
		pointer-events: none;
	}

	.editor-contents {
		/** Width and height should be at least the maximum size of a node to allow for proper content flow */
		position: relative;
		width: 100%;
		height: 100%;
		top: 50%;
		left: 50%;
		overflow: visible;
		z-index: 1;
		transform-origin: top left;
	}

	.controls-container {
		padding: 12px 16px;
		position: absolute;
		bottom: 60px;
		right: 60px;
		z-index: 1;
		display: flex;
		flex-direction: row;
		align-items: center;
		background-color: var(--color-editor-controls-background);
		border-radius: 6px;
	}

	.controls-container > *:not(:last-child) {
		margin-right: 10px;
	}

	.zoom-amount {
		color: var(--color-text);
		cursor: pointer;
	}

	.controls-icon {
		font-size: 32px;
		color: var(--color-text);
		opacity: 0.8;
	}

	.controls-icon:hover {
		cursor: pointer;
		opacity: 1;
	}

	.editor-selection-area {
		position: absolute;
		transform-origin: top left;
		outline: 2px dotted var(--color-editor-node-selection-area-border);
		background-color: var(--color-editor-node-selection-area-background);
		z-index: 50;
	}
</style>
