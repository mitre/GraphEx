<!-- This component is the UI effect for the 'loading ring' that appears when trying to view loading pages -->
<template>
	<div class="loader" :style="customStyle">
		<div class="loader-ring">
			<div :style="customDivStyle"></div>
			<div :style="customDivStyle"></div>
			<div :style="customDivStyle"></div>
			<div :style="customDivStyle"></div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { computed } from 'vue';
	const props = defineProps<{
		width?: string;
		height?: string;
		color?: string;
		thickness?: string;
	}>();

	const customStyle = computed(() => {
		let styles: any = {};
		if (props.width) styles['width'] = props.width;
		if (props.height) styles['height'] = props.height;
		return styles;
	});
	const customDivStyle = computed(() => {
		let styles: any = {};
		if (props.color) styles['border-top-color'] = props.color;
		if (props.thickness) styles['border-width'] = props.thickness;
		return styles;
	});
</script>

<style>
	.loader {
		width: 1em;
		height: 1em;
		margin: 0px;
		margin-right: 0.2em;
		padding: 0px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.loader-ring {
		display: inline-block;
		position: relative;
		width: 100%;
		height: 100%;
	}

	.loader-ring div {
		box-sizing: border-box;
		display: block;
		position: absolute;
		width: 100%;
		height: 100%;
		margin: 0px;
		border: 0.1em solid var(--color-text);
		border-radius: 50%;
		animation: loader-ring 1.44s cubic-bezier(0.5, 0, 0.5, 1) infinite;
		border-color: var(--color-text) transparent transparent transparent;
	}

	.loader-ring div:nth-child(1) {
		animation-delay: -0.54s;
	}

	.loader-ring div:nth-child(2) {
		animation-delay: -0.36s;
	}

	.loader-ring div:nth-child(3) {
		animation-delay: -0.18s;
	}

	@keyframes loader-ring {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}
</style>
