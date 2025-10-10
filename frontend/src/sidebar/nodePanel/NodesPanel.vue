<template>
	<SidebarPanel :header="props.header">
		<div class="search-container">
			<SearchField v-model="searchInput" :placeholder="searchPlaceholder" />
		</div>
		<div class="item-list" v-if="searchInput == '' && !props.hideCategories">
			<span class="item-list-title no-select">Categories</span>
			<BreadcrumbsComponent
				v-show="selectedCategory.length"
				:items="selectedCategory"
				@return-to-index="returnToCategory"
			/>
			<template v-if="displayedCategories.length">
				<CategoryComponent
					v-for="(category, index) in displayedCategories"
					:key="index"
					:name="category.name"
					@selected="() => nextCategory(category.name)"
				/>
			</template>
			<span v-else class="empty-text no-select">No sub-categories found.</span>
		</div>

		<div class="item-list" style="margin-top: 2rem">
			<span class="item-list-title no-select">Nodes</span>
			<template v-if="displayedNodes.length">
				<NodeMetadataComponent v-for="(metadata, index) in displayedNodes" :key="index" :metadata="metadata" />
			</template>
			<span v-else class="empty-text no-select">No nodes found.</span>
		</div>
	</SidebarPanel>
</template>

<script setup lang="ts">
	import type { NodeMetadata } from '@/graph';
import SidebarPanel from '@/sidebar/SidebarPanel.vue';
import BreadcrumbsComponent from '@/sidebar/nodePanel/BreadcrumbsComponent.vue';
import CategoryComponent from '@/sidebar/nodePanel/CategoryComponent.vue';
import NodeMetadataComponent from '@/sidebar/nodePanel/NodeMetadataComponent.vue';
import SearchField from '@/sidebar/nodePanel/SearchField.vue';
import { computed, ref } from 'vue';

	/**
	 * header: The Title displayed at the top of panel.
	 * nodes: All available metadata nodes to be further filtered by category or search.
	 */
	const props = defineProps<{
		header: string;
		nodes: Array<NodeMetadata>;
		hideCategories?: boolean;
	}>();

	interface NodeCategory {
		name: string;
		subcategories: { [name: string]: NodeCategory };
		nodes: Array<NodeMetadata>;
	}

	/** "Two-way-bound" value that holds the value of the search bar */
	const searchInput = ref<string>('');
	const selectedCategory = ref<Array<string>>([]);

	function nextCategory(categoryName: string) {
		selectedCategory.value.push(categoryName);
	}

	function returnToCategory(index: number) {
		selectedCategory.value = selectedCategory.value.slice(0, index);
	}

	const rootCategory = computed(() => {
		const root: NodeCategory = { name: 'All', subcategories: {}, nodes: [] };

		// Sort the nodes
		// Since categorizing the nodes later will maintain order, it is sufficient to sort once here
		// to obtain sorted categories, rather than sorting each category individually
		const sortedNodes = [...props.nodes];
		sortedNodes.sort((a, b) => a.name.localeCompare(b.name));

		// Divide into categories
		for (const entry of sortedNodes) {
			let currentCategory = root;
			for (const categoryName of entry.categories) {
				if (categoryName in currentCategory.subcategories) {
					// Category already exists
					currentCategory = currentCategory.subcategories[categoryName];
					continue;
				}

				// Category does not exist, create it
				const newCategory: NodeCategory = { name: categoryName, subcategories: {}, nodes: [] };
				currentCategory.subcategories[categoryName] = newCategory;
				currentCategory = newCategory;
			}

			// Add the node to the category
			currentCategory.nodes.push(entry);
		}

		return root;
	});

	const searchPlaceholder = computed(() => {
		if (props.header == "Favorite Nodes") return "Search Favorite Nodes"
		if (props.header == "Nodes") return "Search Node Store"
		return "Search"
	});

	const currentCategory = computed(() => {
		let category = rootCategory.value;
		for (const categoryName of selectedCategory.value) {
			category = category.subcategories[categoryName];
		}
		return category;
	});

	const displayedCategories = computed(() => {
		const categories = Object.values(currentCategory.value.subcategories);
		categories.sort((a, b) => a.name.localeCompare(b.name));
		return categories;
	});

	const nodesWithoutInventoryNodes = computed(() => {
		return props.nodes.filter(n => !n.isInventoryNode);
	});

	/**
	 * The nodes displayed in the panel.
	 * The results are dependent upon whether the searchbar is populated with text or not.
	 * When populated: Runs a filter against ALL nodes. The filter selects nodes that fully or partially match the search string.
	 * After filtering, sorts on a weight assigned during filtering.
	 * The weight is assigned (most to least important): exact match of word in node name, partial match on node name,
	 *    exact match of word in search bar to word in description, partial match in description.
	 * If not searching, nodes displayed match the category/subcategories clicked previously in the sidebar.
	 */
	const displayedNodes = computed(() => {
		// If searching, filter and sort on all nodes
		if (searchInput.value != '') {
			/** The entire search phrase (lowercase) */
			const baseSearchWord = searchInput.value
				.replace(/[^A-Za-z0-9 ]/g, '')
				.trim()
				.toLowerCase();
			/** An array of all words in the search phrase */
			const lc_vals = baseSearchWord.split(' ').filter((e) => e != '');
			/** mapping of node name -> weight priority score */
			const weightMap = new Map<string, number>();
			return nodesWithoutInventoryNodes.value
				.filter((node) => {
					/** The final weighted score for this node (if not filtered out) */
					let weight = 0;
					/** How valuable each matching word is in the name */
					const nameWeight = 10.0 / node.name.split(' ').length;
					/** How valuable each matching word is in the description */
					const descWeight = 2.0 / node.description.split(' ').length;

					/** Formatted name of the node being compared (lowercase) */
					const nodeName = node.name
						.replace(/[^A-Za-z0-9 ]/g, '')
						.trim()
						.toLowerCase();
					/** Formatted description of the node being compared (lowercase) */
					const nodeDescription = node.description
						.replace(/[^A-Za-z0-9 ]/g, '')
						.trim()
						.toLowerCase();
					/** Array of all the words in the name ('sentence') and all the words in the description */
					const nodeNameSentence = nodeName.split(' ').filter((e) => e != '');
					/** Array of all the words in the description */
					const nodeDescriptionWords = nodeDescription.split(' ').filter((e) => e != '');

					/** The weights for each word in the search query (all must be non-zero to match) */
					let currentWeights = [];

					// check for exact matches
					if (nodeName == baseSearchWord) currentWeights.push(10000);
					else if (nodeDescription == baseSearchWord) weight = currentWeights.push(1000);
					else {
						// for each word in the search query
						for (let i = 0; i < lc_vals.length; i++) {
							let inName = false;
							let inDesc = false;
							// start the new array
							currentWeights.push(0);
							/** The current word being compared from the search query */
							const word = lc_vals[i];
							// for each word in the node's name
							for (let j = 0; j < nodeNameSentence.length; j++) {
								/** A word from the name of the node */
								const nodeWord = nodeNameSentence[j];
								// check for an exact match on the word
								if (nodeWord == word) {
									currentWeights[i] += nameWeight;
									break;
								}
								// check for the beginning of a match
								if (nodeWord.startsWith(word)) {
									currentWeights[i] += nameWeight / 2;
									break;
								}
							} // end for loop (each word in node name)
							if (nodeName.includes(word)) {
								currentWeights[i] += nameWeight / 4;
								inName = true;
							}
							// for each word in the description
							for (let j = 0; j < nodeDescriptionWords.length; j++) {
								/** A word from the description of the node */
								const nodeDescWord = nodeDescriptionWords[j];
								// check for an exact match in the description
								if (nodeDescWord == word) {
									currentWeights[i] += descWeight;
									break;
								}
								// check for the beginning of a match
								if (nodeDescWord.startsWith(word)) {
									currentWeights[i] += descWeight / 2;
									break;
								}
							} // end for loop (each word in node description)
							if (nodeDescription.includes(word)) {
								currentWeights[i] += descWeight / 4;
								inDesc = true;
							}
							if (!inName && !inDesc) return undefined;
						} // end for loop (each word in search query)
					} // end else (comparing substrings)

					// check each word matched and sum the total score
					for (let i = 0; i < currentWeights.length; i++) {
						weight += currentWeights[i];
					}

					if (weight <= 0) return undefined;

					// set the total score for sorting (next step)
					weightMap.set(node.name, weight);

					// return that this node should be included in the search
					return node;
				}) // end filter
				.sort((a, b) => {
					const aw = weightMap.get(a.name);
					const bw = weightMap.get(b.name);
					if (aw === undefined || bw === undefined) return 0;
					return bw - aw;
				});
		} else if (props.hideCategories) {
			return nodesWithoutInventoryNodes.value;
		}
		// Return the matching categories when not searching
		return currentCategory.value.nodes.filter(n => !n.isInventoryNode);
	});
</script>

<style scoped>
	.search-container {
		width: 100%;
		padding: 0px 12px;
		margin-bottom: 24px;
	}

	.item-list {
		padding: 0px 10px;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.item-list-title {
		width: 100%;
		margin-bottom: 0.5rem;
		color: var(--color-text-secondary);
		letter-spacing: 1px;
	}

	.empty-text {
		font-size: 0.8rem;
		color: var(--color-text);
		opacity: 0.5;
		font-style: italic;
	}
</style>
