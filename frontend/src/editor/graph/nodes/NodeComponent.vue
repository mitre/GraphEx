<template>
	<div
		class="node-container"
		@mousedown="onMouseDown"
		@click.stop.prevent="onClick"
		@dblclick.stop.prevent="onDoubleClick"
		:style="nodeContainerStyles"
		:loading="props.node.isLoading"
		:error="hasErrors"
		:selected="isSelected"
		:highlighted="isHighlighted"
		:isvisible="isVisible"
		:isdisabled="props.disabled ?? false"
		ref="element"
		tabindex="0"
	>
		<ActionNodeComponent
			v-if="props.node.metadata.type == NodeTypes.ACTION"
			:node="props.node"
			:tab-id="tabId"
			:disabled="props.disabled"
		/>
		<DataNodeComponent v-else-if="props.node.metadata.type == NodeTypes.DATA" :node="props.node" :tab-id="tabId" />
		<CastNodeComponent v-else-if="props.node.metadata.type == NodeTypes.CAST" :node="props.node" :tab-id="tabId" />
		<InventoryNodeComponent
			v-else-if="props.node.metadata.type == NodeTypes.GENERATOR && props.node.metadata.isInventoryNode"
			:node="props.node"
			:tab-id="tabId"
		/>
		<GeneratorNodeComponent
			v-else-if="props.node.metadata.type == NodeTypes.GENERATOR"
			:node="props.node"
			:tab-id="tabId"
		/>
		<CommentNodeComponent
			v-else-if="props.node.metadata.type == NodeTypes.COMMENT"
			:node="props.node"
			:disabled="props.disabled"
		/>

		<div v-if="isHighlighted" class="node-highlight"><div class="node-highlight-inner"></div></div>
		<div v-if="hasErrors && !props.node.isLoading" class="node-error"></div>
		<span v-if="props.node.isLoading" class="node-loader"></span>
	</div>
</template>

<script setup lang="ts">
	import { NodeTypes, type GraphNode, type Socket } from '@/graph';
import {
	GRAPH_FILE_EXTENSION,
	useContextmenuStore,
	useEditorStore,
	useErrorStore,
	useFileStore,
	usePromptStore
} from '@/stores';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import ActionNodeComponent from '@/editor/graph/nodes/ActionNodeComponent.vue';
import CastNodeComponent from '@/editor/graph/nodes/CastNodeComponent.vue';
import CommentNodeComponent from '@/editor/graph/nodes/CommentNodeComponent.vue';
import DataNodeComponent from '@/editor/graph/nodes/DataNodeComponent.vue';
import GeneratorNodeComponent from '@/editor/graph/nodes/GeneratorNodeComponent.vue';
import InventoryNodeComponent from './InventoryNodeComponent.vue';

	const props = defineProps<{
		node: GraphNode;
		tabId: string;
		disabled?: boolean;
	}>();

	const contextmenuStore = useContextmenuStore();
	const editorStore = useEditorStore();
	const errorStore = useErrorStore();
	const fileStore = useFileStore();
	const promptStore = usePromptStore();

	const element = ref<HTMLDivElement>();

	const observer = ref<IntersectionObserver>();
	const isVisible = ref<boolean>(true);

	const activeGraph = computed(() => (editorStore.activeGraphTab ? editorStore.activeGraphTab.contents : null));

	onMounted(async () => {
		props.node.setElement(element.value);
		contextmenuStore.getContextMenu(props.tabId).addHook(element.value!, openContextMenu, false);

		// Set up an IntersectionObserver to hide the node when it's not visible
		// This provides a minor performace improvement
		await nextTick(); // Viewport may not be available yet. Adding a nextTick guarantees it will be
		observer.value = new IntersectionObserver(
			(entries: Array<IntersectionObserverEntry>) => {
				const entry = entries[0];
				if (entry.isIntersecting) {
					isVisible.value = true;
				} else {
					isVisible.value = false;
				}
			},
			{ root: props.node.graph.ui.viewportElement, rootMargin: '25%' }
		);

		observer.value.observe(element.value!);

		// Handle duplicate start nodes in a single graph
		if (props.node.metadata.name === "Graph Start") {
			for (const node of activeGraph.value!.getNodes())  {
				if (node.metadata.name === "Graph Start" && node.id != props.node.id) {
					errorStore.addError(props.tabId, props.node.id, 'Node Itself', "Graph can only contain one 'Graph Start' node");
				}
			}
		}
	});

	onBeforeUnmount(() => {
		const thisId = props.node.id;
		const thisTabId = props.tabId;
		clearTimeout(props.node.refreshTimeout);
		observer.value?.disconnect();
		errorStore.removeError(props.tabId, props.node.id, 'Node Itself');
		// handle cleanup when the user deletes original Graph Start nodes instead of the newer duplicate
		if (props.node.metadata.name === "Graph Start" && activeGraph && activeGraph.value) {
			const otherIds = [];
			for (const node of activeGraph.value.getNodes()) {
				if (node.metadata.name === "Graph Start" && node.id != thisId) {
					otherIds.push(node.id);
				}
			}
			if (otherIds.length == 1) {
				errorStore.removeError(thisTabId, otherIds[0], 'Node Itself');
			}
		}
	});

	function onMouseDown(event: MouseEvent) {
		if (editorStore.isResolvingMergeConflict) {
			return;
		}
		if (event.button != 0) {
			return;
		}

		if (event.shiftKey) {
			props.node.graph.ui.toggleNodeSelection(props.node);
		} else {
			props.node.graph.ui.grabNode(props.node);
		}
	}

	function onClick() {
		if (editorStore.isResolvingMergeConflict) {
			return;
		}
		const grabbedSocket = props.node.graph.ui.grabbed.socket;
		if (grabbedSocket) {
			// There is a grabbed socket while this node was clicked
			// See if any data types match on this node that we can auto-connect this socket to
			// This must be unambiguous. If there are more than one candidates, we do nothing.
			let baseSockets = grabbedSocket.metadata.isInput ? props.node.outputSockets : props.node.inputSockets;

			let candidateSockets: Array<Socket> = [];
			for (const socket of baseSockets) {
				try {
					grabbedSocket.connect(socket, { autoAddCastNode: true, dryRun: true });
					candidateSockets.push(socket);
				} catch (e) {
					// Skip
				}
			}

			if (candidateSockets.length == 1) {
				// Found a validate unambiguous socket
				// Try to connect it
				grabbedSocket.connect(candidateSockets[0], { autoAddCastNode: true });
				props.node.graph.ui.grabSocket(null);
				return;
			}
		}
	}

	function onDoubleClick(event: MouseEvent) {
		if (editorStore.isResolvingMergeConflict) {
			return;
		}
		if (event.button == 0) {
			props.node.graph.ui.toggleNodeSelection(props.node);
		}
	}

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		if (isSelected.value) {
			entries.push({
				label: 'De-select Node',
				description: 'De-select this node (Shift+Click or Double Click)',
				callback: () => {
					props.node.graph.ui.deselectNode(props.node);
				}
			});
		} else {
			entries.push({
				label: 'Select Node',
				description: 'Select this node (Shift+Click or Double Click)',
				callback: () => {
					props.node.graph.ui.selectNode(props.node);
				}
			});
		}

		entries.push({
			label: 'Cut',
			description: 'Cut (Copy & Delete) this node',
			callback: () => {
				editorStore.storeCopiedNodes([props.node]);
				props.node.graph.deleteNodes([props.node]);
			}
		});

		entries.push({
			label: 'Copy',
			description: 'Copy this node',
			callback: () => {
				editorStore.storeCopiedNodes([props.node]);
			}
		});

		entries.push({
			label: 'Delete',
			description: 'Delete this node',
			callback: () => {
				props.node.graph.deleteNodes([props.node]);
			},
			divider: true
		});

		if (props.node.metadata.type != NodeTypes.COMMENT) {
			entries.push({
				label: 'Replace with Comment',
				description: 'Replaces this node with a comment',
				callback: () => {
					editorStore.replaceNodeWithCommentSingular(props.node);
				},
				divider: true
			});
		} else if (
			props.node.fieldValue &&
			typeof props.node.fieldValue === 'string' &&
			props.node.fieldValue.startsWith('### COMMENTED NODE ###')
		) {
			// is a commented out Comment Node
			entries.push({
				label: 'Uncomment',
				description: 'Attempts to recreate the node commented out',
				callback: () => {
					editorStore.replaceCommentWithNodeSingular(props.node);
				},
				divider: true
			});
		}

		entries.push({
			label: 'Duplicate',
			description: 'Duplicate this node',
			callback: () => {
				props.node.graph.addNodeStates([props.node.getStateObject()], {
					x: props.node.x + props.node.width() + 50,
					y: props.node.y
				});
			}
		});

		if (props.node.metadata.type != NodeTypes.COMMENT) {
			entries.push({
				label: 'Clear Connections',
				description: "Clear this node's connections",
				callback: () => {
					props.node.clearConnections();
				},
				divider: !props.node.metadata.dynamic
			});
		}

		if (props.node.metadata.dynamic) {
			entries.push({
				label: 'Refresh',
				description: 'Refresh this node',
				callback: () => {
					props.node.requestRefreshMetadata(0, true);
				}
			});
		}

		entries[entries.length - 1].divider = true;

		if (props.node.metadata.type != NodeTypes.COMMENT) {
			entries.push({
				label: 'Select Nodes Before',
				description: 'Select all nodes connected to the left of this node.',
				callback: () => {
					props.node.graph.ui.deselectAllNodes();
					const remaining = [props.node];
					while (remaining.length) {
						const node = remaining.shift();
						if (!node) break;
						if (props.node.graph.ui.selectedNodes.includes(node)) continue;
						props.node.graph.ui.selectNode(node);
						for (const inputSocket of node.inputSockets) {
							for (const target of inputSocket.connections) {
								remaining.push(target.node);
							}
						}
					}
				}
			});

			entries.push({
				label: 'Select Nodes After',
				description: 'Select all nodes connected to the right of this node.',
				callback: () => {
					props.node.graph.ui.deselectAllNodes();
					const remaining = [props.node];
					while (remaining.length) {
						const node = remaining.shift();
						if (!node) break;
						if (props.node.graph.ui.selectedNodes.includes(node)) continue;
						props.node.graph.ui.selectNode(node);
						for (const outputSocket of node.outputSockets) {
							for (const target of outputSocket.connections) {
								remaining.push(target.node);
							}
						}

						if (node !== props.node) {
							for (const inputSocket of node.inputSockets) {
								for (const target of inputSocket.connections) {
									if (target.node.metadata.type == NodeTypes.ACTION) continue;
									remaining.push(target.node);
								}
							}
						}
					}
				}
			});
		}

		if (
			props.node.metadata.dynamic &&
			props.node.metadata.name == 'Execute Graph' &&
			(!props.node.metadata.error ||
				(!props.node.metadata.error.toLowerCase().includes('is not a file accessible by graphex') &&
					!props.node.metadata.error.toLowerCase().includes('no graph file path provided')))
		) {
			entries[entries.length - 1].divider = true;
			entries.push({
				label: 'Open GX File',
				description: 'Open the file associated with this node',
				callback: async () => {
					await fileStore.refreshFiles();

					let filepath: string = String(props.node.fieldValue || '');
					if (!filepath.endsWith(GRAPH_FILE_EXTENSION)) filepath += GRAPH_FILE_EXTENSION;

					const file = fileStore.findFileByPath(filepath);
					if (!file) {
						promptStore.failedAlert(
							'File Open Failure',
							'Failed to find file from path "' + filepath + '" (file does not exist).'
						);
						return;
					}
					await editorStore.openFileInEditor(file.id);
				}
			});
		}

		return { items: entries };
	}

	const isSelected = computed(() => {
		return props.node.graph.ui.selectedNodes.includes(props.node);
	});

	const isHighlighted = computed(() => {
		return props.node.graph.ui.highlightedNodes.includes(props.node);
	});

	const nodeContainerStyles = computed(() => {
		const transform = `translate(${props.node.x}px, ${props.node.y}px)`;
		return {
			transform: transform
		};
	});

	const nodeError = computed(() => {
		return props.node.metadata.error;
	});

	const hasErrors = computed(() => {
		if (nodeError.value && nodeError.value.trim() != '') {
			return true;
		}

		if (!(props.tabId in errorStore.errorMap)) {
			return false;
		}

		return props.node.id in errorStore.errorMap[props.tabId];
	});

	watch(
		nodeError,
		() => {
			if (nodeError.value && nodeError.value.trim() != '') {
				errorStore.addError(props.tabId, props.node.id, 'Node Itself', nodeError.value);
			} else {
				errorStore.removeError(props.tabId, props.node.id, 'Node Itself');
			}
		},
		{ immediate: true }
	);

	// *****************
	// Refresh Handling
	// ******************
	const refreshDependencies = computed(() => {
		return props.node.getRefreshDependencies();
	});

	function requestRefresh() {
		props.node.requestRefreshMetadata();
	}

	watch(refreshDependencies, () => {
		const activeElement = document.activeElement;
		if (activeElement && (activeElement instanceof HTMLTextAreaElement || activeElement instanceof HTMLInputElement)) {
			// Do not refresh while the active element is a textarea/input
			// Instead, wait for the element to lose focus and then refresh
			// Note: Calling addEventListener multiple times with the same handler does not add it multiple times
			activeElement.addEventListener('blur', requestRefresh, { once: true });
			return;
		}

		requestRefresh();
	});
</script>

<style scoped>
	.node-container {
		position: absolute;
		z-index: 10;
		cursor: pointer;
		border-color: var(--color-editor-node-background-primary);
	}

	.node-container[isvisible='false'] {
		/* 
		* When the node is not visible, the best we can do is set 'visiblity: hidden' to improve performance.
		* Using 'display: none' would likely better improve performance, but it would also destroy the formatting of the graph.
		*/
		visibility: hidden;
	}

	.node-container[loading='true'] {
		cursor: wait;
	}

	.node-container[isdisabled='true'] {
		cursor: default;
	}

	.node-container[selected='true'] {
		outline: 2px dashed var(--color-editor-node-selected);
		outline-offset: 4px;
	}

	.node-container[selected='true'][error='true'] {
		outline: 2px dashed var(--color-error);
		outline-offset: 4px;
	}

	.node-container:focus {
		z-index: 11;
	}

	.node-highlight {
		width: 100%;
		height: 100%;
		display: flex;
		position: absolute;
		top: 0px;
		left: 0px;
		z-index: 15;
		outline: 2px solid var(--color-editor-node-highlight);
		opacity: 0.5;
	}

	.node-highlight-inner {
		width: 100%;
		height: 100%;
		background-color: var(--color-editor-node-highlight);
		opacity: 0.1;
	}

	.node-loader {
		position: absolute;
		top: 6px;
		left: 16px;
		z-index: 16;
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background-color: #fff;
		box-shadow: 8px 0 #fff, -8px 0 #fff;
		animation: flash 0.7s ease-out infinite alternate;
	}

	@keyframes flash {
		0% {
			background-color: #fff2;
			box-shadow: 8px 0 #fff2, -8px 0 #fff;
		}
		50% {
			background-color: #fff;
			box-shadow: 8px 0 #fff2, -8px 0 #fff2;
		}
		100% {
			background-color: #fff2;
			box-shadow: 8px 0 #fff, -8px 0 #fff2;
		}
	}

	.node-error {
		width: calc(100% + 12px);
		height: calc(100% + 12px);
		display: flex;
		position: absolute;
		top: -6px;
		left: -6px;
		z-index: 16;
		pointer-events: none;

		background: linear-gradient(to right, var(--color-error) 3px, transparent 3px) 0 0,
			linear-gradient(to right, var(--color-error) 3px, transparent 3px) 0 100%,
			linear-gradient(to left, var(--color-error) 3px, transparent 3px) 100% 0,
			linear-gradient(to left, var(--color-error) 3px, transparent 3px) 100% 100%,
			linear-gradient(to bottom, var(--color-error) 3px, transparent 3px) 0 0,
			linear-gradient(to bottom, var(--color-error) 3px, transparent 3px) 100% 0,
			linear-gradient(to top, var(--color-error) 3px, transparent 3px) 0 100%,
			linear-gradient(to top, var(--color-error) 3px, transparent 3px) 100% 100%;

		background-repeat: no-repeat;
		background-size: 20px 20px;
		animation: errorBlink 0.8s infinite alternate;
	}

	.node-container[selected='true'] .node-error {
		display: none;
	}

	@keyframes errorBlink {
		from {
			opacity: 1;
		}
		to {
			opacity: 0.5;
		}
	}
</style>
