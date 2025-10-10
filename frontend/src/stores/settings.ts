import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useSettingsStore = defineStore('settings', () => {
	/** Whether the minimap is currently being shown or not. */
	const showMinimap = ref<boolean>(false);

	/** Toggle the visibility of the minimap. */
	function toggleMinimap() {
		showMinimap.value = !showMinimap.value;
	}

	return {
		showMinimap,
		toggleMinimap
	};
});
