<template>
	<div class="minimap-container" :style="{ width: `${WIDTH}px`, height: `${HEIGHT}px` }" ref="container">
		<div class="selection-disable" @mousedown.stop.prevent="onMouseDown" @mousemove.stop.prevent="onMouseMove"></div>
		<div class="viewport-area" :style="viewportAreaStyles"></div>

		<iframe ref="iframeEl" :width="VIEWPORT_WIDTH" :height="VIEWPORT_HEIGHT" />

		<div class="minimap-loader" v-if="!isLoaded">
			<RingLoader width="30px" height="30px" />
		</div>
	</div>
</template>

<script setup lang="ts">
	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import RingLoader from '@/components/RingLoader.vue';
import type { Graph } from '@/graph';
import { useContextmenuStore, useSettingsStore } from '@/stores';
import { computed, onMounted, ref } from 'vue';

	const props = defineProps<{
		graph: Graph;
	}>();

	const settingsStore = useSettingsStore();
	const contextmenuStore = useContextmenuStore();

	const container = ref<HTMLDivElement>();

	const WIDTH = 400;
	const VIEWPORT_WIDTH = 360;
	const HEIGHT = 200;
	const VIEWPORT_HEIGHT = 160;

	const iframeEl = ref<HTMLIFrameElement>();
	const updateTimeout = ref<number | undefined>();

	const scale = ref<number>(1);
	const anchorX = ref<number>(0);
	const anchorY = ref<number>(0);

	const isLoaded = ref<boolean>(false);

	onMounted(() => {
		// We use an iframe rather than rendering to "our" DOM because iframes effectively behave as a separate tab.
		// Using an iframe allows us to offload the rendering to a separate thread, which slightly boosts
		// performance on large graphs.

		// Initialize the iframe
		// We'll send messages whenever we want to update the nodes later
		let css = '';
		for (const styleSheet of Array.from(document.styleSheets)) {
			css += Array.from(styleSheet.cssRules)
				.map((rule) => rule.cssText)
				.join('\n');
		}

		// Set up the source document for the iframe.
		// This source document contains the necessary HTML for rendering the minimap, including scaling and translation
		// It also includes an event listener for listening to messages, which will tell the document how to update the
		// minimap when changes occur.
		const srcDoc =
			`
					<!DOCTYPE html>
					<html lang="en">
						<head>
							<meta charset="UTF-8" />
							<style>
							${css}
							</style>
						</head>
						<body style="width: ${VIEWPORT_WIDTH}px; height: ${VIEWPORT_HEIGHT}px; overflow: hidden; background: var(--color-foreground-primary);">
							<div id="minimap-scaler" style="width: 100%; height: 100%; position: absolute; top: 0px; left: 0px; overflow: visible; transform-origin: top left; transform: scale(1)">
								<div id="minimap-contents" style="transform: translate(0px, 0px)"></div>
							</div>
						</body>
						<script>
							window.addEventListener(
								"message",
								(event) => {
									document.getElementById("minimap-scaler").style.transform = "scale(" + event.data.scale + ")";

									const contentsElement = document.getElementById("minimap-contents");
									contentsElement.style.transform = "translate(" + -event.data.anchorX + "px, " + -event.data.anchorY + "px)"
									contentsElement.innerHTML = event.data.innerHTML;

									// Apply the text values
									const textElements = Array.from(contentsElement.querySelectorAll('input, textarea'));
									for(let i = 0; i < textElements.length; i++) {
										textElements[i].value = event.data.textValues[i];
									}

									// Make all nodes visible
									for(const node of contentsElement.querySelectorAll(".node-container[isvisible='false']")) {
										node.setAttribute("isvisible", "true");
									}
								},
								false,
							);
						<` + '/script></html>'; //  Need to separate out the script closing tag to avoid errors

		iframeEl.value!.srcdoc = srcDoc;

		// Add the context menu
		contextmenuStore.getContextMenu('root').addHook(container.value!, openContextMenu, true);

		requestUpdateMinimap();
	});

	/**
	 * Request that the minimap be updated. This will not immediately update the minimap but instead trigger a timeout.
	 * This is used to "buffer" updates so that multiple calls in quick succession are batched into a single update.
	 */
	function requestUpdateMinimap() {
		clearTimeout(updateTimeout.value);
		updateTimeout.value = setTimeout(updateMinimap, 250);
	}

	/**
	 * Update the minimap immediately. This will recompute the required values (scale, anchorX, anchorY)
	 * needed to render the minimap, and will re-fetch the innerHTML of the editor. These values will then be
	 * sent to the iframe for updating.
	 */
	async function updateMinimap() {
		if (!iframeEl.value || !props.graph.ui.contentElement) {
			return;
		}

		if (iframeEl.value.contentWindow!.document.readyState !== 'complete') {
			requestUpdateMinimap();
			return;
		}

		let minX = Infinity;
		let minY = Infinity;
		let maxX = -Infinity;
		let maxY = -Infinity;
		for (const node of props.graph.getNodes()) {
			if (node.x < minX) minX = node.x;
			if (node.y < minY) minY = node.y;

			const nodeEndX = node.x + node.width();
			if (nodeEndX > maxX) maxX = nodeEndX;

			const nodeEndY = node.y + node.height();
			if (nodeEndY > maxY) maxY = nodeEndY;
		}

		const scaleWidth = VIEWPORT_WIDTH / (maxX - minX);
		const scaleHeight = VIEWPORT_HEIGHT / (maxY - minY);

		scale.value = Math.min(scaleWidth, scaleHeight);

		const totalFreespaceX = VIEWPORT_WIDTH / scale.value - (maxX - minX); // The amount of "empty space" that will be in the minimap on the X-axis
		anchorX.value = minX - Math.round(totalFreespaceX / 2);

		const totalFreespaceY = VIEWPORT_HEIGHT / scale.value - (maxY - minY); // The amount of "empty space" that will be in the minimap on the Y-axis
		anchorY.value = minY - Math.round(totalFreespaceY / 2);

		iframeEl.value.contentWindow!.postMessage(
			{
				scale: scale.value,
				anchorX: anchorX.value,
				anchorY: anchorY.value,
				innerHTML: props.graph.ui.contentElement.innerHTML,

				// The innerHTML property does not include input field values,
				// so to show text in the minimap we need to set it afterwards.
				// We'll use 'querySelectorAll' to get all input/textarea elements,
				// which will always return in document-order, and get the text values as an array.
				// Since we set the same HTML in the minimap iframe, performing the same query there
				// will return the elements in the same order. We can then just set the values in-order.
				// This is fast and has negligible performance impact.
				textValues: Array.from(props.graph.ui.contentElement.querySelectorAll('input, textarea')).map(
					(el) => (el as HTMLInputElement).value
				)
			},
			'*'
		);

		isLoaded.value = true;
	}

	function onMouseDown(e: MouseEvent) {
		if (e.buttons == 1) {
			translateEditorToCoordinate(e.offsetX, e.offsetY);
		}
	}

	function onMouseMove(e: MouseEvent) {
		if (e.buttons == 1) {
			translateEditorToCoordinate(e.offsetX, e.offsetY);
		}
	}

	/**
	 * Translate the editor to the equivalent minimap coordinate. This takes the given minimap X/Y and moves the editor
	 * screen to the corresponding position.
	 *
	 * @param minimapX The minimap X coordinate.
	 * @param minimapY The minimap Y-coordinate.
	 */
	function translateEditorToCoordinate(minimapX: number, minimapY: number) {
		const viewportPositions = props.graph.ui.viewportPositions();
		const viewportWidth = viewportPositions.right - viewportPositions.left;
		const viewportHeight = viewportPositions.bottom - viewportPositions.top;

		const minimapStartX = (WIDTH - VIEWPORT_WIDTH) / 2;
		const minimapStartY = (HEIGHT - VIEWPORT_HEIGHT) / 2;

		const editorOffsetX = -anchorX.value - (minimapX - minimapStartX) / scale.value + viewportWidth / 2;
		const editorOffsetY = -anchorY.value - (minimapY - minimapStartY) / scale.value + viewportHeight / 2;

		props.graph.ui.navigateUiToCoordinates(editorOffsetX, editorOffsetY, false);
	}

	/**
	 * Context menu handler.
	 */
	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		entries.push({
			label: 'Hide',
			description: 'Hide the minimap',
			callback: async () => {
				settingsStore.showMinimap = false;
			}
		});

		return { items: entries };
	}

	/**
	 * Computed function for returning the size and position of the minimap viewport area.
	 */
	const viewportAreaStyles = computed(() => {
		if (!props.graph.ui.viewportElement) return {};

		// Get the graph viewport width and height values
		const viewportPositions = props.graph.ui.viewportPositions();
		const viewportWidth = viewportPositions.right - viewportPositions.left;
		const viewportHeight = viewportPositions.bottom - viewportPositions.top;

		// The width and height of the viewport area in the minimap is computed by
		// scaling the viewport sizes down by the amount the minimap is scaled down (scale.value)
		// and adjusting for the viewport scale in the editor.
		const width = (viewportWidth * scale.value) / props.graph.ui.scale;
		const height = (viewportHeight * scale.value) / props.graph.ui.scale;

		// Compute the start positions of the minimap viewport area.
		// This is not (0, 0) because we do not fill the entire minimap space with nodes.
		// Instead, nodes only fill a smaller portion of the minimap space (determined by VIEWPORT_WIDTH/VIEWPORT_HEIGHT).
		// Thus, the (0,0) coordinate of the graph editor is not the (0,0) coordinate of the minimap.
		// The actual value can be found by taking the minimap sizes and subtracting the available space for nodes to find
		// the overall padding size around the minimap, and then dividing by 2 to get the padding on a single side.
		const minimapStartX = (WIDTH - VIEWPORT_WIDTH) / 2;
		const minimapStartY = (HEIGHT - VIEWPORT_HEIGHT) / 2;

		// Compute the offset/translation of the minimap viewport area.
		// There are three things to factor in here:
		//
		//   1. The start position (computed above).
		//   2. The actual offset of the graph editor relative to the "first node" coordinates (anchor).
		//   3. The scaling of the graph editor.
		//
		// For (1), this is trivial since we've calculated the position already. We'll simply start with this value as a base.
		// For (2), we need to take the graph editor offset and factor in the anchor value. The anchor value
		//  is going to be the X/Y coordinate of the left-most/top-most node. Due to how the minimap is designed,
		//  the node corresponding to that anchor value will always be flush-left/flush-top to the minimap, so
		//  we can make the assumption that if the graph editor is flush-left/flush-top to that node, we do not want
		//  any translation. With this is mind, we want to subtract the anchor value such that if the the editor is translated
		//  enough that the anchor node is flush-left/flush-top, we do not do any translation. Furthermore, since the editor
		//  offsets are reversed, we want to subtract the editor offset to factor in the editor's translation.
		//  All this will need to be scaled by the amount that the minimap is scaled by.
		// For (3), we need to factor in the amount that the editor is scaled by and adjust the minimap viewport area to compensate.
		//   Because the editor is scaled relative to its center, but our minimap viewport area is scaled relative to the top-left,
		//   we need to adjust the offset of the viewport area to compensate. This is done by taking minimap viewport area width/height
		//   without any editor scaling to get the "base" size, and then subtracting the scaled version to get the amount that the
		//   minimap viewport area changes when editor scaling is applied. We then divide this value by 2 to "center" it and apply
		//   that as part of our translation.
		const viewportOffsetX =
			minimapStartX + // (1)
			(-props.graph.ui.offsets.x - anchorX.value) * scale.value + // (2)
			(viewportWidth * scale.value - width) / 2; // (3)

		const viewportOffsetY =
			minimapStartY + // (1)
			(-props.graph.ui.offsets.y - anchorY.value) * scale.value + // (2)
			(viewportHeight * scale.value - height) / 2; // (3)

		return {
			width: width + 'px',
			height: height + 'px',
			transform: `translate(${viewportOffsetX - 1}px, ${viewportOffsetY - 1}px)`
		};
	});

	defineExpose({ requestUpdateMinimap });
</script>

<style scoped>
	.minimap-container {
		position: absolute;
		right: 10px;
		top: 10px;
		background: var(--color-foreground-primary);
		border: 2px var(--color-border) solid;
		border-radius: 8px;
		z-index: 98;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
	}

	.selection-disable {
		z-index: 10;
		width: 100%;
		height: 100%;
		position: absolute;
		min-width: 400px;
		min-height: 200px;
	}

	.minimap-container > iframe {
		border: none;
		outline: none;
	}

	.viewport-area {
		position: absolute;
		top: 0px;
		left: 0px;
		border: 1px solid rgba(255, 255, 255, 0.6);
		z-index: 5;
	}

	.minimap-loader {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		position: absolute;
		top: 0px;
		left: 0px;
	}
</style>
