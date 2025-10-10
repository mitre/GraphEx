<template>
	<div v-if="gitStatusCode !== 200">Error retrieving git status</div>
	<div v-else class="git-actions">
		<div>
			<div v-if="editorStore.isResolvingMergeConflict && props.files.length === 0" class="all-resolved-msg">
				All merge conflicts have been resolved!
			</div>
			<div v-if="props.files.length > 0 && editorStore.isResolvingMergeConflict" class="staged-changes-block">
				<div class="actions-title">
					<span>Files with Conflicts</span>
					<span class="material-icons help-icon" :title="conflictsPaneHelpText">help_outline</span>
				</div>
				<div v-for="(file, index) in props.files" :key="index">
					<SourceControlItemComponent
						:name="file"
						:actions="[{ icon: 'error', title: 'View Conflicts', clickAction: 'viewConflicts' }]"
						@view-conflicts="viewMergeConflicts"
					/>
				</div>
				<span v-if="props.resolvedFiles && props.resolvedFiles.length > 0">
					<div class="actions-title">
						<span>Resolved Files</span>
					</div>
					<div v-for="(file, index) in props.resolvedFiles" :key="index">
						<SourceControlItemComponent
							:name="file"
							:git-icon="{ icon: '\u2713', title: 'Conflicts have been resolved' }"
						/>
					</div>
				</span>
			</div>
			<div v-if="stagedFiles.length > 0" class="staged-changes-block">
				<div class="actions-title">Staged Changes</div>
				<div v-for="(file, index) in stagedFiles" :key="index">
					<SourceControlItemComponent
						:name="file"
						:actions="[{ icon: 'remove', title: 'Unstage Changes', clickAction: 'discardChanges' }]"
						@discardChanges="handleDiscardChanges"
					/>
				</div>
			</div>

			<div v-if="modifiedFiles.length > 0" class="git-changes-heading">
				<div class="actions-title">Changes</div>
				<div
					v-if="modifiedFiles.length > 0 || untrackedFiles.length > 0"
					class="add-all-btn material-icons"
					title="Stage all changes"
					@click.stop.prevent="addAll"
				>
					add
				</div>
			</div>
			<div v-for="(file, index) in modifiedFiles" :key="index">
				<SourceControlItemComponent
					:name="file"
					:actions="[{ icon: 'add', title: 'Stage Changes', clickAction: 'addChanges' }]"
					:git-icon="{ icon: 'M', title: 'Modified file' }"
					@addChanges="handleAddChanges"
				/>
			</div>
			<div v-if="!editorStore.isResolvingMergeConflict">
				<div v-for="(file, index) in untrackedFiles" :key="index">
					<SourceControlItemComponent
						:name="file"
						:actions="[{ icon: 'add', title: 'Stage Changes', clickAction: 'addChanges' }]"
						:git-icon="{ icon: 'U', title: 'Untracked file' }"
						@addChanges="handleAddChanges"
					/>
				</div>
			</div>
		</div>
		<div>
			<ButtonComponent
				text="Commit"
				:hint="`Commit staged changes to branch ${currentBranch}`"
				:disabled="isCommitBtnDisabled"
				type="primary"
				@click="commitClicked"
			/>
			<ButtonComponent
				text="Push"
				:hint="`Push changes to branch ${currentBranch}`"
				type="primary"
				:disabled="disablePushButton"
				@click="pushClicked"
			/>
			<ButtonComponent
				v-if="editorStore.isResolvingMergeConflict"
				text="Cancel"
				hint="Cancel merge conflict"
				type="warning"
				@click="cancelMergeClicked"
			/>
		</div>
	</div>
	<GitCommitModal
		v-if="showGitCommitModal"
		v-bind="gitCommitModalForm"
		@close="showGitCommitModal = false"
		@confirm-clicked="onGitCommitModalButtonClick"
	/>
	<GitPushModal
		v-if="showGitPushModal"
		v-bind="gitPushModalForm"
		@close="showGitPushModal = false"
		@confirm-clicked="onGitPushModalButtonClick"
	/>
	<ConfirmCancelMergeModal
		v-if="showConfirmCancelMergeModal"
		v-bind="cancelMergeModalForm"
		@close="showConfirmCancelMergeModal = false"
		@button-click="onConfirmCancelMergeButtonClick"
	/>
</template>

<script setup lang="ts">
	import ButtonComponent from '@/components/ButtonComponent.vue';
	import SourceControlItemComponent from '@/sidebar/panels/sourceControl/SourceControlItemComponent.vue';
	import { useEditorStore, useFileStore, usePromptStore, useTerminalStore } from '@/stores';
	import { computed, ref, type ComputedRef } from 'vue';
	import ConfirmCancelMergeModal, { type ConfirmCancelMergeModalProps } from './modals/ConfirmCancelMergeModal.vue';
	import GitCommitModal, { type ModalGitCommitProps } from './modals/GitCommitModal.vue';
	import GitPushModal, { type ModalGitPushProps } from './modals/GitPushModal.vue';
	const terminalStore = useTerminalStore();
	const editorStore = useEditorStore();
	const fileStore = useFileStore();
	const promptStore = usePromptStore();

	const props = defineProps<{
		files: string[];
		resolvedFiles?: string[];
		otherBranch: string;
	}>();

	const emit = defineEmits<{
		(e: 'switchTabs', value: string, filesWithConflicts: string[], branch: string, filePath: string): void;
		(e: 'concludeMergeResolution'): void;
	}>();

	const disablePushButton = ref<boolean>(true);
	const showGitCommitModal = ref<boolean>(false);
	const showGitPushModal = ref<boolean>(false);
	const showConfirmCancelMergeModal = ref<boolean>(false);

	const existingAuthorName = ref<string>('');
	const existingAuthorEmail = ref<string>('');

	const conflictsPaneHelpText =
		'Click on the ! icon to view the merge conflicts in each file. All conflicts must be resolved to conclude the merge.';

	const gitStatusCode = computed(() => {
		if (terminalStore.gitStatus) {
			return terminalStore.gitStatus[1];
		}
		return null;
	});

	const currentBranch = computed(() => {
		return terminalStore.activeGitBranch;
	});

	const modifiedFiles = computed(() => {
		if (terminalStore.gitStatus) {
			const rawGitStatus: string[] = terminalStore.gitStatus[0].split('\n');
			const start = rawGitStatus.indexOf('Changes not staged for commit:');
			const end = rawGitStatus.indexOf('', start);

			const files = rawGitStatus.slice(start, end);
			const regex = /(\tmodified:)/g;
			const regexFiles = files.map((el) => el.replace(regex, '')).slice(3);
			return regexFiles;
		}
		return [];
	});

	const untrackedFiles = computed(() => {
		if (terminalStore.gitStatus) {
			const rawGitStatus: string[] = terminalStore.gitStatus[0].split('\n');
			const start = rawGitStatus.indexOf('Untracked files:');
			const end = rawGitStatus.indexOf('', start);

			const files = rawGitStatus.slice(start, end);
			const regex = /(\tmodified:|\t)/g;
			const regexFiles = files.map((el) => el.replace(regex, '')).slice(2);
			return regexFiles;
		}
		return [];
	});

	const stagedFiles = computed(() => {
		if (terminalStore.gitStatus) {
			const rawGitStatus: string[] = terminalStore.gitStatus[0].split('\n');
			const start = rawGitStatus.indexOf('Changes to be committed:');
			const end = rawGitStatus.indexOf('', start);

			const staged = rawGitStatus.slice(start, end);
			const regex = /(\tmodified:|\tnew file:)/g;
			const regexFiles = staged.map((el) => el.replace(regex, '')).slice(2);
			return regexFiles;
		}
		return [];
	});

	const unmergedFiles = computed(() => {
		if (terminalStore.gitStatus) {
			const rawGitStatus: string[] = terminalStore.gitStatus[0].split('\n');
			const start = rawGitStatus.indexOf('Unmerged paths:');
			const end = rawGitStatus.indexOf('', start);

			const staged = rawGitStatus.slice(start, end);
			const regex = /(\tboth modified:|\tboth added:)/g;
			const regexFiles = staged.map((el) => el.replace(regex, '')).slice(2);
			return regexFiles;
		}
		return [];
	});

	const isCommitBtnDisabled = computed(() => {
		if (editorStore.isResolvingMergeConflict && (props.files.length === 0 || unmergedFiles.value.length === 0)) {
			return false;
		} else if (!editorStore.isResolvingMergeConflict && stagedFiles.value.length >= 1) {
			return false;
		}
		return true;
	});

	async function handleAddChanges(filePath: string) {
		await editorStore.gitAdd(filePath.trim());
	}

	async function handleDiscardChanges(filePath: string) {
		editorStore.gitUnstage(filePath.trim());
	}

	function commitChanges(msg: string, name: string, email: string) {
		disablePushButton.value = false;
		editorStore.gitCommit(msg, name, email);
	}

	async function pushChanges(username: string, password: string) {
		try {
			await editorStore.gitPush(username, password);
			disablePushButton.value = true;
		} catch (e: any) {
			await promptStore.show({
				title: 'Failed To Push Changes',
				additionalInfo: e,
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
	}

	function commitClicked() {
		showGitCommitModal.value = true;
	}
	function pushClicked() {
		showGitPushModal.value = true;
	}

	function cancelMergeClicked() {
		showConfirmCancelMergeModal.value = true;
	}

	const gitCommitModalForm: ComputedRef<ModalGitCommitProps> = computed(() => {
		return {
			title: 'Commit Changes',
			authorNameProp: existingAuthorName.value,
			authorEmailProp: existingAuthorEmail.value
		};
	});

	function onGitCommitModalButtonClick(data: { commitMsg: string; authorName: string; authorEmail: string }) {
		existingAuthorName.value = data.authorName;
		existingAuthorEmail.value = data.authorEmail;
		commitChanges(data.commitMsg, data.authorName, data.authorEmail);
		showGitCommitModal.value = false;
	}

	const gitPushModalForm: ComputedRef<ModalGitPushProps> = computed(() => {
		return {
			title: 'Push Changes',
			username: editorStore.gitUsername,
			password: editorStore.gitPassword
		};
	});

	function onGitPushModalButtonClick(data: { username: string; password: string }) {
		editorStore.setGitUsername(data.username);
		editorStore.setGitPassword(data.password);
		pushChanges(data.username, data.password);
		showGitPushModal.value = false;
		if (editorStore.isResolvingMergeConflict) {
			emit('concludeMergeResolution');
		}
	}

	function addAll() {
		editorStore.gitAddAll();
	}

	async function viewMergeConflicts(filePath: string) {
		try {
			const path = await fileStore.formatGitFilepath(filePath);
			const file = fileStore.findFileByPath(path);
			if (!file) {
				await promptStore.failedAlert(
					'Error getting merge conflicts',
					'Failed to find file from path "' + filePath + '" (file does not exist).'
				);
				return;
			}

			await editorStore.openFileInEditor(file.id, filePath, true, props.otherBranch);
			await editorStore.openFileInEditor(file.id, filePath, false, props.otherBranch);
			emit('switchTabs', 'Merge Resolution', [], '', filePath);
		} catch (e) {
			await promptStore.show({
				title: 'Error viewing merge conflicts',
				additionalInfo:
					'There was an issue getting merge conflicts. The merge will be cancelled. Please merge the branches from a terminal and resolve the conflicts manually by opening the file in a text editor and choosing the changes you which to keep.',
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
			resetMerge();
		}
	}

	const cancelMergeModalForm: ComputedRef<ConfirmCancelMergeModalProps> = computed(() => {
		return {
			title: 'Cancel Merge',
			buttons: [
				{
					text: 'Confirm',
					type: 'primary'
				},
				{
					text: 'Cancel',
					type: 'secondary'
				}
			]
		};
	});

	function onConfirmCancelMergeButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (data.buttonName == 'Cancel') {
			showConfirmCancelMergeModal.value = false;
			return;
		}

		if (data.buttonName == 'Confirm') {
			resetMerge();
			showConfirmCancelMergeModal.value = false;
		}
	}

	async function resetMerge() {
		try {
			await editorStore.cancelGitMerge();
			emit('concludeMergeResolution');
		} catch (e) {
			console.error(e);
		}
	}
</script>

<style scoped>
	.git-actions {
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: space-between;
	}

	.staged-changes-block {
		padding-bottom: 8px;
	}

	.git-changes-heading {
		display: flex;
		flex-direction: row;
		justify-content: space-between;
		align-items: center;
		padding-right: 16px;
	}

	.actions-title {
		color: var(--color-primary);
		letter-spacing: 1px;
		cursor: default;
		display: flex;
		align-items: center;
	}

	.add-all-btn {
		opacity: 0.6;
		cursor: pointer;
	}

	.add-all-btn:hover {
		opacity: 1;
	}

	.all-resolved-msg {
		display: flex;
		justify-content: center;
	}

	.help-icon {
		margin-left: 6px;
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.6;
		cursor: help;
	}
</style>
