import type { NodeStateObject } from '@/graph';
import type { Graph } from '@/graph/graph';
import { isDeepEqual } from '@/graph/utils';
import { nextTick } from 'vue';

const MAX_HISTORY_LENGTH = 256;

/** The maximum time (in milliseconds) that adjacent events can be apart and still be grouped together. */
const NEW_GROUP_DELAY = 500;

/** Object for information about how node has changed in the graph. */
interface NodeChangeObject {
	lastState?: NodeStateObject;
	newState?: NodeStateObject;
}

/** A set of history objects, representing one or more operations that occurred at the same time and should be treated as a single historical event. */
type HistoryBlock = Array<NodeChangeObject>;

/**
 * Class for managing the history of a graph.
 */
class GraphHistory {
	/** The graph that this history belongs to. */
	graph: Graph;

	/** Whether this is actively restoring the history of a graph. This is used to prevent multiple operations from occuring at once. */
	isRestoringHistory: boolean;

	/** The timeout ID for buffering updates. */
	updateTimeout?: number;

	/** Backward (undo) history in this graph. The last index will be the most recent operation. */
	back: Array<HistoryBlock>;

	/** Forward (redo) history in this graph. The last index will be the most recently "undone" operation. */
	forward: Array<HistoryBlock>;

	/** The last tracked state of the graph. This is used to diff against the current state to obtain all changes made. */
	lastState: Array<NodeStateObject>;

	constructor(parentGraph: Graph) {
		this.graph = parentGraph;
		this.back = [];
		this.forward = [];
		this.isRestoringHistory = false;
		this.updateTimeout = undefined;
		this.lastState = this.getCurrentGraphState();
		this.graph.addOnNodesChangedCallback(async () => await this.historyHandlerCallback());
	}

	async historyHandlerCallback() {
		clearTimeout(this.updateTimeout);
		this.updateTimeout = setTimeout(() => {
			this.updateTimeout = undefined;
			this.commit();
		}, NEW_GROUP_DELAY);
	}

	/**
	 * Get the current state of the graph.
	 *
	 * @returns The current graph state as a list of node states.
	 */
	getCurrentGraphState(): Array<NodeStateObject> {
		const state: Array<NodeStateObject> = [];
		for (const node of this.graph.getNodes()) {
			const outputConnections: Array<string> = [];
			for (const outputSocket of node.outputSockets) {
				for (const connection of outputSocket.connections) {
					outputConnections.push(`${outputSocket.metadata.name}->${connection.node.id}::${connection.metadata.name}`);
				}
			}

			state.push({
				serialized: node.serialize(),
				metadata: JSON.parse(JSON.stringify(node.metadata)),
				outputConnections: outputConnections
			});
		}
		return state;
	}

	/**
	 * Whether this graph has any undo (previous) history.
	 *
	 * @returns A boolean whether this graph has any 'undo' history.
	 */
	hasUndoHistory(): boolean {
		return this.back.length > 0;
	}

	/**
	 * Whether this graph has any redo (future) history.
	 *
	 * @returns A boolean whether this graph has an 'redo' history.
	 */
	hasRedoHistory(): boolean {
		return this.forward.length > 0;
	}

	/**
	 * Undo the last operation.
	 */
	async undo() {
		if (this.isRestoringHistory) return;
		this.isRestoringHistory = true;

		this.commit();
		const last = this.back.pop();
		if (!last) {
			this.isRestoringHistory = false;
			return;
		}

		// Sort the changes
		const nodesToAdd: Array<NodeStateObject> = [];
		const nodesToDelete: Array<NodeStateObject> = [];
		const nodesToUpdate: Array<NodeStateObject> = [];
		for (const obj of last) {
			if (obj.lastState && !obj.newState) {
				// Add the node
				nodesToAdd.push(obj.lastState);
				continue;
			}

			if (!obj.lastState && obj.newState) {
				// Delete the node
				nodesToDelete.push(obj.newState);
				continue;
			}

			if (obj.lastState && obj.newState) {
				// Update the node
				nodesToUpdate.push(obj.lastState);
			}
		}

		await this.mergeState(nodesToAdd, nodesToDelete, nodesToUpdate);

		// Move this block to the redo history
		this.forward.push(last);

		// Track the history from this new state
		this.track();

		this.isRestoringHistory = false;
	}

	/**
	 * Redo the last undone operation.
	 */
	async redo() {
		if (this.isRestoringHistory) return;
		this.isRestoringHistory = true;

		this.commit();
		const last = this.forward.pop();
		if (!last) {
			this.isRestoringHistory = false;
			return;
		}

		// Sort the changes
		const nodesToAdd: Array<NodeStateObject> = [];
		const nodesToDelete: Array<NodeStateObject> = [];
		const nodesToUpdate: Array<NodeStateObject> = [];
		for (const obj of last) {
			if (!obj.lastState && obj.newState) {
				// Re-add the node
				nodesToAdd.push(obj.newState);
				continue;
			}

			if (obj.lastState && !obj.newState) {
				// Re-delete the node
				nodesToDelete.push(obj.lastState);
				continue;
			}

			if (obj.lastState && obj.newState) {
				// Update the node
				nodesToUpdate.push(obj.newState);
			}
		}

		await this.mergeState(nodesToAdd, nodesToDelete, nodesToUpdate);

		// Move this block to the undo history
		this.back.push(last);

		// Track the history from this new state
		this.track();

		this.isRestoringHistory = false;
	}

	/**
	 * Merge the desired state / changes into the graph. This will update the graph according to the provided changes.
	 *
	 * @param nodesToAdd List of node states to add to the graph.
	 * @param nodesToDelete List of node states to delete from the graph.
	 * @param nodesToUpdate List of node states to update within the graph (i.e. node already exists but some aspect of the node has changed).
	 */
	async mergeState(
		nodesToAdd: Array<NodeStateObject>,
		nodesToDelete: Array<NodeStateObject>,
		nodesToUpdate: Array<NodeStateObject>
	) {
		// Delete nodes
		// Also delete the 'updated' nodes (the most straightforward way to update is to just delete the old nodes and replace it with the new ones)
		this.graph.deleteNodes([...nodesToDelete, ...nodesToUpdate].map((n) => n.serialized.id));
		await nextTick();

		// Add nodes
		this.graph.addNodeStates([...nodesToAdd, ...nodesToUpdate], { copyId: true, connect: 'all' });
	}

	/**
	 * Set the history to begin tracking from the current graph state. If there are any uncommitted changes made, they will be lost.
	 *
	 * This effectively updates the "last known state" of the history to the current graph state, discarding the previous tracked state.
	 */
	track() {
		this.lastState = this.getCurrentGraphState();
	}

	/**
	 * Completely reset the history for this graph.
	 */
	reset() {
		this.back = [];
		this.forward = [];
		this.track();
	}

	/**
	 * Commit all changes made between the current state and the last known state to the history.
	 *
	 * This will make the current state of the graph the "last known state" for future calls to this function.
	 */
	commit() {
		clearTimeout(this.updateTimeout);
		this.updateTimeout = undefined;
		const currentState = this.getCurrentGraphState();

		// Diff the graph states to get all differences
		const block: HistoryBlock = [];
		for (const prevStateObj of this.lastState) {
			const currentStateObj = currentState.find((s) => s.serialized.id == prevStateObj.serialized.id);
			if (!currentStateObj) {
				// Tracked node no longer exists (was deleted)
				const historyObj: NodeChangeObject = {
					lastState: prevStateObj,
					newState: undefined
				};

				block.push(historyObj);
				continue;
			}

			if (!isDeepEqual(prevStateObj, currentStateObj)) {
				// Nodes differ
				// Add to the history block
				const historyObj: NodeChangeObject = {
					lastState: prevStateObj,
					newState: currentStateObj
				};

				block.push(historyObj);
			}
		}

		for (const currentStateObj of currentState) {
			const prevStateObj = this.lastState.find((s) => s.serialized.id == currentStateObj.serialized.id);
			if (!prevStateObj) {
				// Node was added
				const historyObj: NodeChangeObject = {
					lastState: undefined,
					newState: currentStateObj
				};

				block.push(historyObj);
				continue;
			}
		}

		if (block.length) {
			this.back.push(block);
			this.forward = [];

			if (this.back.length > MAX_HISTORY_LENGTH) {
				// History too long
				// Remove the oldest (beginning of array)
				this.back.splice(0, MAX_HISTORY_LENGTH - this.back.length);
			}
		}

		this.lastState = currentState;
	}
}

export { GraphHistory };
