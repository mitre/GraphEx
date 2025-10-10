<template>
	<ModalComponent :title="props.title" @close="onClose" :help="props.help">
		<template v-slot:contents>
			<div class="modal-form-loader-container" v-if="props.loading">
				<RingLoader width="50px" height="50px" color="rgb(255, 255, 255)" thickness="2px" />
			</div>

			<template v-else>
				<div class="column-headers-container">
					<div class="left-column-header column-header"> {{ props.leftColumnHeader }}</div>
					<div class="right-column-header column-header"> {{ props.rightColumnHeader  }}</div>
				</div>
				<div class="all-columns-container">
					<div class="left-column-container modal-column-contents-container custom-scrollbar">
						<ModalColumnEntry
							v-for="(n, index) in currentLeftColumn"
							:entry-name="n"
							:index="index"
							:selected="selectedLeftColumn.has(index)"
							@click="selectLeft"
						/>
					</div>
					<div class="middle-divider">
						<span class="material-icons material-button" title="Add Selected" @click.stop.prevent="moveSelectedRight">keyboard_arrow_right</span>
						<span class="material-icons material-button" title="Add All" @click.stop.prevent="moveAllRight">keyboard_double_arrow_right</span>
						<span class="material-icons material-button" title="Remove Selected" @click.stop.prevent="moveSelectedLeft">keyboard_arrow_left</span>
						<span class="material-icons material-button" title="Remove All" @click.stop.prevent="moveAllLeft">keyboard_double_arrow_left</span>
					</div>
					<div class="right-column-container modal-column-contents-container custom-scrollbar">
						<ModalColumnEntry
							v-for="(n, index) in currentRightColumn"
							:entry-name="n"
							:index="index"
							:selected="selectedRightColumn.has(index)"
							@click="selectRight"
						/>
					</div>
				</div>
			</template>
		</template>

		<template v-slot:footer>
			<div class="modal-buttons-footer" v-if="!props.loading">
				<template v-for="(button, index) in props.buttons" :key="index">
					<ButtonComponent v-bind="button" @click="buttonClick(index, button.text)" />
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
import { computed, onMounted, ref } from 'vue';
import ModalColumnEntry from './ModalColumnEntry.vue';

	export interface ModalColumnSelProps {
		title: string;
		leftColumn: Array<string>;
		rightColumn: Array<string>;
		leftColumnHeader: string;
		rightColumnHeader: string;
		buttons: Array<ButtonProps>;
		loading?: boolean;
		help?: string;
	}

	const currentLeftColumn = ref<Array<string>>([]);
	const currentRightColumn = ref<Array<string>>([]);

	const selectedLeftColumn = ref<Set<number>>(new Set());
	const selectedRightColumn = ref<Set<number>>(new Set());

	const props = defineProps<ModalColumnSelProps>();

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'buttonClick', data: { buttonIndex: number; buttonName: string, lCol: Array<string>, rCol: Array<string>}): void;
	}>();

	function onClose() {
		emit('close');
	}

	function buttonClick(buttonIndex: number, name: string) {
		emit('buttonClick', { buttonIndex: buttonIndex, buttonName: name, lCol: currentLeftColumn.value, rCol: currentRightColumn.value });
	}

	function selectLeft(i: number) {
		if (selectedLeftColumn.value.has(i)) {
			selectedLeftColumn.value.delete(i);
		} else {
			selectedLeftColumn.value.add(i);
		}
	}

	function selectRight(i: number) {
		if (selectedRightColumn.value.has(i)) {
			selectedRightColumn.value.delete(i);
		} else {
			selectedRightColumn.value.add(i);
		}
	}

	function moveAllRight() {
		currentLeftColumn.value.forEach((e) => {
			currentRightColumn.value.push(e);
		});
		currentLeftColumn.value = [];
		clearSelected();
	}

	function moveAllLeft() {
		currentRightColumn.value.forEach((e) => {
			currentLeftColumn.value.push(e);
		});
		currentRightColumn.value = [];
		clearSelected();
	}

	function clearSelected() {
		selectedLeftColumn.value.clear();
		selectedRightColumn.value.clear();
	}

	function moveSelectedRight() {
		Array.from(selectedLeftColumn.value).sort().forEach((index) => {
			currentRightColumn.value.push(currentLeftColumn.value[index]);
			delete currentLeftColumn.value[index];
		});
		currentLeftColumn.value = currentLeftColumn.value.filter((e) => e != undefined);
		clearSelected();
	}

	function moveSelectedLeft() {
		Array.from(selectedRightColumn.value).sort().forEach((index) => {
			currentLeftColumn.value.push(currentRightColumn.value[index]);
			delete currentRightColumn.value[index];
		});
		currentRightColumn.value = currentRightColumn.value.filter((e) => e != undefined);
		clearSelected();
	}

	const uniqueLeftColumnEntries = computed(() => {
		return Array.from( new Set(props.leftColumn) );
	});

	const uniqueRightColumnEntries = computed(() => {
		return Array.from( new Set(props.rightColumn) );
	});

	onMounted(() => {
		let interval = setInterval(() => {
			if (!props.loading) {
				clearInterval(interval);
				currentLeftColumn.value = uniqueLeftColumnEntries.value;
				currentRightColumn.value = uniqueRightColumnEntries.value;
			}
		}, 100);
	});
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

	.all-columns-container {
		display: flex;
		flex-direction: row;
		height: 100%;
		width: 100%;
		border: 5px solid var(--color-button-secondary);;
	}

	.left-column-container {
		width: 48%;
		height: 100%;
		padding: 5px;
	}

	.middle-divider {
		display: flex;
  		flex-direction: column;
		width: 4%;
		align-items: center;
		justify-content: center;
		border-left: 5px solid var(--color-button-secondary);
		border-right: 5px solid var(--color-button-secondary);;
	}

	.right-column-container {
		width: 48%;
		height: 100%;
		padding: 5px;
	}

	.material-button {
		padding: 1px;
		font-size: 2rem;
		color: var(--color-text-secondary);
		cursor: pointer;
		border-radius: 4px;
	}

	.material-button:hover {
		background-color: var(--color-foreground-secondary);
		color: var(--color-primary);
	}

	.modal-column-contents-container {
		max-height: 75vh;
		height: 100%;
		width: 100%;
		display: flex;
		flex-direction: column;
		padding: 8px;
		overflow-x: hidden;
		overflow-y: auto;
	}

	.modal-buttons-footer {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
	}

	.modal-buttons-footer > *:not(:last-child) {
		margin-right: 12px;
	}

	.column-headers-container {
		display: flex;
		flex-direction: row;
		width: 100%;
	}

	.column-header {
		width: 50%;
		color: var(--color-text);
		display: flex;
		align-items: center;
		justify-content: center;
		font-weight: bold;
		padding-bottom: 3px;
	}
</style>
