<template>
	<div class="menu-bar">
		<div class="logo menu-logo"></div>

		<div class="menu-bar-entries">
			<template v-for="entry in entries" :key="entry.name">
				<MenuBarEntry v-bind="entry" />
			</template>
		</div>

		<span
			v-if="!terminalStore.mainSocketOk"
			class="material-icons server-disconnected"
			title="ERROR: No connection to server!"
			>wifi_off</span
		>
		<span v-if="terminalStore.activeVenv" class="venv-info" title="The current python virtual environment in use"
			>({{ terminalStore.activeVenv }})
		</span>
		<span v-if="terminalStore.activeGitBranch" class="git-info" title="The current git branch being served">{{
			terminalStore.activeGitBranch
		}}</span>
		<span>
			{{ terminalStore.currentTime }}
		</span>
	</div>
</template>

<script setup lang="ts">
	import { LANGUAGE_MAP } from '@/editor/text/languages';
import { NodeTypes, formatGraph } from '@/graph';
import type { MenuItemProps } from '@/menubar/MenuBarEntry.vue';
import MenuBarEntry from '@/menubar/MenuBarEntry.vue';
import {
	useEditorStore,
	useErrorStore,
	useFileStore,
	usePromptStore,
	useSettingsStore,
	useTerminalStore
} from '@/stores';
import { computed, ref, type ComputedRef } from 'vue';

	const promptStore = usePromptStore();
	const editorStore = useEditorStore();
	const terminalStore = useTerminalStore();
	const errorStore = useErrorStore();
	const fileStore = useFileStore();
	const settingsStore = useSettingsStore();

	const formatPromptDoNotShow = ref<boolean>(false);

	const entries: ComputedRef<Array<MenuItemProps>> = computed(() => [
		fileEntry.value,
		editEntry.value,
		terminalEntry.value,
		helpEntry.value
	]);

	/***************
	 * Files Entry
	 ***************/
	const fileEntry: ComputedRef<MenuItemProps> = computed(() => {
		return {
			name: 'File',
			items: [
				{
					label: 'Save',
					description: 'Ctrl+S',
					callback: async () => {
						const activeTab = editorStore.activeTab;
						if (activeTab) {
							editorStore.saveTab(activeTab.id);
						}
					}
				},
				{
					label: 'Download...',
					description: 'Ctrl+Shift+S',
					callback: () => {
						if (!editorStore.activeTab) return;
						editorStore.exportTabContents(editorStore.activeTab.id);
					}
				},
				{
					label: 'Refresh Files',
					description: 'Ctrl+I',
					callback: () => {
						fileStore.refreshFiles();
					},
					divider: true
				},
				{
					label: 'New Graph',
					description: 'Ctrl+Shift+N',
					callback: () => {
						editorStore.newDefaultGraphTab();
					}
				},
				{
					label: 'Open File (Client)...',
					description: 'Ctrl+O',
					callback: () => {
						editorStore.promptOpenFiles();
					},
					divider: true
				},
				{
					label: 'Open Log File (Server)...',
					description: 'Ctrl+L',
					callback: () => {
						promptStore.openLogModalOpen = true;
					},
					divider: true
				}
			]
		};
	});

	/***************
	 * Edit Entry
	 ***************/
	const editEntry: ComputedRef<MenuItemProps> = computed(() => {
		if (editorStore.activeGraphTab) {
			// Graph-tab entries
			const graph = editorStore.activeGraphTab.contents;
			const hasSelectedNodes = !!graph.ui.selectedNodes.length;
			return {
				name: 'Edit',
				items: [
					{
						label: 'Undo',
						description: 'Ctrl+Z',
						disabled: false,
						callback: () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (activeGraph) {
								activeGraph.history.undo();
							}
						}
					},
					{
						label: 'Redo',
						description: 'Ctrl+Y',
						disabled: false,
						callback: () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (activeGraph) {
								activeGraph.history.redo();
							}
						},
						divider: true
					},
					{
						label: 'Cut Nodes',
						description: 'Ctrl+X',
						disabled: !hasSelectedNodes,
						callback: () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (!activeGraph) {
								return;
							}

							const selectedNodes = activeGraph.ui.selectedNodes;
							if (!selectedNodes.length) {
								return;
							}

							editorStore.storeCopiedNodes(selectedNodes);
							activeGraph.deleteNodes(selectedNodes);
						}
					},
					{
						label: 'Copy Nodes',
						description: 'Ctrl+C',
						disabled: !hasSelectedNodes,
						callback: () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (!activeGraph) {
								return;
							}

							const selectedNodes = activeGraph.ui.selectedNodes;
							if (!selectedNodes.length) {
								return;
							}

							editorStore.storeCopiedNodes(selectedNodes);
						}
					},
					{
						label: 'Paste Nodes',
						description: 'Ctrl+V',
						disabled: !editorStore.copiedNodes.length,
						callback: () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (!activeGraph) {
								return;
							}

							const viewportPositions = activeGraph.ui.viewportPositions();
							const width = viewportPositions.right - viewportPositions.left;
							const height = viewportPositions.bottom - viewportPositions.top;

							const addedNodes = activeGraph.addNodeStates(editorStore.copiedNodes, {
								x: -1 * activeGraph.ui.offsets.x + width / 2,
								y: -1 * activeGraph.ui.offsets.y + height / 2,
								center: true,
								connect: 'group'
							});

							if (addedNodes.length > 1) {
								activeGraph.ui.deselectAllNodes();
								for (const addedNode of addedNodes) {
									activeGraph.ui.selectNode(addedNode);
								}
							}
						},
						divider: true
					},
					{
						label: 'Toggle Node Comments',
						description: 'Ctrl+/',
						disabled: !hasSelectedNodes,
						callback: () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (!activeGraph) {
								return;
							}

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
						},
						divider: true
					},
					{
						label: 'Select All',
						description: 'Ctrl+A',
						disabled: graph.ui.selectedNodes.length === graph.nodes.size,
						callback: async () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (!activeGraph) {
								return;
							}

							activeGraph.ui.selectAllNodes();
						}
					},
					{
						label: 'De-select All',
						description: 'Alt+A',
						disabled: !hasSelectedNodes,
						callback: async () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (!activeGraph) {
								return;
							}

							activeGraph.ui.deselectAllNodes();
						},
						divider: true
					},
					{
						label: 'Toggle Minimap',
						description: 'Alt+M',
						callback: settingsStore.toggleMinimap,
						divider: true
					},
					{
						label: 'Auto-Format',
						description: '',
						callback: async () => {
							const activeGraph = editorStore.activeGraphTab?.contents;
							if (!activeGraph) {
								return;
							}

							if (!formatPromptDoNotShow.value) {
								const value = await promptStore.show({
									title: 'Auto-Format',
									additionalInfo:
										'This operation will make a best-effort attempt to format the current graph and is not intended to provide the best possible formatting. Please check the graph after formatting is complete and make modifications as necessary.',
									entries: [{ label: 'Do not show again.', togglable: true, isToggled: false }],
									buttons: [
										{
											text: 'Cancel',
											type: 'secondary'
										},
										{
											text: 'Continue',
											type: 'primary'
										}
									]
								});

								if (!value || value.buttonName == 'Cancel') {
									return null;
								}

								if (value?.form.entries && value?.form.entries[0].isToggled) {
									formatPromptDoNotShow.value = true;
								}
							}

							formatGraph(activeGraph);
						}
					}
				]
			};
		}

		if (editorStore.activeTextTab) {
			// Text-tab entries
			const component = editorStore.getTextComponent(editorStore.activeTextTab.id);
			if (!component) {
				return {
					name: 'Edit',
					items: []
				};
			}

			return {
				name: 'Edit',
				items: [
					{
						label: 'Undo',
						description: 'Ctrl+Z',
						disabled: component.getUndoDepth() === 0,
						callback: () => {
							editorStore.getTextComponent(editorStore.activeTextTab?.id || '')?.undo();
						}
					},
					{
						label: 'Redo',
						description: 'Ctrl+Y',
						disabled: component.getRedoDepth() === 0,
						callback: () => {
							editorStore.getTextComponent(editorStore.activeTextTab?.id || '')?.redo();
						},
						divider: true
					},
					{
						label: 'Set Indent Unit',
						description: 'Set the width of added indentation.',
						submenu: {
							items: [
								{
									label: 'Tab' + (component.indentUnitValue === '\t' ? ' (Current)' : ''),
									description: 'Indent using a tab.',
									callback: () => {
										editorStore.getTextComponent(editorStore.activeTextTab?.id || '')?.setIndentUnit('\t');
									}
								},
								{
									label: 'Spaces',
									description: 'Indent using spaces.',
									submenu: {
										items: [
											{
												label: '2 Spaces' + (component.indentUnitValue === '  ' ? ' (Current)' : ''),
												description: 'Indent using 2 spaces.',
												callback: () => {
													editorStore.getTextComponent(editorStore.activeTextTab?.id || '')?.setIndentUnit('  ');
												}
											},
											{
												label: '4 Spaces' + (component.indentUnitValue === '    ' ? ' (Current)' : ''),
												description: 'Indent using 4 spaces.',
												callback: () => {
													editorStore.getTextComponent(editorStore.activeTextTab?.id || '')?.setIndentUnit('    ');
												}
											}
										]
									}
								}
							]
						},
						divider: true
					},
					{
						label: 'Set Language',
						description: 'Set the editor language mode.',
						submenu: {
							items: Object.keys(LANGUAGE_MAP).map((name) => {
								return {
									label: name,
									description: component.editorLanguage === name ? '*Selected' : '',
									callback: () => {
										editorStore.getTextComponent(editorStore.activeTextTab?.id || '')?.setLanguageMode(name);
									}
								};
							})
						},
						divider: true
					}
				]
			};
		}

		return {
			name: 'Edit',
			items: []
		};
	});

	/***************
	 * Terminal Entry
	 ***************/
	const terminalEntry: ComputedRef<MenuItemProps> = computed(() => {
		return {
			name: 'Terminal',
			items: [
				{
					label: 'Run Current Graph',
					description: 'Alt+R',
					disabled:
						!editorStore.activeGraphTab ||
						!editorStore.activeGraphTab.contents.canExecute() ||
						errorStore.graphHasErrors(editorStore.activeGraphTab.id),
					callback: () => {
						if (!editorStore.activeGraphTab) return;
						terminalStore.promptGraphExecution(
							editorStore.activeGraphTab.contents,
							editorStore.activeGraphTab.name,
							editorStore.activeGraphTab.fileId
								? fileStore.getFilePath(editorStore.activeGraphTab.fileId) || null
								: null
						);
					}
				},
				{
					label: 'Cancel Run',
					description: 'Alt+S',
					disabled: !terminalStore.terminalOpen || (terminalStore.terminalOpen && !terminalStore.selectedTerminalTabId),
					callback: () => {
						if (terminalStore.selectedTerminalTabId) {
							terminalStore.stopExecutingGraph(terminalStore.selectedTerminalTabId);
						}
					},
					divider: true
				},
				{
					label: 'Toggle Panel',
					callback: () => {
						terminalStore.toggleTerminalOpen();
					}
				}
			]
		};
	});

	/***************
	 * Help Entry
	 ***************/
	const helpEntry: ComputedRef<MenuItemProps> = computed(() => {
		return {
			name: 'Help',
			items: [
				{
					label: 'About GraphEX',
					description: '',
					disabled: promptStore.aboutOpen || terminalStore.graphToPrompt != null,
					callback: () => {
						promptStore.openAboutGraphexModal();
					}
				},
				{
					label: 'Find Erroring Node',
					description: '',
					disabled: promptStore.aboutOpen || terminalStore.graphToPrompt != null,
					callback: async () => {
						const value = await promptStore.show({
							title: 'Find Erroring Node',
							entries: [
								{
									label: 'GraphEX Error Code',
									help: 'The error code provided at the top of the terminal error output.',
									field: {
										value: ''
									},
									focus: true
								}
							],
							buttons: [
								{
									text: 'Find',
									type: 'primary'
								},
								{
									text: 'Cancel',
									type: 'secondary'
								}
							]
						});

						if (!value || value.buttonName == 'Cancel') {
							return;
						}

						const errorCode = value.form.entries[0].field!.value;
						await editorStore.navigateToErroringNode(errorCode);
					}
				},
				{
					label: 'Documentation (Tutorial)',
					description: '',
					callback: () => {
						window.open('/docs/index.html', '_blank');
					}
				}
			]
		};
	});
</script>

<style scoped>
	.menu-bar {
		display: flex;
		flex-direction: row;
		align-items: center;
		width: 100%;
		padding: 5px;
		margin-bottom: 10px;
		background-color: var(--color-foreground-primary);
		border-radius: 5px;
		position: relative;
	}

	.menu-logo {
		width: 1.5rem;
		height: 1.5rem;
		margin-left: 5px;
		margin-right: 24px;
	}

	.menu-bar-entries {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.menu-bar-entries > *:not(:last-child) {
		margin-right: 16px;
	}

	:deep(.menu-item-description) {
		margin-left: 48px;
	}

	.server-disconnected {
		margin-right: 8px;
		color: var(--color-error);
		cursor: help;
		animation: panicblink 1s infinite;
	}

	.venv-info {
		color: var(--color-primary);
	}

	.git-info {
		color: var(--color-primary);
		margin-right: 8px;
		margin-left: 1px;
	}

	@keyframes panicblink {
		from {
			opacity: 0.2;
		}
		to {
			opacity: 1;
		}
	}
</style>
