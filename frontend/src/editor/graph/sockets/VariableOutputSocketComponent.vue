<template>
    <div
        v-if="$props.socket.metadata.allowsVariable"
        class="variable-output-socket no-select"
        :title="variableTextTitle"
    >
        <BooleanCheckboxInput class="variable-output-socket-checkbox" :value="!props.socket.disabledVariableOutput" @update="updateDisabledVariableValue" />
        <div class="variable-output-socket-text">Save To Variable</div>
    </div>
</template>

<script setup lang="ts">
import BooleanCheckboxInput from '@/editor/graph/inputs/BooleanCheckboxInput.vue';
import type { Socket } from '@/graph';
import { computed } from 'vue';

const props = defineProps<{
		socket: Socket;
	}>();

    function updateDisabledVariableValue() {
		props.socket.disabledVariableOutput = !props.socket.disabledVariableOutput;
	}

	const variableTextTitle = computed(() => {
		return "Save the output of this socket to a variable called: " + props.socket.metadata.name + " ... The previous value of the variable will be overwritten if it already exists.";
	})
</script>

<style scoped>
	.variable-output-socket {
		display: flex;
		flex-direction: row;
		font-size: 8px;
		float: left;
	}

	.variable-output-socket-checkbox {
		font-size: 8px;
	}

	.variable-output-socket-text {
		padding-top: 2.5px;
		padding-left: 1.5px;
        color: var(--color-text);
        opacity: 0.8;
	}

    :deep(.boolean-check-icon) {
        font-size: 8px;
    }
</style>
