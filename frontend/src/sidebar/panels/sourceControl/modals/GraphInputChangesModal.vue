<template>
	<ModalComponent :title="props.title" @close="onClose">
		<template v-slot:contents>
			<div class="current-branch-block">
				<div class="branch-label">Current:</div>
				<div v-if="onlyOnOneBranch">
					{{ props.inputChanges.only_on_this_branch ? props.inputChanges.this_branch_yaml : 'Deleted' }}
				</div>
				<div v-else>
					<div v-for="(key, index) in changeKeysList" :key="index">
						<div v-if="keyChanged(key)" class="changed-element">
							{{ key }}: {{ props.inputChanges[`this_branch_${key}`] }}
						</div>
					</div>
				</div>
			</div>
			<div>
				<div class="branch-label">Incoming:</div>
				<div v-if="onlyOnOneBranch">
					{{ props.inputChanges.only_on_other_branch ? props.inputChanges.other_branch_yaml : 'Deleted' }}
				</div>
				<div v-else>
					<div v-for="(key, index) in changeKeysList" :key="index">
						<div v-if="keyChanged(key)" class="changed-element">
							{{ key }}: {{ props.inputChanges[`other_branch_${key}`] }}
						</div>
					</div>
				</div>
			</div>
		</template>
		<template v-slot:footer>
			<div class="modal-form-footer">
				<ButtonComponent text="Choose Current" type="primary" @click="chooseInput(true)" />
				<ButtonComponent text="Choose Incoming" type="secondary" @click="chooseInput(false)" />
			</div>
		</template>
	</ModalComponent>
</template>

<script setup lang="ts">
	import ButtonComponent from '@/components/ButtonComponent.vue';
	import ModalComponent from '@/components/ModalComponent.vue';
	import { useEditorStore } from '@/stores';
	import { computed } from 'vue';

	export interface ModalGraphInputChangesProps {
		title: string;
		inputId: string;
		inputChanges: any;
	}

	const editorStore = useEditorStore();
	const props = defineProps<ModalGraphInputChangesProps>();

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'confirmClicked'): void;
		(e: 'resolvedInput', id: string): void;
	}>();

	const onlyOnOneBranch = computed(() => {
		return props.inputChanges.only_on_this_branch || props.inputChanges.only_on_other_branch;
	});

	const changeKeysList = ['isList', 'descriptions', 'category', 'enumOptions', 'defaultValue', 'isPassword'];

	function keyChanged(keyName: string) {
		const inputChangeKeys = Object.keys(props.inputChanges);
		if (inputChangeKeys.includes(`${keyName}_changed`)) {
			if (props.inputChanges[`${keyName}_changed`] === true) {
				return true;
			}
			return false;
		}
		return false;
	}
	function onClose() {
		emit('close');
	}

	function chooseInput(isCurrent: boolean) {
		if (isCurrent) {
			if (onlyOnOneBranch.value) {
				if (props.inputChanges.only_on_this_branch) {
					// Only set the input if it exists on the chosen branch
					editorStore.setChosenInputConflicts({ [props.inputId]: props.inputChanges.this_branch_yaml });
				}
			} else {
				editorStore.setChosenInputConflicts({ [props.inputId]: props.inputChanges.this_branch_yaml });
			}
		} else {
			if (onlyOnOneBranch.value) {
				if (props.inputChanges.only_on_other_branch) {
					// Only set the input if it exists on the chosen branch
					editorStore.setChosenInputConflicts({ [props.inputId]: props.inputChanges.other_branch_yaml });
				}
			} else {
				editorStore.setChosenInputConflicts({ [props.inputId]: props.inputChanges.other_branch_yaml });
			}
		}
		emit('resolvedInput', props.inputId);
	}
</script>

<style scoped>
	:deep(.modal-popup) {
		width: 50vw;
		overflow: hidden;
	}

	.branch-label {
		padding-bottom: 8px;
		font-size: large;
	}

	.current-branch-block {
		padding-bottom: 16px;
	}

	.changed-element {
		padding-left: 16px;
	}

	.modal-form-footer {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-evenly;
	}
</style>
