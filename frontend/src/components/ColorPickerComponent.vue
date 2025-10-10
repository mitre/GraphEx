<template>
	<div class="rgb-container" @dblclick.stop @mousedown.stop>
		<div class="inputs">
			<div class="background-text-toggle-div" v-if="showBackgroundColors">
				<div class="title-and-icon">
					<h4 class="rgb-title no-select">Background Color</h4>
					<span class="material-icons change-icon" @click="toggleColorInput" title="Swap to Text Color">
						autorenew
					</span>
				</div>
				<div class="rgb-row">
					<span class="rgb-text no-select"> R </span>
					<ColorInputField :value="props.backgroundColor.red()" @update="(r) => updateBackground({ r: r })" />
					<span class="rgb-text no-select"> G </span>
					<ColorInputField :value="props.backgroundColor.green()" @update="(g) => updateBackground({ g: g })" />
					<span class="rgb-text no-select"> B </span>
					<ColorInputField :value="props.backgroundColor.blue()" @update="(b) => updateBackground({ b: b })" />
				</div>
			</div>
			<div class="background-text-toggle-div" v-if="!showBackgroundColors">
				<div class="title-and-icon">
					<h4 class="rgb-title">Text Color</h4>
					<span class="material-icons change-icon" @click="toggleColorInput" title="Swap to Background Color">
						autorenew
					</span>
				</div>
				<div class="rgb-row">
					<span class="rgb-text no-select"> R </span>
					<ColorInputField :value="props.textColor.red()" @update="(r) => updateText({ r: r })" />
					<span class="rgb-text no-select"> G </span>
					<ColorInputField :value="props.textColor.green()" @update="(g) => updateText({ g: g })" />
					<span class="rgb-text no-select"> B </span>
					<ColorInputField :value="props.textColor.blue()" @update="(b) => updateText({ b: b })" />
				</div>
			</div>
		</div>
		<canvas class="canvas" ref="canvas" @mousedown.stop.prevent></canvas>
	</div>
</template>

<script setup lang="ts">
	import { ref, onMounted } from 'vue';
	import ColorInputField from '@/components/ColorInputField.vue';
	import Color from 'color';

	const props = defineProps<{
		backgroundColor: Color;
		textColor: Color;
	}>();

	const emit = defineEmits<{
		(e: 'updateBackground', rgb: Color): void;
		(e: 'updateText', rgb: Color): void;
	}>();

	const canvas = ref<HTMLCanvasElement>();
	const showBackgroundColors = ref<boolean>(true);
	// const pickerCircle = reactive({ x: 30, y: 30, width: 7, height: 7 });

	const mouseDown = ref<boolean>(false);

	function toggleColorInput() {
		showBackgroundColors.value = !showBackgroundColors.value;
	}

	function drawCanvas() {
		if (canvas.value) {
			const context = canvas.value.getContext('2d');
			// draw the color lines that go from left to right
			const gradientHeight = context!.createLinearGradient(0, 0, canvas.value.width, 0);
			gradientHeight.addColorStop(0, 'rgb(255, 0, 0)'); // red
			gradientHeight.addColorStop(1 / 6, 'rgb(255, 255, 0)'); // yellow
			gradientHeight.addColorStop(2 / 6, 'rgb(0, 255, 0)'); // green
			gradientHeight.addColorStop(3 / 6, 'rgb(0, 255, 255)');
			gradientHeight.addColorStop(4 / 6, 'rgb(0, 0, 255)'); // blue
			gradientHeight.addColorStop(5 / 6, 'rgb(255, 0, 255)');
			gradientHeight.addColorStop(1, 'rgb(255, 0, 0)'); // red
			context!.fillStyle = gradientHeight;
			context!.fillRect(0, 0, canvas.value.width, canvas.value.height);

			// create the gradient for white and black across the colors
			const WhiteBlackGradient = context!.createLinearGradient(0, 0, 0, canvas.value.height);
			WhiteBlackGradient.addColorStop(0, 'rgba(255, 255, 255, 1)'); // white
			WhiteBlackGradient.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
			WhiteBlackGradient.addColorStop(0.5, 'rgba(0, 0, 0, 0)'); // transparent
			WhiteBlackGradient.addColorStop(1, 'rgba(0, 0, 0, 1)'); // black
			context!.fillStyle = WhiteBlackGradient;
			context!.fillRect(0, 0, canvas.value.width, canvas.value.height);

			// // draw the circle indicator
			// context!.beginPath();
			// context!.arc(pickerCircle.x, pickerCircle.y, pickerCircle.width, 0, Math.PI * 2);
			// context!.strokeStyle = 'black';
			// context!.stroke();
			// context!.closePath();
		}
	}

	function updateBackground(values: { r?: number; g?: number; b?: number }) {
		emit(
			'updateBackground',
			new Color({
				r: values.r == undefined ? props.backgroundColor.red() : values.r,
				g: values.g == undefined ? props.backgroundColor.green() : values.g,
				b: values.b == undefined ? props.backgroundColor.blue() : values.b
			})
		);
	}

	function updateText(values: { r?: number; g?: number; b?: number }) {
		emit(
			'updateText',
			new Color({
				r: values.r == undefined ? props.textColor.red() : values.r,
				g: values.g == undefined ? props.textColor.green() : values.g,
				b: values.b == undefined ? props.textColor.blue() : values.b
			})
		);
	}

	function updateColors(event: MouseEvent) {
		if (event && event.target && canvas.value) {
			const node = event.target as HTMLCanvasElement;
			const rect = node.getBoundingClientRect();
			const x = event.clientX - rect.left;
			const y = event.clientY - rect.top;

			const context = canvas.value.getContext('2d');
			const imgData = context!.getImageData(x, y, 1, 1);
			const [r, g, b] = imgData.data;

			if (showBackgroundColors.value) {
				updateBackground({ r: r, g: g, b: b });
			} else {
				updateText({ r: r, g: g, b: b });
			}

			// // update the picker circle
			// pickerCircle.x = x;
			// pickerCircle.y = y;
		}
	}

	onMounted(() => {
		if (canvas.value) {
			// draw the canvas on the screen
			drawCanvas();

			// listen for clicks on the canvas
			canvas.value.addEventListener('click', updateColors, true);

			// record when the mouse is down for 'scrolling' through colors
			canvas.value.addEventListener('mousedown', () => {
				mouseDown.value = true;
			});

			// record when the user is done looking through colors
			canvas.value.addEventListener('mouseup', () => {
				mouseDown.value = false;
			});

			// update the color picked if the mouse is down and the user is moving it around
			canvas.value.addEventListener(
				'mousemove',
				(event: MouseEvent) => {
					if (mouseDown.value) {
						updateColors(event);
					}
				},
				true
			);

			// attempt to rebuild the canvas object if it gets resized
			window.addEventListener('resize', drawCanvas, false);
		}
	});
</script>

<style scoped>
	.rgb-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: space-between;
		z-index: 30;
		background: var(--color-background-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 6px 6px 8px 1px var(--color-editor-node-box-shadow);
	}

	.rgb-title {
		text-align: center;
	}

	.rgb-row {
		text-align: center;
		padding: 6px;
	}

	.rgb-text {
		margin-right: 4px;
	}

	.rgb-text:not(:first-child) {
		margin-left: 12px;
	}

	.canvas {
		margin-top: 2px;
		background-color: rgb(255, 255, 255);
		cursor: crosshair;
	}

	.inputs {
		background: var(--color-component-picker-background);
	}

	.title-and-icon {
		padding: 6px;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.background-text-toggle-div {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.change-icon {
		font-size: 1rem;
		margin-left: 6px;
	}
</style>
