<template>
	<SidebarPanel header="Search">
		<div v-if="!referenceSearch" class="search-container">
			<SearchField v-model="searchInput" :placeholder="placeholderText" />
		</div>
		<div class="global-search-options-container">
			<div class="reference-search checkbox-line" title="Show references to this graph being used as a subgraph.">
				<BooleanCheckboxInput
					:value=referenceSearch
					@update="referenceSearch = ! referenceSearch"
				/>
				<span v-if="!referenceSearch" class="reference-search-toggle-title no-select">Find References To This Graph</span>
				<span v-else class="reference-search-toggle-title no-select">References to: {{ graphPath }}</span>
			</div>
			<div v-if="!referenceSearch" class="search-type-container checkbox-line" title="Search all files in the root GraphEx directory for a matching string.">
				<BooleanCheckboxInput
					:value=searchingGlobally
					@update="updateSearchType"
				/>
				<span class="global-search-toggle-title no-select">Global Search</span>
				<span v-if="searchingGlobally" class="material-icons global-search-filter-button" title="Show Filtering Options" @click="toggleGlobalFilterOptions">more_horiz</span>
			</div>
			<div class="global-search-filter-options-container" v-if="searchingGlobally && searchFilterClicked && !referenceSearch">
				<div class="global-search-stop-on-match checkbox-line" title="Stop searching when the first match is found in a file (disabling this increases search time)">
					<BooleanCheckboxInput
						:value=stopOnMatch
						@update="updateStopOnMatch"
					/>
					<span class="global-search-options-text no-select">Stop on Match</span>
				</div>
				<div class="global-search-match-case checkbox-line" title="Enforce searching based on upper/lower casing">
					<BooleanCheckboxInput
						:value=caseSensitive
						@update="updateCaseSensitive"
					/>
					<span class="global-search-options-text no-select">Case Sensitive</span>
				</div>
				<div class="global-search-match-filename checkbox-line" title="Search for the names of the files in the search">
					<BooleanCheckboxInput
						:value=matchFilenames
						@update="updateMatchFilenames"
					/>
					<span class="global-search-options-text no-select">Match Filenames</span>
				</div>
				<div class="global-search-match-filename checkbox-line" title="Limits the search to GX files only and includes matches on both the node description and output sockets.">
					<BooleanCheckboxInput
						:value=nodeDeepSearch
						@update="updateNodeDeepSearch"
					/>
					<span class="global-search-options-text no-select">GX Node Deep Search</span>
				</div>
				<div v-if="!nodeDeepSearch" class="include-extensions-container">
					<span> Include File Extensions</span>
					<SearchField v-model="includeExtInput" placeholder="e.g. gx" />
				</div>
				<div v-if="!nodeDeepSearch" class="exclude-extensions-container">
					<span> Exclude File Extensions</span>
					<SearchField v-model="excludeExtInput" placeholder="e.g. json, sh" />
				</div>
			</div>
		</div>

		<div v-if="!searchingGlobally && !referenceSearch" class="item-list">
			<span class="item-list-title no-select" title="Nodes in this graph that match the search string">Matching Nodes</span>
			<SearchedNodeComponent v-for="(node, index) in displayedNodes" :key="index" :node="node" />
		</div>
		<div v-else class="item-list">
			<span v-if="searchInput.length <= 0 && !referenceSearch" class="item-list-title no-select" title="Files in the root directory that match the search string">Matching Files</span>
			<span v-else-if="searchMatches.length >= 1000" class="item-list-title no-select" title="More results may exist but are not shown">Showing First {{ searchMatches.length }} Matches</span>
			<span v-else class="item-list-title no-select" title="Files in the root directory that match the search string">{{ searchMatches.length }} Matches Found</span>
			<div v-show="awaitingBackendResult && !terminalStore.mainSocketError" class="main-loading">
				<span class="loader"></span>
				<div class="loading-info">Searching...</div>
			</div>
			<div v-if="awaitingBackendResult && terminalStore.mainSocketError" class="main-loading">
				<div class="loading-info socket-error">Error Connecting to Server!</div>
			</div>
			<SearchedFileComponent
				v-for="(m, index) in searchMatches"
				:line-number="m.lineNumber"
				:relative-path="m.filePath"
				:matching-line="m.matchingLine"
				:original-query="globalQuery"
				:matching-id="m.nodeId"
				:is-selected="selectedFileComponent === index"
				@clicked="selectedFileComponent=index"
			/>
		</div>
	</SidebarPanel>
</template>

<script setup lang="ts">
	import BooleanCheckboxInput from '@/editor/graph/inputs/BooleanCheckboxInput.vue';
import SidebarPanel from '@/sidebar/SidebarPanel.vue';
import SearchField from '@/sidebar/nodePanel/SearchField.vue';
import SearchedNodeComponent from '@/sidebar/nodePanel/SearchedNodeComponent.vue';
import SearchedFileComponent from '@/sidebar/panels/files/SearchedFileComponent.vue';
import { useEditorStore, useFileStore, useTerminalStore } from '@/stores';
import { computed, ref, watch } from 'vue';

	export interface globalSearchResult {
		filePath: string,
		lineNumber: number,
		matchingLine: string,
		nodeId: string
	}

	const editorStore = useEditorStore();
	const terminalStore = useTerminalStore();
	const fileStore = useFileStore();

	const searchInput = ref<string>('');
	const graphPath = ref<string>('');
	const excludeExtInput = ref<string>('');
	const includeExtInput = ref<string>('');
	const searchingGlobally = ref<boolean>(false);
	const searchFilterClicked = ref<boolean>(false);
	const matchFilenames = ref<boolean>(false);
	const caseSensitive = ref<boolean>(false);
	const nodeDeepSearch = ref<boolean>(false);
	const stopOnMatch = ref<boolean>(true);
	const awaitingBackendResult = ref<boolean>(false);
	const referenceSearch = ref<boolean>(false);
	const searchMatches = ref<Array<globalSearchResult>>([]);
	const globalSearchDelayTimeout = ref<number>(-1);
	const selectedFileComponent = ref<number>(-1);
	/** This is the query as searched by the backend (as opposed to the value typed into the search bar by the user on the frontend) */
	const globalQuery = ref<string>('');

	const activeGraph = computed(() => (editorStore.activeGraphTab ? editorStore.activeGraphTab.contents : null));

	const displayedNodes = computed(() => {
		if (!activeGraph.value) return [];

		const temp = Array.from(activeGraph.value.getNodes());
		if (searchInput.value == '') {
			return temp;
		}

		const lc_vals = searchInput.value
			.toLowerCase()
			.split(' ')
			.filter((e) => e != '');

		return temp.filter((node) => {
			for (let i = 0; i < lc_vals.length; i++) {
				const word = lc_vals[i];
				if (node.metadata.name.toLowerCase().includes(word) || node.metadata.description.toLowerCase().includes(word)) {
					continue;
				}

				if (node.fieldValue !== undefined && String(node.fieldValue).toLowerCase().includes(word)) {
					continue;
				}

				let match = false;
				for (const socket of node.inputSockets) {
					if (socket.fieldValue !== undefined && String(socket.fieldValue).toLowerCase().includes(word)) {
						match = true;
						break;
					} 
					if (socket.graphInputName !== undefined && String(socket.graphInputName).toLowerCase().includes(word)) {
						match = true;
						break;
					}
					if (socket.metadata.name.toLowerCase().includes(word) && socket.metadata.name != "_backward" && socket.metadata.name != "_forward") {
						match = true;
						break;
					}
				}
				for (const socket of node.outputSockets) {
					if (socket.metadata.name.toLowerCase().includes(word) && socket.metadata.name != "_backward" && socket.metadata.name != "_forward") {
						match = true;
						break;
					}
				}

				if (!match) return undefined;
			}
			return node;
		});
	});

	function updateNodeDeepSearch(newValue: boolean) {
		nodeDeepSearch.value = newValue;

		if (searchInput.value.trim() != "")
			fetchMatchingFiles()
	}

	function updateStopOnMatch(newValue: boolean) {
		stopOnMatch.value = newValue;

		if (searchInput.value.trim() != "")
			fetchMatchingFiles()
	}

	function updateSearchType(newValue: boolean) {
		// when looking at a text file we disable the ability to change the search type back to node search
		if (!editorStore.activeGraphTab && searchingGlobally.value) return
		
		searchingGlobally.value = newValue;
		searchMatches.value = [];
		selectedFileComponent.value = -1;

		if (searchingGlobally.value && searchInput.value.trim() != "")
			fetchMatchingFiles()
	}

	function toggleGlobalFilterOptions() {
		searchFilterClicked.value = !searchFilterClicked.value;
	}

	function updateMatchFilenames(newValue: boolean) {
		matchFilenames.value = newValue;

		if (searchInput.value.trim() != "")
			fetchMatchingFiles()
	}

	function updateCaseSensitive(newValue: boolean) {
		caseSensitive.value = newValue;

		if (searchInput.value.trim() != "")
			fetchMatchingFiles()
	}

	async function fetchMatchingFiles() {
		searchMatches.value = [];
		if (searchInput.value == '') return;

		awaitingBackendResult.value = true;

		const response = await fetch('/api/search', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				"query": searchInput.value.trim(),
				"include_filenames": matchFilenames.value,
				"case_sensitive": caseSensitive.value,
				"include_extensions_string": includeExtInput.value,
				"exclude_extensions_string": excludeExtInput.value,
				"node_deep_search": nodeDeepSearch.value,
				"stop_on_first_match": stopOnMatch.value
			})
		});

		if (!response.ok) return;
		
		const data = await response.json();
		// the absolute root directory path of where the files came from
		let globalRootDir = data["root_dir"];
		if (!globalRootDir.endsWith('/')) globalRootDir += '/'
		// the query as seen by the server
		globalQuery.value = data["query"];

		// Here it is very important that we deep copy the results provided from the promise result
		for (const match of data["list_of_matches"]) {
			searchMatches.value.push({
				filePath: match.filepath.replace(globalRootDir, ""),
				lineNumber: match.line_number,
				matchingLine: match.line_content,
				nodeId: match.node_id
			});
		}

		awaitingBackendResult.value = false;
	}

	const graphName = computed(() => {
		return editorStore.activeGraphTab?.name || "";
	});

	function getGraphPath() {
		if (!editorStore.activeGraphTab) return null;
		if (!editorStore.activeGraphTab.fileId) return null;
		const p = fileStore.getFilePath(editorStore.activeGraphTab.fileId) || null;
		if (!p) return null;

		// Strip off the '.gx' from the filename if it has it
		// This extension isn't required for Execute Graph nodes
		let gxExtensionIndex = p.lastIndexOf('.gx');
		if (gxExtensionIndex >= 0) {
			return p.slice(0, gxExtensionIndex);
		}
		return p;
	}

	async function fetchReferences() {
		searchMatches.value = [];
		let graphPathLocal = graphPath.value;
		if (!graphPathLocal) return;
		awaitingBackendResult.value = true;

		const response = await fetch('/api/search', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				"query": graphPathLocal,
				"include_filenames": false,
				"case_sensitive": true,
				"include_extensions_string": includeExtInput.value,
				"exclude_extensions_string": excludeExtInput.value,
				"node_deep_search": false,
				"stop_on_first_match": false,
				"extract_node_name": true
			})
		});

		if (!response.ok) return;
		
		const data = await response.json();
		// the absolute root directory path of where the files came from
		let globalRootDir = data["root_dir"];
		if (!globalRootDir.endsWith('/')) globalRootDir += '/'
		// the query as seen by the server
		globalQuery.value = data["query"];

		// Here it is very important that we deep copy the results provided from the promise result
		for (const match of data["list_of_matches"]) {
			if ("node_name" in match && match.node_name === "Execute Graph") {
				const strippedLine = String(match.line_content).trim();
				
				if (!strippedLine.startsWith('fieldValue:')) continue;
				if (!strippedLine.includes(graphPathLocal)) continue;

				searchMatches.value.push({
					filePath: match.filepath.replace(globalRootDir, ""),
					lineNumber: match.line_number,
					matchingLine: match.line_content,
					nodeId: match.node_id
				});
			}
		}

		awaitingBackendResult.value = false;
	}

	const placeholderText = computed(() => {
		if (searchingGlobally.value) {
			return "Search Files Globally"
		}
		return "Search This Graph"
	});

	watch(
		searchInput,
		() => {
			if (!searchingGlobally.value) return;
			if (globalSearchDelayTimeout.value > -1)
				clearTimeout(globalSearchDelayTimeout.value);
			globalSearchDelayTimeout.value = setTimeout(() => {
				fetchMatchingFiles();
			}, 300);
		},
		{ immediate: true }
	);

	watch(
		includeExtInput,
		() => {
			if (!searchingGlobally.value) return;
			if (globalSearchDelayTimeout.value > -1)
				clearTimeout(globalSearchDelayTimeout.value);
			globalSearchDelayTimeout.value = setTimeout(() => {
				fetchMatchingFiles();
			}, 300);
		},
		{ immediate: true }
	);

	watch(
		excludeExtInput,
		() => {
			if (!searchingGlobally.value) return;
			if (globalSearchDelayTimeout.value > -1)
				clearTimeout(globalSearchDelayTimeout.value);
			globalSearchDelayTimeout.value = setTimeout(() => {
				fetchMatchingFiles();
			}, 300);
		},
		{ immediate: true }
	);

	watch(
		referenceSearch,
		() => {
			if (!referenceSearch.value) return;
			graphPath.value = getGraphPath() || graphName.value;
			fetchReferences();
		},
		{ immediate: true }
	)

</script>

<style scoped>
	.search-container {
		width: 100%;
		padding: 0px 12px;
	}

	.item-list {
		padding: 0px 0.75rem;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.reference-search {
		display: flex;
		flex-direction: row;
		font-size: 14px;
		margin-top: 6px;
	}

	.reference-search-toggle-title {
		margin-left: 3px;
		margin-top: 3px;
	}

	.search-type-container {
		display: flex;
		flex-direction: row;
	}

	.global-search-options-container {
		display: flex;
		flex-direction: column;
		margin-top: 1.5px;
		margin-bottom: 12px;
		margin-left: 12px;
		font-size: 14px;
	}

	.global-search-filter-options-container {
		display: flex;
		flex-direction: column;
	}

	.global-search-toggle-title {
		margin-left: 3px;
		margin-top: 3px;
	}

	.global-search-options-text {
		margin-left: 3px;
		margin-top: 3px;
	}

	.global-search-match-filename {
		display: flex;
		flex-direction: row;
	}

	.global-search-match-case {
		display: flex;
		flex-direction: row;
	}

	.global-search-stop-on-match {
		display: flex;
		flex-direction: row;
	}

	.item-list-title {
		color: var(--color-text-secondary);
	}

	.global-search-filter-button {
		margin-left: auto;
		padding-right: 12px;
		cursor: pointer;
	}

	.include-extensions-container {
		margin-top: 4px;
		display: flex;
		flex-direction: column;
	}

	.exclude-extensions-container {
		margin-top: 4px;
		display: flex;
		flex-direction: column;
	}
	.main-loading {
		top: 0px;
		left: 0px;
		z-index: 999;
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding-top: 20px;
	}

	.loader {
		transform: rotateZ(45deg);
		perspective: 1000px;
		border-radius: 50%;
		width: 84px;
		height: 84px;
		color: rgb(255, 255, 255);
	}

	.loader:before,
	.loader:after {
		content: '';
		display: block;
		position: absolute;
		top: 0;
		left: 0;
		width: inherit;
		height: inherit;
		border-radius: 50%;
		transform: rotateX(70deg);
		animation: 1.2s spin linear infinite;
	}

	.loader:after {
		color: var(--color-primary);
		transform: rotateY(70deg);
		animation-delay: -0.8s;
	}

	@keyframes rotate {
		0% {
			transform: translate(-50%, -50%) rotateZ(0deg);
		}
		100% {
			transform: translate(-50%, -50%) rotateZ(360deg);
		}
	}

	@keyframes rotateccw {
		0% {
			transform: translate(-50%, -50%) rotate(0deg);
		}
		100% {
			transform: translate(-50%, -50%) rotate(-360deg);
		}
	}

	@keyframes spin {
		0%,
		100% {
			box-shadow: 0.2em 0px 0 0px currentcolor;
		}
		12% {
			box-shadow: 0.2em 0.2em 0 0 currentcolor;
		}
		25% {
			box-shadow: 0 0.2em 0 0px currentcolor;
		}
		37% {
			box-shadow: -0.2em 0.2em 0 0 currentcolor;
		}
		50% {
			box-shadow: -0.2em 0 0 0 currentcolor;
		}
		62% {
			box-shadow: -0.2em -0.2em 0 0 currentcolor;
		}
		75% {
			box-shadow: 0px -0.2em 0 0 currentcolor;
		}
		87% {
			box-shadow: 0.2em -0.2em 0 0 currentcolor;
		}
	}

	.loading-info {
		margin-top: 10px;
		font-size: 1.2rem;
		letter-spacing: 1px;
	}

	.socket-error {
		text-align: center;
		color: var(--color-error);
	}

	.checkbox-line {
		padding-bottom: 2px;
	}
</style>
