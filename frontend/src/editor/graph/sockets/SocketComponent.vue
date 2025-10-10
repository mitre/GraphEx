<template>
	<SocketDropdown ref="dropdown" :socket="props.socket">
		<div class="socket-container-vertical-stack">
			<div
				class="socket-container"
				:socket-only="!!props.socketOnly"
				:is-input="props.socket.metadata.isInput"
				:optional="props.socket.metadata.isOptional"
				:connected="connected"
				:error="!!error"
				@dblclick.stop.prevent
				ref="container"
			>
				<!-- Error Icon -->
				<span class="socket-name-error material-icons" v-if="canHaveError" :title="error || ''" @mousedown.stop
					>error_outline</span
				>

				<!-- Fields -->
				<SocketFieldComponent
					:socket="props.socket"
					:available-variables="availableVariables"
					v-if="!props.socketOnly"
				/>

				<!-- Name -->
				<div
					class="socket-name no-select"
					v-if="!props.socketOnly"
					:title="title"
					@click.stop.prevent="onClick"
					@mousedown.stop
				>
					<span v-if="props.frontendOverrideName">{{ props.frontendOverrideName }}</span>
					<span v-else>{{ props.socket.metadata.name }}</span>
				</div>

				<!-- List socket -->
				<div
					v-if="props.socket.metadata.isList"
					class="array-data-socket no-select"
					ref="element"
					:title="title"
					@click.stop.prevent="onClick"
					@mousedown.stop
				>
					<div v-for="index in 9" :key="index" class="array-data-socket-block" :style="dataSocketStyles"></div>
				</div>

				<!-- Link Socket -->
				<div
					v-else-if="props.socket.metadata.isLink"
					class="link-socket"
					ref="element"
					:title="title"
					@click.stop.prevent="onClick"
					@mousedown.stop
				>
					<svg xmlns="http://www.w3.org/2000/svg">
						<polygon points="0,1 0,11 6,11 12,6 6,1" />
					</svg>
				</div>

				<!-- Standard Socket or VariableOutputSocket -->
				<div
					v-else
					class="data-socket no-select"
					ref="element"
					:style="dataSocketStyles"
					:title="title"
					@click.stop.prevent="onClick"
					@mousedown.stop
				></div>
			</div>
			<!-- Variable Output Socket Checkbox and Text -->
			<VariableOutputSocketComponent :socket="props.socket" />
			<div
				class="socket-num-connections"
				v-if="
					!props.socket.metadata.isInput &&
					!props.socket.metadata.isLink &&
					!props.socket.metadata.isList &&
					connectionIndex > -1 &&
					firstConnectionToList
				"
				title="The index number associated with this socket in the list this socket is connected to"
			>
				{{ connectionIndex }}
			</div>
		</div>
	</SocketDropdown>

	<Teleport :to="props.socket.graph.ui.contentElement" :disabled="!props.socket.graph.ui.contentElement">
		<template v-for="edge in edgeData" :key="edge">
			<SocketEdgeComponent v-bind="edge" />
		</template>
	</Teleport>
</template>

<script setup lang="ts">
	import { DYNAMIC_DATATYPE, NodeTypes, Socket, type GraphInputMetadata, type GraphNode } from '@/graph';
	import { useContextmenuStore, useEditorStore, useErrorStore, useMetadataStore } from '@/stores';
	import { computed, onMounted, onUnmounted, ref, watch, type ComputedRef } from 'vue';

	import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
	import SocketDropdown from '@/editor/graph/sockets/SocketDropdown.vue';
	import SocketFieldComponent from '@/editor/graph/sockets/SocketFieldComponent.vue';

	import type { SocketEdgeProps } from '@/editor/graph/edges/SocketEdgeComponent.vue';
	import SocketEdgeComponent from '@/editor/graph/edges/SocketEdgeComponent.vue';
	import VariableOutputSocketComponent from '@/editor/graph/sockets/VariableOutputSocketComponent.vue';

	const props = defineProps<{
		tabId: string;

		socket: Socket;

		/** Whether to only show the socket itself and hide other components (e.g. the socket name). */
		socketOnly?: boolean;

		/** A frontend only name to give to the socket to make it easier to understand */
		frontendOverrideName?: string;
	}>();

	const metadataStore = useMetadataStore();
	const contextmenuStore = useContextmenuStore();
	const errorStore = useErrorStore();
	const editorStore = useEditorStore();

	const container = ref<HTMLDivElement>();
	const element = ref<HTMLDivElement>();
	const dropdown = ref<InstanceType<typeof SocketDropdown>>();

	const startingValue = ref(props.socket.fieldValue);

	onMounted(() => {
		props.socket.setElement(element.value);
		contextmenuStore.getContextMenu(props.tabId).addHook(container.value!, openContextMenu, false);

		//If the enumOptions have changed since the graph was made, make note of the graph value
		if (
			'enumOptions' in props.socket.metadata &&
			props.socket.fieldValue &&
			!props.socket.metadata.enumOptions.includes(String(props.socket.fieldValue))
		) {
			startingValue.value = props.socket.fieldValue;
			props.socket.fieldValue = '';
		}
	});

	onUnmounted(() => {
		errorStore.removeError(props.tabId, nodeId.value, props.socket.metadata.name);
		errorStore.removeWarning(props.tabId, nodeId.value, props.socket.metadata.name);
	});

	/**********************
	 * Computed Values
	 **********************/
	/** The data type for this socket (null if no data type is associated with this socket). */
	const datatype = computed(() => {
		const name = props.socket.metadata.datatype;
		if (name === null) {
			return null;
		}

		return metadataStore.getDataType(name);
	});

	/** The title (hover text) to display for this socket. */
	const title = computed(() => {
		let title = props.socket.metadata.description + '\n\n';

		if (datatype.value) {
			title += 'Data type: ' + datatype.value.name + '\n\n';
		}

		title += 'Right-click for more options.';

		return title;
	});

	/** Whether this socket has a connection. */
	const connected = computed(() => {
		return props.socket.connections.length > 0;
	});

	const oneConnection = computed(() => {
		return props.socket.connections.length === 1;
	});

	const connectionIndex = computed(() => {
		if (!oneConnection.value) return -1;
		return props.socket.connections[0].connections.indexOf(props.socket, 0);
	});

	const firstConnectionToList = computed(() => {
		if (!connected.value) return false;
		return props.socket.connections[0].metadata.isList;
	});

	/** All available variable nodes that apply to this socket. */
	const availableVariableNodes = computed(() => {
		const nodes: Array<GraphNode> = [];

		for (const node of props.socket.graph.getNodes()) {
			if (node.metadata.name === 'Get Variable' || !metadataStore.VARIABLES_NODE_NAMES.includes(node.metadata.name)) {
				// Not a set-variable node
				continue;
			}

			if (
				metadataStore.VARIABLES_NODE_NAMES.includes(props.socket.node.metadata.name) &&
				props.socket.node.fieldValue == node.fieldValue
			) {
				// Cannot use a variable within its own set-variable node
				continue;
			}

			const dataSocket = node.outputSockets.find((socket) => !!socket.metadata.datatype);
			if (
				props.socket.metadata.datatype !== DYNAMIC_DATATYPE &&
				dataSocket?.metadata.datatype !== props.socket.metadata.datatype
			) {
				// Not the same datatype
				continue;
			}

			if (dataSocket?.metadata.isList !== props.socket.metadata.isList) {
				// List-types do not match
				continue;
			}

			nodes.push(node);
		}

		return nodes;
	});

	const variableNamesCreatedByActionNodes = computed(() => {
		let allowsVariableNames: Set<string> = new Set();
		// For every node in the currently opened graph
		for (const node of props.socket.graph.getNodes()) {
			// if the node is not a node normally associated with variables
			if (!metadataStore.VARIABLES_NODE_NAMES.includes(node.metadata.name)) {
				// Check if any sockets on this node allow a variable to be saved from an output socket
				// and that both the datatype and 'isList' properties match
				for (const socketMetadata of node.metadata.sockets) {
					if (
						'allowsVariable' in socketMetadata &&
						socketMetadata.datatype === props.socket.metadata.datatype &&
						socketMetadata.isList === props.socket.metadata.isList
					) {
						// collect the actual socket to see if the 'Save To Variable' checkbox is disabled
						const actualSocket = node.getOutputSocket(socketMetadata.name);
						// Add the socket/variable name as a match if the checkbox isn't 'unchecked'
						if (!actualSocket.disabledVariableOutput) {
							allowsVariableNames.add(socketMetadata.name);
						}
					}
				}
			}
		}
		return allowsVariableNames;
	});

	/** All available variable names that apply to this socket. */
	const availableVariables = computed(() => {
		let variableNames = Array.from(
			availableVariableNodes.value.reduce((prevValue, node) => {
				const varname = String(node.fieldValue || '').trim();
				if (varname) {
					prevValue.add(varname);
				}
				return prevValue;
			}, new Set<string>())
		);
		variableNamesCreatedByActionNodes.value.forEach((varName) => {
			if (!variableNames.includes(varName)) variableNames.push(varName);
		});
		return variableNames;
	});

	/** Whether it is possible for this socket to have errors. */
	const canHaveError = computed(() => {
		if (!props.socket.metadata.isInput && !props.socket.metadata.isLink) {
			// Output data sockets do not have errors
			return false;
		}
		return true;
	});

	/** Any error on this socket. If `null`, no error is present. */
	const error = computed(() => {
		if (!canHaveError.value) {
			return null;
		}

		let numConnections = props.socket.connections.length;
		if (numConnections == 0 && props.socket.fieldValue !== undefined) {
			numConnections = 1; // Add a 'pseudo-connection' to handle the existence of an input field
		}

		if (numConnections == 0 && (props.socket.variableName !== undefined || props.socket.graphInputName !== undefined)) {
			numConnections = 1; // Add a 'pseudo-connection' to handle the existence of a variable
		}

		// Check that a connection exists when required.
		if (
			numConnections == 0 &&
			props.socket.metadata.isInput &&
			!props.socket.metadata.isOptional &&
			!props.socket.metadata.isLink
		) {
			return `Socket requires a connection.`;
		}

		if (numConnections == 0 && props.socket.metadata.isLink) {
			return `Must connect to another node.`;
		}

		// If the input source is a field, validate the type
		if (
			props.socket.fieldValue !== undefined &&
			!props.socket.metadata.isList &&
			!('enumOptions' in props.socket.metadata)
		) {
			// @ts-ignore
			if (props.socket.metadata.datatype == 'Number' && typeof props.socket.fieldValue !== 'number') {
				return 'Field does not contain a valid number.';
			}

			// @ts-ignore
			if (props.socket.metadata.datatype == 'Boolean' && typeof props.socket.fieldValue !== 'boolean') {
				return 'Field does not contain a valid boolean.';
			}
		}

		if (props.socket.fieldValue !== undefined && props.socket.metadata.isList) {
			if (!Array.isArray(props.socket.fieldValue)) {
				return 'Field is not an array.'; // Should never happen
			}

			if (
				props.socket.metadata.datatype == 'Number' &&
				props.socket.fieldValue.some((val) => typeof val !== 'number')
			) {
				return 'Field is not a valid list of numbers.';
			}

			if (
				props.socket.metadata.datatype == 'Boolean' &&
				props.socket.fieldValue.some((val) => typeof val !== 'boolean')
			) {
				return 'Field is not a valid list of booleans.';
			}
		}

		if (
			'enumOptions' in props.socket.metadata &&
			(!props.socket.fieldValue || props.socket.fieldValue == '') &&
			!connected.value &&
			!props.socket.graphInputName &&
			!props.socket.variableName
		) {
			if (props.socket.fieldValue == '' && startingValue.value != '') {
				return `Value '${startingValue.value}' from saved graph is no longer an option. Please select a valid option.`;
			} else {
				return 'Option must be selected.';
			}
		}
		// Check that the variable exists if the input source is a variable
		if (props.socket.variableName && !availableVariables.value.includes(props.socket.variableName)) {
			return `Variable '${props.socket.variableName}' does not exist for this socket type.`;
		}

		// Check that the graph input exists if the input source is graph_input
		if (
			props.socket.graphInputName &&
			!props.socket.graph.inputMetadata.find(
				(metadata) =>
					metadata.name === props.socket.graphInputName &&
					metadata.datatype == props.socket.metadata.datatype &&
					!!metadata.isList == props.socket.metadata.isList
			)
		) {
			return `Graph Input '${props.socket.graphInputName}' does not exist for this socket type.`;
		}

		return null;
	});

	const hasWarning = computed(() => {
		if (!props.socket.metadata.isLink) {
			if (props.socket.metadata.isInput && props.socket.fieldValue !== undefined) {
				if (!props.socket.metadata.isList) {
					if (props.socket.metadata.datatype == 'String' && props.socket.fieldValue === '')
						return 'Input field is empty.';
					// if (props.socket.metadata.datatype == 'Number' && props.socket.fieldValue === -1) return "Input field is default number of -1.";
				}
				// else {
				// 	if (props.socket.connections.length <= 0 && props.socket.fieldValue == undefined) return "List has no data connections to it."
				// 	if (props.socket.fieldValue && Array.isArray(props.socket.fieldValue) && props.socket.fieldValue.length <= 0) return "List has no values."
				// }
			} else if (
				!props.socket.metadata.isInput &&
				props.socket.connections.length <= 0 &&
				(props.socket.node.metadata.type === 'data' || props.socket.node.metadata.type === 'generator')
			) {
				return "Data node's output socket is not being used.";
			}
		}

		return null;
	});

	/** The data node metadata associated with the data type for this socket (if one exists). */
	const dataNodeMetadata = computed(() => {
		if (datatype.value === null) {
			return null;
		}

		for (const node of metadataStore.nodes) {
			if (node.type !== NodeTypes.DATA) {
				continue;
			}

			const socket = node.sockets.find((socket) => !socket.isInput)!;
			if (socket.datatype === props.socket.metadata.datatype) {
				return node;
			}
		}

		return null;
	});

	/**********************
	 * Edges
	 **********************/
	/** Necessary data for all edges to draw for this socket. */
	const edgeData: ComputedRef<Array<SocketEdgeProps>> = computed(() => {
		if (!props.socket.metadata.isInput) return []; // We only draw edges for input sockets to avoid drawing duplicate edges (i.e. drawing from both ends)
		return props.socket.connections.map((conn) => {
			return {
				input: props.socket,
				output: conn
			};
		});
	});

	/**********************
	 * Handlers
	 **********************/
	/** Click handler for a socket click. */
	function onClick() {
		if (editorStore.isResolvingMergeConflict) {
			return;
		}
		const graph = props.socket.graph;
		const grabbedSocket = graph.ui.grabbed.socket;

		// Handle if there is a grabbed edge while this socket is being clicked
		// If so, we'll try to connect the edge
		if (grabbedSocket) {
			try {
				grabbedSocket.connect(props.socket, { autoAddCastNode: true });
				graph.ui.grabSocket(null);
			} catch (e) {
				console.log(e);
			}
			return;
		}

		// In the case that this socket has no connections, grab it
		if (props.socket.connections.length == 0) {
			graph.ui.grabSocket(props.socket);
			return;
		}

		// In the case that this socket has a single connection and cannot accept more edges,
		// we'll disconnect it and grab the other end
		if (props.socket.connections.length == 1 && props.socket.hasMaxEdges()) {
			const to = props.socket.connections[0];
			props.socket.disconnect(to);
			graph.ui.grabSocket(to);
			return;
		}

		// No previous conditions met
		// Open the dropdown to decide what to do
		if (dropdown.value) {
			dropdown.value.open();
			return;
		}
	}

	function openContextMenu(): MenuOptions | null {
		const entries: Array<MenuItem> = [];

		// Auto-add data node for input socket
		if (dataNodeMetadata.value && props.socket.metadata.isInput && !props.socket.hasMaxEdges()) {
			entries.push({
				label: `Add Node: '${dataNodeMetadata.value.name}'`,
				description: "Auto-add the node for this socket's data type.",
				callback: () => {
					const { top, left } = props.socket.getPositions();
					const addedNode = props.socket.graph.addNode(dataNodeMetadata.value!, left - 400, top);
					addedNode.outputSockets[0].connect(props.socket);
				}
			});
		}

		// Auto-add empty list node for list input socket
		const emptyListNode = metadataStore.findNode(`Empty List (${props.socket.metadata.datatype})`);
		if (props.socket.metadata.isInput && props.socket.metadata.isList && emptyListNode) {
			entries.push({
				label: `Add Node: '${emptyListNode.name}'`,
				description: 'Connect an empty list to this socket.',
				callback: () => {
					const { top, left } = props.socket.getPositions();
					const addedNode = props.socket.graph.addNode(emptyListNode!, left - 400, top);
					addedNode.outputSockets[0].connect(props.socket);
				}
			});
		}

		// Auto-add end node for output link socket
		if (datatype.value === null && !props.socket.metadata.isInput && !props.socket.hasMaxEdges()) {
			entries.push({
				label: `Add Node: 'End'`,
				description: `Auto-add an 'End' node.`,
				callback: () => {
					const endNodeMetadata = metadataStore.getNode('End');
					const { right } = props.socket.getPositions();
					const addedNode = props.socket.graph.addNode(endNodeMetadata, right + 50, props.socket.node.y);
					addedNode.inputSockets[0].connect(props.socket);
				}
			});
		}

		// Auto-add end node for output link socket
		if (datatype.value === null && !props.socket.metadata.isInput) {
			entries.push({
				label: `Add Breakpoint Node`,
				description: `Auto-add an 'Debug Breakpoint (Log)' node.`,
				callback: () => {
					const endNodeMetadata = metadataStore.getNode('Debug Breakpoint (Log)');
					const { right } = props.socket.getPositions();
					const addedNode = props.socket.graph.addNode(endNodeMetadata, right + 50, props.socket.node.y);
					const linkSocket = addedNode.inputSockets.find((s) => s.metadata.name == '_backward');
					if (linkSocket) linkSocket.connect(props.socket);
				}
			});
		}

		// Auto-add set-variable node for output data socket
		if (datatype.value && !props.socket.metadata.isInput && !props.socket.hasMaxEdges()) {
			entries.push({
				label: `Save Value to Variable`,
				description: `Auto-add a node to save this value to a variable.`,
				callback: () => {
					const variableNodeMetadata = metadataStore.getNode(
						props.socket.metadata.isList ? 'Set List Variable' : 'Set Variable'
					);
					const addedNode = props.socket.graph.addNode(
						variableNodeMetadata,
						props.socket.node.x + props.socket.node.width() + 50,
						props.socket.node.y
					);

					// Connect the data socket
					const dataSocket = addedNode.inputSockets.find((s) => s.metadata.name == 'Value To Save');
					if (dataSocket) {
						props.socket.connect(dataSocket);
					}

					// Connect the link sockets
					const forwardLink = props.socket.node.outputSockets.find((socket) => socket.metadata.isLink);
					const backwardLink = addedNode.inputSockets.find((socket) => socket.metadata.isLink);
					if (forwardLink && backwardLink) {
						forwardLink.connect(backwardLink);
					}

					addedNode.requestRefreshMetadata(0, true);
				}
			});
		}

		// Auto-add set-variable node for output data socket
		if (datatype.value && !props.socket.metadata.isInput) {
			entries.push({
				label: `Debug Value with Breakpoint`,
				description: `Auto-add a node to log this value with a breakpoint.`,
				callback: () => {
					const variableNodeMetadata = metadataStore.getNode('Debug Breakpoint (Log)');
					const addedNode = props.socket.graph.addNode(
						variableNodeMetadata,
						props.socket.node.x + props.socket.node.width() + 100,
						props.socket.node.y
					);

					// Connect the data socket
					const dataSocket = addedNode.inputSockets.find((s) => s.metadata.name == 'String');
					if (dataSocket) {
						props.socket.connect(dataSocket, { autoAddCastNode: true, skipComputeCastPosition: true });
					}

					// Connect the link sockets
					const forwardLink = props.socket.node.outputSockets.find((socket) => socket.metadata.isLink);
					const backwardLink = addedNode.inputSockets.find((socket) => socket.metadata.isLink);
					if (forwardLink && backwardLink) {
						forwardLink.connect(backwardLink);
					}
				}
			});
		}

		// Auto-add loop node for output list data socket
		if (
			datatype.value &&
			!props.socket.metadata.isInput &&
			!props.socket.hasMaxEdges() &&
			props.socket.metadata.isList
		) {
			entries.push({
				label: `Add Loop`,
				description: 'Add a loop node for this list value.',
				callback: () => {
					const metadata = metadataStore.getNode('For Each');
					const addedNode = props.socket.graph.addNode(
						metadata,
						props.socket.node.x + props.socket.node.width() + 50,
						props.socket.node.y
					);

					// Connect the sockets
					props.socket.connect(addedNode.getInputSocket('List to Iterate'));

					// Connect the link sockets
					const forwardLink = props.socket.node.outputSockets.find((socket) => socket.metadata.isLink);
					const backwardLink = addedNode.inputSockets.find((socket) => socket.metadata.isLink);
					if (forwardLink && backwardLink) {
						forwardLink.connect(backwardLink);
					}

					addedNode.requestRefreshMetadata(0, true);
				}
			});
		}

		// Add divider
		if (entries.length) {
			entries[entries.length - 1].divider = true;
		}

		if (props.socket.connections.length) {
			entries.push({
				label: `Clear Connections`,
				description: 'Clear the connections for this socket.',
				callback: () => {
					props.socket.disconnectAll();
				}
			});
		}

		if (
			error.value &&
			error.value.toLowerCase().includes('graph input') &&
			error.value.toLowerCase().includes('does not exist for this socket type')
		) {
			entries.push({
				label: `Create New Graph Input`,
				description: 'Creates a New Graph Input with this name and datatype.',
				callback: () => {
					if (!props.socket.graphInputName) return;
					const metadata: GraphInputMetadata = {
						name: props.socket.graphInputName,
						datatype: props.socket.metadata.datatype!,
						isList: props.socket.metadata.isList,
						isPassword: false,
						description: '',
						category: '',
						defaultValue: undefined
					};
					props.socket.graph.updateInputMetadata(metadata);
				}
			});
		}

		return { items: entries };
	}

	/**********************
	 * Styles
	 **********************/
	/** The color for this socket. */
	const color = computed(() => {
		return datatype.value ? datatype.value.color : 'var(--color-editor-link-socket-edge)';
	});

	/** Styles for a data socket */
	const dataSocketStyles = computed(() => {
		return {
			'background-color': connected.value ? color.value : 'transparent',
			'border-color': color.value
		};
	});

	const nodeId = computed(() => {
		return props.socket.node.id;
	});

	watch(
		error,
		() => {
			if (error.value == null) {
				errorStore.removeError(props.tabId, nodeId.value, props.socket.metadata.name);
			} else {
				errorStore.addError(props.tabId, nodeId.value, props.socket.metadata.name, error.value);
			}
		},
		{ immediate: true }
	);

	watch(
		hasWarning,
		() => {
			if (hasWarning.value === null) {
				errorStore.removeWarning(props.tabId, nodeId.value, props.socket.metadata.name);
			} else if (hasWarning.value.trim() != '') {
				errorStore.addWarning(props.tabId, nodeId.value, props.socket.metadata.name, hasWarning.value);
			}
		},
		{ immediate: true }
	);
</script>

<style scoped>
	.socket-container {
		display: flex;
		flex-direction: row;
		align-items: center;
		cursor: pointer;
	}

	.socket-container[is-input='true'] {
		flex-direction: row-reverse;
	}

	.data-socket {
		width: 12px;
		height: 12px;
		border-radius: 100%;
		border: 2px solid transparent;
	}

	.array-data-socket {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		grid-template-rows: repeat(3, 1fr);
		gap: 1px;
	}

	.array-data-socket-block {
		width: 5px;
		height: 5px;
		border: 1px solid transparent;
	}

	.link-socket {
		width: 12px;
		height: 12px;
		position: relative;
	}

	.link-socket svg {
		width: 100%;
		height: 100%;
		overflow: visible;
		position: absolute;
		top: 0px;
		left: 1px;
	}

	.link-socket polygon {
		stroke: var(--color-editor-node-title-text);
		stroke-width: 2px;
	}

	.socket-container[connected='true'] polygon {
		fill: var(--color-editor-node-title-text);
	}

	.socket-name {
		font-size: 0.9rem;
		display: flex;
		flex-direction: row;
		align-items: center;
		white-space: nowrap;
		color: var(--color-editor-socket-text);
	}

	.socket-container[is-input='true'] .socket-name {
		margin-left: 6px;
	}

	.socket-container[is-input='false'] .socket-name {
		margin-right: 6px;
	}

	.socket-name-error {
		font-size: 1rem;
		cursor: help;
		color: var(--color-editor-socket-text-error);
	}

	.socket-container[error='false'] .socket-name-error {
		opacity: 0;
		pointer-events: none;
		cursor: inherit;
	}

	.socket-container[is-input='true'] .socket-name-error {
		margin-left: 3px;
	}

	.socket-container[is-input='false'] .socket-name-error {
		margin-right: 3px;
	}

	.socket-num-connections {
		display: flex;
		color: var(--color-text);
		margin-left: auto;
		padding-right: 2px;
	}

	.socket-container-vertical-stack {
		display: flex;
		flex-direction: column;
	}
</style>
