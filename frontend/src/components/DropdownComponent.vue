<template>
	<div class="dropdown-wrapper" :open="isOpen" ref="wrapper">
		<div class="dropdown-target-container" @click.stop.prevent="onContainerClick">
			<slot></slot>
		</div>

		<Teleport :to="props.teleport" :disabled="!props.teleport">
			<div class="dropdown" v-if="isOpen" ref="dropdown" :style="dropdownStyles">
				<slot name="dropdown"></slot>
			</div>
		</Teleport>
	</div>
</template>

<script setup lang="ts">
	import { computed, nextTick, reactive, ref } from 'vue';

	export interface DropdownProps {
		/** If true, this dropdown is controlled by the parent (i.e. opening of the dropdown must be handled by the parent). Automatic closing by clicking outside the bounds is still handled here. */
		controlled?: boolean;

		/** Element to teleport to. If undefined or null, the dropdown will not be teleported. */
		teleport?: Element | null;

		/** The X coordinate for the dropdown. Will override the default computed value if provided. */
		x?: number;

		/** The Y coordinate for the dropdown. Will override the default computed value if provided. */
		y?: number;

		/** Amount of pixels in the X direction to translate the dropdown from its base position. */
		translateX?: number;

		/** Amount of pixels in the Y direction to translate the dropdown from its base position. */
		translateY?: number;

		/** Whether to automatically fit the dropdown to the screen when opened (default: true). */
		fitToScreen?: boolean;

		/** Whether to automatically set the width of the dropdown to the same width as the target. */
		autoWidth?: boolean;

		disabled?: boolean;
	}

	const props = withDefaults(defineProps<DropdownProps>(), {
		translateX: 0,
		translateY: 0,
		fitToScreen: true,
		disabled: false
	});

	const isOpen = ref<boolean>(false);
	const wrapper = ref<HTMLDivElement>();
	const dropdown = ref<HTMLDivElement>();
	const coordinates = reactive({ x: 0, y: 0 });
	const offsets = reactive({ x: 0, y: 0 });
	const width = ref<number>();

	function onContainerClick() {
		if (props.disabled) {
			return;
		}

		if (props.controlled) {
			return;
		}

		if (isOpen.value) {
			close();
		} else {
			open();
		}
	}

	async function open() {
		if (!wrapper.value) return;
		isOpen.value = true;

		if (props.autoWidth) {
			width.value = wrapper.value.clientWidth;
		}

		const wrapperRect = wrapper.value.getBoundingClientRect();
		coordinates.x = wrapperRect.left;
		coordinates.y = wrapperRect.bottom;

		window.addEventListener('mousedown', onMouseClick, { capture: true });

		// Adjust the dropdown to fit to the screen
		nextTick(() => {
			if (!dropdown.value || !props.fitToScreen) return;
			const dropdownRect = dropdown.value.getBoundingClientRect();

			if (dropdownRect.bottom + offsets.y >= window.innerHeight) {
				offsets.y = -1 * (dropdownRect.bottom - window.innerHeight + 16);
			}

			if (dropdownRect.right + offsets.x >= window.innerWidth) {
				offsets.x = -1 * (dropdownRect.right - window.innerWidth + 16);
			}
		});
	}

	function close() {
		isOpen.value = false;
		window.removeEventListener('mousedown', onMouseClick, { capture: true });
		offsets.x = 0;
		offsets.y = 0;
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

	const dropdownStyles = computed(() => {
		if (!isOpen.value) {
			return {};
		}

		const styles: { [name: string]: string } = {
			transform: `translate(${props.translateX + offsets.x}px, ${props.translateY + offsets.y}px)`,
			left: (props.x !== undefined ? props.x : coordinates.x) + 'px',
			top: (props.y !== undefined ? props.y : coordinates.y) + 'px'
		};

		if (props.autoWidth) {
			styles['width'] = `${width.value}px`;
		}

		return styles;
	});

	defineExpose({
		open,
		close,
		dropdown
	});
</script>

<style scoped>
	.dropdown-target-container {
		cursor: pointer;
	}

	.dropdown {
		position: fixed;
		z-index: 99;
	}
</style>
