import type { Graph } from '@/graph/graph';
import type { GraphNode } from '@/graph/node';
import type { Socket } from '@/graph/socket';
import { useEditorStore } from '@/stores';

/**
 * Serialized form of a Graph UI.
 */
interface SerializedGraphUI {
	/** Editor scale (zoom in/out). */
	scale: number;

	/** Editor content offsets. */
	xy: string;
}

interface HighlightedEdgeIdentifier {
	socket1: Socket;
	socket2: Socket;
}

/** Key flags */
const KeyFlags = {
	SHIFT: 1,
	ALT: 2,
	CTRL: 4,
	META: 8
} as const;

/**
 * User interface data for a graph.
 */
class GraphEditorUI {
	/** The parent graph. */
	graph: Graph;

	/** The Element for the editor's viewport. */
	viewportElement: HTMLDivElement | null;

	/** The Element for the editor's backdrop. */
	backdropElement: HTMLDivElement | null;

	/** The Element for the editor's contents. */
	contentElement: HTMLDivElement | null;

	/** Editor scale (zoom in/out). */
	scale: number;

	/** Editor content offsets. */
	offsets: { x: number; y: number };

	/** Cursor data. */
	cursor: {
		/** The last known X position of the cursor. */
		x: number;

		/** The last known Y position of the cursor. */
		y: number;

		/** The mouse button being held down:
		 * - `-1`: No button pressed.
		 * - `0`: Main button pressed, usually the left button
		 * - `1`: Auxiliary button pressed, usually the wheel button or the middle button (if present)
		 * - `2`: Secondary button pressed, usually the right button
		 * - `3`: Fourth button, typically the Browser Back button
		 * - `4`: Fifth button, typically the Browser Forward button
		 */
		button: number;

		/** Flags for keys being held down. */
		keys: number;
	};

	/** Reference to objects "grabbed" in the UI. */
	grabbed: {
		socket: Socket | null;
		node: GraphNode | null;
	};

	/** List of all nodes selected in the UI. */
	selectedNodes: Array<GraphNode>;

	/** List of all nodes highlighted in the UI. */
	highlightedNodes: Array<GraphNode>;

	/** Selection area anchor in the UI. */
	selectionArea: { x: number; y: number } | null;

	/** Information needed to highlight an edge in the graph UI. */
	highlightedEdge: HighlightedEdgeIdentifier | null;

	/** For keeping track of 'camera' (offset) movement */
	translating: boolean;

	/** For keeping track of the currently executing 'interval' while scrolling / translating the 'camera' (offset variables) */
	translatingInterval: number | null;

	/** Whether the editor is currently in a scaling transition. */
	isScaling: boolean;

	/** Callbacks to execute when the editor is no longer scaling. */
	scaleFrameCallbacks: Array<() => void>;

	/** Cached viewport positions. This is used as an optimization to avoid recomputing the positions when not needed, and is reset on each animation frame.  */
	cachedViewportPositions: { top: number; right: number; bottom: number; left: number } | null = null;

	/** Cached backdrop positions. This is used as an optimization to avoid recomputing the positions when not needed, and is reset on each animation frame.  */
	cachedBackdropPositions: { top: number; right: number; bottom: number; left: number } | null = null;

	/** Cached content positions. This is used as an optimization to avoid recomputing the positions when not needed, and is reset on each animation frame.  */
	cachedContentPositions: { top: number; right: number; bottom: number; left: number } | null = null;

	constructor(graph: Graph) {
		this.graph = graph;
		this.viewportElement = null;
		this.backdropElement = null;
		this.contentElement = null;
		this.scale = 1.0;
		this.offsets = { x: 0, y: 0 };
		this.cursor = { x: 0, y: 0, button: -1, keys: 0 };
		this.grabbed = { socket: null, node: null };
		this.selectedNodes = [];
		this.highlightedNodes = [];
		this.selectionArea = null;
		this.highlightedEdge = null;
		this.translating = false;
		this.translatingInterval = null;
		this.isScaling = false;
		this.scaleFrameCallbacks = [];
	}

	/**
	 * Set the elements for the editor UI.
	 *
	 * @param viewport The viewport element.
	 * @param backdrop The backdrop element.
	 * @param content The content element.
	 */
	setElements(viewport?: HTMLDivElement, backdrop?: HTMLDivElement, content?: HTMLDivElement) {
		this.viewportElement = viewport || null;
		this.backdropElement = backdrop || null;
		this.contentElement = content || null;
	}

	/**
	 * Get the positions of the editor's viewport element.
	 *
	 * @returns The positions of the viewport element.
	 */
	viewportPositions(): { top: number; right: number; bottom: number; left: number } {
		if (!this.viewportElement) return { top: 0, right: 0, bottom: 0, left: 0 };
		if (this.cachedViewportPositions) return this.cachedViewportPositions;

		const viewportRect = this.viewportElement.getBoundingClientRect();
		this.cachedViewportPositions = {
			top: viewportRect.top,
			right: viewportRect.right,
			bottom: viewportRect.bottom,
			left: viewportRect.left
		};

		requestAnimationFrame(() => {
			// Reset the cached value on next update
			this.cachedViewportPositions = null;
		});

		return this.cachedViewportPositions;
	}

	/**
	 * Get the positions of the editor's backdrop element.
	 *
	 * @returns The positions of the backdrop element.
	 */
	backdropPositions(): { top: number; right: number; bottom: number; left: number } {
		if (!this.backdropElement) return { top: 0, right: 0, bottom: 0, left: 0 };
		if (this.cachedBackdropPositions) return this.cachedBackdropPositions;

		const backdropRect = this.backdropElement.getBoundingClientRect();
		this.cachedBackdropPositions = {
			top: backdropRect.top,
			right: backdropRect.right,
			bottom: backdropRect.bottom,
			left: backdropRect.left
		};

		requestAnimationFrame(() => {
			// Reset the cached value on next update
			this.cachedBackdropPositions = null;
		});

		return this.cachedBackdropPositions;
	}

	/**
	 * Get the positions of the editor's content element.
	 *
	 * @returns The positions of the content element.
	 */
	contentPositions(): { top: number; right: number; bottom: number; left: number } {
		if (!this.contentElement) return { top: 0, right: 0, bottom: 0, left: 0 };
		if (this.cachedContentPositions) return this.cachedContentPositions;

		const contentRect = this.contentElement.getBoundingClientRect();
		this.cachedContentPositions = {
			top: contentRect.top,
			right: contentRect.right,
			bottom: contentRect.bottom,
			left: contentRect.left
		};

		requestAnimationFrame(() => {
			// Reset the cached value on next update
			this.cachedContentPositions = null;
		});

		return this.cachedContentPositions;
	}

	/**
	 * Move the grabbed (and possibly selected) nodes by the given x/y amount.
	 *
	 * @param x The amount to move the nodes in the x-direction.
	 * @param y The amount to move the nodes in the y-direction.
	 */
	moveNodes(x: number, y: number) {
		if (!this.grabbed.node) {
			return;
		}

		// Get the nodes that should be moved
		// If the selected nodes also include the grabbed node, we'll move all selected nodes
		// Otherwise, we just move the grabbed node
		const nodesToMove = this.selectedNodes.includes(this.grabbed.node) ? this.selectedNodes : [this.grabbed.node];

		// Move the nodes
		for (const node of nodesToMove) {
			node.x += x;
			node.y += y;
		}
	}

	/**
	 * Callback for a mouse move event on the Graph UI.
	 *
	 * @param event The MouseEvent.
	 */
	onMouseMove(event: MouseEvent) {
		const editorStore = useEditorStore();
		const contentPositions = this.contentPositions();
		const backdropPositions = this.backdropPositions();

		const cursorX =
			(event.clientX - backdropPositions.left - (contentPositions.left - backdropPositions.left)) / this.scale;
		const cursorY =
			(event.clientY - backdropPositions.top - (contentPositions.top - backdropPositions.top)) / this.scale;

		const dX = cursorX - this.cursor.x;
		const dY = cursorY - this.cursor.y;

		if (this.cursor.button == 0 && this.cursor.keys == KeyFlags.SHIFT && !this.selectionArea) {
			if (editorStore.isResolvingMergeConflict) {
				return;
			}
			// Add the selection area
			this.deselectAllNodes();
			this.selectionArea = { x: cursorX, y: cursorY };
			this.cursor.x = cursorX;
			this.cursor.y = cursorY;
			return;
		}

		if (this.selectionArea) {
			if (editorStore.isResolvingMergeConflict) {
				return;
			}
			// Handle selection of nodes
			this.cursor.x = cursorX;
			this.cursor.y = cursorY;

			this.deselectAllNodes();
			const areaMinX = Math.min(this.cursor.x, this.selectionArea.x);
			const areaMinY = Math.min(this.cursor.y, this.selectionArea.y);
			const areaMaxX = Math.max(this.cursor.x, this.selectionArea.x);
			const areaMaxY = Math.max(this.cursor.y, this.selectionArea.y);
			const nodesToSelect = this.graph.findNodesInArea(areaMinX, areaMinY, areaMaxX, areaMaxY);
			this.selectedNodes.push(...nodesToSelect);

			return;
		}

		if (this.cursor.button != 0 || this.cursor.keys) {
			this.cursor.x = cursorX;
			this.cursor.y = cursorY;
			return;
		}

		if (this.grabbed.node && !this.grabbed.socket) {
			if (editorStore.isResolvingMergeConflict) {
				return;
			}
			this.moveNodes(dX, dY);
			this.cursor.x = cursorX;
			this.cursor.y = cursorY;
			return;
		}

		if (!this.grabbed.node && !this.grabbed.socket) {
			// Scroll
			this.offsets.x += dX;
			this.offsets.y += dY;

			// Scrolling also moves the mouse, so we need to adjust accordingly
			this.cursor.x = cursorX - dX;
			this.cursor.y = cursorY - dY;

			return;
		}

		this.cursor.x = cursorX;
		this.cursor.y = cursorY;
	}

	/**
	 * Callback for a mouse down event on the Graph UI.
	 */
	onMouseDown(event: MouseEvent) {
		this.cursor.button = event.button;
		this.cursor.keys = 0;

		this.cursor.keys |= event.shiftKey ? KeyFlags.SHIFT : 0;
		this.cursor.keys |= event.altKey ? KeyFlags.ALT : 0;
		this.cursor.keys |= event.ctrlKey ? KeyFlags.CTRL : 0;
		this.cursor.keys |= event.metaKey ? KeyFlags.META : 0;
	}

	/**
	 * Callback for a mouse up event on the Graph UI.
	 */
	onMouseUp() {
		this.cursor.button = -1;
		this.cursor.keys = 0;
		this.selectionArea = null;
		this.grabNode(null);
	}

	/**
	 * Callback for a click event on the Graph UI.
	 */
	onClick() {
		this.grabSocket(null);
	}

	/**
	 * Zoom the graph UI by the given amount.
	 *
	 * @param amount Amount to zoom. Negative values zoom out, and positive values zoom in.
	 */
	zoom(amount: number) {
		this.scale = Math.min(Math.max(this.scale + amount, 0.1), 2.0);
	}

	/** Zoom out by the standard increment. */
	zoomOut() {
		this.zoom(-0.1);
	}

	/** Zoom in by the standard increment. */
	zoomIn() {
		this.zoom(0.1);
	}

	/** Reset the zoom to default. */
	resetZoom() {
		this.scale = 1.0;
	}

	/**
	 * Grab a socket in the UI.
	 *
	 * @param socket The socket. If null, the grabbed socket is cleared.
	 */
	grabSocket(socket: Socket | null) {
		this.grabbed.socket = socket;
	}

	/**
	 * Grab a node in the UI.
	 *
	 * @param node The node. If null, the grabbed node is cleared.
	 */
	grabNode(node: GraphNode | null) {
		this.grabbed.node = node;
	}

	/**
	 * Select a node.
	 *
	 * @param node The node.
	 */
	selectNode(node: GraphNode) {
		if (!this.selectedNodes.includes(node)) {
			this.selectedNodes.push(node);
		}
	}

	/**
	 * Highlight a node.
	 *
	 * @param node The node.
	 */
	highlightNode(node: GraphNode) {
		if (!this.highlightedNodes.includes(node)) {
			this.highlightedNodes.push(node);
		}
	}

	/**
	 * De-select a node. If the node is not selected, then this does nothing.
	 *
	 * @param node The node.
	 */
	deselectNode(node: GraphNode) {
		const index = this.selectedNodes.findIndex((n) => n === node);
		if (index !== -1) {
			this.selectedNodes.splice(index, 1);
		}
	}

	/**
	 * De-highlight a node. If the node is not highlighted, then this does nothing.
	 *
	 * @param node The node.
	 */
	deHighlightNode(node: GraphNode) {
		const index = this.highlightedNodes.findIndex((n) => n === node);
		if (index !== -1) {
			this.highlightedNodes.splice(index, 1);
		}
	}

	/**
	 * De-highlight all nodes
	 */
	deHighlightAllNodes() {
		this.highlightedNodes.splice(0, this.highlightedNodes.length);
	}

	/**
	 * Select all nodes.
	 */
	selectAllNodes() {
		for (const node of this.graph.getNodes()) {
			this.selectNode(node);
		}
	}

	/**
	 * De-select all nodes.
	 */
	deselectAllNodes() {
		this.selectedNodes.splice(0, this.selectedNodes.length);
	}

	/**
	 * Toggle the selection on a node (select it if it not selected, or de-select it if it is);
	 *
	 * @param node The node.
	 */
	toggleNodeSelection(node: GraphNode) {
		if (this.selectedNodes.includes(node)) {
			this.deselectNode(node);
		} else {
			this.selectNode(node);
		}
	}

	/**
	 * Highlight an edge in the UI.
	 *
	 * @param socket1 The first socket comprising this edge.
	 * @param socket2 The second socket comprising this edge.
	 */
	highlightEdge(socket1: Socket, socket2: Socket) {
		this.highlightedEdge = { socket1: socket1, socket2: socket2 };
	}

	/**
	 * Remove any highlights on edges in the UI.
	 */
	unhighlightEdge() {
		this.highlightedEdge = null;
	}

	/**
	 * Check whether a given edge is highlighted.
	 *
	 * @param socket1 The first socket comprising this edge.
	 * @param socket2 The second socket comprising this edge.
	 * @returns Whether the given edge is highlighted.
	 */
	isEdgeHighlighted(socket1: Socket, socket2: Socket): boolean {
		if (this.highlightedEdge === null) return false;
		return (
			(this.highlightedEdge.socket1 == socket1 && this.highlightedEdge.socket2 == socket2) ||
			(this.highlightedEdge.socket2 == socket1 && this.highlightedEdge.socket1 == socket2)
		);
	}

	/**
	 * Moves the editor 'camera' to the specified coordinate location by modifying the offset variable.
	 * @param x The X coordinate to navigate to
	 * @param y The y coordinate to navigate to
	 * @param translate When true: will 'pan' or 'translate' to the requested coordinates instead of snapping/jumping to them
	 */
	navigateUiToCoordinates(x: number, y: number, translate: boolean) {
		if (this.translating) {
			if (this.translatingInterval) {
				clearInterval(this.translatingInterval);
			}
		}
		if (!translate) {
			this.offsets.x = x;
			this.offsets.y = y;
			return;
		}
		this.translating = true;
		const startingX = this.offsets.x;
		const startingY = this.offsets.y;
		const xDistance = Math.abs(x - this.offsets.x);
		const yDistance = Math.abs(y - this.offsets.y);
		const transitionTime = 50;
		const tranistionStep = 25;
		const xStep = xDistance / tranistionStep;
		const yStep = yDistance / tranistionStep;
		let travelledX = 0;
		let travelledY = 0;
		this.translatingInterval = setInterval(() => {
			let clear = true;
			if (travelledX < xDistance) {
				clear = false;
				if (startingX > x) this.offsets.x += xStep * -1;
				else this.offsets.x += xStep;
				travelledX += xStep;
			}
			if (travelledY < yDistance) {
				clear = false;
				if (startingY > y) this.offsets.y += yStep * -1;
				else this.offsets.y += yStep;
				travelledY += yStep;
			}
			if (clear) {
				if (this.translatingInterval) {
					clearInterval(this.translatingInterval);
					this.translating = false;
				}
			}
		}, transitionTime / tranistionStep);
	}

	/**
	 * Moves the editor 'camera' to the specified node's location by modifying the offset variable.
	 * @param node The node to center the camera on
	 */
	navigateUiToNodeLocation(node: GraphNode) {
		let x = -1 * node.x;
		let y = -1 * node.y;
		if (this.viewportElement) {
			const editorArea = this.viewportPositions();
			x += (editorArea.right - editorArea.left) / 2 - node.width() / 2;
			y += (editorArea.bottom - editorArea.top) / 2 - node.height() / 2;
		}
		this.navigateUiToCoordinates(x, y, true);
	}

	/**
	 * Mark the UI as scaling or not scaling. The UI is scaling when it is performing a CSS transition to scale the editor.
	 *
	 * @param isScaling Whether the UI is scaling.
	 */
	setIsScaling(isScaling: boolean) {
		this.isScaling = isScaling;
	}

	/**
	 * Execute a callback when the UI is not scaling. The UI is scaling when it is performing a CSS transition to scale the editor.
	 *
	 * Some position-dependent UI elements will experience visual issues when added to the DOM while the editor is scaling. Use this
	 * function with a callback to add these elements when the UI stops scaling to avoid such issues.
	 *
	 * If the UI is not currently scaling, the callback will be executed immediately. Otherwise, the callback will be tracked and executed
	 * the next time the UI stops scaling.
	 *
	 * @param callback The callback to execute.
	 */
	requestScaleFrame(callback: () => void) {
		if (this.isScaling) {
			this.scaleFrameCallbacks.push(callback);
			return;
		}

		callback();
	}

	/**
	 * Internal function to execute all scaling callbacks. The tracked callbacks will be removed after they have been executed.
	 */
	handleScaleFrames() {
		for (const callback of this.scaleFrameCallbacks) {
			callback();
		}

		this.scaleFrameCallbacks.splice(0, this.scaleFrameCallbacks.length);
	}

	/**
	 * Serialize relevant data to this object to the format used for representing this object in a file.
	 *
	 * @returns The dictionary representation of the data for this object.
	 */
	serialize(): SerializedGraphUI {
		return {
			scale: Math.floor(this.scale * 10) / 10,
			xy: `${Math.floor(this.offsets.x)},${Math.floor(this.offsets.y)}`
		};
	}
}

export { GraphEditorUI, KeyFlags };
export type { SerializedGraphUI };
