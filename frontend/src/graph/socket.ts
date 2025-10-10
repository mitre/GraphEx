import type { Graph } from '@/graph/graph';
import type { GraphNode } from '@/graph/node';
import { useMetadataStore } from '@/stores';
import { nextTick } from 'vue';

// The name of the 'Dynamic' DataType
const DYNAMIC_DATATYPE = 'Dynamic';

/**
 * Metadata for a socket.
 */
interface SocketMetadata {
	/** Whether this is an input socket. Otherwise, this is an output socket. */
	isInput: boolean;

	/** Whether this is an optional socket. */
	isOptional: boolean;

	/** Whether this is a list socket. */
	isList: boolean;

	/** Whether this is a link socket. */
	isLink: boolean;

	/** The name for this socket. */
	name: string;

	/** The name of the datatype for this socket. */
	datatype: string | null;

	/** The socket description. */
	description: string;

	/** Whether an input field is allowable on this socket. */
	canHaveField: boolean;

	/** Default value for the input field on this socket. If ``null``, no default is included on this socket. */
	field: any;

	/** List of string for enum data. Can be empty. */
	enumOptions: string[];

	/** If the socket can be used to set variables automatically. Can be undefined */
	allowsVariable?: boolean;
}

/**
 * Serialized form of an Socket.
 */
interface SerializedSocket {
	/** The name for this socket. */
	name: string;

	/** The connections for this socket (NodeID::SocketName) */
	connections?: Array<string>;

	/** The value for this sockets's input field. (Input sockets only) */
	fieldValue?: string | number | boolean | Array<string | number | boolean>;

	/** Name of the variable that this socket derives its value from. (Input sockets only) */
	variableName?: string;

	/** Name of the graph input that this socket derives its value from. (Input sockets only) */
	graphInputName?: string;

	/** If 'true': this socket is a VariableOutputSocket that was disabled by the user explicitly in the UI */
	disabledVariableOutput?: boolean;
}

interface SocketConnectOptions {
	/** Whether to attempt to auto-add a cast node if the data types do not match. */
	autoAddCastNode?: boolean;

	/** When creating nodes via code, skip the computation that attempts to center the cast node between sockets */
	skipComputeCastPosition?: boolean;

	/** Whether this connection is a "dry run". If true, this function will not actually connect (or otherwise modify) the sockets. */
	dryRun?: boolean;
}

/** A socket for a node in the graph. */
class Socket {
	/** The node containing this socket. */
	node: GraphNode;

	/** The parent graph. */
	graph: Graph;

	/** The Element for this socket in the graph UI. */
	element: HTMLDivElement | null;

	/** Metadata for this input socket. */
	metadata: SocketMetadata;

	/** List of connections to other sockets. */
	connections: Array<Socket>;

	/** The value of this socket's input field (if one exists). (Input sockets only) */
	fieldValue?: string | number | boolean | Array<string | number | boolean>;

	/** Name of the variable that this socket derives its value from. (Input sockets only) */
	variableName?: string;

	/** Name of the graph input that this socket derives its value from. (Input sockets only) */
	graphInputName?: string;

	/** Cached element positions. This is used as an optimization to avoid recomputing the positions when not needed, and is reset on each animation frame.  */
	cachedPositions: { top: number; right: number; bottom: number; left: number } | null = null;

	/** If 'true': this socket is a VariableOutputSocket that was disabled by the user explicitly in the UI */
	disabledVariableOutput: boolean;

	constructor(node: GraphNode, metadata: SocketMetadata) {
		this.node = node;
		this.graph = node.graph;
		this.element = null;
		this.metadata = metadata;
		this.connections = [];
		this.disabledVariableOutput = false;

		if (metadata.canHaveField && (metadata.field !== null || !metadata.isOptional)) {
			this.setInputFieldDefault();
		}
	}

	/**
	 * Set the element for this input socket.
	 *
	 * @param element The UI element.
	 */
	setElement(element?: HTMLDivElement) {
		this.element = element || null;
	}

	/**
	 * Compute the positions of this socket within the graph (scale independent).
	 *
	 * @returns The positions of the socket element.
	 */
	getPositions(): { top: number; right: number; bottom: number; left: number } {
		if (!this.element) return { top: 0, right: 0, bottom: 0, left: 0 };
		if (this.cachedPositions) return this.cachedPositions;

		const elementRect = this.element.getBoundingClientRect();
		const contentPositions = this.graph.ui.contentPositions();
		const scale = this.graph.ui.scale;

		this.cachedPositions = {
			top: (elementRect.top - contentPositions.top) / scale,
			right: (elementRect.right - contentPositions.left) / scale,
			bottom: (elementRect.bottom - contentPositions.top) / scale,
			left: (elementRect.left - contentPositions.left) / scale
		};

		requestAnimationFrame(() => {
			// Reset the cached value on next update
			this.cachedPositions = null;
		});

		return this.cachedPositions;
	}

	/**
	 * Connect this socket to another.
	 *
	 * @param otherSocket The other socket.
	 * @param options Additonal options for creating this connection.
	 *
	 * @throws An error if this socket cannot connect to the other socket.
	 */
	connect(otherSocket: Socket, options?: SocketConnectOptions) {
		options = options || {};
		if (this.metadata.isInput === otherSocket.metadata.isInput) {
			throw 'Cannot connect two input/output sockets together.';
		}

		const inputSocket = this.metadata.isInput ? this : otherSocket;
		const outputSocket = this.metadata.isInput ? otherSocket : this;

		if (inputSocket.node.id == outputSocket.node.id) {
			throw 'Cannot connect sockets on the same node.';
		}

		if (inputSocket.metadata.isLink !== outputSocket.metadata.isLink) {
			throw 'Cannot connect a link socket to a non-link socket.';
		}

		if (outputSocket.metadata.isList && !inputSocket.metadata.isList) {
			throw 'Cannot connect a list output socket to a non-list input socket';
		}

		if (
			inputSocket.metadata.datatype !== DYNAMIC_DATATYPE &&
			inputSocket.metadata.datatype !== outputSocket.metadata.datatype
		) {
			if (!options.autoAddCastNode) {
				throw 'Cannot connect sockets of different data types.';
			}

			const metadataStore = useMetadataStore();
			const inputSocket = this.metadata.isInput ? this : otherSocket;
			const outputSocket = this.metadata.isInput ? otherSocket : this;

			// We'll add the cast node between this socket and the target socket
			// and then call this function recursively to connect the appropriate edges
			// First, find the appropriate cast node
			const castFrom = outputSocket.metadata.datatype!;
			const castFromIsList = outputSocket.metadata.isList;
			const castTo = inputSocket.metadata.datatype!;
			const castToIsList = inputSocket.metadata.isList;
			const castNodeMetadata = metadataStore.findCastNode(castFrom, castFromIsList, castTo, castToIsList);
			if (!castNodeMetadata) {
				throw `No cast node for casting from ${castFrom} (Is List=${castToIsList}) to ${castTo} (Is List=${castToIsList})`;
			}

			// Checks are done
			// If this is a dry run, end here
			if (options.dryRun) {
				return;
			}

			const {
				top: outputTop,
				right: outputRight,
				bottom: outputBottom,
				left: outputLeft
			} = outputSocket.getPositions();

			if (!options.skipComputeCastPosition) {
				// Get the 'midway' point between the two sockets
				const { top: inputTop, right: inputRight, bottom: inputBottom, left: inputLeft } = inputSocket.getPositions();

				const inputX = inputLeft + (inputRight - inputLeft) / 2;
				const inputY = inputBottom + (inputBottom - inputTop) / 2;
				const outputX = outputLeft + (outputRight - outputLeft) / 2;
				const outputY = outputBottom + (outputBottom - outputTop) / 2;

				const castNodeX = Math.min(inputX, outputX) + Math.abs(inputX - outputX) / 2;
				const castNodeY = Math.min(inputY, outputY) + Math.abs(inputY - outputY) / 2;

				// Add the cast node
				const castNode = this.graph.addNode(castNodeMetadata, castNodeX, castNodeY);

				// Center the cast node
				nextTick(() => castNode.centerPosition(castNodeX, castNodeY));
				
				// Create the input edge for the cast node
				outputSocket.connect(castNode.inputSockets[0]);

				// Create the output edge for the cast node
				inputSocket.connect(castNode.outputSockets[0]);
			} else {
				// Skip the computations to center the cast node
				// Add the cast node
				const castNode = this.graph.addNode(castNodeMetadata, outputLeft + 50, outputBottom);

				// Create the input edge for the cast node
				outputSocket.connect(castNode.inputSockets[0]);

				// Create the output edge for the cast node
				inputSocket.connect(castNode.outputSockets[0]);
			}

			// Done
			return;
		}

		// Checks are done
		// If this is a dry run, end here
		if (options.dryRun) {
			return;
		}

		if (inputSocket.connections.length == 1 && inputSocket.hasMaxEdges()) {
			// Swap the current connection for the new one
			inputSocket.disconnect(inputSocket.connections[0]);
		}

		if (outputSocket.connections.length == 1 && outputSocket.hasMaxEdges()) {
			// Swap the current connection for the new one
			outputSocket.disconnect(outputSocket.connections[0]);
		}

		// Add the connnections
		if (!inputSocket.connections.includes(outputSocket)) {
			inputSocket.clearInputSources(false);
			inputSocket.connections.push(outputSocket);
		}

		if (!outputSocket.connections.includes(inputSocket)) {
			outputSocket.clearInputSources(false);
			outputSocket.connections.push(inputSocket);
		}
	}

	/**
	 * Disconnect this socket from a particular socket. If there is no connection to the given socket, this does nothing.
	 *
	 * @param socket The socket to disconnect from.
	 * @returns The socket disconnected from, or null if this socket did not have a connection.
	 */
	disconnect(otherSocket: Socket): Socket | null {
		const indexSelf = this.connections.indexOf(otherSocket);
		if (indexSelf !== -1) {
			this.connections.splice(indexSelf, 1);
		}

		const indexOther = otherSocket.connections.indexOf(this);
		if (indexOther !== -1) {
			otherSocket.connections.splice(indexOther, 1);
		}

		if (indexSelf !== -1 && indexOther !== -1) {
			return otherSocket;
		}

		return null;
	}

	/**
	 * Disconnect all sockets from this socket.
	 *
	 * @returns All the sockets that originally connected to this socket.
	 */
	disconnectAll(): Array<Socket> {
		const sockets: Array<Socket> = [];
		while (this.connections.length) {
			sockets.push(this.connections[0]);
			this.disconnect(this.connections[0]);
		}
		return sockets;
	}

	/**
	 * Whether this socket has its maximum number of edges.
	 */
	hasMaxEdges(): boolean {
		if (this.connections.length && this.metadata.isLink) return true;
		if (this.connections.length && this.metadata.isInput && !this.metadata.isList) return true;
		return false;
	}

	/**
	 * Swap the order of connections in this socket.
	 *
	 * @param index1 The first index.
	 * @param index2 The second index.
	 */
	swapConnectionOrder(index1: number, index2: number) {
		const temp = this.connections[index1];
		this.connections[index1] = this.connections[index2];
		this.connections[index2] = temp;
	}

	/**
	 * Clear all input sources for this socket. This will effectively reset the socket and leave it waiting for a connection.
	 *
	 * @param resetConnections Whether to disconnect all connections as well.
	 */
	clearInputSources(resetConnections: boolean = true) {
		this.fieldValue = undefined;
		this.variableName = undefined;
		this.graphInputName = undefined;
		if (resetConnections) {
			this.disconnectAll();
		}
	}

	/**
	 * Set the value of this socket input field to its default. If no default value is provided in the metadata,
	 * a default will be assigned based on the datatype.
	 */
	setInputFieldDefault() {
		this.clearInputSources();
		if (!this.metadata.canHaveField) {
			return;
		}

		if (this.metadata.field !== null) {
			this.fieldValue = JSON.parse(JSON.stringify(this.metadata.field)); // Deep copy so that lists are not copied by reference
		} else if (this.metadata.isList) {
			this.fieldValue = [];
		} else if ('enumOptions' in this.metadata){
			this.fieldValue = '';
			// @ts-ignore
		} else if (this.metadata.datatype == 'String') { 
			this.fieldValue = '';
			// @ts-ignore
		} else if (this.metadata.datatype == 'Number') {
			this.fieldValue = 0;
			// @ts-ignore
		} else if (this.metadata.datatype == 'Boolean') {
			this.fieldValue = false;
		} else {
			// @ts-ignore
			throw `Unhandled DataType ${this.metadata.datatype} when setting input field default.`;
		}
	}

	/**
	 * Set the field value for this socket.
	 *
	 * @param newValue The new value.
	 */
	setFieldValue(newValue?: string | number | boolean | Array<string | number | boolean>) {
		this.clearInputSources();
		this.fieldValue = newValue;
	}

	/**
	 * Set the field value at a particular index for this socket (list sockets only).
	 *
	 * @param index The index in the list to set.
	 * @param newValue The new value.
	 */
	setFieldListValue(index: number, newValue: string | number | boolean) {
		if (!Array.isArray(this.fieldValue)) throw `Field value is not an array.`;
		this.fieldValue[index] = newValue;
	}

	/**
	 * Get the field value at a particular index for this socket (list sockets only).
	 * @param index The index in the list to get
	 * @returns The value for the provided index
	 */
	getFieldListValue(index: number) {
		if (!Array.isArray(this.fieldValue)) throw `Field value is not an array.`;
		return this.fieldValue[index];
	}

	/**
	 * Move an inline field list value at the given index to a new index.
	 *
	 * @param index The index of the value to reorder.
	 * @param newIndex The new index of the value.
	 */
	reorderFieldListValue(index: number, newIndex: number) {
		if (!Array.isArray(this.fieldValue)) throw `Field value is not an array.`;
		this.fieldValue.splice(newIndex, 0, ...this.fieldValue.splice(index, 1));
	}

	/**
	 * Add a new field value for this socket (list sockets only).
	 * 
	 * @returns the length of the array
	 */
	addNewFieldListValue() {
		if (!Array.isArray(this.fieldValue)) throw `Field value is not an array.`;

		const newValue = {
			String: '',
			Number: 0,
			Boolean: false
		}[this.metadata.datatype!];

		if (newValue === undefined) {
			throw `Unrecognized field value type.`;
		}

		return this.fieldValue.push(newValue);
	}

	/**
	 * Delete a field value for this socket (list sockets only);
	 *
	 * @param index The index to delete.
	 */
	deleteFieldListValue(index: number) {
		if (!Array.isArray(this.fieldValue)) throw `Field value is not an array.`;
		this.fieldValue.splice(index, 1);
	}

	/**
	 * Set the variable name value for this socket.
	 *
	 * @param name The variable name.
	 */
	setVariableName(name?: string) {
		this.clearInputSources();
		this.variableName = name;
	}

	/**
	 * Set the graph input name value for this socket.
	 *
	 * @param name The graph input name.
	 */
	setGraphInputName(name?: string) {
		this.clearInputSources();
		this.graphInputName = name;
	}

	/**
	 * Serialize relevant data to this object to the format used for representing this object in a file.
	 *
	 * @returns The dictionary representation of the data for this object.
	 */
	serialize(): SerializedSocket {
		const s: SerializedSocket = {
			name: this.metadata.name
		};

		if (this.fieldValue !== undefined) s.fieldValue = this.fieldValue;
		else if (this.variableName !== undefined) s.variableName = this.variableName;
		else if (this.graphInputName !== undefined) s.graphInputName = this.graphInputName;
		else if (this.connections.length)
			s.connections = this.connections.map((conn) => `${conn.node.id}::${conn.metadata.name}`);

		return s;
	}
}

export { DYNAMIC_DATATYPE, Socket };
export type { SerializedSocket, SocketMetadata };

