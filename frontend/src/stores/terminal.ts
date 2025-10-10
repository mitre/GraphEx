import type { Graph, GraphInputMetadata } from '@/graph/graph';
import { usePromptStore } from '@/stores';
import { defineStore } from 'pinia';
import { io, type Socket } from 'socket.io-client';
import { v4 as uuidv4 } from 'uuid';
import { computed, reactive, ref } from 'vue';

/** Data about a particular terminal message. */
export interface MessageData {
	msg: string;
	type: 'debug' | 'info' | 'warning' | 'error' | 'critical' | 'control' | 'image' | 'notice';
}

export interface InputValueMetadata {
	value?: any;
	childValues: { [key: string]: InputValueMetadata };
	fromSecret?: string;
	fromConfig?: boolean;
	datatype: string;
	presetValue?: any;
	metadata?: GraphInputMetadata;
}

/**
 * Backend message for starting a graph.
 */
export interface GraphStartMessage {
	/** Unique ID for this execution. */
	id: string;

	/** The name of this execution. This is typically the graph name. */
	name: string;

	/** The path to the graph on disk for this execution, if available. This refers to the path of the graph **at the time this execution was started**. This need not reflect the updated path to the graph after the execution has started. */
	filepath: string | null;
}

type StringIntTuple = [string, number];
type DictIntTuple = [Record<'branch_names', string[]>, number];

type gitStatusHeartbeatType = [string, number];

type gitBranchesHeartbeatType = DictIntTuple | StringIntTuple;

/**
 * Deep merge function for inputValues.
 * @param targetInputValues The target inputValues object to merge into.
 * @param sourceInputValues The source inputValues object to merge from.
 * @returns The merged inputValues object.
 */
export function deepMergeInputValues(
	targetInputValues: { [inputName: string]: InputValueMetadata },
	sourceInputValues: { [inputName: string]: InputValueMetadata }
): { [inputName: string]: InputValueMetadata } {
	const mergedInputValues: { [inputName: string]: InputValueMetadata } = {};

	// Copy target inputValues
	for (const key in targetInputValues) {
		if (Object.prototype.hasOwnProperty.call(targetInputValues, key)) {
			mergedInputValues[key] = targetInputValues[key];
		}
	}

	// Merge or add source inputValues
	for (const key in sourceInputValues) {
		if (Object.prototype.hasOwnProperty.call(sourceInputValues, key)) {
			mergedInputValues[key] = targetInputValues[key]
				? deepMergeInputValueMetadata(targetInputValues[key], sourceInputValues[key])
				: sourceInputValues[key];
		}
	}

	return mergedInputValues;
}

/**
 * Deep merge function for InputValueMetadata without using spread operator.
 * @param target The target InputValueMetadata object to merge into.
 * @param source The source InputValueMetadata object to merge from.
 * @returns The merged InputValueMetadata object.
 */
function deepMergeInputValueMetadata(target: InputValueMetadata, source: InputValueMetadata): InputValueMetadata {
	const result: InputValueMetadata = {
		value: source.value !== undefined ? source.value : target.value,
		childValues: deepMergeInputValues(target.childValues, source.childValues),
		fromSecret: source.fromSecret !== undefined ? source.fromSecret : target.fromSecret,
		fromConfig: source.fromConfig !== undefined ? source.fromConfig : target.fromConfig,
		datatype: source.datatype || target.datatype
	};

	return result;
}

/**
 * Type that contains all information related to an executing graph (including the websocket instance)
 */
export interface GraphExecutionContext {
	/** Unique ID for this execution. Executions loaded from a log file will have this ID prefixed with `log-`. */
	id: string;

	/** The name of this execution. This is typically the graph name. */
	name: string;

	/** The path to the graph on disk for this execution, if available. This refers to the path of the graph **at the time this execution was started**. This need not reflect the updated path to the graph after the execution has started. */
	filepath: string | null;

	/** The websocket for communicating with the server for this execution. */
	socket: Socket;

	/** The saved output for this execution. */
	logs: Array<MessageData>;

	/** Number of error / critical logs. */
	errorCount: number;

	/** Number of warning logs */
	warningCount: number;

	/** Whether the websocket is connected. If the socket is connected, it may be assumed that the execution is still running. */
	connected: boolean;

	/** Whether the execution has completed (with or without error). */
	completed: boolean;

	/** Whether this execution was triggered locally. If `false`, this execution was discovered from the server. */
	isLocal: boolean;
}

export interface GraphRunSettings {
	/** The input values to use for running the graph. */
	inputValues: { [inputName: string]: InputValueMetadata };

	/** Whether to use verbose mode when running the graph (i.e. debug mode). */
	verbose: boolean;

	/** Whether to show the graph inputs at the top of the terminal */
	showInputs: boolean;
}

export interface heartbeatData {
	venv: string;
	branch: string;
	currentTime: string;
	gitBranches: gitBranchesHeartbeatType;
	gitStatus: gitStatusHeartbeatType;
}

// The location of the SocketIO server
const URL = '/';

export const useTerminalStore = defineStore('terminal', () => {
	const promptStore = usePromptStore();

	/** List of available graph executions. */
	const executions = reactive<Array<GraphExecutionContext>>([]);

	/** Whether or not the terminal UI is open */
	const terminalOpen = ref<boolean>(false);

	/** The context ID of the currently open tab. */
	const selectedTerminalTabId = ref<string>();

	/** Graph to prompt for execution. Setting this value will open the "run prompt" in preparation for execution of this graph. */
	const graphToPrompt = ref<{ graph: Graph; name: string; filepath: string | null } | null>(null);

	/** Saved run settings for previously run graphs. This maps the filepath to the saved settings. */
	const savedRunSettings = reactive<{ [filepath: string]: GraphRunSettings }>({});

	/** Active virtual environment */
	const activeVenv = ref<string>();

	/** Active git branch. */
	const activeGitBranch = ref<string>();

	/** Monitors changes on the current git branch. */
	const gitStatus = ref<gitStatusHeartbeatType>();

	/** Active git branch. */
	const gitBranches = ref<gitBranchesHeartbeatType>();

	/** Current Time */
	const currentTime = ref<string>();

	/**
	 * The main websocket. This is used for starting graphs and listening for graphs that others have started.
	 */
	const mainSocket = io(URL, {
		autoConnect: true,
		path: '/api/socket.io',
		reconnectionAttempts: 1000,
		closeOnBeforeunload: false
	});

	/** Boolean to track the connection to the main socket */
	const mainSocketConnected = ref<boolean>(false);

	/** Boolean to track the error status of the main socket */
	const mainSocketError = ref<boolean>(false);

	/** Returns whether the main socket has an open and error free connection to the server */
	const mainSocketOk = computed(() => {
		if (mainSocketError.value) {
			return false;
		}
		return mainSocketConnected.value;
	});

	/** Callbacks for the main socket */
	mainSocket.on('connect', () => {
		mainSocketConnected.value = true;
		mainSocketError.value = false;
		mainSocket.emit('beginHeartbeat', 1);
	});

	mainSocket.on('disconnect', () => {
		mainSocketConnected.value = false;
	});

	mainSocket.on('connect_error', () => {
		mainSocketError.value = true;
	});

	mainSocket.on('reconnect_error', () => {
		mainSocketError.value = true;
	});

	mainSocket.on('reconnect_failed', () => {
		mainSocketError.value = true;
	});

	mainSocket.on('reconnect', () => {
		mainSocketError.value = false;
	});

	mainSocket.on('graphStart', (data: GraphStartMessage) => {
		const context = createExecutionContext(data.id, data.name, data.filepath, false); // isLocal is 'false' because if the context doesn't exist at this point, it was discovered
		context.completed = false;
		if (!context.connected) {
			context.socket.connect();
		}
	});

	mainSocket.on('heartbeatInfo', (data: heartbeatData) => {
		activeGitBranch.value = data['branch'];
		activeVenv.value = data['venv'];
		currentTime.value = data['currentTime'];

		// Git info
		gitStatus.value = data['gitStatus'];
		gitBranches.value = data['gitBranches'];
	});

	/**
	 * Get an execution context by ID.
	 *
	 * @param contextId The context ID.
	 *
	 * @returns The execution context, or `null` if the context does not exist.
	 */
	function getExecutionContextById(contextId: string): GraphExecutionContext | null {
		return (executions.find((e) => e.id === contextId) as GraphExecutionContext | undefined) || null;
	}

	/** Opens the UI if closed / closes the UI if open. */
	function toggleTerminalOpen() {
		terminalOpen.value = !terminalOpen.value;
	}

	/**
	 * Sets the UI to be open or closed
	 *
	 * @param open When true: sets the UI to open. When false: sets the UI to closed.
	 */
	function setTerminalOpen(open: boolean) {
		terminalOpen.value = open;
	}

	/**
	 * Create a new execution context. If an execution context already exists with the given ID, no new context is created and the old context is simply returned unchanged.
	 *
	 * @param id The ID for this execution context.
	 * @param name The name of this execution context (typically the graph name).
	 * @param filepath The filepath for the graph in this execution, if available.
	 * @param isLocal Whether this execution was triggered locally.
	 *
	 * @returns The created execution context.
	 */
	function createExecutionContext(
		id: string,
		name: string,
		filepath: string | null,
		isLocal: boolean
	): GraphExecutionContext {
		const existingContext = getExecutionContextById(id);
		if (existingContext) {
			return existingContext;
		}

		/** The websocket object instance for this graphId */
		const websocket = io(URL, { autoConnect: false, path: '/api/socket.io', closeOnBeforeunload: false });

		let newId = id;
		if (!id) newId = uuidv4();

		// Initialize metadata and assign all values
		executions.push({
			id: newId,
			name: name,
			filepath: filepath,
			socket: websocket,
			logs: [],
			errorCount: 0,
			warningCount: 0,
			connected: false,
			completed: false,
			isLocal: isLocal
		});

		// We need to grab the proxy object after we add it because
		// otherwise the subsequent updates made to the context in the
		// `websocket.on(...)` callbacks will not be reactive
		// Assigning the original object to a variable *will not* work.
		const newContext = getExecutionContextById(newId)!;

		/**
		 * **************
		 * Assign callbacks for the websocket
		 * These are invoked when certain events happen
		 * **************
		 */
		// 'connect' is invoked when a websocket connects.
		// Typically this is via 'websocket.connect()' on the client side or
		//    after websocket object creation if connect is specified in the constructor.
		websocket.on('connect', () => {
			newContext.connected = true;

			// Let the user know that we established connection to the backend
			newContext.logs.push({ msg: 'Connection opened.', type: 'control' });

			// Begin tracking the graph output
			websocket.emit('graphOutput', { id: newContext.id });
		});

		// 'disconnect' is invoked when a websocket disconnects.
		// Typically this is via our custom event 'graphComplete' (see farther down)
		// It could also be invoked if the server disconnects.
		// You shouldn't expect that in this implementation unless the server encounters an issue.
		websocket.on('disconnect', () => {
			newContext.logs.push({ msg: 'Connection closed.', type: 'control' });
			newContext.connected = false;
		});

		// 'graphOutput' is invoked when the backend emits an event with this name.
		// The callback here handles where the output should be written to in the frontend.
		websocket.on('graphOutput', (data: MessageData) => {
			newContext.logs.push(data);
			if (data.type === 'error' || data.type === 'critical') {
				newContext.errorCount += 1;
			}
			if (data.type === 'warning') {
				newContext.warningCount += 1;
			}
		});

		// 'graphComplete' is invoked when the backend emits an event with this name.
		// This event is the server informing us that it will send us no further data via the 'graphOutput' event.
		// This event is (and should be) fired regardless of the exit code of ended process.
		// Here is the only place that 'disconnect' occurs for a specific graphId in the entire application.
		websocket.on('graphComplete', () => {
			newContext.completed = true;
			websocket.disconnect();
		});

		return newContext;
	}

	/**
	 * Prepare a graph for execution. This will set the internal state in preparation for executing the given graph.
	 *
	 * This function should be used over `runGraph` whenever values should be specified by the user. `runGraph` will later be called once
	 * the prompt receives necessary values.
	 *
	 * @param graph The graph to execute.
	 * @param name The name to give this execution context.
	 * @param filepath The path to the file for this execution, if it exists.
	 */
	async function promptGraphExecution(graph: Graph, name: string, filepath: string | null) {
		if (!graph.canExecute()) {
			await promptStore.show({
				title: `Unable to Run Graph '${filepath || name}'`,
				additionalInfo: 'This graph has a non-primitive input and cannot be directly executed.',
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
			return;
		}

		graphToPrompt.value = { graph: graph, name: name, filepath: filepath };
	}

	/**
	 * Cancel the current graph execution prompt, if any.
	 */
	async function cancelGraphPrompt() {
		graphToPrompt.value = null;
	}

	/**
	 * Runs/Executes the provided graph. Will handle the creation of the websocket and metadata if required.
	 * Will open the terminal UI and handle the selection of terminal tabs.
	 *
	 * @param graph The graph to execute.
	 * @param name The name of the graph to execute.
	 * @param filepath The filepath to the graph on disk, if it exists.
	 * @param settings The run settings for this graph.
	 */
	async function runGraph(graph: Graph, name: string, filepath: string | null, settings: GraphRunSettings) {
		if (!graph.canExecute()) {
			await promptStore.show({
				title: `Unable to Run Graph ${name}`,
				additionalInfo: 'This graph has a non-primitive input and cannot be directly executed.',
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});

			return;
		}

		// Create a new execution context
		const context = createExecutionContext(uuidv4(), name, filepath, true);

		// Force the UI to open to this context's tab
		selectedTerminalTabId.value = context.id;
		terminalOpen.value = true;

		// Start the graph
		// This will connect the graph socket when the server emits its 'graphStart' event
		mainSocket.emit('startGraph', {
			id: context.id,
			name: context.name,
			filepath: context.filepath,
			graph: graph.getSerializedGraphString(),
			values: settings.inputValues,
			debug: settings.verbose,
			showInputs: settings.showInputs
		});
	}

	/**
	 * Emits a request to the backend to stop executing a graph with the given ID. This is a graceful stop (SIGINT) that may or may not actually end the running graph.
	 *
	 * Use killExecutingGraph instead to forcefully kill a running graph.
	 *
	 * @param contextId The ID of the context to stop the execution of.
	 */
	async function stopExecutingGraph(contextId: string) {
		mainSocket.emit('stopGraph', { id: contextId });
	}

	/**
	 * Emits a request to the backend to kill an executing graph with the given ID. This is a forceful operation that will terminate the underlying graph process.
	 *
	 * @param contextId The ID of the context to stop the execution of.
	 */
	async function killExecutingGraph(contextId: string) {
		mainSocket.emit('killGraph', { id: contextId });
	}

	/**
	 * Sets the currently selected terminal tab.
	 * @param contextId The ID of the context to selected.
	 */
	function setSelectedTerminalTab(contextId: string) {
		selectedTerminalTabId.value = contextId;
	}

	/**
	 * Clears all output from the terminal for the given execution context.
	 * This cannot be undone. New output will continue to stream in.
	 *
	 * @param contextId The ID of the context to clear the output from.
	 */
	function clearOutput(contextId: string) {
		const context = getExecutionContextById(contextId);
		if (context) {
			context.logs = [];
			context.errorCount = 0;
			context.warningCount = 0;
		}
	}

	/**
	 * Removes an execution context. This is equivalent to 'closing' the tab.
	 *
	 * Warning: **Does not** kill the executing graph. Call 'killExecutingGraph' first.
	 *
	 * @param contextId The ID of the context to remove.
	 */
	function removeContext(contextId: string) {
		const index = executions.findIndex((e) => e.id === contextId);

		if (index < 0) {
			return false;
		}

		if (executions.length == 1) {
			// If no more contexts will exist after removing this one
			selectedTerminalTabId.value = undefined;
			terminalOpen.value = false;
			executions.splice(0, 1);
			return;
		}

		const context = executions[index];
		if (context.id === selectedTerminalTabId.value && index == 0) {
			// This tab was selected and it's the first, select the next
			setSelectedTerminalTab(executions[1].id);
		} else if (context.id === selectedTerminalTabId.value) {
			// This tab was selected and it's not the first, select the previous
			setSelectedTerminalTab(executions[index - 1].id);
		}

		executions.splice(index, 1);
	}

	/**
	 * A function that queries the backend for all graphs that are currently running.
	 * For each graph found: creates a websocket connection.
	 * This function is meant to be called once when Vue mounts (frontend initialized).
	 */
	async function discoverGraphs() {
		const response = await fetch('/api/runningGraphs', { method: 'GET' });
		if (!response.ok) {
			console.error('Response not ok for getRunningGraphs');
			console.error(response);
			try {
				const errorText = await response.text();
				console.error(errorText);
			} catch (e) {
				console.error('No text response on what the error is.', e);
			}
			return;
		}

		const data: Array<{ id: string; name: string; filepath: string | null }> = await response.json();
		for (const item of data) {
			const context = createExecutionContext(item.id, item.name, item.filepath, false);
			if (!context.connected) {
				context.socket.connect();
			}

			if (executions.length === 1) {
				// We just added the first execution, open the terminal UI
				setSelectedTerminalTab(context.id);
				terminalOpen.value = true;
			}
		}
	}

	/**
	 * Close all open sockets.
	 * This is meant for cleanup only (e.g. Vue unMount)
	 */
	function closeAllSockets() {
		for (const context of executions) {
			context.socket.disconnect();
		}
		mainSocket.disconnect();
	}

	/**
	 * Loads a log file into the terminal as 'dummy data'. Fetches the file data from the provided filepath.
	 *
	 * @param filename The name of the log file to open
	 * @param filepath The path to the log file to open
	 */
	async function openLogFile(filename: string, filepath: string) {
		try {
			const response = await fetch('/api/log?path=' + filepath, { method: 'GET' });
			if (!response.ok) {
				throw await response.text();
			}

			const jsonArray: MessageData[] = await response.json();
			const id = 'log-' + uuidv4();
			executions.push({
				id: id,
				name: filename,
				filepath: filepath,
				socket: io(URL, { autoConnect: false }),
				logs: jsonArray,
				errorCount: jsonArray.reduce(
					(prev, msg) => (msg.type === 'error' || msg.type === 'critical' ? prev + 1 : prev),
					0
				),
				warningCount: jsonArray.reduce((prev, msg) => (msg.type === 'warning' ? prev + 1 : prev), 0),
				connected: false,
				completed: true,
				isLocal: true
			});

			// Force the UI to open to this context's tab
			selectedTerminalTabId.value = id;
			terminalOpen.value = true;
		} catch (e) {
			promptStore.failedAlert(`Failed to Open Log ${filepath}`, String(e));
		}
	}

		/**
	 * Loads a log file into the terminal as 'dummy data'. Uses the provided json string.
	 *
	 * @param filename The name of the log file to open
	 * @param jsonString The JSON string data to import to a terminal tab
	 */
		async function importLogFile(filename: string, jsonString: string) {
			try {
				// console.log(jsonString);
				const jsonArray: MessageData[] = JSON.parse(jsonString);
				const id = 'log-' + uuidv4();
				executions.push({
					id: id,
					name: filename,
					filepath: filename,
					socket: io(URL, { autoConnect: false }),
					logs: jsonArray,
					errorCount: jsonArray.reduce(
						(prev, msg) => (msg.type === 'error' || msg.type === 'critical' ? prev + 1 : prev),
						0
					),
					warningCount: jsonArray.reduce(
						(prev, msg) => (msg.type === 'warning' ? prev + 1 : prev),
						0
					),
					connected: false,
					completed: true,
					isLocal: true
				});
	
				// Force the UI to open to this context's tab
				selectedTerminalTabId.value = id;
				terminalOpen.value = true;
			} catch (e) {
				promptStore.failedAlert(`Failed to Import Log ${filename}`, String(e));
			}
		}

	/**
	 * Reorder tabs such that the first provided tab is moved after the second provided tab.
	 *
	 * @param contextId1 The context ID of the tab to move.
	 * @param contextId2 The context ID of the tab to move the tab after.
	 */
	function reorderTabs(contextId1: string, contextId2: string) {
		const index = executions.findIndex((e) => e.id === contextId1);
		if (index <= -1) return;

		const newIndex = executions.findIndex((e) => e.id === contextId2);
		if (newIndex <= -1) return;

		executions.splice(newIndex, 0, ...executions.splice(index, 1));
	}

	async function fetchGraphInputByNames(names: string[], path: string, includeWildcard?: boolean) {
		const response = await fetch('/api/configGraphInputValues', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				names: names,
				path: path,
				includeWildcard: includeWildcard || false
			})
		});

		if (response.status != 200) {
			await promptStore.show({
				title: 'Failed To Get Configuration File Values',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return await response.json();
	}

	/**
	 * Gets the config file values for graph inputs of the given graph from the backend
	 * @param graph the graph to retrieve config file values for
	 * @param path the path to the file on the filesystem
	 * @returns a JSON object containing the response from the backend
	 */
	async function fetchGraphInputData(graph: Graph, path: string, includeWildcard?: boolean) {
		const response = await fetch('/api/configGraphInputValues', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				names: graph.inputMetadata.map((metadata) => metadata.name),
				path: path,
				includeWildcard: includeWildcard || false
			})
		});

		if (response.status != 200) {
			await promptStore.show({
				title: 'Failed To Get Configuration File Values',
				additionalInfo: await response.text(),
				entries: [],
				buttons: [{ text: 'OK', type: 'primary' }]
			});
		}
		return await response.json();
	}

	return {
		executions,
		terminalOpen,
		selectedTerminalTabId,
		graphToPrompt,
		savedRunSettings,
		mainSocketConnected,
		mainSocketError,
		mainSocketOk,
		activeGitBranch,
		activeVenv,
		currentTime,
		gitBranches,
		gitStatus,
		getExecutionContextById,
		toggleTerminalOpen,
		setTerminalOpen,
		promptGraphExecution,
		cancelGraphPrompt,
		runGraph,
		stopExecutingGraph,
		killExecutingGraph,
		setSelectedTerminalTab,
		clearOutput,
		removeContext,
		discoverGraphs,
		closeAllSockets,
		openLogFile,
		reorderTabs,
		fetchGraphInputData,
		deepMergeInputValues,
		fetchGraphInputByNames,
		importLogFile
	};
});
