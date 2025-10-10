<template>
	<div class="terminal-container">
		<template v-if="terminalStore.executions.length == 0">
			<TerminalConsoleComponent
				:context-id="null"
				:height-percent="props.heightPercent"
				@maximize="emit('maximize')"
				@shrink="emit('shrink')"
			/>
		</template>
		
		<template v-else v-for="context in terminalStore.executions" :key="context.id">
			<TerminalConsoleComponent
				v-show="context.id === terminalStore.selectedTerminalTabId"
				:context-id="context.id"
				:height-percent="props.heightPercent"
				@maximize="emit('maximize')"
				@shrink="emit('shrink')"
				@image-preview="
					(b64string, mouseX, mouseY) => showImage({ b64string: b64string, mouseX: mouseX, mouseY: mouseY })
				"
				:ref="(el) => setConsoleRef(context.id, el)"
			/>
		</template>

		<div class="tabs-container custom-scrollbar" v-if="terminalStore.executions.length > 0">
			<TerminalTabComponent
				v-for="context in terminalStore.executions"
				:key="context.id"
				:context-id="context.id"
				@clicked="() => onTabClick(context.id)"
			/>
		</div>
	</div>
	<div v-if="mouseOverImagePreview != ''" class="image-preview" :style="mousePosStyle">
		<img ref="im" class="image-tag" :src="mouseOverImagePreview" />
	</div>
</template>

<script setup lang="ts">
	import { useTerminalStore } from '@/stores';
	import TerminalConsoleComponent from '@/terminal/TerminalConsoleComponent.vue';
	import TerminalTabComponent from '@/terminal/TerminalTabComponent.vue';
	import { computed, nextTick, reactive, ref } from 'vue';

	const props = defineProps<{
		heightPercent: number;
	}>();

	const emit = defineEmits<{
		(e: 'maximize'): void;
		(e: 'shrink'): void;
	}>();

	const terminalStore = useTerminalStore();

	/** All terminal console component refs, mapping context ID to the component. */
	const consoleRefs = reactive<{ [contextId: string]: InstanceType<typeof TerminalConsoleComponent> | null }>({});

	/** Gets set by @image-preview from TerminalConsoleComponent */
	const mouseOverImagePreview = ref<string>('');

	/** The 'x' position of the mouse when an image is hovered */
	const mouseOverX = ref<number>(-1);

	/** The 'y' position of the mouse when an image is hovered */
	const mouseOverY = ref<number>(-1);

	/** The image element being previewed (if exists) */
	const im = ref<HTMLImageElement>();

	/** The location in which to anchor the image preview */
	const mousePosStyle = computed(() => {
		let buffer_y = -200;
		let buffer_x = 5;
		if (im.value) {
			buffer_y = -1 * im.value.height;
		}
		return {
			top: String(mouseOverY.value + buffer_y) + 'px',
			left: String(mouseOverX.value + buffer_x) + 'px'
		};
	});

	function setConsoleRef(contextId: string, el: any) {
		consoleRefs[contextId] = el;
	}

	function onTabClick(contextId: string) {
		terminalStore.setSelectedTerminalTab(contextId);
		nextTick(() => {
			if(!(contextId in consoleRefs)) {
				console.warn(`Failed to find TerminalConsoleComponent ref for ${contextId}`);
				return;
			}

			const consoleRef = consoleRefs[contextId];
			if(!consoleRef) {
				console.warn(`TerminalConsoleComponent ref for ${contextId} is empty`);
				return;
			}

			consoleRef.updateViewport();
			if (consoleRef.autoScroll) {
				consoleRef.setScrollPosition(consoleRef.totalHeight);
			}
		});
	}

	function showImage(values: { b64string: string; mouseX: number; mouseY: number }) {
		mouseOverImagePreview.value = values.b64string;
		mouseOverX.value = values.mouseX;
		mouseOverY.value = values.mouseY;
	}
</script>

<style scoped>
	.terminal-container {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.tabs-container {
		width: 100%;
		padding-top: 4px;
		padding-bottom: 4px;
		display: flex;
		flex-direction: row;
		align-items: center;
		overflow-y: hidden;
		overflow-x: auto;
	}

	.image-preview {
		background: var(--color-background-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
		position: fixed;
		z-index: 90;
	}

	.image-tag {
		width: 100%;
		height: 100%;
		max-width: 200px;
		max-height: 200px;
	}
</style>
