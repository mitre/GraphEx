<template>
	<ModalComponent :title="props.title" @close="onClose">
		<template v-slot:contents>
			<div class="modal-form-loader-container" v-if="props.loading">
				<RingLoader width="50px" height="50px" color="rgb(255, 255, 255)" thickness="2px" />
			</div>
			<div v-else class="modal-form-contents-container custom-scrollbar">
				<div class="modal-additional-info-contents" v-if="truncatedAdditionalInfo.length != 0">
					<span class="modal-additional-info-text">{{ truncatedAdditionalInfo }}</span>
				</div>

				<template v-if="categories.length <= 0">
					<template v-for="(entry, index) in entries" :key="index">
						<ModalFormEntry
							v-bind="entry"
							@toggled="(val: ToggleValue) => toggleEntry(index, val)"
							@update-value="(val: InputValue) => updateValue(index, val)"
							@remove-list-entry="(idx: ListIndexValue) => removeListEntry(index, idx)"
							@add-list-entry="(data?:CompositeEntryMetadata) => addListEntry(index,data)"
							@update-list-value="(data:ListInputValue) => updateListValue(index, data)"
						/>
					</template>
				</template>
				<template v-else>
					<template v-for="(entry, index) in entries" :key="index">
						<ModalFormEntry
							v-if="entry.category === activeTab"
							v-bind="entry"
							@toggled="(val: ToggleValue) => toggleEntry(index, val)"
							@update-value="(val: InputValue) => updateValue(index, val)"
							@remove-list-entry="(idx: ListIndexValue) => removeListEntry(index, idx)"
							@add-list-entry="() => addListEntry(index)"
							@update-list-value="(data:ListInputValue) => updateListValue(index, data)"
						/>
					</template>
				</template>
			</div>
		</template>
		<template v-slot:footer>
			<div class="error-container" v-if="anyCategoryHasError">
				<span class="error-styling global-error-icon material-icons"> report </span>
				<span class="error-styling">Resolve Errors to Continue</span>
			</div>
			<div class="modal-form-footer" v-if="!props.loading">
				<template v-for="(button, index) in props.buttons" :key="index">
					<ButtonComponent v-bind="button" @click="buttonClick(index, button.text)" />
				</template>
			</div>
		</template>
		<template v-slot:tabs>
			<div class="tabs-container custom-scrollbar" v-if="categories.length > 0">
				<template v-for="(category, index) in categories" :key="index">
					<ModalTab
						:tab-name="category"
						:active="activeTab === category"
						:error="categoryErrors.includes(category)"
						@clicked="tabClicked(category)"
					></ModalTab>
				</template>
			</div>
		</template>
	</ModalComponent>
</template>

<script setup lang="ts">
	import type { ButtonProps } from '@/components/ButtonComponent.vue';
	import ButtonComponent from '@/components/ButtonComponent.vue';
	import ModalComponent from '@/components/ModalComponent.vue';
	import RingLoader from '@/components/RingLoader.vue';
	import type {
		CompositeEntryMetadata,
		InputValue,
		ListIndexValue,
		ListInputValue,
		ModalFormEntryProps,
		ToggleValue
	} from '@/components/modalForm/ModalFormEntry.vue';
	import ModalFormEntry from '@/components/modalForm/ModalFormEntry.vue';
	import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
	import ModalTab from './ModalTab.vue';

	export interface ModalFormProps {
		title: string;
		additionalInfo?: string;
		entries: Array<ModalFormEntryProps>;
		buttons: Array<ButtonProps>;
		loading?: boolean;
	}

	const KEYBINDINGS: { [shorthand: string]: () => void } = {
		Enter: () => {
			for (let i = 0; i < props.buttons.length; i++) {
				const b = props.buttons[i];
				if (!b.disabled && b.type == 'primary') {
					buttonClick(i, b.text);
					return;
				}
			}
		}
	};

	const props = defineProps<ModalFormProps>();

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'toggled', data: ToggleValue): void;
		(e: 'addListEntry', metadata: CompositeEntryMetadata): void;
		(e: 'updateListValue', data: ListInputValue): void;
		(e: 'removeListEntry', index: ListIndexValue): void;

		(e: 'updateValue', inputValue: InputValue): void;
		(e: 'buttonClick', data: { buttonIndex: number; buttonName: string }): void;
	}>();

	const activeTab = ref<string>('');
	const categoriesLength = ref<number>(0);

	function onClose() {
		emit('close');
	}

	function buttonClick(buttonIndex: number, name: string) {
		emit('buttonClick', { buttonIndex: buttonIndex, buttonName: name });
	}

	function toggleEntry(entryIndex: number, subData: ToggleValue) {
		emit('toggled', {
			metadata: subEntryMetadata(entryIndex, subData.metadata),
			value: subData.value
		});
	}

	function updateValue(entryIndex: number, subData: InputValue) {
		emit('updateValue', {
			metadata: subEntryMetadata(entryIndex, subData.metadata),
			value: subData.value
		});
	}

	function removeListEntry(entryIndex: number, subData: ListIndexValue) {
		emit('removeListEntry', {
			metadata: subEntryMetadata(entryIndex, subData.metadata),
			index: subData.index
		});
	}

	function addListEntry(entryIndex: number, subData?: CompositeEntryMetadata) {
		emit('addListEntry', subEntryMetadata(entryIndex, subData));
	}

	function updateListValue(entryIndex: number, subData: ListInputValue) {
		emit('updateListValue', {
			metadata: subEntryMetadata(entryIndex, subData.metadata),
			index: subData.index,
			value: subData.value
		});
	}

	function subEntryMetadata(index: number, subData?: CompositeEntryMetadata): CompositeEntryMetadata {
		return {
			name: props.entries[index].label,
			index: index,
			subMetadata: !subData || subData.index === -1 ? undefined : subData // This is just to get around Typescript being annoying.
		};
	}

	function onKeyDown(event: KeyboardEvent) {
		const keys: Array<string> = [];
		if (event.altKey) keys.push('Alt');
		if (event.ctrlKey) keys.push('Ctrl');
		if (event.metaKey) keys.push('Meta');
		if (event.shiftKey) keys.push('Shift');

		if (event.key != 'Alt' && event.key != 'Control' && event.key != 'Meta' && event.key != 'Shift') {
			keys.push(event.code); // See https://www.toptal.com/developers/keycode
		}

		const shorthand = keys.join('+');

		// Handle key binding
		if (shorthand in KEYBINDINGS) {
			event.preventDefault();
			event.stopPropagation();
			const callback = KEYBINDINGS[shorthand];
			callback();
			return;
		}
	}

	function tabClicked(catg: string) {
		activeTab.value = catg;
	}

	const categories = computed(() => {
		const categoryNames: string[] = [];
		props.entries.forEach((e) => {
			if (e.category === undefined) e.category = '';
			if (e.category && !categoryNames.includes(e.category)) categoryNames.push(e.category);
		});
		if (categoryNames.length > 0 && categoryNames.length != props.entries.length) {
			categoryNames.unshift('');
		}
		return categoryNames;
	});

	const categoryErrors = computed(() => {
		if (categoriesLength.value <= 0) return [];
		const errorCategoryNames: string[] = [];
		props.entries.forEach((e) => {
			if (e.error) {
				if (e.category && !errorCategoryNames.includes(e.category)) {
					errorCategoryNames.push(e.category);
				} else if (!errorCategoryNames.includes('')) {
					errorCategoryNames.push('');
				}
			}
		});
		return errorCategoryNames;
	});

	const anyCategoryHasError = computed(() => {
		return categoryErrors.value.length > 0;
	});

	const truncatedAdditionalInfo = computed(() => {
		if (!props.additionalInfo) return '';
		if (props.additionalInfo.length > 1000) return props.additionalInfo.slice(0, 997) + '...';
		return props.additionalInfo;
	});

	onMounted(async () => {
		window.addEventListener('keydown', onKeyDown, true);
	});

	onBeforeUnmount(async () => {
		window.removeEventListener('keydown', onKeyDown, true);
	});

	watch(
		categories,
		() => {
			if (!categories.value) return;
			if (categoriesLength.value == categories.value.length) return;
			categoriesLength.value = categories.value.length;
			if (categories.value.length > 0) {
				activeTab.value = categories.value[0];
			} else activeTab.value = '';
		},
		{ immediate: true }
	);
</script>

<style scoped>
	:deep(.modal-popup) {
		width: 50vw;
		overflow: hidden;
	}

	.modal-form-loader-container {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.modal-form-contents-container {
		max-height: 75vh;
		display: flex;
		flex-direction: column;
		padding: 8px;
		overflow-x: hidden;
		overflow-y: auto;
	}

	.modal-additional-info-contents {
		margin-top: 8px;
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.modal-additional-info-contents:not(:last-child) {
		margin-bottom: 24px;
	}

	.modal-additional-info-text {
		width: 100%;
		color: var(---color-text);
		font-size: 1rem;
		white-space: pre-wrap;
		word-break: keep-all;
	}

	.modal-form-footer {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
	}

	.modal-form-footer > *:not(:last-child) {
		margin-right: 12px;
	}

	.tabs-container {
		min-height: 30px;
		padding-bottom: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		white-space: nowrap;
		overflow-y: hidden;
		overflow-x: auto;
	}

	.error-container {
		min-width: 30%;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.global-error-icon {
		font-size: 32px;
	}

	.error-styling {
		color: var(--color-error);
	}
</style>
