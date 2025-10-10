import type { Graph, GraphNode, Socket } from '@/graph';
import { nextTick } from 'vue';

/** Amount of horizontal spacing between node chains. */
const CHAIN_HORIZONTAL_SPACING = 25;

/** Amount of vertical spacing between vertically stacked groups for a fork (two or more output links). */
const FORK_GROUP_VERTICAL_SPACING = 40;

/** Amount of horizontal spacing between a node and its data node(s), recursively. */
const DATA_NODE_HORIZONTAL_SPACING = 25;

/** Amount of vertical spacing between node's data node(s) */
const DATA_NODE_VERTICAL_SPACING = 10;

/**
 * Auto-format a graph according to predefined rules (node positions, etc). This will update the graph in-place.
 *
 * @param graph The graph to format.
 */
async function formatGraph(graph: Graph) {
	preprocess(graph);
	await nextTick();

	// Save the relative positions of comments to their nearest neighbor
	// We'll restore this relative positioning after all nodes have been formatted
	// Positioning comments is difficult since they are unconnected in the graph
	// This is a lazy but good-enough way to position the comments
	const commentNodes = Array.from(graph.getNodes()).filter((n) => n.metadata.name == 'Comment');
	const nonCommentNodes = Array.from(graph.getNodes()).filter((n) => n.metadata.name !== 'Comment');
	const commentNearestNeighbor: { [id: string]: { neighborId: string; xOffset: number; yOffset: number } } = {};
	for (const commentNode of commentNodes) {
		let smallestDistance = Infinity;
		let nearestNeighbor = null;
		for (const neighbor of nonCommentNodes) {
			const deltaX = commentNode.x - neighbor.x;
			const deltaY = commentNode.y - neighbor.y;
			const distance = Math.sqrt(Math.pow(deltaX, 2) + Math.pow(deltaY, 2));
			if (distance < smallestDistance) {
				smallestDistance = distance;
				nearestNeighbor = { neighborId: neighbor.id, xOffset: deltaX, yOffset: deltaY };
			}
		}

		if (nearestNeighbor) {
			commentNearestNeighbor[commentNode.id] = nearestNeighbor;
		}
	}

	// For each node without a incoming link, start formatting from that node
	for (const node of graph.getNodes()) {
		const linkInputs = node.inputSockets.filter((s) => s.metadata.isLink);
		const linkOutputs = node.outputSockets.filter((s) => s.metadata.isLink);
		if ((linkInputs.length || linkOutputs.length) && !getPreviousNode(node)) {
			// No previous, so this is a valid "start"
			formatNode(node);
		}
	}

	// Reposition all comments according to the old nearest neighbor
	for (const commentNode of commentNodes) {
		if (!(commentNode.id in commentNearestNeighbor)) {
			continue;
		}
		const nearestNeighborData = commentNearestNeighbor[commentNode.id];
		let nearestNeighborNode: GraphNode;
		try {
			nearestNeighborNode = graph.getNode(nearestNeighborData.neighborId);
		} catch (e) {
			console.warn(e);
			continue;
		}

		commentNode.x = nearestNeighborNode.x + nearestNeighborData.xOffset;
		commentNode.y = nearestNeighborNode.y + nearestNeighborData.yOffset;
	}

	// Find the global minimum (X, Y) and shift by the amount so that the graph starts from (0, 0)
	const globalMinX = Math.min(...Array.from(graph.getNodes()).map((n) => n.x));
	const globalMinY = Math.min(...Array.from(graph.getNodes()).map((n) => n.y));
	translateAll(Array.from(graph.getNodes()), -globalMinX, -globalMinY);
	graph.ui.offsets.x += globalMinX;
	graph.ui.offsets.y += globalMinY;

	await nextTick();
	graph.ui.requestScaleFrame(() => {
		graph.forceRerender();
	});
}

/**
 * Perform preprocessing on a graph prior to formatting. This will perform transformations to the graph according to "best practices",
 * e.g. inlining variables rather than using 'Get Variable' nodes where possible.
 *
 * @param graph The graph to preprocess.
 */
function preprocess(graph: Graph) {
	// Inline 'Get Graph Input' and 'Get Variable' nodes where possible
	const inlinableNodes = Array.from(graph.getNodes()).filter(
		(n) => n.metadata.name == 'Get Graph Input' || n.metadata.name == 'Get Variable'
	);
	for (const node of inlinableNodes) {
		const fieldValue = node.fieldValue;
		if (!fieldValue || typeof fieldValue !== 'string') {
			graph.deleteNodes([node]);
			continue;
		}

		let outputSocket: Socket;
		try {
			outputSocket = node.getOutputSocket('Value');
		} catch {
			continue;
		}

		for (const connection of [...outputSocket.connections]) {
			if (connection.metadata.isList !== outputSocket.metadata.isList) {
				continue;
			}

			if (connection.metadata.datatype !== outputSocket.metadata.datatype) {
				continue;
			}

			if (node.metadata.name == 'Get Graph Input') {
				connection.setGraphInputName(fieldValue);
			} else if (node.metadata.name == 'Get Variable') {
				connection.setVariableName(fieldValue);
			}
		}

		if (outputSocket.connections.length == 0) {
			// Remove this node as it's no longer needed
			graph.deleteNodes([node]);
		}
	}
}

/**
 * Format a node.
 *
 * @param node The node to format.
 *
 * @returns All nodes that were repositioned / considered for repositioning (including itself).
 */
function formatNode(node: GraphNode): Array<GraphNode> {
	const graph = node.graph;
	const previousNode = getPreviousNode(node);
	const nextNodes = getNextNodes(node);

	const repositionedNodes: Array<GraphNode> = [node];

	// Format non-linked dependencies
	// These are data (or other similar non-linked) nodes that are connected to this node
	// We will want to position these next to the node in question
	const repositionedDataNodes = formatDataInputNodes(node);
	repositionedNodes.push(...repositionedDataNodes);

	// Align this node with it's previous node
	if (previousNode) {
		const nodeGroup = [node, ...repositionedDataNodes]; // Also reposition any connected data nodes
		const boundingRect = getBoundingRect(nodeGroup);
		const xAmount = -1 * (boundingRect.minX - (previousNode.x + previousNode.width()));
		const yAmount = -1 * (node.y - previousNode.y);
		translateAll(nodeGroup, xAmount + CHAIN_HORIZONTAL_SPACING, yAmount);
	}

	if (nextNodes.length == 0) {
		// Nothing more to do
		return repositionedNodes;
	}

	if (nextNodes.length == 1) {
		// Only one next node, just move on to it.
		return [...repositionedNodes, ...formatNode(nextNodes[0])];
	}

	// Multiple next nodes
	// We'll format each node and collect the "groups"
	// Then we'll space out the groups so they do not overlap
	const groups: Array<Array<GraphNode>> = [];
	for (const nextNode of nextNodes) {
		const formatted = formatNode(nextNode);
		groups.push(formatted);
		repositionedNodes.push(...formatted);
	}

	// Space out the groups
	// We'll leave the first group alone (aligned with this node),
	// and stack the rest vertically.
	let lastBoundingRect = getBoundingRect(groups[0]);
	for (const group of groups.slice(1)) {
		const boundingRect = getBoundingRect(group);
		const yAmount = lastBoundingRect.maxY - boundingRect.minY + FORK_GROUP_VERTICAL_SPACING;
		translateAll(group, 0, yAmount);
		boundingRect.minY += yAmount;
		boundingRect.maxY += yAmount;
		lastBoundingRect = boundingRect;
	}

	// Revisit the positioning of each group now that they are stacked vertically
	//
	// If there is space above a group, we'll use that space (i.e. collapse whitespace vertically)
	// Starting from the second group ensures that this terminates and does not go off into infinity
	// upwards, as group 0 acts as a upper bound that should be hit.
	// Nonetheless, we use a global minimum Y to prevent runaway looping just in case.
	const globalMinY = Math.min(...Array.from(graph.getNodes()).map((n) => n.y));
	for (const group of groups.slice(1)) {
		const boundingRect = getBoundingRect(group);

		const getNodesInArea = () => {
			return graph.findNodesInArea(
				boundingRect.minX - CHAIN_HORIZONTAL_SPACING + 1,
				boundingRect.minY - FORK_GROUP_VERTICAL_SPACING * 2,
				boundingRect.maxX + CHAIN_HORIZONTAL_SPACING - 1,
				boundingRect.maxY + FORK_GROUP_VERTICAL_SPACING * 2,
				group
			);
		};

		while (boundingRect.minY > globalMinY && getNodesInArea().length == 0) {
			const shiftAmountY = -FORK_GROUP_VERTICAL_SPACING;
			translateAll(group, 0, shiftAmountY);
			boundingRect.minY += shiftAmountY;
			boundingRect.maxY += shiftAmountY;
		}

		const nodesInArea = getNodesInArea();
		const remainingMoveAmount = Math.min(
			FORK_GROUP_VERTICAL_SPACING,
			...nodesInArea.map((n) => boundingRect.minY - (n.y + n.width()))
		);
		if (remainingMoveAmount > 0) {
			translateAll(group, 0, -remainingMoveAmount);
		}
	}

	// If there is space to the left of a group, we'll use the space (i.e. collapse whitespace horizontally)
	// This should only occur if extra spacing was added due to the existence data nodes on the first node
	// We'll try to move the group leftward (up to approximately the size of that data group) if possible
	// Again, this should only occur for the second group and onward, as the first group will be positioned
	// according to normal horizontal flow
	for (let i = 1; i < groups.length; i++) {
		const group = groups[i];
		const firstLinkedNode = nextNodes[i];

		const dataGroup = getDataInputNodes(firstLinkedNode);
		if (dataGroup.length == 0) {
			continue;
		}

		const remainingGroup = group.filter((n) => !dataGroup.includes(n));

		const dataGroupBoundingRect = getBoundingRect(dataGroup);
		const remainingGroupBoundingRect = getBoundingRect(remainingGroup);

		const minRemainingGroupAllowedX = dataGroupBoundingRect.minX;
		while (
			remainingGroupBoundingRect.minX > minRemainingGroupAllowedX &&
			graph.findNodesInArea(
				dataGroupBoundingRect.minX - CHAIN_HORIZONTAL_SPACING,
				dataGroupBoundingRect.minY - FORK_GROUP_VERTICAL_SPACING + 1,
				dataGroupBoundingRect.maxX + CHAIN_HORIZONTAL_SPACING,
				dataGroupBoundingRect.maxY + FORK_GROUP_VERTICAL_SPACING - 1,
				group
			).length == 0 &&
			graph.findNodesInArea(
				remainingGroupBoundingRect.minX - CHAIN_HORIZONTAL_SPACING,
				remainingGroupBoundingRect.minY - FORK_GROUP_VERTICAL_SPACING + 1,
				remainingGroupBoundingRect.maxX + CHAIN_HORIZONTAL_SPACING,
				remainingGroupBoundingRect.maxY + FORK_GROUP_VERTICAL_SPACING - 1,
				group
			).length == 0
		) {
			const shiftAmountX = -Math.min(
				CHAIN_HORIZONTAL_SPACING,
				remainingGroupBoundingRect.minX - minRemainingGroupAllowedX
			);

			translateAll(dataGroup, shiftAmountX, 0);
			dataGroupBoundingRect.minX += shiftAmountX;
			dataGroupBoundingRect.maxX += shiftAmountX;

			translateAll(remainingGroup, shiftAmountX, 0);
			remainingGroupBoundingRect.minX += shiftAmountX;
			remainingGroupBoundingRect.maxX += shiftAmountX;
		}
	}

	return repositionedNodes;
}

/**
 * Format / reposition data input nodes (non-linked dependencies). This function will make a best-effort attempt to position all the non-linked
 * nodes connected to the given node such that the nodes are non-overlapping and positioned next to the target node.
 *
 * @param node The target node whose data nodes are to be formatted.
 *
 * @returns All data nodes that were repositioned / considered for repositioning (does not include the provided node).
 */
function formatDataInputNodes(node: GraphNode): Array<GraphNode> {
	interface DataNodePositions {
		node: GraphNode;
		x: number;
		y: number;
		width: number;
		height: number;
	}

	const positions: Array<DataNodePositions> = [];
	const dataNodes: Array<GraphNode> = [];

	const getOverlappingPosition = (targetPosition: DataNodePositions): DataNodePositions | null => {
		for (const position of positions) {
			if (targetPosition == position) {
				continue;
			}

			if (position.x + position.width < targetPosition.x || targetPosition.x + targetPosition.width < position.x) {
				// One is left or right of the other
				continue;
			}

			if (position.y + position.height < targetPosition.y || targetPosition.y + targetPosition.height < position.y) {
				// One is above or below the other
				continue;
			}

			// Node overlaps
			return position;
		}

		return null;
	};

	const reposition = (inputSocket: Socket, connectedNode: GraphNode) => {
		const foundSelfPositions = positions.find((p) => p.node == connectedNode);
		if (
			[...connectedNode.inputSockets, ...connectedNode.outputSockets].find((s) => s.metadata.isLink) ||
			foundSelfPositions
		) {
			// Skip this node if it contains a link socket or if we've already repositioned this node
			return;
		}

		const foundParentPositions = positions.find((p) => p.node == inputSocket.node);
		const socketPositions = inputSocket.getPositions();

		const width = connectedNode.width();
		const height = connectedNode.height();

		let desiredX = 0;
		let desiredY = 0;
		if (foundParentPositions) {
			// We'll need to offset the positions for this socket if the parent node has been repositioned already
			desiredX =
				socketPositions.left - inputSocket.node.x + foundParentPositions.x - DATA_NODE_HORIZONTAL_SPACING - width;
			desiredY = socketPositions.top - inputSocket.node.y + foundParentPositions.y;
		} else {
			// Position next to the socket
			desiredX = socketPositions.left - DATA_NODE_HORIZONTAL_SPACING - width;
			desiredY = socketPositions.top;
		}

		// Set default positions
		const nodePositions = {
			node: connectedNode,
			x: desiredX,
			y: desiredY,
			width: width,
			height: height
		};

		// Adjust the position as needed to not overlap with any previously positioned node
		// We only need to worry about re-positioning along the y-axis, as the x-axis positioning
		// should be inherently OK due to how the default positioning works.
		let overlappingPosition = getOverlappingPosition(nodePositions);
		while (overlappingPosition) {
			nodePositions.y = overlappingPosition.y + overlappingPosition.height + DATA_NODE_VERTICAL_SPACING;
			overlappingPosition = getOverlappingPosition(nodePositions);
		}

		// Commit the new position
		positions.push(nodePositions);
		dataNodes.push(connectedNode);

		// Reposition all dependencies
		const inputSockets = connectedNode.inputSockets.filter((s) => !!s.metadata.datatype);
		for (const socket of inputSockets) {
			for (const connection of socket.connections) {
				reposition(socket, connection.node);
			}
		}
	};

	// Trigger a reposition on each node connected to a data socket on this node
	const inputSockets = node.inputSockets.filter((s) => !!s.metadata.datatype);
	for (const socket of inputSockets) {
		for (const connection of socket.connections) {
			reposition(socket, connection.node);
		}
	}

	// Set all the data nodes to their final positions
	for (const position of positions) {
		position.node.x = position.x;
		position.node.y = position.y;
	}

	return dataNodes;
}

/**
 * Get the smallest rectangle positions that completely bound the given nodes.
 *
 * @param nodes The nodes.
 *
 * @returns The rectangle positions.
 */
function getBoundingRect(nodes: Array<GraphNode>): { minX: number; minY: number; maxX: number; maxY: number } {
	const rect = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };

	for (const node of nodes) {
		if (node.x < rect.minX) {
			rect.minX = node.x;
		}

		if (node.y < rect.minY) {
			rect.minY = node.y;
		}

		if (node.x + node.width() > rect.maxX) {
			rect.maxX = node.x + node.width();
		}

		if (node.y + node.height() > rect.maxY) {
			rect.maxY = node.y + node.height();
		}
	}

	return rect;
}

/**
 * Translate all provided nodes by the given amount.
 *
 * @param nodes The nodes to translate.
 * @param x The amount to translate along the x-axis.
 * @param y The amount to translate along the y-axis.
 */
function translateAll(nodes: Array<GraphNode>, x: number, y: number) {
	for (const node of nodes) {
		node.x += x;
		node.y += y;
	}
}

/**
 * Get all data input nodes (non-linked dependencies) for a node.
 *
 * @param node The node.
 *
 * @return All data input nodes (non-linked dependencies) for the node. Duplicates will not be included, and results will be returned in DFS-order.
 */
function getDataInputNodes(node: GraphNode): Array<GraphNode> {
	const dataNodes: Array<GraphNode> = [];

	const dataSockets = node.inputSockets.filter((s) => !s.metadata.isLink && !!s.metadata.datatype);
	for (const socket of dataSockets) {
		for (const connection of socket.connections) {
			if (!dataNodes.includes(connection.node)) {
				dataNodes.push(connection.node);
			}

			for (const child of getDataInputNodes(connection.node)) {
				if (!dataNodes.includes(child)) {
					dataNodes.push(child);
				}
			}
		}
	}

	return dataNodes;
}

/**
 * Given a node in a graph, get the node that is linked before it.
 *
 * @param node The node.
 *
 * @returns The node that is linked before the given node, or null if no such node exists.
 */
function getPreviousNode(node: GraphNode): GraphNode | null {
	const linkInputs = node.inputSockets.filter((s) => s.metadata.isLink);
	if (linkInputs.length == 0) {
		return null;
	}

	if (linkInputs.length > 1) {
		console.warn(
			`Autoformat: Node ${node.id} has multiple link input sockets. This is not supported for autoformatting.`
		);
		return null;
	}

	const linkInput = linkInputs[0];
	if (linkInput.connections.length == 0) {
		return null;
	}

	if (linkInput.connections.length > 1) {
		console.warn(
			`Autoformat: Socket ${linkInput.metadata.name} on node ${node.id} has multiple link input connections. This is not supported for autoformatting.`
		);
		return null;
	}

	const connectedNode = linkInput.connections[0].node;
	if (connectedNode == node) {
		return null;
	}

	return connectedNode;
}

/**
 * Given a node in a graph, get the nodes that are linked after it.
 *
 * @param node The node.
 *
 * @returns The nodes that are linked after the given node.
 */
function getNextNodes(node: GraphNode): Array<GraphNode> {
	const connectedNodes: Array<GraphNode> = [];
	const linkOutputs = node.outputSockets.filter((s) => s.metadata.isLink);
	for (const linkOutput of linkOutputs) {
		if (linkOutput.connections.length == 0) {
			continue;
		}

		if (linkOutput.connections.length > 1) {
			console.warn(
				`Autoformat: Socket ${linkOutput.metadata.name} on node ${node.id} has multiple link output connections. This is not supported for autoformatting.`
			);
			continue;
		}

		const connectedNode = linkOutput.connections[0].node;
		if (connectedNode != node && !connectedNodes.includes(connectedNode)) {
			connectedNodes.push(connectedNode);
		}
	}

	return connectedNodes;
}

export { formatGraph };
