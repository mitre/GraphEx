import type GraphComponent from '@/editor/graph/GraphComponent.vue';
import type TextEditorComponent from '@/editor/text/TextEditorComponent.vue';
import {
	Graph,
	NodeTypes,
	type GraphNode,
	type NodeMetadata,
	type NodeStateObject,
	type SerializedGraph,
	type SerializedNode,
	type Socket
} from '@/graph';
import { useErrorStore } from '@/stores/error';
import { GRAPH_FILE_EXTENSION, LOG_FILE_EXTENSION, useFileStore } from '@/stores/files';
import { useMetadataStore } from '@/stores/metadata';
import { usePromptStore } from '@/stores/prompts';
import { useTerminalStore } from '@/stores/terminal';
import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import { computed, nextTick, reactive, ref, watch } from 'vue';
import YAML, { YAMLParseError } from 'yaml';

export interface EditorTab {
	/** The ID for this tab. */
	id: string;

	/**
	 * Reference to a file on the file system, if it exists. It may be assumed that if this fileId is populated, the file exists in the file tree,
	 * as this will be set to `null` as soon as the file is found to not exist.
	 */
	fileId: string | null;

	/** The name of this tab. This will be automatically updated if this tab is associated with a file and the file changes names. */
	name: string;

	/** The contents for this tab. */
	contents: Graph | string;

	/** The string representation of the tab contents since the last time it was saved. */
	serialContentsAtLastSave: string;
}

interface EditorGraphTab extends EditorTab {
	contents: Graph;
}

interface EditorTextTab extends EditorTab {
	contents: string;
}

export const useEditorStore = defineStore('editor', () => {
	const fileStore = useFileStore();
	const promptStore = usePromptStore();
	const metadataStore = useMetadataStore();
	const errorStore = useErrorStore();
	const terminalStore = useTerminalStore();

	/** List of open editor tabs. */
	const tabs = reactive<Array<EditorTab>>([]);

	/** Mapping of tab ID to the tab. */
	const tabIdToTab = computed(() => {
		const idMap: { [id: string]: EditorTab } = {};
		for (const tab of tabs) {
			idMap[tab.id] = tab;
		}
		return idMap;
	});

	const graphComponents: { [id: string]: InstanceType<typeof GraphComponent> } = reactive({});

	const textComponents: { [id: string]: InstanceType<typeof TextEditorComponent> } = reactive({});

	/** The ID for the active editor tab. */
	const activeTabId = ref<string>('');

	/** The currently active tab. */
	const activeTab = computed(() => tabs.find((t) => t.id === activeTabId.value));

	/** The currently active graph tab. This will be `undefined` if the currently open tab does not refer to a graph. */
	const activeGraphTab = computed(() =>
		activeTab.value && activeTab.value.contents instanceof Graph ? (activeTab.value as EditorGraphTab) : undefined
	);

	/** The currently active text tab. This will be `undefined` if the currently open tab does not refer to a text-like file. */
	const activeTextTab = computed(() =>
		activeTab.value && typeof activeTab.value.contents === 'string' ? (activeTab.value as EditorTextTab) : undefined
	);

	/** Nodes that were copied in an editor. */
	const copiedNodes = reactive<Array<NodeStateObject>>([]);

	const isResolvingMergeConflict = ref<boolean>(false);

	const selectedIssueNodeId = ref<string>('');

	const conflictsToResolve = ref<any>({});

	const chosenGraphInputConflicts = ref<any>({});
	const chosenNodeConflicts = ref<any>({});

	const gitUsername = ref<string>('');
	const gitPassword = ref<string>('');

	function setGraphComponent(id: string, component: InstanceType<typeof GraphComponent> | null | undefined) {
		if (!component) {
			if (id in graphComponents) {
				delete graphComponents[id];
			}
			return;
		}
		graphComponents[id] = component;
	}

	function getGraphComponent(id: string): InstanceType<typeof GraphComponent> | null {
		if (id in graphComponents) {
			return graphComponents[id];
		}
		return null;
	}

	function setTextComponent(id: string, component: InstanceType<typeof TextEditorComponent> | null | undefined) {
		if (!component) {
			if (id in textComponents) {
				delete textComponents[id];
			}
			return;
		}
		textComponents[id] = component;
	}

	function getTextComponent(id: string): InstanceType<typeof TextEditorComponent> | null {
		if (id in textComponents) {
			return textComponents[id];
		}
		return null;
	}

	/**
	 * Get a tab by its ID.
	 *
	 * @param id The ID.
	 *
	 * @returns The tab object, or `null` if the tab is not found.
	 */
	function getTabById(id: string): EditorTab | null {
		if (id in tabIdToTab.value) {
			return tabIdToTab.value[id];
		}
		return null;
	}

	/**
	 * Make a tab active.
	 *
	 * @param id The ID of the tab to make active.
	 *
	 * @throws If a tab does not exist for the given file ID.
	 */
	function setActiveTab(id: string) {
		const tab = getTabById(id);
		if (!tab) {
			throw `No tab exists for ID ${id}`;
		}
		activeTabId.value = id;
	}

	/**
	 * Delete a tab. If the tab does not exist, this does nothing.
	 *
	 * @param id The ID of the tab.
	 *
	 * @returns Whether the tab existed and was removed.
	 */
	function removeTab(id: string): boolean {
		const index = tabs.findIndex((t) => t.id === id);
		if (index < 0) {
			return false;
		}

		const tab = tabs[index];
		if (tabs.length == 1) {
			// If no more graphs will exist after removing this one, add a default graph
			tabs.splice(0, 1);
			newDefaultGraphTab();
			return true;
		}

		if (tab.id == activeTabId.value && index == 0) {
			// This graph was selected and it's the first, select the next
			setActiveTab(tabs[1].id);
		} else if (tab.id == activeTabId.value) {
			// This graph was selected and it's not the first, select the previous
			setActiveTab(tabs[index - 1].id);
		}

		tabs.splice(index, 1);
		return true;
	}

	/**
	 * Delete tabs used in merge conflict resolution. If the tab does not exist, this does nothing.
	 *
	 * @param fileId The ID of the file.
	 *
	 */
	function removeMergeConflictTabs(filePath: string) {
		const relevantTabs = tabs.filter((t) => t.name === filePath);
		relevantTabs.forEach((tab) => {
			removeTab(tab.id);
		});
	}

	/**
	 * Reorder tabs such that the first provided tab is moved after the second provided tab.
	 *
	 * @param id1 The ID of the tab to move.
	 * @param id2 The ID of the tab to move the tab after.
	 */
	function reorderTabs(id1: string, id2: string) {
		const index = tabs.findIndex((t) => t.id === id1);
		if (index <= -1) return;

		const newIndex = tabs.findIndex((t) => t.id === id2);
		if (newIndex <= -1) return;

		tabs.splice(newIndex, 0, ...tabs.splice(index, 1));
	}

	/**
	 * Open a new tab in the editor. This tab will be made immediately active.
	 *
	 * @param name The name of the tab. If not provided and `fileId` is also not provided, a generic name will be given to the tab.
	 * @param fileId The ID for the file associated with this tab, if one exists. If provided, the file name for this file will be used rather than any value specified for `name`.
	 * @param contents The contents of the tab.
	 *
	 * @returns The ID of the newly added tab.
	 * @throws If a fileId is specified for a file that does not exist.
	 */
	function addTab(name: string | null, fileId: string | null, contents: string | Graph): string {
		if (fileId) {
			const file = fileStore.findFileById(fileId);
			if (!file) {
				throw `No file exists for ID ${fileId}`;
			}
			if (!name) {
				name = fileStore.getFileName(file);
			}
		}

		if (name === null) {
			// Create a generic name
			// Find an available name to avoid conflicts
			const ext = contents instanceof Graph ? GRAPH_FILE_EXTENSION : '.txt';
			const usedNames = tabs.filter((t) => !t.fileId).map((t) => t.name);
			const baseName = 'Untitled-';
			let index = 1;
			while (usedNames.includes(baseName + index + ext)) index += 1;
			name = baseName + index + ext;
		}

		// Add the new tab
		const newTab: EditorTab = {
			id: uuidv4(),
			fileId: fileId,
			name: name,
			contents: contents,
			serialContentsAtLastSave: ''
		};
		tabs.push(newTab);
		newTab.serialContentsAtLastSave = getTabSerialContents(newTab.id);

		// Make this tab active
		setActiveTab(newTab.id);

		// Check if previously open tab meet the criteria for auto-closing:
		if (
			tabs.length == 2 &&
			tabs[0].name === 'Untitled-1' + GRAPH_FILE_EXTENSION &&
			tabs[1].name !== 'Untitled-2' + GRAPH_FILE_EXTENSION &&
			tabs[0].contents instanceof Graph &&
			tabs[1].contents instanceof Graph &&
			!tabs[0].fileId &&
			!tabHasChanges(tabs[0].id)
		) {
			removeTab(tabs[0].id);
		}

		return newTab.id;
	}

	/**
	 * Add a new Graph with defaults.
	 *
	 * This tab will be made immediately active.
	 *
	 * @returns The ID of the added tab.
	 */
	function newDefaultGraphTab(): string {
		// Create the graph
		const graph = new Graph();

		// Add a initial nodes
		try {
			// Add the default nodes
			const start = graph.addNode(metadataStore.getNode('Graph Start'), 200, 200);
			const print = graph.addNode(metadataStore.getNode('Log (Print)'), 407, 200);
			const end = graph.addNode(metadataStore.getNode('End'), 740, 200);

			// Set the initial print value
			print.inputSockets[0].fieldValue = 'Hello World!';

			// Connect the nodes together
			print.getInputSocket('_backward').connect(start.getOutputSocket('_forward'));
			print.getOutputSocket('_forward').connect(end.getInputSocket('_backward'));
		} catch (e) {
			console.warn('Could not create default graph: ' + e);
		}

		graph.history.reset();
		return addTab(null, null, graph);
	}

	/**
	 * Store nodes copied by the context menu. Will overwrite previously copied nodes.
	 *
	 * @param nodes The nodes.
	 */
	function storeCopiedNodes(nodes: Array<GraphNode>) {
		copiedNodes.splice(0, copiedNodes.length); // Clear
		for (const node of nodes) {
			copiedNodes.push(node.getStateObject());
		}
	}

	/**
	 * Add a new graph from its serialized form. This will prompt if information is needed from the user to load the serialized graph.
	 *
	 * This tab will be made immediately active.
	 *
	 * @param name The name of the tab. If not provided and `fileId` is also not provided, a generic name will be given to the tab.
	 * @param fileId The ID for the file associated with this tab, if one exists. If provided, the file name for this file will be used rather than any value specified for `name`.
	 * @param serialized The serialized Graph.
	 *
	 * @returns The ID of the newly added tab, or `null` if the load was canceled by the user (should be treated gracefully, not as an error).
	 * @throws If the Graph cannot be loaded from its serialized form, or if a fileId is specified for a file that does not exist.
	 */
	async function addGraphTabFromSerialized(
		name: string | null,
		fileId: string | null,
		serialized: SerializedGraph
	): Promise<string | null> {
		const graph = new Graph();

		// Set up I/O
		for (const input of serialized.inputs || []) {
			graph.updateInputMetadata(JSON.parse(JSON.stringify(input)));
		}

		for (const output of serialized.outputs || []) {
			graph.updateOutputMetadata(JSON.parse(JSON.stringify(output)));
		}

		graph.description = serialized.description || '';

		let graph_start_x = 0;
		let graph_start_y = 0;

		// Make sure each node is available
		const missingNodes: { [name: string]: number } = {};
		for (const serializedNode of serialized.nodes) {
			const metadata = metadataStore.findNode(serializedNode.name);
			if (serializedNode.name.toLowerCase() == 'graph start') {
				const [str_x, str_y] = serializedNode.xy.split(',');
				graph_start_x = Number(str_x);
				graph_start_y = Number(str_y);
			}

			if (!metadata) {
				missingNodes[serializedNode.name] = (missingNodes[serializedNode.name] || 0) + 1;
			}
		}

		// Set up UI
		graph.ui.scale = 1.0;
		// Important note: the viewport positions for the editor don't exist at this point
		graph.ui.offsets.x = graph_start_x * -1;
		graph.ui.offsets.y = graph_start_y * -1;

		let missingNodeAction: 'error' | 'skip' | 'comment' = 'error';
		if (Object.keys(missingNodes).length != 0) {
			// One or more nodes are missing
			// Display a prompt to ask if we want to replace these nodes with comments
			let additionalInfo = `Graph contains nodes that do not exist.\n\n`;
			additionalInfo +=
				'This may occur if the graph was created using a different version of GraphEX or a different plugin version, or using a plugin that has not been loaded.\n\n';
			additionalInfo += 'The missing nodes are:\n\n';
			for (const nodeName of Object.keys(missingNodes)) {
				const instances = missingNodes[nodeName];
				additionalInfo += `- ${nodeName} (${instances} instance${instances > 1 ? 's' : ''})\n`;
			}
			additionalInfo += '\n';
			additionalInfo += 'How should these nodes be loaded?';

			const value = await promptStore.show({
				title: 'Graph Contains Missing Nodes',
				additionalInfo: additionalInfo,
				entries: [],
				buttons: [
					{
						text: 'Replace With Comments',
						type: 'primary'
					},
					{
						text: 'Delete The Nodes',
						type: 'warning'
					},
					{
						text: 'Cancel',
						type: 'secondary'
					}
				]
			});

			if (!value || value.buttonName == 'Cancel') {
				return null;
			}

			if (value.buttonName == 'Replace With Comments') {
				missingNodeAction = 'comment';
			}

			if (value.buttonName == 'Delete The Nodes') {
				missingNodeAction = 'skip';
			}
		}

		// Get all the node metadata
		const nodeMetadata: { [id: string]: NodeMetadata } = {};
		for (const serializedNode of serialized.nodes) {
			const metadata = metadataStore.findNode(serializedNode.name);
			if (!metadata) continue;
			if (!metadata.dynamic) {
				nodeMetadata[serializedNode.id] = metadata;
				continue;
			}

			const response = await fetch('/api/updateNode', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					graph: serialized,
					id: serializedNode.id
				})
			});

			if (response.status != 200) {
				throw `Failed to refresh node: ${await response.text()}`;
			}

			nodeMetadata[serializedNode.id] = await response.json();
		}

		// Add the nodes
		const skippedNodes: Array<string> = [];
		for (const serializedNode of serialized.nodes) {
			const metadata = nodeMetadata[serializedNode.id];

			if (!metadata && (missingNodeAction === 'skip' || missingNodeAction === 'comment')) {
				// Skip this node
				// We'll skip even if we should add a comment because we want to
				// add comments after all the nodes (that was can add) have been added
				// This ensures we don't step on any comment IDs
				skippedNodes.push(serializedNode.id);
				continue;
			}

			if (!metadata) {
				throw `No node found with name "${serializedNode.name}"`;
			}

			// Add the node
			const xy = serializedNode.xy.split(',');
			const n = graph.addNode(metadata, Number(xy[0]), Number(xy[1]), {
				fieldValue: serializedNode.fieldValue,
				id: serializedNode.id,
				color: serializedNode.color,
				textColor: serializedNode.textColor
			});

			// Disable variable output sockets that were specified to be disabled previously in the serialized state
			if (serializedNode.disabledVariableOutputs && serializedNode.disabledVariableOutputs.length) {
				serializedNode.disabledVariableOutputs.forEach((disabledName) => {
					const s = n.outputSockets.find((s) => s.metadata.name === disabledName);
					if (s) {
						s.disabledVariableOutput = true;
					}
				});
			}
		}

		// Replace missing nodes with comments if requested
		if (skippedNodes.length && missingNodeAction === 'comment') {
			for (const serializedNode of serialized.nodes) {
				if (!skippedNodes.includes(serializedNode.id)) continue;
				addCommentNodeFromSerializedInfo(graph, serialized, serializedNode, '--- MISSING NODE ---', '#640000');
			}
		}

		// Go through each socket in the graph and set the appropriate connections/data
		// Note: This has to be done after all the nodes are added to ensure all nodes exist to make connections
		for (const serializedNode of serialized.nodes) {
			if (skippedNodes.includes(serializedNode.id)) continue;
			const node = graph.getNode(serializedNode.id);

			for (const serializedSocket of serializedNode.inputs || []) {
				let socket: Socket | null = null;
				try {
					socket = node.getInputSocket(serializedSocket.name);
				} catch (e) {
					console.warn(e);
				}

				if (!socket) {
					continue;
				}

				// Set data
				if (serializedSocket.fieldValue !== undefined) {
					socket.setFieldValue(JSON.parse(JSON.stringify(serializedSocket.fieldValue)));
				} else if (serializedSocket.variableName !== undefined) {
					socket.setVariableName(serializedSocket.variableName);
				} else if (serializedSocket.graphInputName !== undefined) {
					socket.setGraphInputName(serializedSocket.graphInputName);
				} else {
					// Explicitly unset each socket value
					// This is needed to override any defaults
					socket.setFieldValue();
					socket.setVariableName();
					socket.setGraphInputName();
				}

				// Add connections
				for (const connection of serializedSocket.connections || []) {
					const [connNodeId, connSocketName] = connection.split('::');
					if (skippedNodes.includes(connNodeId)) continue;

					let outputNode: GraphNode | null = null;
					let outputSocket: Socket | null = null;
					try {
						outputNode = graph.getNode(connNodeId);
						outputSocket = outputNode?.getOutputSocket(connSocketName);
					} catch (e) {
						console.warn(e);
					}
					if (!outputNode) {
						continue;
					}

					if (!outputSocket) {
						continue;
					}

					try {
						socket.connect(outputSocket);
					} catch (e) {
						promptStore.failedAlert(
							'Failed to Connect Sockets',
							'Failed to connect socket: "' +
								socket.metadata.name +
								'" to other socket: "' +
								outputSocket.metadata.name +
								'" when creating node: ' +
								node.metadata.name +
								'" ... The node has ID: "' +
								node.id +
								'"'
						);
					}
				}
			}
		}
		graph.history.reset();
		return addTab(name, fileId, graph);
	}

	/**
	 * Replaces the provided serializedNode in the serialized graph with a comment describing the node and adds it to the provided graph
	 * @param graph The graph in which to add the comment node to
	 * @param serialized The serialized graph containing the node to replace with a comment node
	 * @param serializedNode The node to replace with a comment node
	 * @param commentReasonString The reason for replacing this node (shown on the top line of the comment node)
	 * @param backgroundColorString The background color of the comment node to create
	 *
	 * @returns An object of {"newCommentNode" and "outputConnectionInfo"} with the outputConnectionInfo string being: the ID::socketName (string) of the node connected to the "_forward" (output) link socket of this node (string will be empty if not found)
	 */
	function addCommentNodeFromSerializedInfo(
		graph: Graph,
		serialized: SerializedGraph,
		serializedNode: SerializedNode,
		commentReasonString: string,
		backgroundColorString: string
	) {
		let outputConnection = '';

		const commentMetadata = metadataStore.getNode('Comment');
		let commentText = commentReasonString + '\n\n';
		commentText += `Name: ${serializedNode.name}\n`;
		commentText += `ID: ${serializedNode.id}`;

		if (serializedNode.fieldValue !== undefined) {
			commentText += `\n\nField Value: ${serializedNode.fieldValue}`;
		}

		if (serializedNode.inputs && serializedNode.inputs.length) {
			commentText += `\n\nInput Sockets:\n${YAML.stringify(serializedNode.inputs, {
				indent: 4,
				lineWidth: 0,
				minContentWidth: 0
			})}`;
		}

		// Output socket data isn't stored on the serialized node
		// Construct it manually
		// We'll need to go through all the nodes available and see if any would have connected
		// to this node
		const outputConnections: { [name: string]: Array<string> } = {};
		for (const otherSerializedNode of serialized.nodes) {
			for (const otherNodeInput of otherSerializedNode.inputs || []) {
				if (!otherNodeInput.connections) continue;
				for (const otherConnection of otherNodeInput.connections) {
					const [connId, connSocket] = otherConnection.split('::');
					if (connId !== serializedNode.id) continue;
					if (!(connSocket in outputConnections)) outputConnections[connSocket] = [];
					const formattedConnectionString = otherSerializedNode.id + '::' + otherNodeInput.name;
					outputConnections[connSocket].push(formattedConnectionString);
					if (otherNodeInput.name.toLowerCase() == '_backward') {
						outputConnection = formattedConnectionString;
					}
				}
			}
		}

		if (Object.keys(outputConnections).length != 0) {
			const serializedOutputs = [];
			for (const outputSocketName of Object.keys(outputConnections)) {
				serializedOutputs.push({
					name: outputSocketName,
					connections: outputConnections[outputSocketName]
				});
			}

			commentText += `\n\nOutput Sockets:\n${YAML.stringify(serializedOutputs, {
				indent: 4,
				lineWidth: 0,
				minContentWidth: 0
			})}`;
		}

		const xy = serializedNode.xy.split(',');
		const newCommentNode = graph.addNode(commentMetadata, Number(xy[0]), Number(xy[1]), {
			fieldValue: commentText,
			color: backgroundColorString,
			textColor: '#FFFFFF'
		});

		graph.recordCommentNodeID(serializedNode.id);

		return { newCommentNode: newCommentNode, outputConnectionInfo: outputConnection };
	}

	/**
	 * Takes in a comment node that was created by the right-click context menu and attempts to convert it back into the original node.
	 * This function assumes the comment is already in the correct structure to be parsed
	 * (e.g. begins with: '### COMMENTED NODE ###' and has had extra text applied to it)
	 * This function does not handle parsing errors and will throw an error when the parsing fails (for any reason)
	 * @param commentNode The node that is currently a comment but is desired to be returned to its original node
	 */
	async function createNodeFromComment(commentNode: GraphNode) {
		// The graph that the node should be added and connected to
		const graph = commentNode.graph;

		// We need to parse through the fieldValue of the comment node to find the information for the node to recreate
		// First find the "Name" substring
		const textbox = (commentNode.fieldValue as string).slice((commentNode.fieldValue as string).indexOf('Name:'));
		let nextNewlineIndex = textbox.indexOf('\n');
		const nameOfNode = textbox.slice('Name:'.length, nextNewlineIndex).trim();

		// Grab the "ID" substring in case we need it later
		nextNewlineIndex = textbox.indexOf('\n', nextNewlineIndex + 1);
		const idOfNode = textbox.slice(textbox.indexOf('ID:') + 'ID:'.length, nextNewlineIndex).trim();

		// Find this type of node from the metadata store and add it to the graph
		const nodeMetadata = metadataStore.getNode(nameOfNode);
		graph.removeCommentedNodeId(idOfNode);
		const newNode = graph.addNode(nodeMetadata, commentNode.x, commentNode.y, { id: idOfNode });

		// Grab the "Field Value" substring and assign in the case of nodes with field values
		const fieldValueIndex = textbox.indexOf('Field Value:', nextNewlineIndex);
		if (fieldValueIndex > -1) {
			const currentFieldValue = newNode.fieldValue;
			const valueToAssign = textbox
				.slice(fieldValueIndex + 'Field Value:'.length, textbox.indexOf('Input Sockets:'))
				.trim();
			if (typeof currentFieldValue === 'string') {
				newNode.setFieldValue(YAML.parse(valueToAssign));
			} else if (typeof currentFieldValue === 'number') {
				newNode.setFieldValue(+valueToAssign);
			} else if (typeof currentFieldValue === 'boolean') {
				if (valueToAssign.toLowerCase() === 'true') newNode.setFieldValue(true);
				else newNode.setFieldValue(false);
			}

			// If the node is dynamic, refresh it to pull the graph inputs from the file
			if (newNode.metadata.dynamic) {
				await newNode.refreshMetadata();
			}
		}

		// Grab the sections of text for input and output sockets
		const inputSocketsIndex = textbox.indexOf('Input Sockets:', nextNewlineIndex + 1);
		const outputSocketsIndex = textbox.indexOf('Output Sockets:', inputSocketsIndex + 'Input Sockets:'.length);
		let graphInputsText = textbox.slice(inputSocketsIndex + 'Input Sockets:'.length, outputSocketsIndex).trim();
		let graphOutputsText = textbox.slice(outputSocketsIndex + 'Output Sockets:'.length).trim();

		if (inputSocketsIndex < 0) graphInputsText = '';
		if (outputSocketsIndex < 0) graphOutputsText = '';

		// // // Parse Inputs // // //
		// e.g.
		// - name: Old
		// // ^ is the name of the socket (could be data or link)
		// fieldValue: "{VERSION}"
		// connections:
		// graphInputName: VirtualMachineName
		// variableName: VM
		// // ^ the name of the type of key relevant here that provides values to the socket
		// Arrays are a bit trickier:
		/**
	- name: Disks
		fieldValue:
			- 0
			- 1
			- 2 */
		const inputLines = graphInputsText.split('\n');
		let currentName = '';
		let isArray = false;
		let assigningConnections = false;
		for (const line of inputLines) {
			// Extract the name of the socket to assign values to
			if (line.includes('name:')) {
				// grab the name of this socket
				currentName = line.split('name:')[1].trim();
				isArray = false;
				assigningConnections = false;
				// We are currently going through a list of values to assign to the socket
			} else if (isArray) {
				const v = line.slice(line.indexOf('-') + 1).trim();
				const currentDatatype = newNode.getInputSocket(currentName).metadata.datatype?.toLowerCase();
				const arrayLength = newNode.getInputSocket(currentName).addNewFieldListValue();
				if (currentDatatype === 'string') {
					newNode.getInputSocket(currentName).setFieldListValue(arrayLength - 1, YAML.parse(v));
				} else if (currentDatatype === 'number') {
					newNode.getInputSocket(currentName).setFieldListValue(arrayLength - 1, +v);
				} else if (currentDatatype === 'boolean') {
					if (v.toLowerCase() === 'true') {
						newNode.getInputSocket(currentName).setFieldListValue(arrayLength - 1, true);
					} else {
						newNode.getInputSocket(currentName).setFieldListValue(arrayLength - 1, false);
					}
				}
				// We are currently going through a list of connections to assign to the socket
			} else if (assigningConnections) {
				const v = line.slice(line.indexOf('-') + 1).trim();
				const [connId, connSocket] = v.split('::');
				const otherNode = graph.findNode(connId);
				if (otherNode) newNode.getInputSocket(currentName).connect(otherNode.getOutputSocket(connSocket));
				// We have a fieldValue textbox to assign values to, but we don't know if it is an array or not yet
			} else if (line.includes('fieldValue:')) {
				const v = line.split('fieldValue:')[1].trim();
				if (v) {
					const currentFieldValue = newNode.getInputSocket(currentName).fieldValue;
					if (typeof currentFieldValue === 'string') {
						newNode.getInputSocket(currentName).setFieldValue(YAML.parse(v));
					} else if (typeof currentFieldValue === 'number') {
						newNode.getInputSocket(currentName).setFieldValue(+v);
					} else if (typeof currentFieldValue === 'boolean') {
						if (v.toLowerCase() === 'true') newNode.getInputSocket(currentName).setFieldValue(true);
						else newNode.getInputSocket(currentName).setFieldValue(false);
					}
				} else {
					// Must be an array
					isArray = true;
				}
				// The input socket is assigned a value via a variable
			} else if (line.includes('variableName:')) {
				const v = line.split('variableName:')[1].trim();
				newNode.getInputSocket(currentName).setVariableName(v);
				// The input socket is assigned a value via a graph input
			} else if (line.includes('graphInputName:')) {
				const v = line.split('graphInputName:')[1].trim();
				newNode.getInputSocket(currentName).setGraphInputName(v);
				// The input socket is connected to an output socket of another node, which provides the value
			} else if (line.includes('connections:')) {
				assigningConnections = true;
			} // end conditionals for each line
		} // end for line in inputLines

		// // // // // // // // // // //
		// // // Parse Outputs // // //
		// // // // // // // // // // //
		// The structure in the comment is the same as described in the "Parse Inputs" comment above
		const outputLines = graphOutputsText.split('\n');
		currentName = '';
		assigningConnections = false;
		for (const line of outputLines) {
			// Extract the name of the socket to assign values to
			if (line.includes('name:')) {
				// grab the name of this socket
				currentName = line.split('name:')[1].trim();
				assigningConnections = false;
				// We are currently going through a list of values to assign to the socket
			} else if (assigningConnections) {
				const v = line.slice(line.indexOf('-') + 1).trim();
				const [connId, connSocket] = v.split('::');
				const otherNode = graph.findNode(connId);
				if (otherNode) newNode.getOutputSocket(currentName).connect(otherNode.getInputSocket(connSocket));
				// The output socket is connected to an output socket of another node, which provides the value
			} else if (line.includes('connections:')) {
				assigningConnections = true;
			} // end conditionals for each line
		} // end for line in inputLines

		return newNode;
	}

	/**
	 * Performs three operations: (1) Creates a comment node from the provided node, (2) Connects the link sockets for nodes before and after the provided one,
	 * (3) Deletes the provided node
	 * @param node The node to replace with a commented node
	 *
	 * @returns An dictionary/object containing the following keys: "newCommentNode" and "outputConnectionInfo"
	 */
	function replaceNodeWithCommentSingular(node: GraphNode) {
		node.graph.ui.deselectAllNodes();
		// add the comment node to the graph, retrieve information about the node and socketname that follows our node
		const addCommentInfo = addCommentNodeFromSerializedInfo(
			node.graph,
			node.graph.serialize(),
			node.serialize(),
			'### COMMENTED NODE ###',
			'#006400'
		);
		const [idOfNodeAfterThisOne, forwardNodeSocketName] = addCommentInfo['outputConnectionInfo'].split('::');
		// Replace the connections
		node.graph.replaceNodeLinkConnections(node, idOfNodeAfterThisOne);
		// Delete the node
		node.graph.deleteNodes([node]);
		return addCommentInfo;
	}

	/**
	 * For each node in the array, performs three operations. Each operation is completed for all nodes before moving on to the next one:
	 * (1) Creates a comment from the node (2) Deletes the node (3) Selects the newly created node
	 * @param nodeArray A grouping of nodes that may or may not contain pre-existing comment nodes
	 * @param graph The graph in which the nodes reside
	 */
	function replaceMultipleNodesWithComments(nodeArray: GraphNode[], graph: Graph) {
		// const chainToConnect: string[] = [];
		const markedForDeletion: GraphNode[] = [];
		const nodesToSelect: GraphNode[] = [];
		// First we replace every node with a comment node showing their original connections
		for (const node of nodeArray) {
			if (node.metadata.type != NodeTypes.COMMENT) {
				// add the comment node to the graph, retrieve information about the node and socketname that follows our node
				const addCommentInfo = addCommentNodeFromSerializedInfo(
					node.graph,
					node.graph.serialize(),
					node.serialize(),
					'### COMMENTED NODE ###',
					'#006400'
				);
				// const [idOfNodeAfterThisOne, forwardNodeSocketName] = (addCommentInfo["outputConnectionInfo"]).split('::');
				// chainToConnect.push(idOfNodeAfterThisOne);
				markedForDeletion.push(node);
				nodesToSelect.push(addCommentInfo['newCommentNode']);
			} else {
				nodesToSelect.push(node);
			}
		}
		// // then we attempt to hookup link nodes to bypass the commented nodes
		// for (const node of markedForDeletion) {
		// 	if (chainToConnect.length) {
		// 		// Replace the connections
		// 		const nextLink = chainToConnect.pop();
		// 		console.log("the next link is: ", nextLink);
		// 		if (nextLink)
		// 			node.graph.replaceNodeLinkConnections(node, nextLink);
		// 	}
		// }
		// Delete the nodes that are to be replaced with comments
		graph.deleteNodes(markedForDeletion);
		// Select all the newly commented (and existing comment) nodes
		graph.ui.deselectAllNodes();
		for (const node of nodesToSelect) {
			graph.ui.selectNode(node);
		}
	}

	/**
	 * Peforms two operations: (1) Attempts to convert a previously commented node into an uncommented node (2) Deletes the comment node
	 * @param node The comment node to replace with a non-comment node
	 * @returns The newly created (recreated) non-comment node
	 */
	async function replaceCommentWithNodeSingular(node: GraphNode) {
		try {
			// Attempt to create a node from the fieldValue string contained in the comment node
			const newNode = await createNodeFromComment(node);
			// Delete the comment node
			node.graph.deleteNodes([node]);
			return newNode;
		} catch (e) {
			console.log('Error converting comment node back to original node: ', e as string);
		}
		return null;
	}

	async function replaceMultipleCommentsWithNodes(nodeArray: GraphNode[], graph: Graph) {
		const markedForDeletion: GraphNode[] = [];
		const nodesToSelect: GraphNode[] = [];
		// Recreate the nodes that were commented out
		for (const node of nodeArray) {
			if (
				node.metadata.type == NodeTypes.COMMENT &&
				typeof node.fieldValue === 'string' &&
				node.fieldValue.startsWith('### COMMENTED NODE ###')
			) {
				const newNode = await createNodeFromComment(node);
				markedForDeletion.push(node);
				nodesToSelect.push(newNode);
			} else {
				nodesToSelect.push(node);
			}
		}
		// Delete the nodes that are to be replaced with comments
		graph.deleteNodes(markedForDeletion);
		// Select all the newly commented (and existing comment) nodes
		graph.ui.deselectAllNodes();
		for (const node of nodesToSelect) {
			graph.ui.selectNode(node);
		}
	}

	/**
	 * Rename this tab. If this tab is associated with a file, the file will be renamed.
	 *
	 * @param id The tab ID.
	 * @param newName The new name for the tab.
	 *
	 * @returns A boolean whether the rename succeeded.
	 */
	async function renameTab(id: string, newName: string): Promise<boolean> {
		const tab = getTabById(id);
		if (!tab) {
			console.warn(`No tab exists for ID ${id}`);
			return false;
		}

		newName = newName.trim();
		if (newName.length === 0) {
			return false;
		}

		if (!tab.fileId) {
			// Just rename the tab itself since there's no file
			tab.name = newName;
			return true;
		}

		// Rename the file
		// The tab name will automatically update if this succeeds
		return await fileStore.renameFile(tab.fileId, newName);
	}

	/**
	 * Extract information from a base64 encoded string that was provided by an ERRORLINK log message.
	 * @param b64str The base64 encoded string
	 * @returns An object containing fields extracted from the base64 string
	 */
	function extractErrorLink(b64str: string) {
		const match = /errorLink:\/\/([a-zA-Z0-9]+)/.exec(b64str);
		if (!match) {
			throw `Error link not found in ${b64str}`;
		}
		const actualB64String = match[1];
		const decodedString = atob(actualB64String);
		const nodeInfoParts = decodedString.split('+');
		return {
			nodeName: nodeInfoParts[0],
			nodeId: nodeInfoParts[1],
			graphName: nodeInfoParts[2],
			b64string: actualB64String
		};
	}

	/**
	 * Navigate to an erroring node given the error code (base64 string). This will open the appropriate graph if needed.
	 *
	 * @param b64str The error code.
	 *
	 * @returns A boolean whether this was successful.
	 */
	async function navigateToErroringNode(b64str: string): Promise<boolean> {
		let errorLinkInfo = { nodeName: '', nodeId: '', graphName: '', b64string: b64str };
		try {
			errorLinkInfo = extractErrorLink(b64str);
		} catch {
			try {
				errorLinkInfo = extractErrorLink('errorLink://' + b64str);
			} catch {
				promptStore.failedAlert('Failed to Find Erroring Node', 'Invalid code (base64) provided: "' + b64str + '"');
				return false;
			}
		}

		// First check the open tabs to see if any match the graph name + node ID
		const graphPath = fileStore.normalizePath(errorLinkInfo.graphName);
		let targetTabId: string | undefined | null = tabs.find(
			(t) =>
				t.contents instanceof Graph &&
				t.contents.findNode(errorLinkInfo.nodeId) &&
				((t.fileId && fileStore.getFilePath(t.fileId) === graphPath) || t.name === graphPath)
		)?.id;

		if (!targetTabId) {
			// Tab not open
			// Search for a file in the file system with the same path
			await fileStore.refreshFiles();
			const file = fileStore.findFileByPath(graphPath);
			if (file) {
				// Open the file in the editor
				targetTabId = await openFileInEditor(file.id);
			}
		}

		// Check the tab for correctness
		if (!targetTabId) {
			console.error(
				'Failed to Find Erroring node at graphPath: ',
				graphPath,
				' ... graphName:',
				errorLinkInfo.graphName,
				' ... nodeId:',
				errorLinkInfo.nodeId
			);
			let failedMsg = `Path "${graphPath}" does not exist.`;
			const regex = /^Untitled-\d+\.gx$/;
			if (regex.test(graphPath)) {
				failedMsg +=
					" Please make sure the graph that errored still exists. Since the graph has the name 'Untitled-#.gx', it is possible the graph was removed since this error first occured in the terminal pane.";
			}
			promptStore.failedAlert('Failed to Find Erroring Node', failedMsg);
			return false;
		}

		const targetTab = getTabById(targetTabId)!;
		if (!(targetTab.contents instanceof Graph)) {
			promptStore.failedAlert('Failed to Find Erroring Node', `File "${graphPath}" does not contain a valid graph.`);
			return false;
		}

		const graph = targetTab.contents;
		const node = graph.findNode(errorLinkInfo.nodeId);
		if (!node) {
			promptStore.failedAlert(
				'Failed to Find Erroring Node',
				`File "${graphPath}" does not contain a node with ID ${errorLinkInfo.nodeId}.`
			);
			return false;
		}

		setActiveTab(targetTabId);
		await nextTick();
		await new Promise((r) => setTimeout(r, 10));
		graph.ui.deselectAllNodes();
		graph.ui.selectNode(node);
		graph.ui.navigateUiToNodeLocation(node);
		return true;
	}

	/**
	 * Prompt the user to open files as tabs.
	 *
	 * @returns The IDs of the loaded tabs.
	 */
	async function promptOpenFiles(): Promise<Array<string>> {
		const input = document.createElement('input');
		input.type = 'file';
		input.multiple = true;

		// Create promise to get the files
		const filesPromise: Promise<Array<File>> = new Promise((resolve) => {
			input.onchange = () => resolve(input.files ? Array.from(input.files) : []);
		});

		// Trigger the file input
		input.click();

		// Wait for the files
		const files = await filesPromise;

		// Load each file
		const loadedTabs: Array<string> = [];
		for (const file of files) {
			try {
				// Get the file content
				const reader = new FileReader();
				reader.readAsText(file, 'UTF-8');

				const contents: string | ArrayBuffer | null = await new Promise((resolve, reject) => {
					reader.onload = () => resolve(reader.result);
					reader.onerror = () => reject(reader.error);
				});

				if (contents === null || typeof contents !== 'string') {
					throw `Unable to read file contents.`;
				}

				if (file.name.toLowerCase().endsWith(GRAPH_FILE_EXTENSION)) {
					// Load as graph
					const serializedGraph: SerializedGraph = YAML.parse(contents);
					const newTabId = await addGraphTabFromSerialized(file.name, null, serializedGraph);
					if (newTabId) {
						loadedTabs.push(newTabId);
					}
					continue;
				} else if (file.name.toLowerCase().endsWith(LOG_FILE_EXTENSION)) {
					terminalStore.importLogFile(file.name, contents);
					return [];
				}

				loadedTabs.push(addTab(file.name, null, contents));
			} catch (e) {
				alert(`Failed to load ${file.name}: ${e}`);
			}
		}
		return loadedTabs;
	}

	/**
	 * Open a file in the editor. If the file is already open, it will be made active.
	 *
	 * @param fileId The file ID.
	 *
	 * @returns The loaded tab ID if the operation was successful. `null` if the open failed.
	 */
	async function openFileInEditor(
		fileId: string,
		filepath?: string,
		isCurrentBranch?: boolean,
		otherBranchName?: string
	): Promise<string | null> {
		// Check if a tab is already open to the file
		const foundTab = tabs.find((t) => t.fileId === fileId);
		if (foundTab) {
			setActiveTab(foundTab.id);
			return foundTab.id;
		}

		const file = fileStore.findFileById(fileId);
		if (!file) {
			await promptStore.failedAlert('Unable To Open File', 'File does not exist on disk.');
			return null;
		}

		let isGraph = false;
		const filename_lc = file.name.toLowerCase();
		if (filename_lc.endsWith(GRAPH_FILE_EXTENSION)) {
			isGraph = true;
			fileStore.activeFileOperations.push('Opening Graph File');
		} else {
			fileStore.activeFileOperations.push('Opening File');
		}

		let isImage = false;
		const imageExtensions = ['jpeg', 'jpg', 'png', 'gif'];
		const thisExt = filename_lc.replace(/.*\./, '');
		if (imageExtensions.indexOf(thisExt) >= 0) {
			isImage = true;
		}

		try {
			const fileContents = await fileStore.getFileContents(file.id, isImage);
			if (fileContents === null) {
				return null;
			}

			if (isGraph) {
				try {
					return await addGraphTabFromSerialized(null, fileId, YAML.parse(fileContents));
				} catch (e) {
					if (e instanceof YAMLParseError && fileContents.includes('<<<<<<<')) {
						if (isResolvingMergeConflict.value && filepath && isCurrentBranch !== undefined && otherBranchName) {
							// Merge conflict exists. Show both branches in separate tabs
							const conflictPath = filepath;
							conflictsToResolve.value = await getMergeConflicts(otherBranchName, conflictPath);

							const currentBranchFilePath = 'Current_Branch_' + conflictPath;
							const incomingBranchFilePath = 'Incoming_Branch_' + conflictPath;

							const nodes = Object.keys(conflictsToResolve.value.changes_to_nodes);
							let currentBranchNodes = {};
							let incomingBranchNodes = {};

							// TODO this may need to be modified to handle conflicts caused by a deleted node
							// This looks for the node in each branch-- it may fail or cause unexpected behavior if the node isn't present
							nodes.forEach((node: string) => {
								if (!conflictsToResolve.value.changes_to_nodes[node].only_in_other_branch) {
									const currentBranchPair = {
										[node]: conflictsToResolve.value.changes_to_nodes[node].this_branch_yaml
									};
									currentBranchNodes = { ...currentBranchNodes, ...currentBranchPair };
								}
								if (!conflictsToResolve.value.changes_to_nodes[node].only_in_this_branch) {
									const incomingBranchPair = {
										[node]: conflictsToResolve.value.changes_to_nodes[node].other_branch_yaml
									};
									incomingBranchNodes = { ...incomingBranchNodes, ...incomingBranchPair };
								}
							});

							const inputs = Object.keys(conflictsToResolve.value.identified_conflicts.matching_graph_input_data);
							let currentBranchInputs = {};
							let incomingBranchInputs = {};
							inputs.forEach((input: string) => {
								if (!conflictsToResolve.value.changes_to_graph_inputs[input].only_on_other_branch) {
									const currentBranchPair = {
										[input]: conflictsToResolve.value.changes_to_graph_inputs[input].this_branch_yaml
									};
									currentBranchInputs = { ...currentBranchInputs, ...currentBranchPair };
								}
								if (!conflictsToResolve.value.changes_to_graph_inputs[input].only_on_this_branch) {
									const incomingBranchPair = {
										[input]: conflictsToResolve.value.changes_to_graph_inputs[input].other_branch_yaml
									};
									incomingBranchInputs = { ...incomingBranchInputs, ...incomingBranchPair };
								}
							});

							// Create the second branch yaml
							let currentBranchContents = '';
							let incomingBranchContents = '';

							if (isCurrentBranch) {
								currentBranchContents = await resolveMergeConflicts(
									otherBranchName,
									conflictPath,
									currentBranchInputs,
									currentBranchNodes,
									conflictsToResolve.value['identified_conflicts'],
									conflictsToResolve.value['current_branch_nodes_to_yaml']
								);
								return await addGraphTabFromSerialized(currentBranchFilePath, null, YAML.parse(currentBranchContents));
							} else {
								incomingBranchContents = await resolveMergeConflicts(
									otherBranchName,
									conflictPath,
									incomingBranchInputs,
									incomingBranchNodes,
									conflictsToResolve.value['identified_conflicts'],
									incomingBranchNodes
								);
								return await addGraphTabFromSerialized(
									incomingBranchFilePath,
									null,
									YAML.parse(incomingBranchContents)
								);
							}
						} else {
							// Merge conflict happened outside of the GraphEx UI
							await promptStore.failedAlert(
								'Failed to Get File',
								'The file contains a merge conflict. Resolution for this in the UI is not yet implemented in GraphEx. Please resolve manually by opening the file in a text editor and choosing the changes you which to keep.'
							);
							return null;
						}
					} else {
						throw e;
					}
				}
			}

			if (isImage) {
				let actualB64String = fileContents;
				if (fileContents.includes(']')) {
					const lastIndexOfBracket = fileContents.lastIndexOf(']');
					actualB64String = fileContents.slice(lastIndexOfBracket + 1).trim();
				}
				actualB64String = 'data:image/' + thisExt + ';base64,' + actualB64String;
				window.open(actualB64String, '_blank');
				return null;
			}

			// Not a graph file, nor an image
			// Just open the contents in the text editor
			return addTab(null, fileId, fileContents);
		} finally {
			fileStore.activeFileOperations.pop();
		}
	}

	/**
	 * Get the serialization for a tab's contents.
	 *
	 * @param id The ID of the tab.
	 *
	 * @returns The string representation of the contents of the tab.
	 */
	function getTabSerialContents(id: string): string {
		const tab = getTabById(id);
		if (!tab) {
			console.warn(`No tab exists for ID ${id}`);
			return '';
		}

		if (tab.contents instanceof Graph) {
			return JSON.stringify(tab.contents.serialize(), (key, value) => {
				if (key == 'ui') return undefined;
				return value;
			});
		}

		return tab.contents;
	}

	/**
	 * Check whether the given tab has changes that require saving.
	 *
	 * @param id The ID of the tab.
	 *
	 * @returns Whether the tab needs saving.
	 */
	function tabHasChanges(id: string): boolean {
		const tab = getTabById(id);
		if (!tab) {
			console.warn(`No tab exists for ID ${id}`);
			return false;
		}

		return tab.serialContentsAtLastSave != getTabSerialContents(id);
	}

	/**
	 * Save the contents of a tab to disk. If the file for the tab does not exist, it will be created.
	 *
	 * @param id The ID of the tab.
	 *
	 * @returns Whether the save was successful.
	 */
	async function saveTab(id: string): Promise<boolean> {
		const tab = getTabById(id);
		if (!tab) {
			console.warn(`No tab exists for ID ${id}`);
			return false;
		}

		if (tab.contents instanceof Graph && errorStore.graphHasErrors(tab.id)) {
			// Ask first before saving a graph with errors
			const value = await promptStore.show({
				title: 'Graph Contains Errors',
				additionalInfo: `The graph '${tab.name}' contains errors. Are you sure you want to save this graph?`,
				entries: [],
				buttons: [
					{
						text: 'Save With Errors',
						type: 'warning'
					},
					{
						text: 'Cancel',
						type: 'secondary'
					}
				]
			});

			if (!value || value.buttonName == 'Cancel') {
				return false;
			}
		}

		const filepath = tab.fileId ? fileStore.getFilePath(tab.fileId) || tab.name : tab.name;
		let overwrite = false;
		if (!tab.fileId && fileStore.findFileByPath(filepath)) {
			const value = await promptStore.show({
				title: 'File Already Exists',
				additionalInfo: `File '${filepath}' already exists on disk. Do you want to overwrite this file?`,
				entries: [],
				buttons: [
					{
						text: 'Overwrite',
						type: 'warning'
					},
					{
						text: 'Cancel',
						type: 'secondary'
					}
				]
			});

			if (!value || value.buttonName == 'Cancel') {
				return false;
			}

			overwrite = true;
		} else if (tab.fileId) {
			overwrite = true;
		}

		const contentToWrite = tab.contents instanceof Graph ? tab.contents.getSerializedGraphString() : tab.contents;
		const fileId = await fileStore.writeToDisk(filepath, contentToWrite, overwrite);
		if (!fileId) {
			return false;
		}

		tab.fileId = fileId;
		tab.serialContentsAtLastSave = getTabSerialContents(tab.id);
		return true;
	}

	/**
	 * Export the contents of a tab (i.e. download the file via the browser).
	 *
	 * @param id The ID of the tab.
	 */
	function exportTabContents(id: string) {
		const tab = getTabById(id);
		if (!tab) {
			console.warn(`No tab exists for ID ${id}`);
			return;
		}

		const contentToDownload = tab.contents instanceof Graph ? tab.contents.getSerializedGraphString() : tab.contents;

		// Download
		const file = new Blob([contentToDownload], { type: 'text/plain' });
		const a = document.createElement('a');
		const url = URL.createObjectURL(file);
		a.href = url;
		a.download = tab.name;
		document.body.appendChild(a);
		a.click();
		setTimeout(() => {
			document.body.removeChild(a);
			window.URL.revokeObjectURL(url);
		}, 10);
	}

	/**
	 * Watch relevant files for changes and reset file IDs / names as needed.
	 */
	const tabFileNames = computed(() => tabs.map((t) => (t.fileId ? fileStore.getFileName(t.fileId) || null : null)));
	watch(tabFileNames, () => {
		for (let i = 0; i < tabs.length; i++) {
			const fileName = tabFileNames.value[i];
			if (!fileName || !fileName.length) {
				tabs[i].fileId = null;
				continue;
			}

			tabs[i].name = fileName;
		}
	});

	/**
	 * Sends a request to the backend to compute resolution options for the file with a merge conflict.
	 * The user will then have to choose the yaml blocks corresponding to the changes they intend to keep from the conflict.
	 * @param otherBranchName The name of the other branch in which has a merge conflict
	 * @param pathToFileWithConflicts The path to the file containing a merge conflict
	 * @returns A python object (JSON from the request) with the following keys:
	 * "changes_to_nodes": dict_of_specific_changes_to_nodes,
				"changes_to_graph_inputs": dict_of_specific_changes_to_graph_inputs,
				"identified_conflicts": dict_of_node_ids_and_gi_names,
				"current_branch_nodes_to_yaml": current_branch_nodes_to_yaml,
		Please see the backend code in server.py / git_resolution.py for more details on the structure of the values for each key.
		Additionally, "identified_conflicts" and "current_branch_nodes_to_yaml" shouldn't require any modification and simply need to be returned to the backend on the next request
		(the request to resolve the conflict)
	 */
	async function getMergeConflicts(otherBranchName: string, pathToFileWithConflicts: string) {
		const response = await fetch('/api/git/mergeConflict', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				other_branch_name: otherBranchName,
				path: pathToFileWithConflicts
			})
		});

		if (response.status != 200) {
			throw `Failed to get merge conflict resolution options: ${await response.text()}`;
		}

		return await response.json();
	}

	/**
	 * Sends a request to the backend to resolve a merge conflict with the options provided by the user.
	 * @param otherBranchName The name of the other branch in which has a merge conflict
	 * @param pathToFileWithConflicts The path to the file containing a merge conflict
	 * @param chosenGraphInputs The backend expects a python dictionary like object with the names of the graph inputs as keys and the yaml blocks selected by the user as the values
	 * @param chosenNodes The backend expects a python dictionary like object with the IDs of the nodes as keys and the yaml blocks selected by the user as the values
	 * @param identifiedConflicts This should simply be the the key "identified_conflicts" that is returned by the function 'getMergeConflicts(...)' above
	 * @param currentBranchNodesToYaml This should simply be the the key "current_branch_nodes_to_yaml" that is returned by the function 'getMergeConflicts(...)' above
	 * @returns A YML string containing the new contents of the file. It should be parsable by this frontend using the YML parser. The backend will also overwrite the existing file with this same string.
	 */
	async function resolveMergeConflicts(
		otherBranchName: string,
		pathToFileWithConflicts: string,
		chosenGraphInputs: object,
		chosenNodes: object,
		identifiedConflicts: object,
		currentBranchNodesToYaml: object
	) {
		const response = await fetch('/api/git/resolveMergeConflict', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				other_branch_name: otherBranchName,
				path: pathToFileWithConflicts,
				chosen_inputs: chosenGraphInputs,
				chosen_nodes: chosenNodes,
				identified_conflicts: identifiedConflicts,
				current_branch_nodes_to_yaml: currentBranchNodesToYaml
			})
		});

		if (response.status != 201) {
			await promptStore.show({
				title: 'Error resolving merge conflicts',
				additionalInfo:
					'Please resolve manually by opening the file in a text editor and choosing the changes you wish to keep.',
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
			throw `Failed to resolve merge conflict and get resulting file: ${await response.text()}`;
		}

		return await response.text();
	}

	/**
	 * Attempts to get the names of the branches that are involved in a merge conflict.
	 * @returns If successful, a python dictionary like object containing two keys: "this_branch" and "other_branch"
	 */
	async function getMergeConflictBranches() {
		const response = await fetch('/api/git/mergeConflictBranches', {
			method: 'GET'
		});

		if (response.status != 200) {
			throw `Failed to get merge conflict branch names: ${await response.text()}`;
		}

		return await response.json();
	}

	async function gitAdd(filepath: string) {
		try {
			const response = await fetch('/api/git/add?path=' + filepath, { method: 'POST' });
			if (!response.ok) {
				throw await response.text();
			}
		} catch (e) {
			return e;
		}
	}
	async function gitAddAll() {
		try {
			const response = await fetch('/api/git/addAll', { method: 'POST' });
			if (!response.ok) {
				throw await response.text();
			}
		} catch (e) {
			return e;
		}
	}

	async function gitUnstage(filepath: string) {
		try {
			const response = await fetch('/api/git/unstage?path=' + filepath, { method: 'POST' });
			if (!response.ok) {
				throw await response.text();
			}
		} catch (e) {
			return e;
		}
	}

	function setIsResolvingMergeConflict(value: boolean) {
		isResolvingMergeConflict.value = value;
	}

	function setSelectedIssueNodeId(value: string) {
		selectedIssueNodeId.value = value;
	}

	function setChosenNodeConflicts(selectedYaml: object) {
		if (Object.keys(selectedYaml).length > 0) {
			// add
			chosenNodeConflicts.value = { ...chosenNodeConflicts.value, ...selectedYaml };
		} else {
			// clear
			chosenNodeConflicts.value = {};
		}
	}

	function setChosenInputConflicts(selectedYaml: object) {
		if (Object.keys(selectedYaml).length > 0) {
			// add
			chosenGraphInputConflicts.value = { ...chosenGraphInputConflicts.value, ...selectedYaml };
		} else {
			// clear
			chosenGraphInputConflicts.value = {};
		}
	}

	async function confirmFileResolution(otherBranchName: string, filePath: string) {
		const allConflicts = conflictsToResolve.value;
		const chosenNodes = chosenNodeConflicts.value;
		const chosenInputs = chosenGraphInputConflicts.value;

		try {
			const resolvedFile = await resolveMergeConflicts(
				otherBranchName,
				filePath,
				chosenInputs,
				chosenNodes,
				allConflicts.identified_conflicts,
				allConflicts.current_branch_nodes_to_yaml
			);
			// Update the file
			const updatedFilePath = await fileStore.formatGitFilepath(filePath);
			await fileStore.writeToDisk(updatedFilePath, resolvedFile, true);

			await gitAdd(filePath);
		} catch (e) {
			throw 'Failed to resolve merge conflict';
		}
	}

	async function gitPush(username: string, password: string) {
		const response = await fetch('/api/git/push', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				username: username,
				password: password
			})
		});

		if (response.status === 201) {
			await promptStore.show({
				title: 'Success',
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else {
			throw await response.text();
		}
		return response;
	}

	async function switchOrCreateBranch(branchName: string) {
		const response = await fetch('/api/git/branch?name=' + branchName, { method: 'POST' });

		if (response.status === 200) {
			fileStore.refreshFiles();
			await promptStore.show({
				title: `Successfully switched to branch ${branchName}`,
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else if (response.status === 201) {
			fileStore.refreshFiles();
			await promptStore.show({
				title: `Successfully created branch ${branchName}`,
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else {
			await promptStore.show({
				title: `Failed to create or switch to branch ${branchName}`,
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return response;
	}

	async function gitPull(username: string, password: string) {
		const response = await fetch('/api/git/pull', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				username: username,
				password: password
			})
		});
		if (response.status === 200) {
			await promptStore.show({
				title: 'Success',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else {
			await promptStore.show({
				title: 'Error pulling latest changes',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return response;
	}

	async function gitFetch(username: string, password: string, branch?: string) {
		const response = await fetch('/api/git/fetch', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				username: username,
				password: password,
				branch_name: branch ?? ''
			})
		});
		if (response.status === 200) {
			await promptStore.show({
				title: 'Success',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else {
			await promptStore.show({
				title: 'Error fetching latest changes',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return response;
	}

	async function gitCommit(msg: string, name: string, email: string) {
		const response = await fetch('/api/git/commit', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				msg: msg,
				author_name: name,
				author_email: email
			})
		});

		if (response.status === 201) {
			await promptStore.show({
				title: 'Success',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else {
			await promptStore.show({
				title: 'Failed To Commit Changes',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return response;
	}

	async function gitMerge(branch: string) {
		const response = await fetch('/api/git/merge', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				other_branch_name: branch
			})
		});
		const res = response.clone();
		const status = res.status;
		if (status === 200) {
			await promptStore.show({
				title: 'Success',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else if (status !== 201) {
			await promptStore.show({
				title: 'Error merging changes',
				additionalInfo:
					'Please resolve manually by opening the file in a text editor and choosing the changes you wish to keep.',
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return await res.json();
	}

	async function cancelGitMerge() {
		const response = await fetch('/api/git/cancelMerge', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});

		if (response.status === 200) {
			await promptStore.show({
				title: '',
				additionalInfo: 'Successfully cancelled merge',
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		} else {
			await promptStore.show({
				title: 'Error',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return response;
	}

	async function gitDiff(branchName: string, filepath: string) {
		const response = await fetch('/api/git/diff', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				other_branch_name: branchName,
				path: filepath
			})
		});
		if (response.status !== 200) {
			await promptStore.show({
				title: 'Error getting diff',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return await response.json();
	}

	function setGitUsername(username: string) {
		gitUsername.value = username;
	}

	function setGitPassword(password: string) {
		gitPassword.value = password;
	}

	return {
		tabs,
		activeTabId,
		activeTab,
		activeGraphTab,
		activeTextTab,
		copiedNodes,
		isResolvingMergeConflict,
		selectedIssueNodeId,
		conflictsToResolve,
		chosenNodeConflicts,
		chosenGraphInputConflicts,
		gitUsername,
		gitPassword,
		setGraphComponent,
		getGraphComponent,
		setTextComponent,
		getTextComponent,
		getTabById,
		setActiveTab,
		reorderTabs,
		addTab,
		newDefaultGraphTab,
		storeCopiedNodes,
		addGraphTabFromSerialized,
		renameTab,
		removeTab,
		removeMergeConflictTabs,
		extractErrorLink,
		navigateToErroringNode,
		promptOpenFiles,
		openFileInEditor,
		getTabSerialContents,
		tabHasChanges,
		saveTab,
		exportTabContents,
		replaceNodeWithCommentSingular,
		replaceCommentWithNodeSingular,
		replaceMultipleNodesWithComments,
		replaceMultipleCommentsWithNodes,
		setIsResolvingMergeConflict,
		setSelectedIssueNodeId,
		setChosenNodeConflicts,
		setChosenInputConflicts,
		confirmFileResolution,
		gitAdd,
		gitAddAll,
		gitUnstage,
		gitCommit,
		gitPush,
		switchOrCreateBranch,
		gitPull,
		gitFetch,
		gitMerge,
		cancelGitMerge,
		gitDiff,
		setGitUsername,
		setGitPassword
	};
});
