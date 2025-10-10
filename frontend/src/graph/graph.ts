import { GraphEditorUI } from '@/graph/graphui';
import { GraphHistory } from '@/graph/history';
import { GraphNode, type NodeMetadata, type NodeStateObject, type SerializedNode } from '@/graph/node';
import { useMetadataStore } from '@/stores';
import { nextTick } from 'vue';
import YAML from 'yaml';
/**
 * Serialized form of a Graph.
 */
interface SerializedGraph {
	/** Nodes in the graph. */
	nodes: Array<SerializedNode>;

	/** Inputs to this graph. */
	inputs?: Array<GraphInputMetadata>;

	/** Outputs to this graph. */
	outputs?: Array<GraphOutputMetadata>;

	/** The help description for this node */
	description?: string;
}

interface AddNodeOptions {
	/** The value of the field for this node. If undefined, the default value will be used (if a field exists). */
	fieldValue?: string | number | boolean;

	/** The ID of the node. If undefined, a new ID will be generated. */
	id?: string;

	/** Custom color of this node */
	color?: string;

	/** Custom text color of this node  */
	textColor?: string;
}

interface AddNodeStatesOptions {
	/** Whether to also copy the IDs of serialized nodes to the new nodes. If false, a new ID will be generated for each node. */
	copyId?: boolean;

	/** The X position at which these nodes should be added. If not provided, the nodes will be absolutely positioned according to their serialized data. */
	x?: number;

	/** The Y position at which these nodes should be added. If not provided, the nodes will be absolutely positioned according to their serialized data. */
	y?: number;

	/** Whether to center the added nodes around the given (x, y) */
	center?: boolean;

	/**
	 * How to connect added nodes within the graph.
	 * - If 'all', all connections will be added (even those to nodes that weren't added by this call).
	 * - If 'group', only connections to other nodes also added by *this* operation will be added. Connections to pre-existing nodes will be ignored.
	 * - If 'none' or undefined, no connections at all will be added.
	 */
	connect?: 'all' | 'group' | 'none';
}

interface GraphInputMetadata {
	/** Name of this input. */
	name: string;

	/** Name of the data type for this input. */
	datatype: string;

	/** Whether this is a list input. */
	isList?: boolean;

	/** Whether this is a password that should be obfuscated or not */
	isPassword?: boolean;

	/** Description for this input. */
	description?: string;

	/** Category for displaying this value under in the UI */
	category?: string;

	/** Default value for this input. */
	defaultValue?: string | number | boolean | Array<string | number | boolean>;

	enumOptions?: string[];

	/** Whether this graph input should be stored as a secret or not. Secrets WILL NOT have any encrypted values shown in the UI. */
	isSecret?: boolean;
}

interface CompositeValue {
	name: string;
	value?: any;
	children: CompositeValue[];
	metadata: GraphInputMetadata;
	fromSecret?: string;
	presetValue?: any;
	isModified?: boolean;
}

type GroupedInputs = {
	[category: string]: GraphInputMetadata[];
};

type CompositeGraphInputMetadata = {
	datatype: string;
	InputMetadata: GraphInputMetadata[];
};
interface GraphInputMetadataWithState {
	metadata: GraphInputMetadata;
	isSelected: boolean;
}
interface GraphOutputMetadata {
	/** Name of this input. */
	name: string;

	/** Name of the data type for this output. */
	datatype: string;

	/** Whether this is a list output. */
	isList?: boolean;

	/** Description for this output. */
	description?: string;
}

/**
 * A graph and associated metadata.
 */
class Graph {
	/** All nodes in the graph (ID mapped to GraphNode). */
	nodes: Map<string, GraphNode>;

	/** UI metadata for this graph. */
	ui: GraphEditorUI;

	/** History manager for this graph. */
	history: GraphHistory;

	/** Custom metadata about this graph's inputs. */
	inputMetadata: Array<GraphInputMetadata>;

	/** Custom metadata about this graph's outputs. */
	outputMetadata: Array<GraphOutputMetadata>;

	/** The description for this graph. */
	description: string;

	/** Callbacks to call whenever the graph nodes change. */
	onNodesChangedCallbacks: Array<(g: Graph) => Promise<void>>;

	/** Node IDs currently being held by commentted out nodes */
	commentedNodeIds: Set<string>;

	constructor() {
		this.nodes = new Map<string, GraphNode>();
		this.ui = new GraphEditorUI(this);
		this.inputMetadata = [];
		this.outputMetadata = [];
		this.description = '';
		this.onNodesChangedCallbacks = [];
		this.history = new GraphHistory(this);
		this.commentedNodeIds = new Set<string>();
	}

	/**
	 * Add a new node to this graph.
	 *
	 * Note that because this method is synchronous, it may be necessary to follow this with a `nextTick()` call before the
	 * node is available in the DOM.
	 *
	 * @param metadata The metadata for this node.
	 * @param x The X position of the node.
	 * @param y The Y position of the node.
	 * @param options Additional options for adding this node.
	 *
	 * @returns The new GraphNode object.
	 */
	addNode(metadata: NodeMetadata, x: number, y: number, options?: AddNodeOptions): GraphNode {
		options = options || {};
		const newNode = new GraphNode(
			this,
			metadata,
			x,
			y,
			options.fieldValue,
			options.id,
			options.color,
			options.textColor
		);
		this.nodes.set(newNode.id, newNode);
		const newNodeProxy = this.getNode(newNode.id); // We need to use getNode to ensure reactivity is maintained (i.e. a proxy is returned as needed)

		// console.log(`Added node ${newNode.id}`);
		return newNodeProxy;
	}

	/**
	 * Keeps track of a node that was commented out
	 * @param id The ID of the node to keep track of
	 */
	recordCommentNodeID(id: string) {
		this.commentedNodeIds.add(id);
	}

	/**
	 * Removes the ID of a node that was commented out
	 * @param id The ID of the node to stop tracking
	 */
	removeCommentedNodeId(id: string) {
		this.commentedNodeIds.delete(id);
	}

	/**
	 * Add nodes to this graph based on the given node states.
	 *
	 * Note that because this method is synchronous, it may be necessary to follow this with a `nextTick()` call before the
	 * nodes are available in the DOM.
	 *
	 * @param nodeStates The node states to add to the graph.
	 * @param options Options for how to add the nodes.
	 *
	 * @returns The added nodes.
	 */
	addNodeStates(nodeStates: Array<NodeStateObject>, options?: AddNodeStatesOptions): Array<GraphNode> {
		options = options || {};

		let offsetX = 0;
		let offsetY = 0;
		if (options.x !== undefined) {
			// Find the minimum X value of these nodes and use that as the offset
			offsetX = Math.min(...nodeStates.map((state) => Number(state.serialized.xy.split(',')[0])));
		}

		if (options.y !== undefined) {
			// Find the minimum Y value of these nodes and use that as the offset
			offsetY = Math.min(...nodeStates.map((state) => Number(state.serialized.xy.split(',')[1])));
		}

		// Add nodes
		const addedNodes: Array<GraphNode> = []; // All added nodes
		const addedNodeIds: { [oldId: string]: string } = {}; // Maps the serialized node ID to the actual node ID (used to convert old connection IDs)
		const addedNodeData: Array<[GraphNode, NodeStateObject]> = []; // List of tuples (Added Node, The state object for the added node)

		for (const nodeToAdd of nodeStates) {
			const xy = nodeToAdd.serialized.xy.split(',');
			const addedNode = this.addNode(
				nodeToAdd.metadata,
				Number(xy[0]) - offsetX + (options.x ? options.x : 0),
				Number(xy[1]) - offsetY + (options.y ? options.y : 0),
				{
					fieldValue: nodeToAdd.serialized.fieldValue,
					id: options.copyId ? nodeToAdd.serialized.id : undefined,
					color: nodeToAdd.serialized.color,
					textColor: nodeToAdd.serialized.textColor
				}
			);

			addedNodeIds[nodeToAdd.serialized.id] = addedNode.id;
			addedNodes.push(addedNode);
			addedNodeData.push([addedNode, nodeToAdd]);
		}

		// For all the added/updated nodes, go throught the sockets and apply the correct configurations
		// This has to be done after adding all the nodes to ensure that the nodes all exist in the graph before connecting them
		for (const data of addedNodeData) {
			const [addedNode, stateObj] = data;

			// Handle input sockets
			for (const inputSocket of addedNode.inputSockets) {
				const serializedSocket = stateObj.serialized.inputs?.find((s) => s.name == inputSocket.metadata.name);
				if (!serializedSocket) {
					continue;
				}

				inputSocket.clearInputSources();
				inputSocket.fieldValue =
					serializedSocket.fieldValue !== undefined
						? JSON.parse(JSON.stringify(serializedSocket.fieldValue))
						: undefined;
				inputSocket.variableName = serializedSocket.variableName;
				inputSocket.graphInputName = serializedSocket.graphInputName;

				// Update connections
				if (options.connect === 'all' || options.connect === 'group') {
					for (const connection of serializedSocket.connections || []) {
						const [nodeId, socketName] = connection.split('::');
						if (options.connect !== 'all' && !(nodeId in addedNodeIds)) {
							continue;
						}

						try {
							const targetNode = this.getNode(addedNodeIds[nodeId] || nodeId);
							const targetSocket = targetNode.getOutputSocket(socketName);
							inputSocket.connect(targetSocket);
						} catch (e) {
							console.warn(e);
						}
					}
				}
			}

			// Handle output sockets
			if (options.connect === 'all' || options.connect === 'group') {
				for (const connectionData of stateObj.outputConnections) {
					const [outputSocketName, connection] = connectionData.split('->');
					const outputSocket = addedNode.getOutputSocket(outputSocketName);
					const [connNodeId, connSocketName] = connection.split('::');

					if (options.connect !== 'all' && !(connNodeId in addedNodeIds)) {
						continue;
					}

					try {
						const targetNode = this.getNode(addedNodeIds[connNodeId] || connNodeId);
						const targetSocket = targetNode.getInputSocket(connSocketName);
						targetSocket.connect(outputSocket);
					} catch (e) {
						console.warn(e);
					}
				}
			}
		}

		// Center the nodes if requested
		if (options.center) {
			nextTick(() =>
				requestAnimationFrame(() => {
					// Find the min and max X nodes
					const minXNode = addedNodes.reduce((prev, curr) => (prev.x < curr.x ? prev : curr));
					const maxXNode = addedNodes.reduce((prev, curr) => (prev.x > curr.x ? prev : curr));

					// Find the min and max Y nodes
					const minYNode = addedNodes.reduce((prev, curr) => (prev.y < curr.y ? prev : curr));
					const maxYNode = addedNodes.reduce((prev, curr) => (prev.y > curr.y ? prev : curr));

					// Compute the width and height of the entire group
					const width = maxXNode.x + maxXNode.width() - minXNode.x;
					const height = maxYNode.y + maxYNode.height() - minYNode.y;

					// Offset all nodes by half these amounts
					for (const node of addedNodes) {
						node.x = node.x - width / 2;
						node.y = node.y - height / 2;
					}
				})
			);
		}

		return addedNodes;
	}

	/**
	 * Get the nodes of this graph as an iterable.
	 *
	 * @returns Returns an iterable of GraphNodes in the graph.
	 */
	getNodes(): IterableIterator<GraphNode> {
		return this.nodes.values();
	}

	/**
	 * Get an node by ID.
	 *
	 * @param id The ID of the node.
	 * @returns The found node.
	 * @throws An error if the node is not found.
	 */
	getNode(id: string): GraphNode {
		const node = this.nodes.get(id);
		if (!node) {
			throw `No node with ID ${id} exists.`;
		}
		return node;
	}

	/**
	 * Get an node by ID. If the node is not found, `null` is returned.
	 *
	 * @param id The ID of the node.
	 *
	 * @returns The found node, or `null` if the node is not found.
	 */
	findNode(id: string): GraphNode | null {
		return this.nodes.get(id) || null;
	}

	/**
	 * Delete one or more nodes from the graph.
	 *
	 * @param nodes The nodes to delete (list of node objects or node IDs).
	 */
	deleteNodes(nodes: Array<GraphNode | string>) {
		const targets = nodes.map((node) => (typeof node === 'string' ? this.getNode(node) : node));
		for (const node of targets) {
			this.ui.deselectNode(node);
			node.clearConnections();
			const id = node.id;
			this.nodes.delete(id);
			// console.log(`Deleted node ${node.id}`);
		}
	}

	/**
	 * Find all nodes within a given rectangle. Nodes do not need to be fully contained to be considered within the area; as long as any
	 * portion of a node is within the area, it will be returned as a result.
	 *
	 * @param minX The minimum X position of the rectangle (left edge).
	 * @param minY The minimum Y position of the rectangle (top edge).
	 * @param maxX The maximum X position of the rectangle (right edge).
	 * @param maxY The maximum Y position of the rectangle (bottom edge).
	 * @param exclude Exclude the given nodes from the calculation, if provided.
	 *
	 * @returns All nodes in the graph contained with the given rectangle.
	 */
	findNodesInArea(
		minX: number,
		minY: number,
		maxX: number,
		maxY: number,
		exclude?: Array<GraphNode>
	): Array<GraphNode> {
		const excludedNodes = exclude || [];
		return Array.from(this.getNodes()).filter((node) => {
			if (excludedNodes && excludedNodes.includes(node)) {
				return false;
			}
			const nodeMinX = node.x;
			const nodeMinY = node.y;
			const nodeMaxX = node.x + node.width();
			const nodeMaxY = node.y + node.height();
			return !(nodeMinX > maxX || nodeMinY > maxY || nodeMaxX < minX || nodeMaxY < minY);
		});
	}

	/**
	 * Add or update metadata for a graph input.
	 *
	 * @param metadata The metadata.
	 * @param overwrite The name of the existing input to overwrite.
	 */
	updateInputMetadata(metadata: GraphInputMetadata, overwrite?: string) {
		// Sanitize the metadata
		metadata.name = metadata.name.trim();
		metadata.datatype = metadata.datatype.trim();
		metadata.isList = metadata.isList ? true : undefined;
		metadata.isPassword = metadata.isPassword ? true : undefined;
		metadata.description =
			metadata.description && metadata.description.trim() ? metadata.description.trim() : undefined;
		metadata.category = metadata.category && metadata.category.trim() ? metadata.category.trim() : undefined;

		// Find the value to update
		if (overwrite) {
			const index = this.inputMetadata.findIndex((m) => m.name == overwrite.trim());
			if (index === -1) {
				throw `No graph input found with name ${overwrite}`;
			}

			this.inputMetadata[index] = metadata;
		} else {
			this.inputMetadata.push(metadata);
		}

		//Resort data by categories
		this.orderInputMetadataByCategory();
	}

	/**
	 * Remove/delete metadata for a graph input by name.
	 *
	 * @param name The name of the input to remove.
	 * @throws If the input is not found.
	 */
	removeInputMetadata(name: string) {
		const index = this.inputMetadata.findIndex((md) => md.name == name);
		if (index == -1) {
			throw `Input with name ${name} not found`;
		}

		this.inputMetadata.splice(index, 1);
	}
	/**
	 * Sort the input metadata by category, with 'default' (undefined) inputs being a the top.
	 * Sort the categories in order
	 */
	orderInputMetadataByCategory() {
		const originalOrderMap = new Map<GraphInputMetadata, number>();

		// Attach the original index to each item
		this.inputMetadata.forEach((item, index) => {
			originalOrderMap.set(item, index);
		});

		this.inputMetadata.sort((a, b) => {
			// Inputs with undefined categories come first
			if (!a.category && !b.category) return originalOrderMap.get(a)! - originalOrderMap.get(b)!;
			if (!a.category) return -1;
			if (!b.category) return 1;

			// Compare categories alphabetically
			const categoryComparison = a.category.localeCompare(b.category);
			if (categoryComparison !== 0) {
				return categoryComparison;
			}

			// If categories are the same, preserve the original order
			return originalOrderMap.get(a)! - originalOrderMap.get(b)!;
		});
	}

	/**
	 * See if an input is used
	 *
	 * @param input the input metadata to check against
	 * @returns if the input is used or not
	 */
	inputIsUsed(input: GraphInputMetadata) {
		if (!input) {
			return false;
		}

		for (const node of this.getNodes()) {
			if (node.metadata.name == 'Get Graph Input' && node.fieldValue === input.name) {
				return true;
			}

			for (const inputSocket of node.inputSockets) {
				if (inputSocket.graphInputName === input.name) {
					return true;
				}
			}
		}
		return false;
	}

	/**
	 * See if an output is used
	 *
	 * @param output the output metadata to check against
	 * @returns if the output is used or node
	 */
	outputIsUsed(output: GraphOutputMetadata) {
		if (!output) {
			return false;
		}

		for (const node of this.getNodes()) {
			if (node.metadata.name == 'Set Graph Output' && node.fieldValue === output.name) {
				return true;
			}
		}
		return false;
	}
	/**
	 * Move an input at the given index to a new index.
	 *
	 * @param index The index of the input to reorder.
	 * @param newIndex The new index of the input.
	 */
	reorderInputMetadata(index: number, newIndex: number) {
		this.inputMetadata.splice(newIndex, 0, ...this.inputMetadata.splice(index, 1));
	}

	/**
	 * Test whether this graph can be directly executed. A graph can only be directly executed when all its inputs are primitive types.
	 *
	 * If this graph cannot be directly executed (i.e. this function returns `false`), this graph can only be executed by another graph.
	 *
	 * @returns A boolean whether this graph can be directly executed.
	 */
	canExecute(): boolean {
		const metadataStore = useMetadataStore();
		return this.inputMetadata.every(
			(metadata) =>
				['String', 'Number', 'Boolean'].includes(metadata.datatype) ||
				metadataStore.hasCompositeInput(metadata.datatype) && !metadata.isList
		);
	}

	/**
	 * Add or update metadata for a graph output.
	 *
	 * @param metadata The metadata.
	 * @param overwrite The name of the existing output to overwrite.
	 */
	updateOutputMetadata(metadata: GraphOutputMetadata, overwrite?: string) {
		// Sanitize the metadata
		metadata.name = metadata.name.trim();
		metadata.datatype = metadata.datatype.trim();
		metadata.isList = metadata.isList ? true : undefined;
		metadata.description =
			metadata.description && metadata.description.trim() ? metadata.description.trim() : undefined;

		// Find the value to update
		if (overwrite) {
			const index = this.outputMetadata.findIndex((m) => m.name == overwrite.trim());
			if (index === -1) {
				throw `No graph output found with name ${overwrite}`;
			}

			this.outputMetadata[index] = metadata;
			return;
		}

		this.outputMetadata.push(metadata);
	}

	/**
	 * Remove/delete metadata for a graph output by name.
	 *
	 * @param name The name of the output to remove.
	 * @throws If the output is not found.
	 */
	removeOutputMetadata(name: string) {
		const index = this.outputMetadata.findIndex((md) => md.name == name);
		if (index == -1) {
			throw `Output with name ${name} not found`;
		}

		this.outputMetadata.splice(index, 1);
	}

	/**
	 * Move an output at the given index to a new index.
	 *
	 * @param index The index of the output to reorder.
	 * @param newIndex The new index of the output.
	 */
	reorderOutputMetadata(index: number, newIndex: number) {
		this.outputMetadata.splice(newIndex, 0, ...this.outputMetadata.splice(index, 1));
	}

	/**
	 * Serialize this graph to an object that may be saved to a file to represent this graph persistently.
	 *
	 * @returns The dictionary representation of the data for this graph.
	 */
	serialize(): SerializedGraph {
		const visitedNodes = new Set<string>();
		const serializedNodes: SerializedNode[] = [];
		const dfs = (node: GraphNode) => {
			// If the node has input connections that haven't been visited, backtrack to those first
			for (const socket of node.inputSockets) {
				for (const connectedSocket of socket.connections) {
					if (!visitedNodes.has(connectedSocket.node.id)) {
						dfs(connectedSocket.node);
					}
				}
			}
			// If the node has already been visited, don't visit it again
			if (visitedNodes.has(node.id)) {
				return;
			}
			// Mark the node as visited
			visitedNodes.add(node.id);
			// Serialize the node and add it to the list
			serializedNodes.push(node.serialize());
			// Recursively visit all nodes connected to the current node's output sockets
			for (const socket of node.outputSockets) {
				for (const connectedSocket of socket.connections) {
					if (!visitedNodes.has(connectedSocket.node.id)) {
						dfs(connectedSocket.node);
					}
				}
			}
		};
		// Identify all root nodes
		const allNodes = Array.from(this.getNodes());
		const rootNodes = allNodes.filter((node) => node.inputSockets.every((socket) => socket.connections.length === 0));
		// Start the DFS from the 'GraphStart-0' node
		const startNode = rootNodes.find((node) => node.id === 'GraphStart-0');
		if (startNode) {
			dfs(startNode);
		}
		// Continue the DFS from the remaining root nodes
		// This should not be needed but is here so things don't break.
		for (const rootNode of rootNodes) {
			if (rootNode.id !== 'GraphStart-0') {
				dfs(rootNode);
			}
		}
		const s: SerializedGraph = {
			description: this.description.trim(),
			nodes: serializedNodes,
			inputs: this.inputMetadata,
			outputs: this.outputMetadata
		};
		if (!s.description) delete s.description;
		if (!s.inputs || !s.inputs.length) delete s.inputs;
		if (!s.outputs || !s.outputs.length) delete s.outputs;
		return s;
	}

	/**
	 * Get the serialized version of this graph as a string.
	 *
	 * @returns The serialized graph (YAML string).
	 */
	getSerializedGraphString(): string {
		let s = YAML.stringify(this.serialize(), {
			indent: 2,
			lineWidth: 0,
			minContentWidth: 0,
			version: '1.1' // The backend pyYAML library is a v1.1 parser
		});

		// Add additional newlines for separation
		s = s.replace(/^nodes:/gm, '\nnodes:');
		s = s.replace(/^inputs:/gm, '\ninputs:');
		s = s.replace(/^outputs:/gm, '\noutputs:');
		s = s.replace(/^ui:/gm, '\nui:');
		s = s.replace(/^ {2}- name:/gm, '\n  - name:');
		s = s.replace(/^nodes:\n\n/gm, 'nodes:\n');
		s = s.replace(/^inputs:\n\n/gm, 'inputs:\n');
		s = s.replace(/^outputs:\n\n/gm, 'outputs:\n');

		return s.trim();
	}

	/**
	 * Add a new callback for whenever one or more of the nodes in the graph are changed.
	 *
	 * @param callback The callback
	 */
	addOnNodesChangedCallback(cb: (g: Graph) => Promise<void>) {
		this.onNodesChangedCallbacks.push(cb);
	}

	/**
	 * Handler for whenever one or more of the nodes in the graph are changed.
	 */
	async onNodesChanged() {
		for (const callback of this.onNodesChangedCallbacks) {
			await callback(this);
		}
	}

	/**
	 * Force a re-render of all nodes in this graph.
	 */
	forceRerender() {
		for (const node of this.getNodes()) {
			node.forceRerender();
		}
	}

	/**
	 * Connect the node before the "currentNode" to the node after the current one. This will leave the "currentNode" without link connections.
	 * @param currentNode The node to disconnect and have its link sockets hooked up to another sequence
	 * @param idOfNodeAfterThisOne The ID (string) of the node that you want the forward link socket to connect to
	 * @param backwardConnectionName The name of the backward connection to query in order to discover the socket of the node before the current node
	 *
	 * @return true if the connection was attempted, false if the connection could not be made
	 */
	replaceNodeLinkConnections(
		currentNode: GraphNode,
		idOfNodeAfterThisOne: string,
		backwardConnectionName: string = '_backward'
	): boolean {
		// (We need to find two valid link sockets in order to connect them together) If a forward node ID was found:
		if (idOfNodeAfterThisOne == '') return false;
		// find the backward socket
		const backwardSocket = currentNode.inputSockets.find((s) => s.metadata.name == backwardConnectionName);
		if (backwardSocket && backwardSocket.connections && backwardSocket.connections.length) {
			// connect the backward socket to the socket on the node after the one we are commenting out
			const socketBeforeThisNode = backwardSocket.connections[0];
			const nodeAfterThisOne = currentNode.graph.getNode(idOfNodeAfterThisOne);
			socketBeforeThisNode.connect(nodeAfterThisOne.getInputSocket(backwardConnectionName));
		} else {
			return false;
		}
		return true;
	}
}

export { Graph };
export type {
	AddNodeOptions,
	CompositeGraphInputMetadata,
	CompositeValue,
	GraphInputMetadata,
	GraphInputMetadataWithState,
	GraphOutputMetadata,
	GroupedInputs,
	SerializedGraph
};

