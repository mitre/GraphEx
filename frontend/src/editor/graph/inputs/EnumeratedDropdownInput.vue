<template>
	<div class="dropdown-enum-input-wrapper" ref="wrapper" :disabled="editorStore.isResolvingMergeConflict">
		<div @click.stop.prevent="toggleDropdown" class="dropdown-header">
			<span class="dropdown-value no-select">{{ selectedOption || 'Select an Option' }}</span>
			<div class="dropdown-icon material-icons">expand_more</div>
		</div>
		<div v-if="isOpen" class="dropdown-contents-container custom-scrollbar" ref="dropdown">
			<span v-for="option in enumOptions" :key="option" class="dropdown-option no-select" @click="selectOption(option)">
				{{ option }}
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { useEditorStore } from '@/stores';
	import { ref } from 'vue';

	const props = defineProps<{
		fieldName?: string;
		value: string;
		enumOptions: string[];
	}>();

	const editorStore = useEditorStore();
	const dropdown = ref<HTMLDivElement>();
	const wrapper = ref<HTMLDivElement>();
	const emit = defineEmits<{ (e: 'update', newValue: string): void }>();

	const isOpen = ref(false);
	const selectedOption = ref(props.value);

	function toggleDropdown() {
		if (editorStore.isResolvingMergeConflict) {
			return;
		}
		if (!isOpen.value) {
			open();
		} else {
			close();
		}
	}

	function selectOption(option: string) {
		selectedOption.value = option;
		emit('update', option);
		isOpen.value = false;
	}

	async function open() {
		isOpen.value = true;
		window.addEventListener('mousedown', onMouseClick, { capture: true });
	}

	async function close() {
		isOpen.value = false;
		window.removeEventListener('mousedown', onMouseClick, { capture: true });
	}

	function onMouseClick(event: MouseEvent) {
		const target = event.target;
		if (
			target &&
			target instanceof Node &&
			((dropdown.value && dropdown.value.contains(target)) || (wrapper.value && wrapper.value.contains(target)))
		) {
			// Target is contained within the dropdown, do not close
			// This is left up to the parent
			return;
		}

		close();
	}
</script>

<style scoped>
	.dropdown-enum-input-wrapper {
		width: 100%;
		background-color: var(--color-editor-text-input-background);
		border: 2px solid var(--color-editor-text-input-border);
		padding: 2px 6px;
		box-shadow: 0px 0px 6px 1px rgba(0, 0, 0, 0.3);
		position: relative;
		cursor: pointer;
		border-radius: 4px;
	}

	.dropdown-enum-input-wrapper[disabled='true'] {
		cursor: default;
	}

	.dropdown-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.dropdown-value {
		padding: 8px;
		font-size: 1rem;
	}

	.dropdown-icon {
		font-size: 1.4rem;
		color: var(--color-text);
		opacity: 0.7;
	}

	.dropdown-contents-container {
		position: absolute;
		top: 100%;
		left: 0;
		width: 100%;
		z-index: 1000;
		max-height: 400px;
		display: flex;
		flex-direction: column;
		background-color: var(--color-background-primary);
		border: 2px solid var(--color-editor-text-input-border);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
		border-radius: 4px;
		overflow: auto;
	}

	.dropdown-option {
		padding: 8px;
		cursor: pointer;
	}

	.dropdown-option:hover {
		background-color: var(--color-foreground-secondary);
	}
</style>
