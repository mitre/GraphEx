<template>
	<div class="modal-container">
		<div class="modal-popup">
			<div class="modal-header no-select">
				<span class="modal-title" :title="title">{{ props.title }}</span>
				<div class="icons">
					<span class="material-icons modal-help" :title="props.help" @click.self.stop.prevent v-if="props.help">
						help_outline
					</span>
					<span class="material-icons modal-close" title="Close" @click.self.stop.prevent="close" v-if="!noClose">
						close
					</span>
				</div>
			</div>
			<div class="modal-contents">
				<slot name="contents"></slot>
			</div>
			<div class="modal-footer">
				<slot name="footer"></slot>
			</div>
			<div class="modal-tabs">
				<slot name="tabs"></slot>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	const props = defineProps<{
		title: string;
		noClose?: boolean;
		help?: string;
	}>();

	const emit = defineEmits<{
		(e: 'close'): void;
	}>();

	function close() {
		emit('close');
	}
</script>

<style scoped>
	.modal-container {
		width: 100vw;
		height: 100vh;
		position: fixed;
		top: 0px;
		left: 0px;
		z-index: 99;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(0, 0, 0, 0.6);
	}

	.modal-popup {
		padding: 16px;
		box-shadow: 0px 0px 8px 4px rgba(0, 0, 0, 0.4);
		background-color: var(--color-foreground-primary);
		border-radius: 5px;
		display: flex;
		flex-direction: column;
		justify-content: flex-start;
		align-items: flex-start;
	}

	.modal-header {
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
	}

	.modal-title {
		font-size: 1.3rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		color: var(--color-text);
	}

	.modal-close {
		font-size: 1.4em;
		color: var(--color-text);
		cursor: pointer;
		opacity: 0.6;
	}

	.modal-close:hover {
		opacity: 1;
	}

	.modal-help {
		font-size: 1.4em;
		color: var(--color-text);
		cursor: help;
		opacity: 0.6;
	}

	.modal-contents {
		margin-top: 0.5rem;
		padding: 0.5em 0px;
		width: 100%;
		flex: 1 1;
		display: flex;
		flex-direction: column;
	}

	.modal-footer {
		margin-top: 0.5rem;
		padding: 0.5em;
		width: 100%;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: flex-end;
	}

	.modal-tabs {
		overflow: auto;
		width: 100%;
	}

	.modal-tabs:not(:empty) {
		padding: 16px;
	}
</style>
