<template>
	<div
		class="input-field-container"
		:floating-label="props.floatingLabel"
		:focused="focused"
		:label-lifted="isLabelLifted"
		:error="!!props.error"
		:disabled="disabled"
		@click.stop.prevent="onClick"
		@dblclick.stop.prevent
	>
		<span v-if="props.floatingLabel && props.label" class="input-field-label no-select" :label-lifted="isLabelLifted">{{
			props.label
		}}</span>

		<textarea
			class="input-field"
			:value="value"
			@mousedown.stop
			@click.stop
			@dblclick.stop.prevent
			@keydown="onKeyDown"
			@input.stop.prevent="onInput"
			@change.stop.prevent="onChange"
			@focus="onFocus"
			@blur="onBlur"
			autocomplete="off"
			autocorrect="off"
			spellcheck="false"
			:placeholder="props.floatingLabel ? undefined : props.label"
			:rows="rows"
			:cols="cols"
			:disabled="disabled"
			ref="inputRef"
		/>

		<div class="input-controls">
			<span
				v-if="props.clearButton && !disabled"
				class="clear-icon material-icons"
				title="Clear"
				@click.stop="clearValue"
			>
				clear
			</span>
			<span v-if="props.error" class="error-icon material-icons" :title="props.error" @click.stop> priority_high </span>
			<slot></slot>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { useContextmenuStore, useEditorStore } from '@/stores';
	import { computed, nextTick, onMounted, ref } from 'vue';
	import type { MenuItem, MenuOptions } from './MenuComponent.vue';

	export interface InputFieldProps {
		/** The current value of this field. */
		value: string;

		/** The label / placeholder for this field. */
		label?: string;

		/** Whether to use a floating label. */
		floatingLabel?: boolean;

		/** Minimum width (in characters) of the input field. */
		minWidth?: number;

		/** Whether this field accepts newline characters. */
		multiline?: boolean;

		/** The error message for this field. */
		error?: string;

		/** Whether to enable the clear button or not */
		clearButton?: boolean;
	}

	const props = withDefaults(defineProps<InputFieldProps>(), {
		floatingLabel: false,
		minWidth: 16,
		multiline: false,
		clearButton: true
	});

	const emit = defineEmits<{
		(e: 'focus'): void;
		(e: 'blur'): void;
		(e: 'input', value: string): void;
		(e: 'change', value: string): void;
	}>();

	const contextmenuStore = useContextmenuStore();
	const editorStore = useEditorStore();

	const focused = ref<boolean>(false);
	const inputRef = ref<HTMLTextAreaElement>();

	const disabled = computed(() => {
		return editorStore.isResolvingMergeConflict;
	});

	function onClick() {
		if (disabled.value) {
			return;
		}
		inputRef.value!.focus();
	}

	function onFocus() {
		if (disabled.value) {
			return;
		}
		focused.value = true;
		emit('focus');
	}

	function onBlur() {
		focused.value = false;
		emit('blur');
	}

	function onKeyDown(event: KeyboardEvent) {
		if (disabled.value) {
			event.preventDefault();
			return;
		}
		if (event.key == 's' && event.ctrlKey) {
			event.preventDefault();
			return;
		}

		if (event.ctrlKey && event.key == ']') {
			indent();
			event.preventDefault();
			return;
		}

		if (event.ctrlKey && event.key == '[') {
			unindent();
			event.preventDefault();
			return;
		}

		event.stopPropagation();

		if (!props.multiline && event.key == 'Enter') {
			event.preventDefault();
			return;
		}

		if (event.key == 'Tab') {
			event.preventDefault();
			const target = event.target as HTMLInputElement;
			const start = target.selectionStart;
			const end = target.selectionEnd;
			if (start === null || end === null) {
				return;
			}

			emit('input', target.value.substring(0, start) + '\t' + target.value.substring(end));
			nextTick(() => {
				target.selectionStart = start + 1;
				target.selectionEnd = end + 1;
			});
			return;
		}
	}

	function onInput(event: Event) {
		if (disabled.value) {
			return;
		}
		if (!event.target) return;

		const target = event.target as HTMLTextAreaElement;
		let newValue = target.value;

		if (!props.multiline) {
			newValue = newValue.replace(/\n/g, '');
		}

		emit('input', newValue);
	}

	function onChange(event: Event) {
		if (disabled.value) {
			return;
		}
		if (!event.target) return;

		const target = event.target as HTMLTextAreaElement;
		let newValue = target.value;

		if (!props.multiline) {
			newValue = newValue.replace(/\n/g, '');
		}

		emit('change', newValue);
	}

	function clearValue() {
		if (disabled.value) {
			return;
		}
		emit('change', '');
	}

	function indent() {
		if (disabled.value) {
			return;
		}
		const inputEl = inputRef.value;
		if (!inputEl) return;

		const selectionStart = inputEl.selectionStart;
		const selectionEnd = inputEl.selectionEnd;
		const lines = props.value.split('\n');
		let new_string = '';

		if (lines.length <= 1) {
			// no newlines
			new_string = '\t' + props.value;
		} else if (selectionStart === selectionEnd) {
			// no selection
			for (let i = 0; i < lines.length; i++) {
				const line = lines[i];
				new_string += '\t' + line;
				if (i + 1 < lines.length) new_string += '\n';
			}
		} else {
			// highlighted selection
			// We also know there is at least one newline in the whole text area
			let sel = props.value.slice(selectionStart, selectionEnd);
			const sel_lines = sel.split('\n');
			const lastNewlineIndex = props.value.lastIndexOf('\n', selectionStart);

			if (sel_lines.length > 1) {
				// newlines in the selection
				// we want to indent every line that follows a newline
				if (sel_lines[0] == '') {
					// if the selection started on a newline character, ignore that part
					// the newline doesn't show up when highlighting with the mouse
					sel_lines.shift();
				}
				let new_sel = sel_lines.join('\n\t');

				// we also need to find the newline that comes before our selection and indent that
				if (lastNewlineIndex <= 0) {
					new_string = '\t' + props.value.slice(0, selectionStart) + new_sel + props.value.slice(selectionEnd);
				} else {
					new_string =
						props.value.slice(0, lastNewlineIndex + 1) +
						'\t' +
						props.value.slice(lastNewlineIndex + 1, selectionStart) +
						new_sel +
						props.value.slice(selectionEnd);
				}
			} else {
				// no newlines in the selection
				// find the previous newline and insert a tab after it
				if (lastNewlineIndex <= 0) {
					new_string = '\t' + props.value;
				} else {
					new_string = props.value.slice(0, lastNewlineIndex + 1) + '\t' + props.value.slice(lastNewlineIndex + 1);
				}
			}
		}
		emit('change', new_string);
	}

	function unindent() {
		if (disabled.value) {
			return;
		}
		const inputEl = inputRef.value;
		if (!inputEl) return;

		const selectionStart = inputEl.selectionStart;
		const selectionEnd = inputEl.selectionEnd;
		const lines = props.value.split('\n');
		let new_string = props.value;

		if (lines.length <= 1) {
			// no newlines
			if (props.value.startsWith('\t')) {
				new_string = props.value.slice(1);
			}
		} else if (selectionStart === selectionEnd) {
			new_string = '';
			for (let i = 0; i < lines.length; i++) {
				const line = lines[i];
				let temp = line;
				if (line.startsWith('\t')) {
					temp = line.slice(1);
				}
				new_string += temp;
				if (i + 1 < lines.length) new_string += '\n';
			}
		} else {
			// highlighted selection
			// We also know there is at least one newline in the whole text area
			let sel = props.value.slice(selectionStart, selectionEnd);
			const lastNewlineIndex = props.value.lastIndexOf('\n\t', selectionStart);

			if (sel.split('\n').length > 1) {
				const sel_split = sel.split('\n\t');
				if (sel_split[0] == '') {
					// if the selection started on a newline character, ignore that part
					// the newline doesn't show up when highlighting with the mouse
					sel_split.shift();
				}
				let new_sel = sel_split.join('\n');

				// we also need to find the newline that comes before our selection and indent that
				if (lastNewlineIndex <= 0) {
					new_string = props.value.slice(0, selectionStart) + new_sel + props.value.slice(selectionEnd);
					if (new_string.startsWith('\t')) {
						new_string = new_string.slice(1);
					}
				} else {
					new_string =
						props.value.slice(0, lastNewlineIndex + 1) +
						props.value.slice(lastNewlineIndex + 2, selectionStart) +
						new_sel +
						props.value.slice(selectionEnd);
				}
			} else {
				// no newlines in the selection
				// find the previous newline
				if (lastNewlineIndex <= 0) {
					if (props.value.startsWith('\t')) {
						new_string = props.value.slice(1);
					}
				} else {
					new_string = props.value.slice(0, lastNewlineIndex + 1) + props.value.slice(lastNewlineIndex + 2);
				}
			}
		}
		emit('change', new_string);
	}

	async function writeClipboardText(text: string) {
		try {
			await navigator.clipboard.writeText(text);
		} catch (error: any) {
			console.error(error.message);
		}
	}

	function copyText(isCut: boolean) {
		const inputEl = inputRef.value;
		if (!inputEl) return;

		const selectionStart = inputEl.selectionStart;
		const selectionEnd = inputEl.selectionEnd;
		let new_string = props.value;

		if (selectionStart !== selectionEnd) {
			// Highlighted value
			let sel = props.value.slice(selectionStart, selectionEnd);
			writeClipboardText(sel);
			if (isCut) {
				// Delete the copied string
				new_string = props.value.replace(sel, '');
			}
		}

		emit('change', new_string);
	}

	function pasteText() {
		if (disabled.value) {
			return;
		}
		const inputEl = inputRef.value;
		if (!inputEl) return;
		// console.log('inputEl', inputEl, props.value);

		const selectionStart = inputEl.selectionStart;
		const selectionEnd = inputEl.selectionEnd;
		let new_string = props.value;

		navigator.clipboard
			.readText()
			.then((clipText) => {
				if (selectionStart === selectionEnd) {
					// Paste text where cursor is
					new_string = [props.value.slice(0, selectionStart), clipText, props.value.slice(selectionStart)].join('');
				} else {
					// Replace highlighted text with pasted text
					let sel = props.value.slice(selectionStart, selectionEnd);
					let tempString = props.value.replace(sel, '');

					new_string = [tempString.slice(0, selectionStart), clipText, tempString.slice(selectionStart)].join('');
				}
			})
			.then(() => emit('change', new_string));
	}

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Indent',
			description: 'Indent (selection or all lines, ctrl+] )',
			disabled: disabled.value ?? false,
			callback: () => {
				indent();
			}
		});

		entries.push({
			label: 'Unindent',
			description: 'Unindent (selection or all lines, ctrl+[ )',
			disabled: disabled.value ?? false,
			callback: () => {
				unindent();
			},
			divider: true
		});
		entries.push({
			label: 'Copy',
			description: 'Copy (selection or all lines, ctrl+c )',
			callback: () => {
				copyText(false);
			}
		});
		entries.push({
			label: 'Cut',
			description: 'Cut (selection or all lines, ctrl+x )',
			disabled: disabled.value ?? false,
			callback: () => {
				copyText(true);
			}
		});
		entries.push({
			label: 'Paste',
			description: 'Paste (selection or all lines, ctrl+v )',
			disabled: disabled.value ?? false,
			callback: () => {
				pasteText();
			}
		});

		return { items: entries };
	}

	const isLabelLifted = computed(() => {
		return focused.value || !!props.value;
	});

	const rows = computed(() => {
		return Math.max(props.value.split('\n').length, 1);
	});

	const cols = computed(() => {
		let maxLineLength = 0;
		for (const line of String(props.value).split('\n')) {
			let lineLength = line.replace(/\t/g, ' '.repeat(4)).length;
			if (lineLength > maxLineLength) {
				maxLineLength = lineLength;
			}
		}
		return Math.max(props.minWidth, maxLineLength);
	});

	onMounted(() => {
		contextmenuStore.getContextMenu('root').addHook(inputRef.value!, openContextMenu, true);
	});
</script>

<style scoped>
	.input-field-container {
		display: flex;
		flex-direction: row;
		align-items: center;
		cursor: text;
		position: relative;
		padding: 4px;
		background-color: var(--color-foreground-secondary);
		border: 1px solid var(--color-border);
		border-radius: 4px;
		font-size: 1rem;
	}

	.input-field-container[focused='true'][error='false'] {
		border-color: var(--color-border-highlight);
	}

	.input-field-container[error='true'] {
		border-color: var(--color-error);
	}

	.input-field-container[disabled='true'] {
		cursor: default;
	}

	.input-field-label {
		position: absolute;
		top: calc(50% - 0.5em);
		font-size: 0.8em;
		pointer-events: none;
		transition: all 200ms cubic-bezier(0, 0, 0.2, 1) 0ms;
		white-space: pre;
		color: var(--color-text-secondary);
	}

	.input-field-label[label-lifted='true'] {
		top: 4px;
		font-size: 0.6em;
		color: var(--color-primary);
	}

	.input-field {
		width: 100%;
		padding: 0px;
		background: none;
		border: none;
		resize: none;
		white-space: pre;
		overflow: hidden;
		tab-size: 4;
		color: var(--color-text);
		font-family: 'Roboto Mono';
		font-size: 0.9rem;
	}

	.input-field-container[floating-label='true'] .input-field {
		margin-top: 1em;
		margin-bottom: 5px;
	}

	.input-controls {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.error-icon {
		font-size: 1em;
		cursor: help;
		color: var(--color-error);
	}

	.clear-icon {
		font-size: 1em;
		cursor: pointer;
		color: var(--color-border-highlight);
		opacity: 0;
	}

	.input-field-container:hover .clear-icon {
		opacity: 0.6;
	}

	.input-field-container:hover .clear-icon:hover {
		opacity: 1;
	}
</style>
