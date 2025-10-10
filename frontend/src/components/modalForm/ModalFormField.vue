<template>
	<div class="modal-form-field-container">
		<div class="modal-form-field" :error="!!props.error">
			<template v-if="!props.options">
				<input
					ref="theinput"
					:type="inputType"
					:value="props.value"
					:disabled="props.disabled"
					@input="onInput"
					@keydown.stop
				/>
				<template v-if="props.password">
					<div v-if="showPassword" class="material-icons password-visible-icons" @click="togglePasswordVisible">
						visibility_off
					</div>
					<div v-else class="material-icons password-visible-icons" @click="togglePasswordVisible">visibility</div>
				</template>
			</template>

			<DropdownComponent v-else ref="dropdown" auto-width>
				<span class="dropdown-value no-select" :style="dropdownStyles">{{ props.value || '&nbsp;' }}</span>
				<div class="dropdown-icon material-icons">expand_more</div>

				<template v-slot:dropdown>
					<div class="dropdown-contents-container custom-scrollbar">
						<span
							v-for="option in props.options"
							:key="option"
							class="dropdown-option no-select"
							@click.stop="selectOption(option)"
						>
							{{ option }}
						</span>
					</div>
				</template>
			</DropdownComponent>

			<div class="error-icon material-icons" v-if="props.error" :title="props.error">warning_amber</div>
		</div>
		<span class="modal-form-field-error" v-if="props.error">{{ props.error }}</span>
	</div>
</template>

<script setup lang="ts">
	import DropdownComponent from '@/components/DropdownComponent.vue';
import { computed, onMounted, ref } from 'vue';

	export interface ModalFormFieldProps {
		value: string;
		error?: string | null;
		disabled?: boolean;
		options?: Array<string>;
		password?: boolean;
		focus?: boolean;
		textTransform?: string | undefined
	}
	
	//by default the textTransform is capitilize
	const dropdownStyles = computed(() => {
		const styles: { [name: string]: string } = {
			textTransform: props.textTransform ? props.textTransform : 'capitalize'
		};

		return styles;
	});
	const props = defineProps<ModalFormFieldProps>();

	const emit = defineEmits<{
		(e: 'updateValue', value: string): void;
	}>();

	const dropdown = ref<InstanceType<typeof DropdownComponent>>();
	const showPassword = ref<boolean>(false);
	const theinput = ref<HTMLInputElement>();

	function onInput(event: Event) {
		if (!event.target) {
			return;
		}

		const target = event.target as HTMLInputElement;
		emit('updateValue', target.value);
	}

	function selectOption(option: string) {
		emit('updateValue', option);
		dropdown.value?.close();
	}

	async function togglePasswordVisible() {
		showPassword.value = !showPassword.value;
	}

	const inputType = computed(() => {
		if (props.password && props.password === true && !showPassword.value) {
			return 'password';
		}
		return 'text';
	});

	onMounted(async () => {
		if (theinput.value && props.focus) {
			theinput.value.focus();
		}
	});
</script>

<style scoped>
	.modal-form-field-container {
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.modal-form-field {
		background-color: var(--color-background-primary);
		border-radius: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.modal-form-field[error='true'] {
		outline: 1px solid var(--color-error);
	}

	input {
		flex: 1 0;
		padding: 8px;
		border: none;
		outline: none;
		background: none;
		color: var(--color-text);
		font-size: 1rem;
	}

	input:disabled {
		opacity: 0.6;
	}

	:deep(.dropdown-wrapper) {
		flex: 1 0;
	}

	:deep(.dropdown-target-container) {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.dropdown-value {
		flex: 1 0;
		padding: 8px;
		font-size: 1rem;
		text-transform: inherit;
	}

	.dropdown-icon {
		margin: 0px 8px;
		font-size: 1.4rem;
		color: var(--color-text);
		opacity: 0.7;
	}

	:deep(.dropdown) {
		width: 100%;
	}

	.dropdown-contents-container {
		max-height: 400px;
		flex: 1 0;
		display: flex;
		flex-direction: column;
		padding: 6px 0px;
		background-color: var(--color-background-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 0px 0px 8px 4px rgba(0, 0, 0, 0.4);
		border-radius: 4px;
		overflow: auto;
	}

	.dropdown-option {
		flex: 1 0;
		padding: 8px;
		cursor: pointer;
	}

	.dropdown-option:hover {
		background-color: var(--color-foreground-secondary);
	}

	.error-icon {
		margin: 0px 8px;
		color: var(--color-error);
		cursor: help;
	}

	.modal-form-field-error {
		margin-top: 4px;
		width: 100%;
		font-size: 0.9rem;
		font-style: italic;
		color: var(--color-error);
	}

	.password-visible-icons {
		opacity: 70%;
		padding-right: 5px;
		padding-top: 2px;
	}
</style>
