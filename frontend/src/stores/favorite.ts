/**
 * Pinia store that keeps track of which nodes the user has favorited.
 * Updates the browser 'localStorage' to cache the favorite nodes for different clients.
 */

import { defineStore } from 'pinia';
import { computed, reactive } from 'vue';

export const useFavoriteStore = defineStore('favorite', () => {
	/** The nodes favorited by the user. Updates based on the browser localStorage. */
	const favoritedNodes = reactive<Set<String>>(new Set());

	/** The key to use when referencing the browser cache localStorage */
	const favoriteNodesKeyName: string = 'favoriteNodes';

	/** Returns if the specified nodeName has been favorited or not. */
	const isFavorited = computed(() => {
		return (nodeName: string) => {
			return favoritedNodes.has(nodeName.toLowerCase());
		};
	});

	/** Favorite a node (see clickFavorite()). */
	function favoriteNodeName(nodeName: string) {
		favoritedNodes.add(nodeName.toLowerCase());
	}

	/** Remove a node as favorite (see clickFavorite()) */
	function removeFavoriteNode(nodeName: string) {
		favoritedNodes.delete(nodeName.toLowerCase());
	}

	/** Updates the browser localStorage to match the favoritedNodes object */
	function updateLocalStorage() {
		if (localStorage) {
			localStorage.clear();
			localStorage.setItem(favoriteNodesKeyName, JSON.stringify([...favoritedNodes]));
		}
	}

	/** Updates this Pinia store with the values from the browser localStore. */
	function getLocalStorageValues() {
		if (localStorage) {
			const favoriteData = localStorage.getItem(favoriteNodesKeyName);
			if (favoriteData) {
				const data: Array<string> = JSON.parse(favoriteData);
				// console.log('Favorite data from localStorage:', data);
				if (data && data.length > 0) {
					data.forEach((entry: string) => {
						favoriteNodeName(entry);
					});
				}
			}
		}
	}

	/** Toggle a node to be favorited or 'un-favorited' */
	function clickFavorite(nodeName: string) {
		// Update the pinia store references
		if (favoritedNodes.has(nodeName.toLowerCase())) {
			removeFavoriteNode(nodeName);
		} else {
			favoriteNodeName(nodeName);
		}
		// Update the browser localStorage
		updateLocalStorage();
	}

	return {
		isFavorited,
		clickFavorite,
		getLocalStorageValues
	};
});
