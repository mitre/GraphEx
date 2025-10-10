<template>
	<PromptComponent />
	<GraphRunPrompt v-if="terminalStore.graphToPrompt" v-bind="terminalStore.graphToPrompt" />
	<AboutGraphexModal v-if="promptStore.aboutOpen" />
	<OpenLogModal v-if="promptStore.openLogModalOpen"></OpenLogModal>
	<ContextMenu :ref="(el) => contextmenuStore.setContextMenu('root', el)" />
	<main @contextmenu="onContextMenu">
		<MenuBar />
		<div class="body-view">
			<div class="sidebar-view" :style="sidebarStyles">
				<SidebarComponent ref="sidebar" />
			</div>
			<div class="body-resizer" v-if="!!sidebar?.selectedTab">
				<span
					class="resizer-icon material-icons"
					title="Click and drag to resize"
					@mousedown="onResizeStart('sidebar')"
					horizontal
					>drag_handle</span
				>
			</div>
			<div class="main-view">
				<div class="editor-view">
					<EditorDisplay />
				</div>
				<div class="terminal-resizer" v-if="terminalStore.terminalOpen">
					<span
						class="resizer-icon material-icons"
						title="Click and drag to resize"
						@mousedown="onResizeStart('terminal')"
						>drag_handle</span
					>
				</div>
				<div class="terminal-view" v-if="terminalStore.terminalOpen" :style="terminalStyles">
					<TerminalComponent
						:height-percent="terminalHeightPercent"
						@maximize="maximizeTerminal"
						@shrink="shrinkTerminal"
					/>
				</div>
			</div>
		</div>
		<div v-show="loading" class="main-loading">
			<span class="loader"></span>
			<div class="loading-info">{{ fileStore.activeFileOperations[fileStore.activeFileOperations.length - 1] }}</div>
		</div>
	</main>
</template>

<script setup lang="ts">
	import AboutGraphexModal from '@/components/AboutGraphexModal.vue';
	import ContextMenu from '@/components/ContextMenu.vue';
	import OpenLogModal from '@/components/OpenLogModal.vue';
	import PromptComponent from '@/components/PromptComponent.vue';
	import EditorDisplay from '@/editor/EditorDisplay.vue';
	import MenuBar from '@/menubar/MenuBar.vue';
	import SidebarComponent from '@/sidebar/SidebarComponent.vue';
	import {
		useContextmenuStore,
		useEditorStore,
		useErrorStore,
		useFileStore,
		useMetadataStore,
		usePromptStore,
		useSettingsStore,
		useTerminalStore
	} from '@/stores';
	import GraphRunPrompt from '@/terminal/GraphRunPrompt.vue';
	import TerminalComponent from '@/terminal/TerminalComponent.vue';
	import { computed, onMounted, ref } from 'vue';
	import { NodeTypes } from './graph/node';

	const editorStore = useEditorStore();
	const metadataStore = useMetadataStore();
	const contextmenuStore = useContextmenuStore();
	const promptStore = usePromptStore();
	const terminalStore = useTerminalStore();
	const errorStore = useErrorStore();
	const fileStore = useFileStore();
	const settingsStore = useSettingsStore();

	const sidebar = ref<InstanceType<typeof SidebarComponent> | null>(null);

	/** The target for a resize operation. */
	const resizeTarget = ref<'sidebar' | 'terminal' | null>(null);

	/** Percentage of the available width that the sidebar should occupy (100 = max). */
	const sidebarWidthPercent = ref<number>(15);

	/** Maximum width of the sidebar (percentage) */
	const MAX_SIDEBAR_WIDTH = 75;

	/** Minimum width of the sidebar (percentage) */
	const MIN_SIDEBAR_WIDTH = 10;

	/** Percentage of the available height that the terminal should occupy (100 = max). */
	const terminalHeightPercent = ref<number>(30);

	/** Maximum height of the terminal (percentage) */
	const MAX_TERMINAL_HEIGHT = 90;

	/** Minimum height of the terminal (percentage) */
	const MIN_TERMINAL_HEIGHT = 15;

	const loading = computed(() => {
		return fileStore.activeFileOperations.length > 0;
	});

	onMounted(async () => {
		await metadataStore.update();
		await fileStore.refreshFiles();
		editorStore.newDefaultGraphTab();

		window.onbeforeunload = function (event) {
			// Check if there are any unsaved tabs
			const anyUnsaved = !!editorStore.tabs.find((t) => editorStore.tabHasChanges(t.id));
			if (anyUnsaved) {
				event.preventDefault();
				event.stopImmediatePropagation();
				return true;
			}

			// Close any open sockets before the page unloads (closes/refreshes)
			// This is not strictly necessary, but we'd like to free server resources if possible
			terminalStore.closeAllSockets();
			return void 0;
		};

		window.addEventListener('keydown', onKeyDown);
		terminalStore.discoverGraphs();

		// Update the title
		const response = await fetch('/api/title', { method: 'GET' });
		if (response.ok) {
			const newTitle = await response.text();
			if (newTitle.trim().length) {
				document.title = newTitle;
			}
		}

		// const fpsMeter = () => {
		// 	let prevTime = Date.now();
		// 	let frames = 0;

		// 	requestAnimationFrame(function loop() {
		// 		const time = Date.now();
		// 		frames++;
		// 		if (time > prevTime + 1000) {
		// 			let fps = Math.round((frames * 1000) / (time - prevTime));
		// 			prevTime = time;
		// 			frames = 0;

		// 			console.info('FPS: ', fps);
		// 		}

		// 		requestAnimationFrame(loop);
		// 	});
		// };

		// fpsMeter();
	});

	// Global Key / Event Bindings
	const KEYBINDINGS: { [shorthand: string]: (event: KeyboardEvent) => void } = {
		'Ctrl+Equal': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			if (!editorStore.activeGraphTab) return;
			editorStore.activeGraphTab.contents.ui.zoomIn();
		},
		'Ctrl+Minus': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			if (!editorStore.activeGraphTab) return;
			editorStore.activeGraphTab.contents.ui.zoomOut();
		},
		ArrowRight: (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveX(-20, 10);
		},
		'Shift+ArrowRight': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveX(-50, 25);
		},
		ArrowLeft: (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveX(20, -10);
		},
		'Shift+ArrowLeft': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveX(50, -25);
		},
		ArrowUp: (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveY(20, -10);
		},
		'Shift+ArrowUp': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveY(50, -25);
		},
		ArrowDown: (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveY(-20, 10);
		},
		'Shift+ArrowDown': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			moveY(-50, 25);
		},
		'Ctrl+KeyS': async (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			const activeTab = editorStore.activeTab;
			if (activeTab) {
				editorStore.saveTab(activeTab.id);
			}
		},
		'Ctrl+Shift+KeyS': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			const activeTab = editorStore.activeTab;
			if (activeTab) {
				editorStore.exportTabContents(activeTab.id);
			}
		},
		'Ctrl+Shift+KeyN': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			editorStore.newDefaultGraphTab();
		},
		'Ctrl+KeyO': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			editorStore.promptOpenFiles();
		},
		'Ctrl+KeyL': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			promptStore.openLogModalOpen = true;
		},
		'Ctrl+KeyI': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			fileStore.refreshFiles();
		},
		'Ctrl+KeyA': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			editorStore.activeGraphTab.contents.ui.selectAllNodes();
		},
		'Alt+KeyA': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			editorStore.activeGraphTab.contents.ui.deselectAllNodes();
		},
		'Alt+KeyR': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			if (errorStore.graphHasErrors(editorStore.activeGraphTab.id)) {
				return;
			}

			let filepath = null;
			if (editorStore.activeGraphTab.fileId) {
				filepath = fileStore.getFilePath(editorStore.activeGraphTab.fileId) || null;
			}

			terminalStore.promptGraphExecution(
				editorStore.activeGraphTab.contents,
				editorStore.activeGraphTab.name,
				filepath
			);
		},
		'Alt+KeyS': (event: KeyboardEvent) => {
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			if (!terminalStore.terminalOpen) {
				return;
			}

			const contextId = terminalStore.selectedTerminalTabId;
			if (!contextId) {
				return;
			}

			const context = terminalStore.getExecutionContextById(contextId);
			if (!context) {
				return;
			}

			if (context.connected) {
				return;
			}

			terminalStore.stopExecutingGraph(context.id);
		},
		'Alt+KeyM': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			settingsStore.toggleMinimap();
		},
		'Ctrl+KeyX': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			if (!editorStore.activeGraphTab.contents.ui.selectedNodes.length) {
				return;
			}

			editorStore.storeCopiedNodes(editorStore.activeGraphTab.contents.ui.selectedNodes);
			editorStore.activeGraphTab.contents.deleteNodes(editorStore.activeGraphTab.contents.ui.selectedNodes);
		},
		'Ctrl+KeyC': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			if (!editorStore.activeGraphTab.contents.ui.selectedNodes.length) {
				return;
			}

			editorStore.storeCopiedNodes(editorStore.activeGraphTab.contents.ui.selectedNodes);
		},
		'Ctrl+KeyV': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			if (!editorStore.copiedNodes.length) {
				return;
			}

			const graph = editorStore.activeGraphTab.contents;
			const ui = graph.ui;
			const viewportPositions = ui.viewportPositions();
			const width = viewportPositions.right - viewportPositions.left;
			const height = viewportPositions.bottom - viewportPositions.top;

			const addedNodes = graph.addNodeStates(editorStore.copiedNodes, {
				x: -1 * ui.offsets.x + width / 2,
				y: -1 * ui.offsets.y + height / 2,
				center: true,
				connect: 'group'
			});

			// Select the added nodes
			ui.deselectAllNodes();
			for (const addedNode of addedNodes) {
				ui.selectNode(addedNode);
			}
		},
		Delete: (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			if (editorStore.isResolvingMergeConflict) return;
			if (!editorStore.activeGraphTab.contents.ui.selectedNodes.length) {
				return;
			}

			editorStore.activeGraphTab.contents.deleteNodes(editorStore.activeGraphTab.contents.ui.selectedNodes);
		},
		'Ctrl+KeyF': (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			event.preventDefault();
			event.stopPropagation();
			sidebar.value?.selectTab('graphSearch');
		},
		'Ctrl+KeyZ': async (event: KeyboardEvent) => {
			if (editorStore.isResolvingMergeConflict) return;
			if (!editorStore.activeGraphTab) return;
			if (!editorStore.activeGraphTab.contents.history.hasUndoHistory()) return;

			event.preventDefault();
			event.stopPropagation();
			await editorStore.activeGraphTab.contents.history.undo();
		},
		'Ctrl+KeyY': async (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			if (editorStore.isResolvingMergeConflict) return;
			event.preventDefault();
			event.stopPropagation();
			await editorStore.activeGraphTab.contents.history.redo();
		},
		'Ctrl+Slash': async (event: KeyboardEvent) => {
			if (!editorStore.activeGraphTab) return;
			if (editorStore.isResolvingMergeConflict) return;
			event.preventDefault();
			event.stopPropagation();

			const selectedNodes = editorStore.activeGraphTab.contents.ui.selectedNodes;

			if (selectedNodes.length < 1) {
				return;
			} else if (selectedNodes.length == 1) {
				// one node is selected
				const node = selectedNodes[0];
				if (node.metadata.type != NodeTypes.COMMENT) {
					editorStore.replaceNodeWithCommentSingular(node);
				} else if (
					node.fieldValue &&
					typeof node.fieldValue === 'string' &&
					node.fieldValue.startsWith('### COMMENTED NODE ###')
				) {
					editorStore.replaceCommentWithNodeSingular(node);
				}
			} else {
				// multiple nodes are selected
				// This "toggle" will match the functionality in VS code, i.e.:
				// If all selected lines are uncommented: comment all lines
				// If all selected lines are commented: uncomment all lines
				// If there is a mixture of comments and uncomments: comment everything and ignore existing comments
				// We can simplify the problem like this:
				// If any non-comment nodes are found in the selection, then we run the comment all code block
				// Otherwise, everything is a comment in the selection and we can run the uncomment all code block
				let existingNonCommentNode = false;
				for (const node of selectedNodes) {
					if (node.metadata.type != NodeTypes.COMMENT) {
						existingNonCommentNode = true;
						break;
					}
				}
				if (existingNonCommentNode) {
					// at least one node in the selection isn't a comment
					editorStore.replaceMultipleNodesWithComments(selectedNodes, selectedNodes[0].graph);
				} else {
					// all the nodes are already comments
					editorStore.replaceMultipleCommentsWithNodes(selectedNodes, selectedNodes[0].graph);
				}
			}
		}
	};

	function onKeyDown(event: KeyboardEvent) {
		if (loading.value) {
			// Disable keybindings when loading
			event.preventDefault();
			event.stopPropagation();
			return;
		}

		const keys: Array<string> = [];
		if (event.altKey) keys.push('Alt');
		if (event.ctrlKey) keys.push('Ctrl');
		if (event.metaKey) keys.push('Meta');
		if (event.shiftKey) keys.push('Shift');

		if (event.key != 'Alt' && event.key != 'Control' && event.key != 'Meta' && event.key != 'Shift') {
			keys.push(event.code); // See https://www.toptal.com/developers/keycode
		}

		const shorthand = keys.join('+');

		// Overrides
		if (shorthand == 'Ctrl+KeyC' && !window.getSelection()?.isCollapsed && window.getSelection()?.toString() !== '') {
			return; // Allow default for copy
		}

		// Handle key binding
		if (shorthand in KEYBINDINGS) {
			KEYBINDINGS[shorthand](event);
			return;
		}
	}

	function onContextMenu(event: MouseEvent) {
		event.stopPropagation();

		if (event.ctrlKey && event.altKey) {
			// Allow for normal context menu when ctrl+alt is held down
			return;
		}

		event.preventDefault();
	}

	function moveX(editorAmount: number, nodeAmount: number) {
		const activeGraph = editorStore.activeGraphTab?.contents;
		if (!activeGraph) {
			return;
		}

		if (activeGraph.ui.selectedNodes.length) {
			// Move selected nodes
			for (const node of activeGraph.ui.selectedNodes) {
				node.x += nodeAmount;
			}

			return;
		}

		// Move the editor viewport
		activeGraph.ui.offsets.x += editorAmount / activeGraph.ui.scale;
	}

	function moveY(editorAmount: number, nodeAmount: number) {
		const activeGraph = editorStore.activeGraphTab?.contents;
		if (!activeGraph) {
			return;
		}

		if (activeGraph.ui.selectedNodes.length) {
			// Move selected nodes
			for (const node of activeGraph.ui.selectedNodes) {
				node.y += nodeAmount;
			}

			return;
		}

		// Move the editor viewport
		activeGraph.ui.offsets.y += editorAmount / activeGraph.ui.scale;
	}

	function onResizeStart(target: 'sidebar' | 'terminal') {
		resizeTarget.value = target;
		document.addEventListener('mouseup', onResizeEnd);
		document.addEventListener('mousemove', onSidebarResize);
	}

	function onSidebarResize(e: MouseEvent) {
		if (resizeTarget.value == 'sidebar') {
			const newPosition = sidebarWidthPercent.value + (100 * e.movementX) / window.innerWidth;
			sidebarWidthPercent.value = Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, newPosition));
		}

		if (resizeTarget.value == 'terminal') {
			const newPosition = terminalHeightPercent.value + (100 * (-1 * e.movementY)) / window.innerHeight;
			terminalHeightPercent.value = Math.min(MAX_TERMINAL_HEIGHT, Math.max(MIN_TERMINAL_HEIGHT, newPosition));
		}
	}

	function onResizeEnd() {
		resizeTarget.value = null;
		document.removeEventListener('mouseup', onResizeEnd);
		document.removeEventListener('mousemove', onSidebarResize);
	}

	function maximizeTerminal() {
		terminalHeightPercent.value = MAX_TERMINAL_HEIGHT;
	}

	function shrinkTerminal() {
		terminalHeightPercent.value = MIN_TERMINAL_HEIGHT;
	}

	const sidebarStyles = computed(() => {
		if (sidebar.value?.selectedTab !== null) {
			return {
				width: sidebarWidthPercent.value + '%'
			};
		}

		return {};
	});

	const terminalStyles = computed(() => {
		return {
			height: terminalHeightPercent.value + '%'
		};
	});
</script>

<style>
	.material-icons {
		-webkit-user-select: none;
		-ms-user-select: none;
		user-select: none;
	}

	.no-select {
		-webkit-user-select: none;
		-ms-user-select: none;
		user-select: none;
	}

	:root {
		/** Main palette */
		--color-background-primary: rgb(14, 19, 21);

		--color-foreground-primary: rgb(22, 29, 33);
		--color-foreground-secondary: rgb(32, 42, 46);
		--color-foreground-tertiary: rgb(50, 65, 70);
		--color-border: rgb(61, 79, 88);
		--color-border-highlight: rgb(82, 104, 116);

		--color-text: rgb(230, 230, 230);
		--color-text-secondary: rgb(179, 179, 179);

		--color-primary: rgb(138, 228, 255);
		--color-warning: rgb(255, 185, 15);
		--color-error: rgb(175, 15, 15);

		--color-button-text: rgb(255, 255, 255);
		--color-button-primary: rgb(11, 85, 145);
		--color-button-primary-hover: rgb(21, 105, 173);
		--color-button-secondary: rgb(57, 63, 70);
		--color-button-secondary-hover: rgb(68, 75, 83);
		--color-button-warning: rgb(92, 23, 11);
		--color-button-warning-hover: rgb(119, 30, 15);
		--color-button-disabled: rgb(41, 46, 51);
		--color-button-disabled-text: rgb(130, 130, 130);

		/** Editor palette */
		--color-editor-grid: rgb(31, 40, 44);
		--color-editor-controls-background: rgba(255, 255, 255, 0.08);

		--color-editor-node-background-primary: rgb(8, 13, 15);
		--color-editor-node-background-secondary: rgb(20, 28, 32);
		--color-editor-node-title-text: rgb(230, 230, 230);
		--color-editor-node-body-text-primary: rgb(179, 211, 233);
		--color-editor-node-body-text-secondary: rgb(118, 131, 139);
		--color-editor-node-box-shadow: rgba(0, 0, 0, 0.4);
		--color-editor-node-selected: rgb(255, 255, 100);
		--color-editor-node-highlight: rgb(138, 228, 255);
		--color-editor-node-selection-area-border: rgba(255, 255, 255, 0.7);
		--color-editor-node-selection-area-background: rgba(255, 255, 255, 0.02);

		--color-editor-socket-background: rgb(20, 28, 32);
		--color-editor-socket-text: rgb(125, 155, 175);
		--color-editor-socket-text-error: rgb(189, 47, 28);

		--color-editor-link-socket-edge: rgb(255, 255, 255);

		--color-editor-text-input-background: rgb(12, 17, 19);
		--color-editor-text-input-border: rgb(31, 36, 39);
		--color-editor-text-input-border-highlight: rgb(70, 85, 95);
		--color-editor-text-input-error: rgb(136, 18, 18);

		/* Terminal */
		--color-component-terminal-text-critical: rgb(255, 0, 0);
		--color-component-terminal-text-error: rgb(255, 50, 50);
		--color-component-terminal-text-warning: rgb(255, 255, 0);
		--color-component-terminal-text-notice: rgb(0, 220, 255);
		--color-component-terminal-text-info: rgb(220, 220, 220);
		--color-component-terminal-text-debug: rgb(230, 80, 245);
		--color-component-terminal-text-control: rgb(150, 150, 150);
		--color-component-terminal-text-hyperlink: rgb(100, 172, 230);
		--color-component-terminal-text-errorlink: rgb(255, 165, 0);
		--color-component-terminal-text-image: rgb(50, 225, 50);

		--color-component-terminal-background: rgb(6, 9, 10);
		--color-component-terminal-border: rgb(32, 42, 46);
		--color-component-terminal-status-done: rgb(0, 200, 0);
		--color-component-terminal-status-running: rgb(0, 200, 0);
		--color-component-terminal-status-idle: grey;

		/* Text Editor */
		--color-component-text-editor-text: rgb(230, 230, 230);
		--color-component-text-editor-caret: rgb(179, 179, 179);
		--color-component-text-editor-gutter-text: rgb(100, 120, 125);
		--color-component-text-editor-selection: rgba(138, 228, 255, 0.2);
		--color-component-text-editor-search-match: rgba(138, 228, 255, 0.3);
		--color-component-text-editor-search-match-selected: rgb(138, 228, 255);
		--color-component-text-editor-active-line: rgba(138, 228, 255, 0.05);

		--color-component-text-editor-syntax-keyword: rgb(105, 220, 240);
		--color-component-text-editor-syntax-punctuation: rgb(30, 160, 255);
		--color-component-text-editor-syntax-operator: rgb(250, 40, 115);
		--color-component-text-editor-syntax-typeName: rgb(255, 150, 30);
		--color-component-text-editor-syntax-variableName: rgb(255, 150, 30);
		--color-component-text-editor-syntax-atom: rgb(255, 150, 30);
		--color-component-text-editor-syntax-meta: rgb(165, 225, 50);
		--color-component-text-editor-syntax-className: rgb(165, 225, 50);
		--color-component-text-editor-syntax-string: rgb(230, 220, 115);
		--color-component-text-editor-syntax-bool: rgb(175, 130, 255);
		--color-component-text-editor-syntax-number: rgb(175, 130, 255);
		--color-component-text-editor-syntax-comment: rgb(100, 100, 90);

		/* Sidebar */
		--color-component-sidebar-searchbar: rgb(14, 19, 21);
		--color-component-sidebar-searchbar-border: rgba(0, 0, 0, 0);
		--color-component-sidebar-nodes-favorite-star-icon-favorited: rgb(255, 255, 0);
		--color-component-sidebar-variables-no-setter: rgb(189, 47, 28);
		--color-component-sidebar-variables-empty-setter: rgb(222, 222, 0);
		--color-component-sidebar-variables-connected: rgb(145, 255, 145);
	}

	.custom-scrollbar {
		scrollbar-color: var(--color-foreground-tertiary) transparent;
		scrollbar-width: thin;
	}

	.custom-scrollbar::-webkit-scrollbar {
		width: 6px;
		height: 6px;
		background-color: transparent;
	}

	.custom-scrollbar::-webkit-scrollbar-thumb {
		background-color: var(--color-foreground-tertiary);
	}

	*,
	*::before,
	*::after {
		margin: 0;
		padding: 0;
		box-sizing: border-box;
		outline: none;
	}

	body {
		width: 100vw;
		min-width: 100vw;
		height: 100vh;
		min-height: 100vh;
		color: var(--color-text);
		background: var(--color-background-primary);
		font-family: 'Roboto';
		font-size: 16px;
		text-rendering: optimizeLegibility;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
	}

	input,
	textarea {
		font-family: 'Roboto';
		font-size: 1rem;
		outline: none;
	}

	#app {
		width: 100%;
		height: 100%;
		overflow: hidden;
	}

	.logo {
		width: 1rem;
		height: 1rem;
		background-image: url('/logo.png');
		background-position: center;
		background-repeat: no-repeat;
		background-size: 100% 100%;
	}
</style>

<style scoped>
	main {
		width: 100%;
		height: 100%;
		padding: 10px 20px 20px 20px;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.body-view {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		overflow: hidden;
	}

	.body-resizer {
		height: 100%;
		width: 12px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}

	.terminal-resizer {
		height: 12px;
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
	}

	.resizer-icon {
		cursor: ns-resize;
		color: var(--color-text);
		font-size: 1rem;
		opacity: 0.3;
	}

	.resizer-icon[horizontal] {
		cursor: ew-resize;
		transform: rotate(90deg);
	}

	.sidebar-view {
		height: 100%;
		display: flex;
		overflow: hidden;
	}

	.main-view {
		flex: 1 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.editor-view {
		display: flex;
		flex: 1 0;
		overflow: hidden;
	}

	.terminal-view {
		overflow: hidden;
	}

	.main-loading {
		position: fixed;
		top: 0px;
		left: 0px;
		z-index: 999;
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		background-color: rgba(0, 0, 0, 0.2);
	}

	.loader {
		transform: rotateZ(45deg);
		perspective: 1000px;
		border-radius: 50%;
		width: 84px;
		height: 84px;
		color: rgb(255, 255, 255);
	}

	.loader:before,
	.loader:after {
		content: '';
		display: block;
		position: absolute;
		top: 0;
		left: 0;
		width: inherit;
		height: inherit;
		border-radius: 50%;
		transform: rotateX(70deg);
		animation: 1.2s spin linear infinite;
	}

	.loader:after {
		color: var(--color-primary);
		transform: rotateY(70deg);
		animation-delay: -0.8s;
	}

	@keyframes rotate {
		0% {
			transform: translate(-50%, -50%) rotateZ(0deg);
		}
		100% {
			transform: translate(-50%, -50%) rotateZ(360deg);
		}
	}

	@keyframes rotateccw {
		0% {
			transform: translate(-50%, -50%) rotate(0deg);
		}
		100% {
			transform: translate(-50%, -50%) rotate(-360deg);
		}
	}

	@keyframes spin {
		0%,
		100% {
			box-shadow: 0.2em 0px 0 0px currentcolor;
		}
		12% {
			box-shadow: 0.2em 0.2em 0 0 currentcolor;
		}
		25% {
			box-shadow: 0 0.2em 0 0px currentcolor;
		}
		37% {
			box-shadow: -0.2em 0.2em 0 0 currentcolor;
		}
		50% {
			box-shadow: -0.2em 0 0 0 currentcolor;
		}
		62% {
			box-shadow: -0.2em -0.2em 0 0 currentcolor;
		}
		75% {
			box-shadow: 0px -0.2em 0 0 currentcolor;
		}
		87% {
			box-shadow: 0.2em -0.2em 0 0 currentcolor;
		}
	}

	.loading-info {
		margin-top: 30px;
		font-size: 1.2rem;
		letter-spacing: 1px;
	}
</style>
