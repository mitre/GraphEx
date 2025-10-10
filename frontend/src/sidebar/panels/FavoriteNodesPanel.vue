<template>
	<NodesPanel header="Favorite Nodes" :nodes="nodes" :hide-categories="true" />
</template>

<script setup lang="ts">
	import { computed, onMounted } from 'vue';
	import NodesPanel from '@/sidebar/nodePanel/NodesPanel.vue';
	import { useMetadataStore, useFavoriteStore } from '@/stores';

	const metadataStore = useMetadataStore();
	const favoriteStore = useFavoriteStore();

	const nodes = computed(() => {
		return metadataStore.nodes.filter((node) => favoriteStore.isFavorited(node.name));
	});

	onMounted(() => {
		favoriteStore.getLocalStorageValues();
	});
</script>
