<template>
	<div class="sidebar">
		<div class="tabs">
			<!-- Top -->
			<div class="tabs-section">
				<div
					class="tab-button"
					v-for="panel in panels"
					:key="panel.name"
					:selected="selectedTab == panel.name"
					:disabled="disabledPanels.includes(panel.name)"
					@click="() => selectTab(panel.name)"
					:title="panel.title + (disabledPanels.includes(panel.name) ? ' (Not Available)' : '')"
				>
					<span
						:style="iconColorStyle(panel.errorColor, panel.warningColor, panel.name)"
						class="tab-button-icon material-icons"
						>{{ panel.icon }}</span
					>
				</div>
			</div>

			<!-- Bottom -->
			<div class="tabs-section">
				<span
					v-show="numTerminalWarnings > 0 && numTerminalErrors <= 0"
					class="terminal-warning material-icons"
					:title="terminalWarningTitle"
				>
					warning
				</span>
				<span
					v-show="numTerminalErrors > 0"
					class="terminal-critical material-icons"
					:title="terminalCriticalTitle"
					ref="terminalCritical"
				>
					priority_high
				</span>
				<span
					class="terminal-button material-icons"
					:style="terminalIconStyle"
					@click="terminalStore.toggleTerminalOpen"
					title="Toggle Terminal"
					ref="terminalButton"
				>
					terminal
				</span>
				<div
					:style="{ opacity: numTerminalExecuting > 0 ? 1 : 0 }"
					class="terminal-executing-dots"
					@click="terminalStore.toggleTerminalOpen"
				>
					<span class="material-icons executing-circle" id="circle1">circle</span>
					<span class="material-icons executing-circle" id="circle2">circle</span>
					<span class="material-icons executing-circle" id="circle3">circle</span>
				</div>
			</div>
		</div>
		<div v-show="selectedTab" class="panel">
			<component v-for="panel in panels" :key="panel.name" v-show="selectedTab == panel.name" :is="panel.component" />
		</div>
	</div>
</template>

<script setup lang="ts">
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
	import DataNodesPanel from '@/sidebar/panels/DataNodesPanel.vue';
	import FavoriteNodesPanel from '@/sidebar/panels/FavoriteNodesPanel.vue';
	import GraphSearchPanel from '@/sidebar/panels/GraphSearchPanel.vue';
	import FilesPanel from '@/sidebar/panels/files/FilesPanel.vue';
	import GraphIOPanel from '@/sidebar/panels/graphIO/GraphIOPanel.vue';
	import { useContextmenuStore, useEditorStore, useErrorStore, usePromptStore, useTerminalStore } from '@/stores';
	import { computed, onMounted, reactive, ref, shallowRef, watch, type Component } from 'vue';
	import ErrorsPanel from './panels/ErrorsPanel.vue';
	import InventoryPanel from './panels/inventory/InventoryPanel.vue';
	import SourceControlPanel from './panels/sourceControl/SourceControlPanel.vue';
	import VariablePanel from './panels/variable/VariablePanel.vue';

	interface PanelData {
		name: string;
		title: string;
		component: Component;
		icon: string;
		hidden?: () => boolean;
		errorColor?: string;
		warningColor?: string;
	}

	const editorStore = useEditorStore();
	const terminalStore = useTerminalStore();
	const contextmenuStore = useContextmenuStore();
	const promptStore = usePromptStore();
	const errorStore = useErrorStore();

	const terminalButton = ref<HTMLSpanElement>();
	const terminalCritical = ref<HTMLSpanElement>();

	const numTerminalErrors = computed(() =>
		terminalStore.executions.reduce((num, e) => (e.completed && e.errorCount > 0 ? num + 1 : num), 0)
	);

	const numTerminalWarnings = computed(() =>
		terminalStore.executions.reduce((num, e) => (e.completed && e.warningCount > 0 ? num + 1 : num), 0)
	);

	const numTerminalExecuting = computed(() =>
		terminalStore.executions.reduce((num, e) => (!e.completed ? num + 1 : num), 0)
	);

	const panels = reactive<Array<PanelData>>([
		{ name: 'files', title: 'Files', component: shallowRef(FilesPanel), icon: 'folder_open' },
		{ name: 'nodes', title: 'Add Nodes', component: shallowRef(DataNodesPanel), icon: 'dashboard_customize' },
		{
			name: 'favoriteNodes',
			title: 'Favorite Nodes',
			component: shallowRef(FavoriteNodesPanel),
			icon: 'star_border'
		},
		{
			name: 'graphSearch',
			title: 'Search for Nodes in the Graph (Ctrl+F)',
			component: shallowRef(GraphSearchPanel),
			icon: 'query_stats'
		},
		{
			name: 'graphIO',
			title: 'Configure Graph',
			component: shallowRef(GraphIOPanel),
			icon: 'settings_input_component',
			warningColor: 'var(--color-warning)'
		},
		{
			name: 'variables',
			title: 'Variables',
			component: shallowRef(VariablePanel),
			icon: 'abc'
		},
		{
			name: 'inventory',
			title: 'Inventory',
			component: shallowRef(InventoryPanel),
			icon: 'storage'
		},
		{
			name: 'sourceControls',
			title: 'Source Control',
			component: shallowRef(SourceControlPanel),
			icon: 'webhook'
		},
		{
			name: 'errors',
			title: 'Errors and Warnings',
			component: shallowRef(ErrorsPanel),
			icon: 'report',
			errorColor: 'var(--color-error)',
			warningColor: 'var(--color-warning)'
		}
	]);

	const disabledPanels = computed(() => {
		const disabled: Array<string> = [];
		if (!editorStore.activeGraphTab) {
			disabled.push('graphIO', 'nodes', 'favoriteNodes', 'variables', 'errors');
		}
		if (editorStore.isResolvingMergeConflict) {
			disabled.push('files', 'graphSearch', 'graphIO', 'nodes', 'favoriteNodes', 'variables', 'errors', 'inventory');
		}
		return disabled;
	});

	const selectedTab = ref<string | null>(null);
	function selectTab(tabName: string) {
		if (disabledPanels.value.includes(tabName)) {
			return;
		}
		selectedTab.value = tabName == selectedTab.value ? null : tabName;
	}

	watch([selectedTab, disabledPanels], () => {
		if (selectedTab.value && disabledPanels.value.includes(selectedTab.value)) {
			// Tab that was selected is now hidden
			// Select the first tab that is not hidden
			const newPanel = panels.find((panel) => !disabledPanels.value.includes(panel.name));
			selectedTab.value = newPanel ? newPanel.name : null;
		}
	});

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Close Finished Tabs',
			description: 'Closes all tabs that have finished executing',
			callback: async () => {
				for (const context of Array.from(terminalStore.executions)) {
					if (context.completed) {
						terminalStore.removeContext(context.id);
					}
				}
			},
			divider: true
		});

		entries.push({
			label: 'Open Log File...',
			description: "Open a previous run's log",
			callback: async () => {
				promptStore.openLogModalOpen = true;
			},
			divider: true
		});

		entries.push({
			label: 'Toggle',
			description: 'Show or hide the terminal window',
			callback: terminalStore.toggleTerminalOpen,
			divider: true
		});

		return { items: entries };
	}

	/**
	 * Stylizes the color of the terminal icon based on whether it is currently open or closed.
	 */
	const terminalIconStyle = computed(() => {
		return {
			color: terminalStore.terminalOpen ? 'var(--color-primary)' : 'var(--color-text)'
		};
	});

	const iconColorStyle = computed(() => {
		return (errorColor: string | undefined, warningColor: string | undefined, name: string | undefined) => {
			if (name) {
				if (name === 'errors') {
					if (errorsInGraph.value && errorColor) {
						return {
							color: errorColor
						};
					}
					if (warningsInGraph.value && warningColor) {
						return {
							color: warningColor
						};
					}
				}
				if (graphInputWarningsInGraph.value && name === 'graphIO' && warningColor) {
					return {
						color: warningColor
					};
				}
			}
			return {
				color: 'var(--color-text)'
			};
		};
	});

	const errorsInGraph = computed(() => {
		if (editorStore.activeGraphTab) {
			return errorStore.graphHasErrors(editorStore.activeGraphTab.id);
		}
		return false;
	});

	const warningsInGraph = computed(() => {
		if (editorStore.activeGraphTab) {
			return errorStore.graphHasWarning(editorStore.activeGraphTab.id);
		}
		return false;
	});

	const graphInputWarningsInGraph = computed(() => {
		if (editorStore.activeGraphTab) {
			return errorStore.graphHasGraphInputWarning(editorStore.activeGraphTab.id);
		}
		return false;
	});

	const terminalCriticalTitle = computed(() => {
		if (numTerminalErrors.value == 1) {
			return 'A graph completed with an error.';
		}
		return String(numTerminalErrors.value) + ' graphs completed with errors.';
	});

	const terminalWarningTitle = computed(() => {
		if (numTerminalWarnings.value == 1) {
			return 'A graph completed with an warning.';
		}
		return String(numTerminalWarnings.value) + ' graphs completed with warnings.';
	});

	onMounted(async () => {
		contextmenuStore.getContextMenu('root').addHook(terminalButton.value!, openContextMenu, false);
	});

	defineExpose({
		selectTab,
		selectedTab
	});
</script>

<style scoped>
	.sidebar {
		width: 100%;
		display: flex;
		flex-direction: row;
		overflow: hidden;
	}

	.tabs {
		width: 50px;
		height: 100%;
		margin-right: 10px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: space-between;
	}

	.tabs-section {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.terminal-button {
		border-radius: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		font-size: 32px;
		opacity: 0.8;
	}

	.terminal-button:hover {
		opacity: 1;
	}

	.tab-button {
		width: 50px;
		height: 50px;
		border-radius: 10px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.tab-button[disabled='false'] {
		cursor: pointer;
	}

	.tab-button-icon {
		font-size: 32px;
		opacity: 0.8;
	}

	.tab-button[disabled='true'] .tab-button-icon {
		opacity: 0.25;
	}

	.tab-button[selected='false'][disabled='false']:hover .tab-button-icon {
		opacity: 1;
	}

	.tab-button[selected='true'][disabled='false'] {
		background-color: var(--color-foreground-primary);
	}

	.tab-button[selected='true'][disabled='false'] .tab-button-icon {
		opacity: 1;
	}

	.panel {
		flex: 1 0;
		height: 100%;
		display: flex;
		flex-direction: column;
		background-color: var(--color-foreground-primary);
		border-radius: 10px;
		overflow: hidden;
	}

	.terminal-executing-dots {
		display: flex;
		flex-direction: row;
		position: relative;
	}

	.executing-circle {
		color: grey;
		font-size: 8px;
		bottom: 2.5vh;
	}

	.executing-circle:not(:last-child) {
		margin-right: 1px;
	}

	#circle1 {
		animation-name: dotbounce;
		animation-iteration-count: infinite;
		animation-duration: 3s;
	}

	#circle2 {
		animation-name: dotbounce;
		animation-iteration-count: infinite;
		animation-duration: 3s;
		animation-delay: 1s;
	}

	#circle3 {
		animation-name: dotbounce;
		animation-iteration-count: infinite;
		animation-duration: 3s;
		animation-delay: 2s;
	}

	@keyframes dotbounce {
		0% {
			transform: translateY(0px);
			color: var(--color-component-terminal-status-idle);
		}
		12% {
			transform: translateY(0px);
			color: var(--color-component-terminal-status-idle);
		}
		25% {
			transform: translateY(0px);
			color: var(--color-component-terminal-status-idle);
		}
		40% {
			transform: translateY(-2px);
			color: var(--color-component-terminal-status-running);
		}
		80% {
			transform: translateY(0px);
			color: var(--color-component-terminal-status-idle);
		}
		100% {
			transform: translateY(0px);
			color: var(--color-component-terminal-status-idle);
		}
	}

	.terminal-critical {
		color: var(--color-component-terminal-text-critical);
	}

	.terminal-warning {
		color: var(--color-component-terminal-text-warning);
	}
</style>
