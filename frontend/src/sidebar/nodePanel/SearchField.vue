<template>
	<div class="search-field">
		<span class="material-icons search-icon"> search </span>
		<input
			@keydown.stop
			@input="onInput"
			:value="props.modelValue"
			class="search-input"
			:placeholder=props.placeholder
			tabindex="0"
			ref="theInput"
		/>
		<div v-if="!!props.modelValue" class="material-icons cancel-search" title="Clear Input" @click.stop="clear">
			close
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

	const props = defineProps<{
		modelValue: string;
		placeholder: string;
	}>();

	const theInput = ref<HTMLInputElement>();

	const emit = defineEmits<{
		(e: 'update:modelValue', value: string): void;
	}>();

	function onInput(event: Event) {
		if (!event.target) {
			return;
		}

		const target = event.target as HTMLInputElement;
		emit('update:modelValue', target.value);
	}

	function clear() {
		emit('update:modelValue', '');
	}

	function focus() {
		if (theInput.value) {
			theInput.value.focus();
			theInput.value.select();
		}
	}

	function hasFocus() {
		if (theInput.value && document.activeElement == theInput.value) {
			return true;
		}
		return false;
	}

	defineExpose({
		focus,
		hasFocus
	});
</script>

<style scoped>
	.search-field {
		position: relative;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.search-icon {
		position: absolute;
		font-size: 1.3rem;
		left: 6px;
		color: var(--color-text);
		opacity: 0.5;
		transition: opacity 100ms ease;
	}

	.search-input {
		width: 100%;
		padding: 8px calc(12px + 1.4rem);
		color: var(--color-text);
		background-color: var(--color-component-sidebar-searchbar);
		border: 1px solid var(--color-component-sidebar-searchbar-border);
		border-radius: 4px;
	}

	.cancel-search {
		position: absolute;
		right: 8px;
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.4;
		transition: opacity 50ms ease;
	}

	.cancel-search:hover {
		opacity: 1;
		cursor: pointer;
	}
</style>
