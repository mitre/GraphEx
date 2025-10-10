import {
	GraphEditorUI,
	NodeTypes,
	type CompositeGraphInputMetadata,
	type DataTypeMetadata,
	type GraphInputMetadata,
	type GraphOutputMetadata,
	type NodeMetadata
} from '@/graph';
import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';

export const useMetadataStore = defineStore('metadata', () => {
	/** Node metadata. */
	const nodes = ref<Array<NodeMetadata>>([]);

	/** Data type metadata. */
	const dataTypes = ref<Array<DataTypeMetadata>>([]);

	/**Composite input metadata */
	const compositeInputs = ref<Array<CompositeGraphInputMetadata>>([]);

	/** Copied metadata about a graph's inputs. */
	const copiedInputMetadata = reactive<Array<GraphInputMetadata>>([]);

	/** Copied metadata about a graph's outputs. */
	const copiedOutputMetadata = reactive<Array<GraphOutputMetadata>>([]);

	/* Object containing inventory filepaths as keys **/
	const inventoryFiles = ref<Record<string, any>>();

	/** All node names associated with variables */
	const VARIABLES_NODE_NAMES: Array<string> = [
		'Set Variable',
		'Set List Variable',
		'Append To List Variable',
		'Get Variable',
		'Set Variable (String)',
		'Set Variable (Number)',
		'Set Variable (Boolean)',
		'Set List Variable (String)',
		'Set List Variable (Number)',
		'Set List Variable (Boolean)',
		'Append To List Variable (String)',
		'Append To List Variable (Number)',
		'Append To List Variable (Boolean)'
	];

	/** Update all metadata. */
	async function update() {
		// Fetch metadata
		const response = await fetch('/api/metadata', { method: 'GET' });
		if (!response.ok) {
			return;
		}
		const data = await response.json();

		// Add nodes
		nodes.value = data.nodes;

		// Add data types
		dataTypes.value = data.datatypes;

		compositeInputs.value = data.compositeInputs;
		inventoryFiles.value = data.inventory.inventory_files;
	}

	/**
	 * Get a node's metadata by name.
	 *
	 * @param name The name of the node.
	 * @returns The found NodeMetadata.
	 * @throws An error if the node is not found.
	 */
	function getNode(name: string): NodeMetadata {
		const found = nodes.value.find((metadata) => metadata.name.toLowerCase() === name.toLowerCase());
		if (!found) {
			throw `No node found with name "${name}"`;
		}
		return found;
	}

	/**
	 * Find a node's metadata by name.
	 *
	 * @param name The name of the node.
	 *
	 * @returns The found NodeMetadata, or null if the node is not found.
	 */
	function findNode(name: string): NodeMetadata | null {
		const found = nodes.value.find((metadata) => metadata.name.toLowerCase() === name.toLowerCase());
		if (!found) {
			return null;
		}
		return found;
	}

	/**
	 * Get a data type's metadata by name.
	 *
	 * @param name The name of the datatype.
	 * @returns The found DataTypeMetadata.
	 * @throws An error if the data type is not found.
	 */
	function getDataType(name: string): DataTypeMetadata {
		const found = dataTypes.value.find((metadata) => metadata.name === name);
		if (!found) {
			throw `No datatype found with name "${name}"`;
		}
		return found;
	}

	/**
	 * Get a data type's metadata by color.
	 *
	 * @param color The color of the datatype.
	 * @returns The found DataTypeMetadata.
	 * @throws An error if the data type is not found.
	 */
	function getDataTypeByColor(color: string): DataTypeMetadata {
		const found = dataTypes.value.find((metadata) => metadata.color === color);
		if (!found) {
			throw `No datatype found with color "${color}"`;
		}
		return found;
	}

	/**
	 *  Get a compositeInput by datatype
	 *
	 * @param datatype
	 * @returns the found CompositeInputMetadata
	 * @throws An error if there is not a composite input for the datatype
	 */
	function getCompositeInput(datatype: string): CompositeGraphInputMetadata {
		const found = compositeInputs.value.find((metadata) => metadata.datatype === datatype);
		if (!found) {
			throw `No composite input found with datatype "${datatype}"`;
		}
		return found;
	}

	/**
	 *  See if dataType has compositeInput
	 *
	 * @param datatype
	 * @returns the found CompositeInputMetadata
	 * @throws An error if there is not a composite input for the datatype
	 */
	function hasCompositeInput(datatype_name: string): boolean {
		const found = compositeInputs.value.find((metadata) => metadata.datatype === datatype_name);
		if (!found) {
			return false;
		}
		return true;
	}

	/**
	 * Find a cast node that casts from the given datatype to another datatype.
	 *
	 * @param fromType The type to cast from.
	 * @param fromIsList Whether the `fromType` is a list.
	 * @param toType The type to cast to.
	 * @param toIsList Whether the `toType` is a list.
	 * @returns The found cast node, or null if the node does not exist.
	 */
	function findCastNode(fromType: string, fromIsList: boolean, toType: string, toIsList: boolean): NodeMetadata | null {
		for (const node of nodes.value) {
			if (node.type !== NodeTypes.CAST) {
				continue;
			}

			const inputSocket = node.sockets.find((socket) => socket.isInput);
			const outputSocket = node.sockets.find((socket) => !socket.isInput);

			if (inputSocket?.datatype === fromType && outputSocket?.datatype === toType) {
				if (
					(inputSocket.isList == fromIsList && outputSocket.isList == toIsList) ||
					(!inputSocket.isList && fromType.toLowerCase() == 'number') ||
					(fromType.toLowerCase() == 'boolean' && toType.toLowerCase() == 'string' && toIsList)
				) {
					return node;
				}
			}
		}

		return null;
	}

	/**
	 * Store graph inputs copied by the context menu. Will overwrite previously copied inputs.
	 *
	 * @param nodes The inputs.
	 */
	function storeCopiedInputs(inputs: Array<GraphInputMetadata>) {
		copiedInputMetadata.splice(0, copiedInputMetadata.length); // Clear
		for (const i of inputs) {
			copiedInputMetadata.push(i);
		}
	}

	/**
	 * Store graph outputs copied by the context menu. Will overwrite previously copied outputs.
	 *
	 * @param nodes The outputs.
	 */
	function storeCopiedOutputs(outputs: Array<GraphOutputMetadata>) {
		copiedOutputMetadata.splice(0, copiedOutputMetadata.length); // Clear
		for (const o of outputs) {
			copiedOutputMetadata.push(o);
		}
	}

	/**
	 * Computes the coordinates to center newly created nodes in the middle of the editor panel
	 */
	function getNodeStartPositions(ui: GraphEditorUI) {
		const viewportPositions = ui.viewportPositions();
		const width = viewportPositions.right - viewportPositions.left;
		const height = viewportPositions.bottom - viewportPositions.top;
		const x = -1 * ui.offsets.x + width / 2;
		const y = -1 * ui.offsets.y + height / 2;
		return { x, y };
	}

	return {
		nodes,
		dataTypes,
		compositeInputs,
		inventoryFiles,
		update,
		getNode,
		findNode,
		getDataType,
		findCastNode,
		copiedInputMetadata,
		storeCopiedInputs,
		copiedOutputMetadata,
		storeCopiedOutputs,
		getNodeStartPositions,
		VARIABLES_NODE_NAMES,
		getDataTypeByColor,
		hasCompositeInput,
		getCompositeInput
	};
});
