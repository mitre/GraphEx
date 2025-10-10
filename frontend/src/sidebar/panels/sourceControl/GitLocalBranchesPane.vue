<template>
	<div v-if="branchStatus !== 200">Error retrieving git branches</div>
	<div v-else class="git-branches">
		<div>
			<div class="actions-title">Local Branches</div>
			<div v-for="(branch, index) in branches" :key="index">
				<SourceControlItemComponent
					:name="branch"
					:actions="[]"
					:git-icon="branch === terminalStore.activeGitBranch ? { icon: '*', title: 'Current branch' } : undefined"
					:dropdown-options="
						branch === terminalStore.activeGitBranch ? currentBranchMenuOptions : otherBranchMenuOptions
					"
					@branch-options="branchOptionsClicked"
				/>
			</div>
		</div>
		<div>
			<ButtonComponent
				text="Create New Branch"
				:hint="``"
				type="primary"
				:disabled="false"
				@click="showCreateNewBranchModal = true"
			/>
		</div>
	</div>
	<GitBranchesModal
		v-if="showGitBranchesModal"
		v-bind="gitBranchesModalForm"
		@close="showGitBranchesModal = false"
		@confirm-clicked="gitBranchesModalConfirmedClicked"
	/>
	<CreateBranchModal
		v-if="showCreateNewBranchModal"
		title="Create New Branch"
		@close="showCreateNewBranchModal = false"
		@confirm-clicked="createBranchModalConfirmedClicked"
	/>
</template>

<script setup lang="ts">
	import ButtonComponent from '@/components/ButtonComponent.vue';
	import SourceControlItemComponent from '@/sidebar/panels/sourceControl/SourceControlItemComponent.vue';
	import { useEditorStore, usePromptStore, useTerminalStore } from '@/stores';
	import { computed, ref, type ComputedRef } from 'vue';
	import CreateBranchModal from './modals/CreateBranchModal.vue';
	import GitBranchesModal, { type ModalGitBranchesProps } from './modals/GitBranchesModal.vue';
	const terminalStore = useTerminalStore();
	const promptStore = usePromptStore();
	const editorStore = useEditorStore();

	const showGitBranchesModal = ref<boolean>(false);
	const showBranchesDropdown = ref<boolean>(false);
	const showCredentials = ref<boolean>(true);
	const showCreateNewBranchModal = ref<boolean>(false);

	const selectedMenuOption = ref<string>('');

	const filesWithConflicts = ref<string[]>([]);
	const emit = defineEmits<{
		(e: 'switchTabs', value: string, filesWithConflicts: string[], branch: string): void;
	}>();

	const branches = computed(() => {
		if (terminalStore.gitBranches) {
			if (typeof terminalStore.gitBranches[0] === 'string') {
				return [terminalStore.gitBranches[0]];
			} else {
				return terminalStore.gitBranches[0].branch_names;
			}
		}
		return [];
	});

	const branchStatus = computed(() => {
		if (terminalStore.gitBranches) {
			return terminalStore.gitBranches[1];
		}
		return null;
	});

	function branchOptionsClicked(label: string, branchName: string) {
		selectedMenuOption.value = label;

		switch (label) {
			case 'Fetch':
				showCredentials.value = true;
				showBranchesDropdown.value = true;
				showGitBranchesModal.value = true;
				break;
			case 'Pull':
				showCredentials.value = true;
				showBranchesDropdown.value = false;
				showGitBranchesModal.value = true;
				break;
			case 'Merge':
				showCredentials.value = false;
				showBranchesDropdown.value = true;
				showGitBranchesModal.value = true;
				break;
			case 'Switch to branch':
				switchOrCreateBranch(branchName);
				break;
			default:
				break;
		}
	}

	function switchOrCreateBranch(newBranch: string) {
		editorStore.switchOrCreateBranch(newBranch);
	}

	const currentBranchMenuOptions = computed(() => {
		const items = [
			{
				label: 'Fetch',
				description: 'Download objects and refs from another repository'
			},
			{
				label: 'Pull',
				description: 'Fetch from and integrate with the local branch'
			},
			{
				label: 'Merge',
				description: 'Join two or more development histories together'
			}
		];
		return items;
	});

	const otherBranchMenuOptions = computed(() => {
		const items = [
			{
				label: 'Switch to branch'
			}
		];
		return items;
	});

	const gitBranchesModalForm: ComputedRef<ModalGitBranchesProps> = computed(() => {
		return {
			title: selectedMenuOption.value,
			username: showCredentials.value ? editorStore.gitUsername : undefined,
			password: showCredentials.value ? editorStore.gitPassword : undefined,
			gitBranches: showBranchesDropdown.value ? branches.value : undefined,
			activeBranch: terminalStore.activeGitBranch
		};
	});

	async function gitBranchesModalConfirmedClicked(data: {
		action: string;
		username: string;
		password: string;
		remoteBranch?: string;
	}) {
		showGitBranchesModal.value = false;
		editorStore.setGitUsername(data.username);
		editorStore.setGitPassword(data.password);

		const branchName = data.remoteBranch ?? '';
		switch (data.action) {
			case 'Fetch':
				editorStore.gitFetch(data.username, data.password, branchName);
				break;
			case 'Pull':
				editorStore.gitPull(data.username, data.password);
				break;
			case 'Merge':
				filesWithConflicts.value = await editorStore.gitMerge(branchName);
				if (filesWithConflicts.value.length > 0) {
					const value = await promptStore.show({
						title: 'Conflicts',
						additionalInfo: 'Please resolve conflicts to continue merging.',
						entries: [],
						buttons: [
							{ text: 'View Conflicts', type: 'primary' },
							{ text: 'Cancel', type: 'secondary' }
						]
					});

					if ((!value || value.buttonName == 'View Conflicts') && data.remoteBranch) {
						editorStore.setIsResolvingMergeConflict(true);
						emit('switchTabs', 'Source Control', filesWithConflicts.value, data.remoteBranch);
					}
					if (!value || value.buttonName == 'Cancel') {
						editorStore.setIsResolvingMergeConflict(false); // Should already be false
						editorStore.cancelGitMerge();
					}
				}
				break;
			default:
				break;
		}
	}

	function createBranchModalConfirmedClicked(data: { newBranchName: string }) {
		switchOrCreateBranch(data.newBranchName);
		showCreateNewBranchModal.value = false;
	}
</script>

<style scoped>
	.git-branches {
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
	}

	.actions-title {
		color: var(--color-primary);
		letter-spacing: 1px;
		cursor: default;
	}
</style>
