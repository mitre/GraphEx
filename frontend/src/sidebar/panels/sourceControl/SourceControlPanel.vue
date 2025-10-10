<template>
	<SidebarPanel header="Source Control">
		<BreadcrumbsComponent
			v-show="selectedCategory.length && !editorStore.isResolvingMergeConflict"
			:items="selectedCategory"
			@return-to-index="returnToCategory"
		/>
		<div>
			<div class="repoLabel">Current Repo</div>
			<div class="currentGitRepoLabel">
				{{ activeRepo }}
			</div>
		</div>
		<div v-if="clickedTab === ''">
			<CategoryComponent
				v-for="(category, index) in sourceControlOptions"
				:key="index"
				:name="category.name"
				@selected="() => nextCategory(category.name)"
			/>
		</div>
		<GitActionsPane
			v-else-if="clickedTab === 'Source Control'"
			:files="filesWithConflicts"
			:resolved-files="resolvedFiles"
			:otherBranch="otherBranch"
			@switch-tabs="switchTab"
			@conclude-merge-resolution="concludeMergeResolution"
		/>
		<GitLocalBranchesPane v-else-if="clickedTab === 'Local Branches'" @switch-tabs="switchTab" />
		<GitRemoteBranches v-else-if="clickedTab === 'Remote Branches'" @switch-tabs="switchTab" />
		<GitMergeResolutionPane
			v-else-if="clickedTab === 'Merge Resolution'"
			@confirm-resolution="confirmFileResolution"
			@cancel-resolution="cancelFileResolution"
			:file-path="fileBeingResolved"
			:other-branch="otherBranch"
		/>
	</SidebarPanel>
</template>

<script setup lang="ts">
	import SidebarPanel from '@/sidebar/SidebarPanel.vue';
	import BreadcrumbsComponent from '@/sidebar/nodePanel/BreadcrumbsComponent.vue';
	import CategoryComponent from '@/sidebar/nodePanel/CategoryComponent.vue';
	import { useEditorStore } from '@/stores';
	import { onMounted, ref } from 'vue';
	import GitActionsPane from './GitActionsPane.vue';
	import GitLocalBranchesPane from './GitLocalBranchesPane.vue';
	import GitMergeResolutionPane from './GitMergeResolutionPane.vue';
	import GitRemoteBranches from './GitRemoteBranches.vue';

	const editorStore = useEditorStore();

	const clickedTab = ref<string>('');

	const sourceControlOptions = [{ name: 'Source Control' }, { name: 'Local Branches' }, { name: 'Remote Branches' }];

	const selectedCategory = ref<Array<string>>([]);

	const filesWithConflicts = ref<Array<string>>([]);
	const resolvedFiles = ref<Array<string>>([]);

	const otherBranch = ref<string>('');
	const fileBeingResolved = ref<string>('');

	const activeRepo = ref<string>('');

	onMounted(async () => {
		const response = await fetch('/api/packageInfo', { method: 'GET' });
		if (response.ok) {
			const data = await response.json();
			activeRepo.value = data['repo'];
		} else {
			activeRepo.value = 'Unable to retrieve git repo';
		}
	});

	function nextCategory(categoryName: string) {
		selectedCategory.value.push(categoryName);
		clickedTab.value = categoryName;
	}

	function returnToCategory(index: number) {
		selectedCategory.value = selectedCategory.value.slice(0, index);
		if (selectedCategory.value.length < 1) {
			clickedTab.value = '';
		}
	}

	function switchTab(tab: string, files: string[], branch: string, fileName?: string) {
		if (fileName) {
			fileBeingResolved.value = fileName;
		}
		if (tab === 'Source Control') {
			filesWithConflicts.value = files;
			otherBranch.value = branch;
		}
		returnToCategory(0);
		nextCategory(tab);
	}

	async function confirmFileResolution(filePath: string, otherBranch: string) {
		try {
			await editorStore.confirmFileResolution(otherBranch, filePath);

			// Remove the resolved file from filesWithConflicts
			filesWithConflicts.value = filesWithConflicts.value.filter((file) => file !== filePath);

			// Track the resolved files
			if (!resolvedFiles.value.includes(filePath)) {
				resolvedFiles.value.push(filePath);
			}

			// Close the incoming and current graph files
			editorStore.removeMergeConflictTabs('Current_Branch_' + filePath);
			editorStore.removeMergeConflictTabs('Incoming_Branch_' + filePath);
			returnToCategory(0);
			nextCategory('Source Control');
		} catch (e) {
			console.error('Error confirming merge conflict choices', e);
		}
	}

	function cancelFileResolution(filePath: string) {
		returnToCategory(0);
		nextCategory('Source Control');
		editorStore.removeMergeConflictTabs('Current_Branch_' + filePath);
		editorStore.removeMergeConflictTabs('Incoming_Branch_' + filePath);
	}

	function concludeMergeResolution() {
		resolvedFiles.value = [];
		filesWithConflicts.value = [];
		editorStore.setIsResolvingMergeConflict(false);
	}
</script>

<style scoped>
	.currentGitRepoLabel {
		padding-bottom: 16px;
		overflow-wrap: anywhere;
	}

	.repoLabel {
		color: var(--color-primary);
		letter-spacing: 1px;
		cursor: default;
		display: flex;
		align-items: center;
	}
</style>
