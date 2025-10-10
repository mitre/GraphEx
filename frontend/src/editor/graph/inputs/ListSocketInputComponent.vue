<template>
	<template v-if="props.socket.metadata.canHaveField && Array.isArray(props.socket.fieldValue)">
		<DropdownComponent :teleport="props.socket.graph.ui.viewportElement" :disabled="props.disabled">
			<span class="list-socket-input-button no-select" title="Inline list contents">
				<span class="list-socket-input-more-icon material-icons">menu_open</span>
				({{ props.socket.fieldValue.length }})
			</span>

			<template v-slot:dropdown>
				<div class="list-socket-dropdown-contents">
					<span class="list-socket-dropdown-empty no-select" v-if="props.socket.fieldValue.length == 0">Empty...</span>

					<div
						class="list-socket-dropdown-item"
						v-for="(item, index) in props.socket.fieldValue"
						:key="index"
						@dragover="onDragOver($event, index)"
					>
						<InputField
							v-if="props.socket.metadata.datatype == 'String'"
							:value="String(item)"
							:min-width="24"
							@input="(val: any) => updateValue(index, val)"
							@change="(val: any) => onChange(index, val)"
							multiline
						/>

						<InputField
							v-if="props.socket.metadata.datatype == 'Number'"
							:value="String(item)"
							:min-width="24"
							:error="numberError(item)"
							@input="(val: any) => updateNumberValue(index, val)"
							@change="(val: any) => onChangeNumber(index, val)"
						/>

						<BooleanSliderInput
							v-if="props.socket.metadata.datatype == 'Boolean'"
							:value="item"
							@update="(val: any) => onChange(index, val)"
						/>

						<span
							class="list-socket-dropdown-move material-icons"
							title="Move this list item."
							draggable="true"
							@dragstart="onDragStart($event, index)"
						>
							drag_handle
						</span>

						<span
							class="list-socket-dropdown-remove material-icons"
							title="Delete this list item."
							@click.stop="() => deleteEntry(index)"
						>
							delete_forever
						</span>
					</div>

					<div class="list-socket-dropdown-footer">
						<span class="list-socket-dropdown-add no-select" @click.stop="addNewEntry">+ Add</span>
					</div>
				</div>
			</template>
		</DropdownComponent>
	</template>
</template>

<script setup lang="ts">
	import DropdownComponent from '@/components/DropdownComponent.vue';
	import InputField from '@/components/InputField.vue';
	import BooleanSliderInput from '@/editor/graph/inputs/BooleanSliderInput.vue';
	import type { Socket } from '@/graph';
	import { ref } from 'vue';

	const props = defineProps<{
		/** The socket for this input. */
		socket: Socket;
		disabled?: boolean;
	}>();

	const draggedIndex = ref<number>(-1);

	function addNewEntry() {
		if (props.disabled) {
			return;
		}
		props.socket.addNewFieldListValue();
	}

	function deleteEntry(index: number) {
		if (props.disabled) {
			return;
		}
		props.socket.deleteFieldListValue(index);
	}

	function updateValue(index: number, newValue: any) {
		if (props.disabled) {
			return;
		}
		props.socket.setFieldListValue(index, newValue);
	}

	function updateNumberValue(index: number, newValue: any) {
		if (props.disabled) {
			return;
		}
		if ((typeof newValue === 'string' && newValue.trim().length == 0) || isNaN(Number(newValue))) {
			updateValue(index, newValue);
		} else {
			updateValue(index, Number(newValue));
		}
	}

	async function onChange(index: number, newValue: any) {
		updateValue(index, newValue);
	}

	async function onChangeNumber(index: number, newValue: any) {
		updateNumberValue(index, newValue);
	}

	function numberError(val: any) {
		if (String(val).length == 0) {
			return 'Empty values are not permitted.';
		}

		if (typeof val !== 'number' || isNaN(val)) {
			return 'Not a number.';
		}

		if (!isFinite(val)) {
			return 'Not finite.';
		}

		return undefined;
	}

	function onDragStart(ev: DragEvent, index: number) {
		if (props.disabled) {
			return;
		}
		draggedIndex.value = index;
		ev.dataTransfer?.setData('listsocketFieldMove', String(index));
	}

	function onDragOver(ev: DragEvent, index: number) {
		if (props.disabled) {
			return;
		}
		if (ev.dataTransfer && ev.dataTransfer.types) {
			const otherIndex = draggedIndex.value;
			if (otherIndex == index) return;
			props.socket.reorderFieldListValue(index, otherIndex);
			draggedIndex.value = index;
		}
	}
</script>

<style scoped>
	.list-socket-input-button {
		display: flex;
		flex-direction: row;
		align-items: center;
		font-size: 0.8rem;
		color: var(--color-editor-node-body-text-secondary);
	}

	.list-socket-input-button:hover {
		color: var(--color-editor-node-body-text-primary);
	}

	.list-socket-input-more-icon {
		font-size: 1.2rem;
		margin-right: 1px;
	}

	.list-socket-dropdown-contents {
		min-width: 8rem;
		display: flex;
		flex-direction: column;
		padding: 6px;
		background-color: var(--color-foreground-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 0px 0px 8px 4px rgba(0, 0, 0, 0.4);
		border-radius: 4px;
	}

	.list-socket-dropdown-empty {
		width: 100%;
		text-align: center;
		font-size: 0.8rem;
		font-style: italic;
		color: var(--color-text);
		opacity: 0.6;
	}

	.list-socket-dropdown-item {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.list-socket-dropdown-item:not(:first-child) {
		margin-top: 4px;
	}

	.list-socket-dropdown-remove {
		margin-left: 4px;
		padding: 2px;
		border-radius: 3px;
		font-size: 1rem;
		color: rgb(--color-text);
		opacity: 0.4;
		cursor: pointer;
	}

	.list-socket-dropdown-remove:hover {
		opacity: 0.8;
		background-color: var(--color-foreground-secondary);
	}

	.list-socket-dropdown-move {
		font-size: 1rem;
		color: rgb(--color-text);
		opacity: 0.4;
		cursor: pointer;
	}

	.list-socket-dropdown-move:hover {
		opacity: 0.8;
		background-color: var(--color-foreground-secondary);
	}

	.list-socket-dropdown-footer {
		margin-top: 8px;
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
	}

	.list-socket-dropdown-add {
		padding: 2px 6px;
		font-size: 0.9rem;
		color: var(--color-text);
		opacity: 0.8;
		border-radius: 3px;
		cursor: pointer;
	}

	.list-socket-dropdown-add:hover {
		opacity: 1;
		background-color: var(--color-foreground-secondary);
	}

	.input-field-container {
		width: 100%;
		background-color: var(--color-editor-text-input-background);
		border-color: var(--color-editor-text-input-border);
		padding: 2px 2px 2px 6px;
		box-shadow: 0px 0px 6px 1px rgba(0, 0, 0, 0.3);
	}

	.input-field-container[focused='true'][error='false'] {
		border-color: var(--color-editor-text-input-border-highlight);
	}

	.input-field-container[error='true'] {
		border-color: var(--color-editor-text-input-error);
	}
</style>
