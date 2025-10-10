<template>
	<div
		class="tab no-select"
		@click="onTabClick"
		ref="tabElement"
		draggable="true"
		@dragstart="onDragStart"
		@dragenter.prevent
		@dragover.prevent
		@drop="onDrop"
		:active="isActive"
		:local="isLocalExecuted"
		:connected="isSocketConnected"
		:completed="isSocketCompleted"
		:error="finishedWithErrors"
		:is-log="isLog"
	>
		<div class="tab-info">
			<span v-if="!isLog" class="status-container">
				<span v-if="finishedWithWarnings && !finishedWithErrors" class="material-icons status-warning" title="Completed With Warnings"
					>warning</span
				>
				<span v-else-if="finishedWithErrors" class="material-icons status-error" title="Completed With Errors"
					>error_outlined</span
				>
				<span v-else-if="isSocketCompleted" class="material-icons status-completed" title="Completed">done</span>
				<span
					v-else
					class="material-icons status-circle"
					:title="isSocketConnected ? 'Currently Running' : 'Not Connected'"
					>circle</span
				>
			</span>

			<div
				v-if="!isLog && !isLocalExecuted"
				class="material-icons non-local-icon"
				title="Graph execution was started by a peer."
			>
				wifi
			</div>

			<div v-if="isLog" class="material-icons-outlined log-icon" title="Logs from a previously executed graph.">
				article
			</div>

			<div class="tab-name">
				{{ name }}
			</div>

			<div v-if="filepath" class="tab-path" :title="filepath">
				{{ filepath }}
			</div>
		</div>

		<div class="tab-close material-icons" title="Close" @click.stop="onCloseClick">close</div>
	</div>
</template>

<script setup lang="ts">
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import { useContextmenuStore, usePromptStore, useTerminalStore } from '@/stores';
import { computed, onMounted, ref } from 'vue';

	const props = defineProps<{
		/** The execution context ID for this terminal tab.*/
		contextId: string;
	}>();

	/** Events that this component emit to its parent component. */
	const emit = defineEmits<{
		(e: 'clicked'): void;
	}>();

	const promptStore = usePromptStore();
	const contextmenuStore = useContextmenuStore();
	const terminalStore = useTerminalStore();

	/** A reference to the HTML 'div' element that contains the entire tab. */
	const tabElement = ref<HTMLDivElement>();

	/** The execution context for this tab. */
	const context = computed(() => terminalStore.getExecutionContextById(props.contextId));

	/** The name for the tab. */
	const name = computed(() => (context.value ? context.value.name : 'N/A'));

	/** The path to the file for the context, if it exists. */
	const filepath = computed(() => (context.value ? context.value.filepath : null));

	/** Returns whether this tab is the currently 'active' (selected) tab. */
	const isActive = computed(() => props.contextId == terminalStore.selectedTerminalTabId);

	const isLocalExecuted = computed(() => (context.value ? context.value.isLocal : false));

	const isSocketConnected = computed(() => (context.value ? context.value.connected : false));

	const isSocketCompleted = computed(() => (context.value ? context.value.completed : false));

	const finishedWithErrors = computed(() =>
		context.value ? context.value.completed && context.value.errorCount > 0 : false
	);

	const finishedWithWarnings = computed(() =>
		context.value ? context.value.completed && context.value.warningCount > 0 : false
	);

	const isLog = computed(() => (context.value ? context.value.id.startsWith('log-') : false));

	function onDragStart(ev: DragEvent) {
		ev.dataTransfer!.dropEffect = 'move';
		ev.dataTransfer!.effectAllowed = 'move';
		ev.dataTransfer!.setData('contextId', props.contextId);
	}

	function onDrop(ev: DragEvent) {
		if (ev.dataTransfer && ev.dataTransfer.getData('contextId')) {
			const movingContextId = ev.dataTransfer.getData('contextId');
			if (movingContextId === props.contextId) {
				return;
			}
			terminalStore.reorderTabs(movingContextId, props.contextId);
		}
	}

	/**
	 * Callback from the Vue event 'clicked' (for most of the tab).
	 * Sets this tab as the currently selected one and emits the 'clicked' event to the parent.
	 */
	function onTabClick() {
		emit('clicked');
	}

	/**
	 * Callback for the Vue event 'clicked' on the 'X' / close indicator for the tab.
	 * Invokes the 'handleClose' function in this component.
	 */
	function onCloseClick() {
		handleClose();
	}

	/**
	 * Callback invoked when the user right clicks on the tab.
	 * Opens the custom context menu for the tab.
	 */
	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Close',
			description: 'Close this tab (and cancel execution).',
			callback: () => {
				handleClose();
			},
			divider: true
		});

		entries.push({
			label: 'View',
			description: 'Show the ouptut for this terminal connection.',
			callback: () => {
				onTabClick();
			}
		});

		return { items: entries };
	}

	async function handleClose() {
		if (!isSocketConnected.value) {
			terminalStore.removeContext(props.contextId);
			return;
		}

		const value = await promptStore.show({
			title: 'Cancel Executing Graph',
			additionalInfo: `Graph '${name.value}' is currently executing. The graph must finish executing before this tab can be closed.`,
			entries: [],
			buttons: [
				{
					text: 'Cancel Execution',
					hint: 'Attempt to gracefully stop this running graph by sending an interrupt signal.',
					type: 'primary'
				},
				{
					text: 'Forcefully Stop Execution',
					hint: 'Forcefully kill the process for this running graph.',
					type: 'warning'
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

		if (value.buttonName == 'Cancel Execution') {
			terminalStore.stopExecutingGraph(props.contextId);
			return;
		}

		if (value.buttonName == 'Forcefully Stop Execution') {
			terminalStore.killExecutingGraph(props.contextId);
			terminalStore.removeContext(props.contextId);
		}
	}

	/** Add the context menu event listener when this component mounts. */
	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(tabElement.value!, openContextMenu, false);
	});
</script>

<style scoped>
	.tab {
		min-height: 38px;
		height: 38px;
		margin-right: 8px;
		display: flex;
		flex-direction: row;
		align-items: center;
		cursor: pointer;
		border-bottom: 2px solid var(--color-foreground-tertiary);
	}

	.tab[active='true'] {
		border-color: var(--color-primary);
	}

	.tab-info {
		display: flex;
		flex-direction: row;
		align-items: center;
		opacity: 0.6;
	}

	.tab[active='true'] .tab-info {
		opacity: 1;
	}

	.status-container {
		width: 22px;
		margin-left: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.status-circle {
		margin-left: 3px;
		font-size: 0.6rem;
	}

	.tab[connected='false'] .status-circle {
		color: var(--color-component-terminal-status-idle);
	}

	.tab[connected='true'] .status-circle {
		color: var(--color-component-terminal-status-running);
	}

	.status-completed {
		font-size: 1rem;
		font-weight: bold;
		color: var(--color-component-terminal-status-done);
	}

	.status-error {
		font-size: 1rem;
		color: var(--color-component-terminal-text-critical);
	}

	.status-warning {
		font-size: 1rem;
		color: var(--color-component-terminal-text-warning);
	}

	.tab-path {
		max-width: 150px;
		outline: none;
		border: none;
		white-space: nowrap;
		text-overflow: ellipsis;
		color: var(--color-text-secondary);
		opacity: 0.8;
		overflow: hidden;
		font-size: 0.8rem;
		margin-left: 8px;
	}

	.non-local-icon {
		margin-right: 4px;
		font-size: 1rem;
		color: var(--color-primary);
		opacity: 0.5;
	}

	.log-icon {
		margin-right: 6px;
		font-size: 1rem;
		color: var(--color-primary);
		opacity: 0.8;
	}

	.tab-close {
		padding: 2px;
		margin-left: 8px;
		margin-right: 4px;
		font-size: 1rem;
		opacity: 0.3;
		color: var(--color-text);
		border-radius: 5px;
	}

	.tab[active='true'] .tab-close {
		opacity: 0.7;
	}

	.tab-close:hover {
		background-color: var(--color-foreground-tertiary);
	}
</style>
