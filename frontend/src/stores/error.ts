import { defineStore } from 'pinia';
import { reactive } from 'vue';

interface ErrorMap {
	[tabId: string]: {
		[nodeId: string]: {
			[socketName: string]: string; // Socket name -> error message
		};
	};
}

interface WarningMap {
	[tabId: string]: {
		[nodeId: string]: {
			[socketName: string]: string; // Socket name -> error message
		};
	};
}

interface giWarningMap {
	[tabId: string]: {
		[inputName: string]: boolean;
	}
}


export const useErrorStore = defineStore('error', () => {
	/** Map of all current errors. */
	const errorMap = reactive<ErrorMap>({});

	/** Map of all current warnings. */
	const warningMap = reactive<ErrorMap>({});

	/** Map of tabs with unused graph inputs */
	const graphInputWarningMap = reactive<giWarningMap>({});

	function addError(tabId: string, nodeId: string, socketName: string, message: string) {
		if (!(tabId in errorMap)) {
			errorMap[tabId] = {};
		}

		const nodeMap = errorMap[tabId];
		if (!(nodeId in nodeMap)) {
			nodeMap[nodeId] = {};
		}

		const socketMap = nodeMap[nodeId];
		socketMap[socketName] = message;
	}

	function removeError(tabId: string, nodeId: string, socketName: string) {
		if (!(tabId in errorMap)) {
			return;
		}

		const nodeMap = errorMap[tabId];
		if (!(nodeId in nodeMap)) {
			return;
		}

		const socketMap = nodeMap[nodeId];
		delete socketMap[socketName];

		if (Object.keys(socketMap).length === 0) {
			// If there are no sockets left in the node map, remove the node map reference
			delete nodeMap[nodeId];
		}

		if (Object.keys(nodeMap).length == 0) {
			// If there are no nodes left in the node map, remove the error map reference
			delete errorMap[tabId];
		}
	}

	function removeErrorsForNode(tabId: string, nodeId: string) {
		if (!(tabId in errorMap)) {
			return;
		}

		const nodeMap = errorMap[tabId];
		if (!(nodeId in nodeMap)) {
			return;
		}

		delete nodeMap[nodeId];
		if (Object.keys(nodeMap).length == 0) {
			// If there are no nodes left in the node map, remove the error map reference
			delete errorMap[tabId];
		}
	}

	function addGraphInputWarning(tabId: string, inputName: string) {
		if (!(tabId in graphInputWarningMap)) {
			graphInputWarningMap[tabId] = {};
		}

		const graphInputNameMap = graphInputWarningMap[tabId];
		if (!(inputName in graphInputNameMap)) {
			graphInputNameMap[inputName] = true;
		}
	}

	function removeGraphInputWarning(tabId: string, inputName: string) {
		if (!(tabId in graphInputWarningMap)) {
			return;
		}

		const graphInputNameMap = graphInputWarningMap[tabId];
		if (!(inputName in graphInputNameMap)) {
			return;
		}

		delete graphInputNameMap[inputName];

		if (Object.keys(graphInputNameMap).length == 0) {
			// If there are no nodes left in the node map, remove the error map reference
			delete graphInputWarningMap[tabId];
		}
	}

	function graphHasErrors(tabId: string) {
		return tabId in errorMap;
	}

	function graphHasGraphInputWarning(tabId: string) {
		return tabId in graphInputWarningMap;
	}

	function addWarning(tabId: string, nodeId: string, socketName: string, message: string) {
		if (!(tabId in warningMap)) {
			warningMap[tabId] = {};
		}

		const nodeMap = warningMap[tabId];
		if (!(nodeId in nodeMap)) {
			nodeMap[nodeId] = {};
		}

		const socketMap = nodeMap[nodeId];
		socketMap[socketName] = message;
	}

	function removeWarning(tabId: string, nodeId: string, socketName: string) {
		if (!(tabId in warningMap)) {
			return;
		}

		const nodeMap = warningMap[tabId];
		if (!(nodeId in nodeMap)) {
			return;
		}

		const socketMap = nodeMap[nodeId];
		delete socketMap[socketName];

		if (Object.keys(socketMap).length === 0) {
			// If there are no sockets left in the node map, remove the node map reference
			delete nodeMap[nodeId];
		}

		if (Object.keys(nodeMap).length == 0) {
			// If there are no nodes left in the node map, remove the error map reference
			delete warningMap[tabId];
		}
	}

	function graphHasWarning(tabId: string) {
		return tabId in warningMap;
	}

	return {
		errorMap,
		warningMap,
		addError,
		removeError,
		removeErrorsForNode,
		graphHasErrors,
		addGraphInputWarning,
		removeGraphInputWarning,
		graphHasGraphInputWarning,
		graphHasWarning,
		addWarning,
		removeWarning
	};
});
