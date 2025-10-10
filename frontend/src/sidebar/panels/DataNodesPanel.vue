<template>
	<NodesPanel header="Nodes" :nodes="nodes" />
</template>

<script setup lang="ts">
	import { computed } from 'vue';
	import NodesPanel from '@/sidebar/nodePanel/NodesPanel.vue';
	import { useMetadataStore } from '@/stores';

	const metadataStore = useMetadataStore();

	const nodes = computed(() => {
		return metadataStore.nodes;
	});
</script>
