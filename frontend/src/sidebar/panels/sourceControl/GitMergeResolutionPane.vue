<template>
	<div class="merge-resolution-pane">
		<div>
			<div class="title">
				<span>Resolving conflicts in {{ props.filePath }}</span>
				<span class="material-icons help-icon" :title="resolveConflictsHelpText">help_outline</span>
			</div>
			<div v-if="nodeIdConflicts.length > 0" class="sub-title">
				<span>Nodes</span>
				<span class="material-icons help-icon" :title="nodesHelpText">help_outline</span>
			</div>
			<div v-for="(nodeId, index) in nodeIdConflicts" :key="index" class="item-group">
				<SourceControlItemComponent
					:name="nodeId"
					:actions="[]"
					:dropdown-options="conflictItemOptions"
					@branch-options="conflictOptionsClicked"
					@item-clicked="nodeClicked"
					:git-icon="
						resolvedItems.includes(nodeId)
							? { icon: '\u2713', title: 'Conflicts have been resolved' }
							: { icon: '!', title: 'Contains conflicts' }
					"
				/>
			</div>
			<div v-if="inputIdConflicts.length > 0" class="sub-title">Inputs</div>
			<div v-for="(inputId, index) in inputIdConflicts" :key="index" class="item-group">
				<SourceControlItemComponent
					:name="inputId"
					:actions="[]"
					@item-clicked="inputClicked"
					:git-icon="
						resolvedItems.includes(inputId)
							? { icon: '\u2713', title: 'Conflicts have been resolved' }
							: { icon: '!', title: 'Contains conflicts' }
					"
				/>
			</div>
		</div>
		<div>
			<ButtonComponent
				text="Confirm Choices"
				hint="Confirm choices and return to the file list"
				type="primary"
				:disabled="isConfirmDisabled"
				@click="confirmResolution"
			/>
			<ButtonComponent text="Reset All" hint="Reset all choices" type="warning" @click="resetResolution" />
			<ButtonComponent
				text="Back"
				hint="Reset choices and return to the file list"
				type="secondary"
				:disabled="false"
				@click="cancelResolution"
			/>
		</div>
		<GraphInputChangesModal
			v-if="showgraphInputChangesModal"
			v-bind="graphInputChangessModalForm"
			@resolvedInput="resolvedInput"
			@close="showgraphInputChangesModal = false"
		/>
	</div>
</template>

<script setup lang="ts">
	import ButtonComponent from '@/components/ButtonComponent.vue';
	import type { GraphNode } from '@/graph';
	import { useEditorStore } from '@/stores';
	import { computed, type ComputedRef, onMounted, ref } from 'vue';
	import GraphInputChangesModal, { type ModalGraphInputChangesProps } from './modals/GraphInputChangesModal.vue';
	import SourceControlItemComponent from './SourceControlItemComponent.vue';
	const editorStore = useEditorStore();

	interface GitMergeResolutionPaneProps {
		filePath: string;
		otherBranch: string;
	}
	const props = defineProps<GitMergeResolutionPaneProps>();

	const nodeIdConflicts = ref<string[]>([]);
	const inputIdConflicts = ref<string[]>([]);

	const selectedMenuOption = ref<string>('');

	const allConflicts = ref<any>({});
	const selectedInputId = ref<string>('');
	const selectedInputChanges = ref<any>({});
	const showgraphInputChangesModal = ref<boolean>(false);

	const resolvedItems = ref<string[]>([]);

	const emit = defineEmits<{
		(e: 'confirmResolution', filePath: string, otherBranch: string): void;
		(e: 'cancelResolution', filePath: string): void;
	}>();

	onMounted(async () => {
		try {
			allConflicts.value = editorStore.conflictsToResolve;
			nodeIdConflicts.value = allConflicts.value.identified_conflicts.matching_node_ids;
			inputIdConflicts.value = Object.keys(allConflicts.value.identified_conflicts.matching_graph_input_data);
		} catch (e) {
			editorStore.setIsResolvingMergeConflict(false);
		}
	});
	const resolveConflictsHelpText =
		'Click on each node/input to view the diff between the branches. Resolve all conflicts to continue.';
	const nodesHelpText = 'Select ... next to each node to choose the current or incoming changes';

	const isConfirmDisabled = computed(() => {
		const totalLength = nodeIdConflicts.value.length + inputIdConflicts.value.length;
		if (resolvedItems.value.length < totalLength) {
			return true;
		}
		return false;
	});

	function conflictOptionsClicked(label: string, nodeId: string) {
		selectedMenuOption.value = label;
		let selectedChange = {};

		switch (label) {
			case 'Choose Current':
				selectedChange = { [nodeId]: allConflicts.value.changes_to_nodes[nodeId].this_branch_yaml };
				resolvedItems.value.push(nodeId);
				break;
			case 'Choose Incoming':
				selectedChange = { [nodeId]: allConflicts.value.changes_to_nodes[nodeId].other_branch_yaml };
				resolvedItems.value.push(nodeId);
				break;
			default:
				break;
		}
		editorStore.setChosenNodeConflicts(selectedChange);
	}

	const conflictItemOptions = computed(() => {
		const items = [
			{
				label: 'Choose Current',
				description: 'Keep the current changes'
			},
			{
				label: 'Choose Incoming',
				description: 'Keep the incoming changes'
			}
		];
		return items;
	});

	function nodeClicked(nodeId: string) {
		try {
			const node = editorStore?.activeGraphTab?.contents.getNode(nodeId);
			node?.graph.ui.deHighlightAllNodes();
			if (editorStore.selectedIssueNodeId === nodeId) {
				// De-highlight issue node
				editorStore.setSelectedIssueNodeId('');
			} else {
				// Highlight issue node
				editorStore.setSelectedIssueNodeId(nodeId);
				node?.graph.ui.highlightNode(node);
				if (node) {
					navigateToNode(node);
				}
			}
		} catch (e) {
			console.error(e);
		}
	}

	function navigateToNode(node: GraphNode) {
		if (editorStore.activeGraphTab) {
			if (node) {
				const ui = editorStore.activeGraphTab.contents.ui;
				ui.resetZoom();
				ui.navigateUiToNodeLocation(node);
			}
		}
	}

	async function inputClicked(inputId: string) {
		selectedInputId.value = inputId;
		selectedInputChanges.value = allConflicts.value.changes_to_graph_inputs[inputId];
		showgraphInputChangesModal.value = true;
	}

	const graphInputChangessModalForm: ComputedRef<ModalGraphInputChangesProps> = computed(() => {
		return {
			title: selectedInputId.value,
			inputId: selectedInputId.value,
			inputChanges: selectedInputChanges.value
		};
	});

	function resolvedInput(inputId: string) {
		resolvedItems.value.push(inputId);
		showgraphInputChangesModal.value = false;
	}

	function confirmResolution() {
		emit('confirmResolution', props.filePath, props.otherBranch);
	}

	function resetResolution() {
		editorStore.setChosenInputConflicts({});
		editorStore.setChosenNodeConflicts({});
		resolvedItems.value = [];
	}

	function cancelResolution() {
		editorStore.setChosenInputConflicts({});
		editorStore.setChosenNodeConflicts({});
		resolvedItems.value = [];
		emit('cancelResolution', props.filePath);
	}
</script>

<style scoped>
	.merge-resolution-pane {
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
	}

	.title {
		color: var(--color-primary);
		letter-spacing: 1px;
		cursor: default;
		padding-bottom: 8px;
		display: flex;
		align-items: center;
	}

	.sub-title {
		color: var(--color-primary);
		letter-spacing: 1px;
		cursor: default;
		display: flex;
		align-items: center;
	}

	.item-group {
		padding-bottom: 8px;
	}

	.help-icon {
		margin-left: 6px;
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.6;
		cursor: help;
	}
</style>
