<template>
	<div
		class="file-result-container no-select"
		title="Left-click to open this file"
		:style="selectedStyle"
		@click="openFile"
	>
		<div class="file-result-body">
			<div class="file-result-matching-line no-select">
				<span>{{ beforeQuery }}</span>
				<span class="query-span">{{ query }}</span>
				<span>{{ afterQuery }}</span>
			</div>
			<span class="file-relative-path no-select">{{ props.relativePath }}</span>
			<span v-if="props.lineNumber >= 0" class="file-line-number no-select">Line {{ props.lineNumber }}</span>
			<span v-else-if="props.lineNumber == -1" class="file-line-number no-select">Filename Match</span>
			<span v-else-if="props.lineNumber == -2" class="file-line-number no-select">Node Description Match {{ firstNodeId }}</span>
			<span v-else-if="props.lineNumber == -3" class="file-line-number no-select">Node Output Socket Name Match {{ firstNodeId }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useEditorStore, useFileStore } from '@/stores';
import { computed, ref } from 'vue';

	const props = defineProps<{
		relativePath: string,
		lineNumber: number,
		matchingLine: string,
		originalQuery: string,
		isSelected: boolean,
		matchingId: string
	}>();

	const emit = defineEmits<{
		(e: 'clicked'): void;
	}>();

	const fileStore = useFileStore();
	const editorStore = useEditorStore();
	const maxDisplayedResultLength = ref<number>(500);

	async function openFile() {
		emit('clicked');
		const fileObj = fileStore.findFileByPath(props.relativePath);
		if (fileObj) {
			const id = await editorStore.openFileInEditor(fileObj.id);
			if (id) {
				const textEditorPage = editorStore.getTextComponent(id);
				if (textEditorPage) {
					// if we make it to this conditional block, the content of the tab is a text editor page
					textEditorPage.goToLine(props.lineNumber);
				// this is a GX file, find out if the clicked search result cooresponds to a node in the yaml file
				} else {
					let nodeId = null;
					if (props.matchingId) {
						// this result is from a deep search
						// just grab the first ID for now
						nodeId = props.matchingId;
					} else {
						// not a deep search
						const response = await fetch('/api/nodeIdFromFile', {
							method: 'POST',
							headers: {
								'Content-Type': 'application/json'
							},
							body: JSON.stringify({
								"path": props.relativePath,
								"line_number": props.lineNumber
							})
						});

						if (!response.ok) return;
						const data = await response.json();
						nodeId = data["nodeId"];
					}
					if (nodeId && editorStore.activeGraphTab) {
						const node = editorStore.activeGraphTab.contents.getNode(nodeId);
						if (node) {
							const ui = editorStore.activeGraphTab.contents.ui;
							ui.deselectAllNodes();
							ui.selectNode(node);
							ui.resetZoom();
							ui.navigateUiToNodeLocation(node);
						}
					}
				}
			}
		}
	}

	const firstNodeId = computed(() => {
		if (props.matchingId) {
			return "(" + props.matchingId + ")";
		}
		return "";
	});

	/** Takes in props.matchingLine and formats it to be within the bounds of the character limit imposed by maxDisplayedResultLength */
	const matchingSearchLine = computed(() => {
		if (props.matchingLine.length <= maxDisplayedResultLength.value)
			return props.matchingLine;
		// else the matching line is over the character limit for what we want to see in the sidebar panel
		// find the matching query and truncate it by equal length from both ends
		const matchingIndex = props.matchingLine.toLowerCase().indexOf(props.originalQuery.toLowerCase());
		// this shouldn't happen, but slice if it does anyway
		if (matchingIndex < 0)
			return props.matchingLine.slice(0, maxDisplayedResultLength.value);
		// How far in each direction from the query matched that we should slice
		const midPointAmount = maxDisplayedResultLength.value / 2;
		// How far the query is from the middle
		const matchingMidPointDifference = matchingIndex - midPointAmount;
		if (matchingMidPointDifference <= 0) {
			// This indicates the query is before the midpoint of the character limit or equal to the midpoint
			return props.matchingLine.slice(0, maxDisplayedResultLength.value);
		} else {
			// This indicates the query is after the midpoint of the character limit
			try {
				// This should never crash in JavaScript land, even if the index to end at is too high
				return props.matchingLine.slice(matchingMidPointDifference, matchingMidPointDifference + maxDisplayedResultLength.value);
			} catch {
				// catch just in case it does crash
				return props.matchingLine.slice(matchingMidPointDifference);
			}
		}
	});

	const matchingSearchLineQueryIndex = computed(() => {
		return matchingSearchLine.value.toLowerCase().indexOf(props.originalQuery.toLowerCase());
	});

	const query = computed(() => {
		return matchingSearchLine.value.slice(matchingSearchLineQueryIndex.value, matchingSearchLineQueryIndex.value+props.originalQuery.length);
	});

	const beforeQuery = computed(() => {
		return matchingSearchLine.value.slice(0, matchingSearchLineQueryIndex.value);
	});

	const afterQuery = computed(() => {
		return matchingSearchLine.value.slice(matchingSearchLineQueryIndex.value+props.originalQuery.length);
	});

	const selectedStyle = computed(() => {
		if (!props.isSelected) {
			return {};
		}

		return {
			"border": "2px solid",
			"border-color": "white"
	 	}
	});
</script>

<style scoped>
	.file-result-container {
		width: 100%;
		margin-top: 0.5rem;
		display: flex;
		flex-direction: column;
		background-color: var(--color-background-primary);
	}

	.file-result-container {
		cursor: alias;
	}

	.file-result-body {
		width: 100%;
		padding: 0.5rem;
		display: flex;
		flex-direction: column;
	}

	.file-result-matching-line {
		width: 100%;
		flex-direction: row;
		align-items: center;
		color: var(--color-text);
		overflow-wrap: break-word;
	}

	.file-relative-path {
		margin-top: 2px;
		color: var(--color-text);
		opacity: 0.5;
		font-style: italic;
		font-size: 0.8rem;
		white-space: pre-wrap;
	}

	.file-line-number {
		margin-top: 2px;
		color: var(--color-primary);
		opacity: 0.8;
		font-size: 0.8rem;
	}

	.file-result-container:hover .node-color {
		opacity: 1;
		transition: opacity 100ms linear;
	}

	.query-span {
		color: var(--color-primary);
	}
</style>
