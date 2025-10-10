<template>
    <div :style="dynamicStyle" @click.stop.prevent="onClick" class="entry-name">{{ props.entryName }}</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
    const props = defineProps<{
		entryName: string;
        selected: boolean;
        index: number;
	}>();

    const emit = defineEmits<{
		(e: 'click', entryIndex: number): void;
	}>();

    function onClick(event: MouseEvent) {
		emit('click', props.index);
	}

    const dynamicStyle = computed(() => {
        if (props.selected) {
            return {
                "color": "var(--color-primary)",
                "background-color": "var(--color-foreground-secondary)"
            };
        }
        return {};
    });
</script>

<style scoped>
    .entry-name {
		color: var(--color-text);
		cursor: pointer;
        width: 100%;
        height: 100%;
	}

	.entry-name:hover {
		background-color: var(--color-foreground-secondary);
	}
</style>