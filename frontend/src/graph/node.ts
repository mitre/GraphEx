import type { Graph } from '@/graph/graph';
import type { SerializedSocket, SocketMetadata } from '@/graph/socket';
import { Socket } from '@/graph/socket';
import { nextTick } from 'vue';

const NodeTypes = {
	ACTION: 'action',
	DATA: 'data',
	CAST: 'cast',
	GENERATOR: 'generator',
	COMMENT: 'comment'
} as const;

type NodeType = (typeof NodeTypes)[keyof typeof NodeTypes];

/**
 * Metadata about a node's input field.
 */
interface InputFieldMetadata {
	/** The default value for the input field. */
	default: any;

	/** The name of this input field. */
	name: string;

	/** Whether this is a multi-line text area (otherwise, newlines are not allowed). */
	multiline: boolean;

	/** Whether this field is required. */
	required: boolean;

	/** Whether to use the 'floating label' style of input. */
	floatingLabel: boolean;
}

/**
 * Metadata for a node.
 */
interface NodeMetadata {
	/** The type of this node. */
	type: NodeType;

	/** The name of this node. */
	name: string;

	/** Description of this node. */
	description: string;

	/** The link to external documentation (Python, Bash, etc) */
	hyperlink?: Array<string>;

	/** The color used to represent this node. */
	color: string;

	/** Custom text color of this node  */
	textColor: string;

	/** The sockets for this node. */
	sockets: Array<SocketMetadata>;

	/** The categories under which this node is sorted. */
	categories: Array<string>;

	/** Input field to use in this node. */
	field: InputFieldMetadata | null;

	/** Whether this is a dynamic node (metadata is dependent on graph context). A true value will refresh this node's metadata as the node changes. */
	dynamic: boolean;

	/** Dynamic error information for this node. */
	error: string;

	/** The plugin which provides this node (or GraphEx itself) */
	original_plugin: string;

	/** Whether this node was created by the inventory or not */
	isInventoryNode: boolean;

	/** The value of the inventory Node */
	inventoryValue: string | number | boolean | Array<string> | Array<number> | Array<boolean> | null;

	/** Whether this node allows for more input sockets to be added to it or not */
	allowsNewInputs: boolean;
}

/**
 * Serialized form of a GraphNode.
 */
interface SerializedNode {
	/** The name of this node. */
	name: string;

	/** Unique ID to identify this node within this graph. */
	id: string;

	/** The X,Y position of the node. */
	xy: string;

	/** Input sockets on this node (we only need inputs to reconstruct the graph; tracking the outputs is unnecessary). */
	inputs?: Array<SerializedSocket>;

	/** The value for this node's input field. */
	fieldValue?: string | number | boolean;

	/** Custom color of this node */
	color?: string;

	/** Custom text color of this node  */
	textColor?: string;

	/** Output sockets that were explicitly disabled via the UI */
	disabledVariableOutputs?: Array<String>;

	/** Whether or not this node needs an inventory to be loaded to use it */
	requiresInventory?: boolean;
}

/**
 * Get the complete state of a node. This contains all the necessary information to completely restore a node without needing
 * external graph state/network requests to fetch updated metadata.
 */
interface NodeStateObject {
	/** The serialized node. */
	serialized: SerializedNode;

	/** The metadata for this node at this given state. */
	metadata: NodeMetadata;

	/** The output connections for this node. The format is {outputSocket.metadata.name}->{connection.node.id}::{connection.metadata.name} */
	outputConnections: Array<string>;
}

/**
 * A node in a graph.
 */
class GraphNode {
	/** The parent graph. */
	graph: Graph;

	/** Unique ID to identify this node within this graph. */
	id: string;

	/** The Element for this node in the graph UI. */
	element: HTMLDivElement | null;

	/** Whether this node is currently loading. */
	isLoading: boolean;

	/** Metadata for this node. */
	metadata: NodeMetadata;

	/** The X position of the node. */
	x: number;

	/** The Y position of the node. */
	y: number;

	/** Input sockets on this node (order-dependent). */
	inputSockets: Array<Socket>;

	/** Output sockets on this node (order-dependent). */
	outputSockets: Array<Socket>;

	/** The value of this node's input field (if one exists). */
	fieldValue?: string | number | boolean;

	/** Custom color of this node, if applicable. */
	color?: string;

	/** Custom text color of this node, if applicable.  */
	textColor?: string;

	/** Cached node width. This is used as an optimization to avoid recomputing the width when not needed, and is reset on each animation frame.  */
	cachedWidth: number | null = null;

	/** Cached node height. This is used as an optimization to avoid recomputing the height when not needed, and is reset on each animation frame.  */
	cachedHeight: number | null = null;

	/** Timeout referenced used for buffering this node's refresh. */
	refreshTimeout?: number;

	/** Dependencies gathered from this node's last refresh. This is used to skip refreshing this node when a refresh is not needed. */
	lastRefreshedDependencies: string;

	/** Value tracking whether the next refresh should be forced through (regardless of the current lastRefreshedDependencies). */
	forceRefresh: boolean;

	/** Value used to force a re-render. */
	renderKey: number;

	constructor(
		graph: Graph,
		metadata: NodeMetadata,
		x: number,
		y: number,
		fieldValue?: string | number | boolean,
		id?: string,
		color?: string,
		textColor?: string
	) {
		this.graph = graph;

		if (id) {
			this.id = id;
		} else {
			const namePrefix = metadata.name.replace(/[^a-zA-Z0-9]/g, '') + '-';
			let suffix = 0;
			while (graph.commentedNodeIds.has(namePrefix + suffix)) {
				suffix += 1;
			}
			while (Array.from(graph.getNodes()).some((n) => n.id == namePrefix + suffix)) {
				suffix += 1;
			}
			this.id = namePrefix + suffix;
		}

		this.element = null;
		this.isLoading = false;
		this.metadata = metadata;
		this.x = x;
		this.y = y;
		this.renderKey = 0;
		this.inputSockets = [];
		this.outputSockets = [];

		this.forceRefresh = false;
		this.lastRefreshedDependencies = '';

		if (fieldValue !== undefined && metadata.field) {
			this.fieldValue = fieldValue;
		} else if (metadata.field) {
			this.fieldValue = metadata.field.default;
		}

		this.color = color;
		this.textColor = textColor;

		for (const inputSocketMetadata of metadata.sockets) {
			this.addSocket(inputSocketMetadata);
		}

		this.lastRefreshedDependencies = this.getRefreshDependencies();
	}

	/**
	 * Set the element for this node.
	 *
	 * @param element The UI element.
	 */
	setElement(element?: HTMLDivElement) {
		this.element = element || null;
	}

	/**
	 * Get the width of this node in the UI.
	 *
	 * @returns The width of the node.
	 * @throws If the node element is not available in the UI.
	 */
	width(): number {
		if (!this.element) throw `width(): Node element not available for node ${this.id}`;
		if (this.cachedWidth !== null) return this.cachedWidth;

		this.cachedWidth = this.element.offsetWidth;

		requestAnimationFrame(() => {
			// Reset the cached value on next update
			this.cachedWidth = null;
		});

		return this.cachedWidth;
	}

	/**
	 * Get the height of this node in the UI.
	 *
	 * @returns The height of the node.
	 * @throws If the node element is not available in the UI.
	 */
	height(): number {
		if (!this.element) throw `height(): Node element not available for node ${this.id}`;
		if (this.cachedHeight !== null) return this.cachedHeight;

		this.cachedHeight = this.element.offsetHeight;

		requestAnimationFrame(() => {
			// Reset the cached value on next update
			this.cachedHeight = null;
		});

		return this.cachedHeight;
	}

	/**
	 * Create a new socket on this node.
	 *
	 * @param metadata The socket metadata.
	 * @returns The newly created socket.
	 */
	addSocket(metadata: SocketMetadata): Socket {
		const socket = new Socket(this, metadata);
		if (metadata.isInput) {
			this.inputSockets.push(socket);
			return this.getInputSocket(metadata.name); // We need to use getInputSocket to ensure reactivity is maintained (i.e. a proxy is returned)
		}
		this.outputSockets.push(socket);
		return this.getOutputSocket(metadata.name); // We need to use getOutputSocket to ensure reactivity is maintained (i.e. a proxy is returned)
	}

	/**
	 * Get an input socket on this node.
	 *
	 * @param name The name of the socket.
	 * @returns The found input socket.
	 * @throws An error if the input socket was not found.
	 */
	getInputSocket(name: string): Socket {
		const socket = this.inputSockets.find((s) => s.metadata.name == name);
		if (!socket) {
			throw `Input socket ${name} not found on node ${this.id}`;
		}
		return socket;
	}

	/**
	 * Check whether an input socket exists on this node.
	 *
	 * @param name The name of the socket
	 * @returns Whether the socket exists.
	 */
	hasInputSocket(name: string): boolean {
		return !!this.inputSockets.find((s) => s.metadata.name == name);
	}

	/**
	 * Get an output socket on this node.
	 *
	 * @param name The name of the socket.
	 * @returns The found output socket.
	 * @throws An error if the output socket was not found.
	 */
	getOutputSocket(name: string): Socket {
		const socket = this.outputSockets.find((s) => s.metadata.name == name);
		if (!socket) {
			throw `Output socket ${name} not found on node ${this.id}`;
		}
		return socket;
	}

	/**
	 * Check whether an output socket exists on this node.
	 *
	 * @param name The name of the socket
	 * @returns Whether the socket exists.
	 */
	hasOutputSocket(name: string): boolean {
		return !!this.outputSockets.find((s) => s.metadata.name == name);
	}

	/**
	 * Serialize relevant data to this object to the format used for representing this object in a file.
	 *
	 * @returns The dictionary representation of the data for this object.
	 */
	serialize(): SerializedNode {
		const s: SerializedNode = {
			name: this.metadata.name,
			id: this.id,
			xy: `${Math.floor(this.x)},${Math.floor(this.y)}`
		};

		if (this.inputSockets.length) s.inputs = this.inputSockets.map((socket) => socket.serialize());
		if (this.outputSockets.length) {
			const disabledSocketNames: string[] = [];
			this.outputSockets.forEach((socket) => {
				if (socket.disabledVariableOutput) disabledSocketNames.push(socket.metadata.name);
			});
			if (disabledSocketNames.length) s.disabledVariableOutputs = disabledSocketNames;
		}
		if (this.fieldValue !== undefined && this.metadata.field) s.fieldValue = this.fieldValue;
		if (this.color) s.color = this.color;
		if (this.textColor) s.textColor = this.textColor;
		if (this.metadata.isInventoryNode) s.requiresInventory = true;

		return s;
	}

	/**
	 * Get the NodeStateObject for this node.
	 *
	 * @returns The NodeStateObject representing the current node state.
	 */
	getStateObject(): NodeStateObject {
		const obj: NodeStateObject = {
			metadata: JSON.parse(JSON.stringify(this.metadata)),
			serialized: this.serialize(),
			outputConnections: []
		};

		for (const outputSocket of this.outputSockets) {
			for (const connection of outputSocket.connections) {
				obj.outputConnections.push(`${outputSocket.metadata.name}->${connection.node.id}::${connection.metadata.name}`);
			}
		}

		return obj;
	}

	/**
	 * Clears/Resets/Deletes the connections of this node to other nodes.
	 */
	clearConnections() {
		// Clear input sockets
		for (const socket of this.inputSockets) {
			socket.disconnectAll();
		}

		// Clear output sockets
		for (const socket of this.outputSockets) {
			socket.disconnectAll();
		}
	}

	/**
	 * Set the field value for this node.
	 *
	 * @param newValue The new value.
	 */
	setFieldValue(newValue: string | number | boolean) {
		this.fieldValue = newValue;
	}

	/**
	 * Set the color for this node.
	 * @param newValue a string containing a color in hex
	 */
	setColorValue(newValue?: string) {
		this.color = newValue;
	}

	/**
	 * Set the text color fr this node.
	 * @param newValue a string containing a color in hex
	 */
	setTextColorValue(newValue?: string) {
		this.textColor = newValue;
	}

	/**
	 * Center a node around the given (x, y). If a coordinate is not specified, the current coordinate will be used.
	 *
	 * @param x The X coordinate to center around. If not specified, the current X coordinate will be used.
	 * @param y The Y coordinate to center around. If not specified, the current Y coordinate will be used.
	 */
	centerPosition(x?: number, y?: number) {
		x = x === undefined ? this.x : x;
		y = y === undefined ? this.y : y;

		this.x = x - this.width() / 2;
		this.y = y - this.height() / 2;
	}

	/**
	 * Dependencies that are taken into consideration when determining whether a node needs to be refreshed. When these dependencies change,
	 * the node should be refreshed to get the latest metadata. This is provided as a string rather than an object for easy equality checking.
	 *
	 * @returns The string representation of the refresh dependencies.
	 */
	getRefreshDependencies(): string {
		return JSON.stringify([
			this.fieldValue,
			this.inputSockets.map((socket) => socket.serialize()),
			this.outputSockets.map((socket) => socket.serialize())
		]);
	}

	/**
	 * Force a re-render of this node in the graph.
	 */
	forceRerender() {
		this.renderKey += 1;
	}

	/**
	 * Request that this node refresh its metadata. This will not immediately trigger a refresh but instead will buffer the refresh (via a timeout)
	 * to ensure that several refresh requests in a short timeframe only trigger a single refresh (which is an expensive operation).
	 *
	 * This will not necessarily trigger a refresh if a refresh is not needed (e.g. dependencies from the last refresh have not changed).
	 *
	 * @param timeout The time (in ms) to set for the refresh timeout (buffer time).
	 * @param force Force a refresh to occur regardless of the dependency state.
	 */
	requestRefreshMetadata(timeout: number = 100, force: boolean = false) {
		clearTimeout(this.refreshTimeout);
		if (force) {
			this.forceRefresh = true;
		}

		this.refreshTimeout = setTimeout(async () => {
			clearTimeout(this.refreshTimeout);
			if (!this.forceRefresh && this.lastRefreshedDependencies === this.getRefreshDependencies()) {
				// Skip a refresh when the last state is the same as the current state
				// This is used to prevent a refresh from triggering another refresh unnecessarily
				return;
			}

			if (this.isLoading) {
				// Already refreshing, trigger another
				this.forceRefresh = true;
				this.requestRefreshMetadata();
				return;
			}
			this.forceRefresh = false;

			await this.refreshMetadata();
			this.lastRefreshedDependencies = this.getRefreshDependencies();
		}, timeout);
	}

	/**
	 * Immediately refresh the metadata for this node. This will perform a network request to get the latest metadata for this node dependent on
	 * the graph context. The sockets and other information about this node will be updated automatically (and in-place) after the request completes.
	 *
	 * This is an expensive operation. In most cases, use `requestRefreshMetadata` instead.
	 */
	async refreshMetadata() {
		if (!this.metadata.dynamic) {
			return;
		}

		this.isLoading = true;

		let newMetadata = this.metadata;
		try {
			const response = await fetch('/api/updateNode', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					graph: this.graph.serialize(),
					id: this.id
				})
			});

			if (response.status != 200) {
				throw `Failed to refresh node: ${await response.text()}`;
			}

			newMetadata = await response.json();
		} catch (e) {
			newMetadata.error = String(e);
		} finally {
			this.metadata = newMetadata;

			// Reload the sockets
			// First, delete all the sockets that are no longer present on the node
			// We'll keep the sockets that are the same after the reload to preserve any connections/state
			for (const inputSocket of [...this.inputSockets]) {
				const newInputSocket = this.metadata.sockets.find((s) => s.isInput && s.name === inputSocket.metadata.name);
				if (newInputSocket) {
					// Exists already
					// Update the socket metadata and disconnect any connections that are no longer allowed
					inputSocket.metadata = newInputSocket;

					for (const connection of inputSocket.connections) {
						try {
							inputSocket.connect(connection, { dryRun: true });
						} catch {
							inputSocket.disconnect(connection);
						}
					}

					continue;
				}

				inputSocket.disconnectAll();
				this.inputSockets.splice(this.inputSockets.indexOf(inputSocket), 1);
			}

			for (const outputSocket of [...this.outputSockets]) {
				const newOutputSocket = this.metadata.sockets.find((s) => !s.isInput && s.name === outputSocket.metadata.name);

				if (newOutputSocket) {
					// Exists already
					// Update the socket metadata and disconnect any connections that are no longer allowed
					outputSocket.metadata = newOutputSocket;

					for (const connection of outputSocket.connections) {
						try {
							outputSocket.connect(connection, { dryRun: true });
						} catch {
							outputSocket.disconnect(connection);
						}
					}

					continue;
				}

				outputSocket.disconnectAll();
				this.outputSockets.splice(this.outputSockets.indexOf(outputSocket), 1);
			}

			await nextTick();

			// Iterate through the new sockets and add any that didn't exist before
			for (let i = 0; i < this.metadata.sockets.length; i++) {
				const socketMetadata = this.metadata.sockets[i];
				const currentSocketList = socketMetadata.isInput ? this.inputSockets : this.outputSockets;

				const position = currentSocketList.findIndex((s) => s.metadata.name === socketMetadata.name);
				if (position === -1) {
					// Socket doesn't exist yet
					// Insert into list
					currentSocketList.splice(i, 0, new Socket(this, socketMetadata));
				}
			}

			// Done
			this.isLoading = false;
		}
	}
}

export { GraphNode, NodeTypes };
export type { NodeMetadata, NodeStateObject, NodeType, SerializedNode };

