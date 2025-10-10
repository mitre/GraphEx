<template>
	<svg :style="svgStyles">
		<path :d="curve" :style="pathStyles"></path>
	</svg>
</template>

<script setup lang="ts">
	import Color from 'color';
	import { computed } from 'vue';

	export interface GraphEdge {
		/** The start X position of this edge. */
		startX: number;

		/** The start Y position of this edge. */
		startY: number;

		/** The end X position of this edge. */
		endX: number;

		/** The end Y position of this edge. */
		endY: number;

		/** Color for this edge. */
		color: string;

		/** Whether to highlight this edge. */
		highlight?: boolean;
	}

	const props = defineProps<GraphEdge>();

	const curve = computed(() => {
		const toX = props.endX - props.startX;
		const toY = props.endY - props.startY;

		const lineToX1 = Math.abs(toX) * 0.03;
		const lineToY1 = 0;

		const curveControlX1 = Math.abs(toX) * 0.33;
		const curveControlY1 = 0;

		const curveControlX2 = toX - Math.abs(toX) * 0.33;
		const curveControlY2 = toY;

		const curveEndX = toX - Math.abs(toX) * 0.03;
		const curveEndY = toY;

		const lineToX2 = toX;
		const lineToY2 = toY;

		return `M 0, 0 L ${lineToX1}, ${lineToY1} C ${curveControlX1}, ${curveControlY1} ${curveControlX2}, ${curveControlY2} ${curveEndX}, ${curveEndY} L ${lineToX2}, ${lineToY2}`;
	});

	// Styles
	const svgStyles = computed(() => {
		const styles: { [key: string]: string } = {};

		if (props.highlight) {
			try {
				const color = Color(props.color).whiten(1.0);
				styles['filter'] = `drop-shadow(0px 0px 5px ${color.hex()})`;
			} catch {
				styles['filter'] = `drop-shadow(0px 0px 5px #FFFFFF)`;
			}
		}

		styles['transform'] = `translate(${props.startX}px, ${props.startY}px)`;

		return styles;
	});

	const pathStyles = computed(() => {
		return {
			stroke: props.color
		};
	});
</script>

<style scoped>
	svg {
		overflow: visible !important;
		position: absolute;
		z-index: 20;
		pointer-events: none;
	}

	path {
		fill: none;
		stroke-width: 2px;
		filter: drop-shadow(2px 2px 3px rgba(0, 0, 0, 0.5));
	}
</style>
