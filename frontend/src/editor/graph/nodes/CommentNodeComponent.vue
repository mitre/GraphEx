<template>
	<div class="comment-node" :style="styleComment" ref="comment">
		<div class="body">
			<div>
				<DropdownComponent
					:teleport="props.node.graph.ui.viewportElement"
					:style="{ position: 'absolute', top: '4px', right: '4px' }"
					:disabled="props.disabled"
				>
					<span class="material-icons pallete-icon" :style="stylePalleteIcon" ref="palette"> palette </span>
					<template v-slot:dropdown>
						<ColorPickerComponent
							:background-color="backgroundColor"
							:text-color="textColor"
							@update-background="updateBackgroundColor"
							@update-text="updateTextColor"
						/>
					</template>
				</DropdownComponent>
				<div class="contents" :style="styleContents">
					<InputField
						v-if="inputField"
						:floating-label="inputField.floatingLabel"
						:value="inputFieldValue"
						:label="inputField.name"
						:multiline="true"
						:clear-button="false"
						@input="updateValue"
						@change="onChange"
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import ColorPickerComponent from '@/components/ColorPickerComponent.vue';
	import DropdownComponent from '@/components/DropdownComponent.vue';
	import InputField from '@/components/InputField.vue';
	import type { GraphNode } from '@/graph';
	import Color from 'color';
	import { computed, ref } from 'vue';

	const props = defineProps<{
		node: GraphNode;
		disabled: boolean;
	}>();

	const palette = ref<HTMLElement>();

	const backgroundColor = computed(() => {
		return new Color(props.node.color || props.node.metadata.color);
	});

	const textColor = computed(() => {
		return new Color(props.node.textColor || props.node.metadata.textColor);
	});

	const styleComment = computed(() => {
		return {
			background: String(backgroundColor.value.rgb())
		};
	});

	const styleContents = computed(() => {
		return {
			color: String(textColor.value.hex())
		};
	});

	const stylePalleteIcon = computed(() => {
		return {
			color: String(backgroundColor.value.negate().rgb())
		};
	});

	const inputField = computed(() => {
		return props.node.metadata.field;
	});

	const inputFieldValue = computed(() => {
		return String(props.node.fieldValue || '');
	});

	function updateValue(newValue: any) {
		if (props.disabled) {
			return;
		}
		props.node.setFieldValue(newValue);
	}

	function onChange(newValue: any) {
		if (props.disabled) {
			return;
		}
		updateValue(newValue);
	}

	function updateBackgroundColor(value: Color) {
		if (props.disabled) {
			return;
		}
		props.node.setColorValue(value.hex());
	}

	function updateTextColor(value: Color) {
		if (props.disabled) {
			return;
		}
		props.node.setTextColorValue(value.hex());
	}
</script>

<style scoped>
	.comment-node {
		min-width: 200px;
		min-height: 20px;
		display: flex;
		flex-direction: column;
		border-radius: 8px;
		padding-right: 8px;
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
		opacity: 0.9;
	}

	.contents {
		flex: 1 0;
		padding: 12px;
		display: flex;
		flex-direction: column;
		justify-content: center;
	}

	:deep(.input-field-container) {
		background-color: revert;
		border: none;
	}

	:deep(.input-field) {
		color: inherit;
		font-family: 'Roboto';
		font-size: 1.1rem;
	}

	.pallete-icon {
		font-size: 1rem;
		opacity: 0.6;
	}

	.pallete-icon:hover {
		opacity: 1;
	}
</style>
