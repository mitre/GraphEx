import type { ModalFormProps } from '@/components/modalForm/ModalFormComponent.vue';
import { defineStore } from 'pinia';
import { reactive, ref } from 'vue';

export interface PromptButton {
	text: string;
	action: string;
	highlight: boolean;
	warning?: boolean;
}

export interface PromptDetails {
	title: string;
	text: string;
	buttons: Array<PromptButton>;
}

type PromptCallbackData = null | { buttonName: string; form: ModalFormProps };
type PromptCallback = (value: PromptCallbackData) => void;

export const usePromptStore = defineStore('prompts', () => {
	/** All prompts currently open (last index is most recent). */
	const prompts = reactive<Array<ModalFormProps>>([]);

	/** (internal) Callbacks for each prompt. */
	const promptsCallbacks = reactive<Array<PromptCallback>>([]);

	/** When True, opens the "About" Modal/Window/Popup for Graphex */
	const aboutOpen = ref<boolean>(false);

	/** When true, opens the 'Open Log File' modal */
	const openLogModalOpen = ref<boolean>(false);

	/**
	 * Show a prompt. Await this call to get the response value for the prompt.
	 * A value of 'null' indicates the close button was clicked, while a non-null value
	 * will contain the button name that was clicked and the state of the form when the button
	 * was clicked.
	 */
	async function show(form: ModalFormProps): Promise<PromptCallbackData> {
		let callback: PromptCallback | null = null;

		const promise = new Promise((resolve: PromptCallback) => {
			callback = resolve;
		});

		if (!callback) {
			return null;
		}

		promptsCallbacks.push(callback);
		prompts.push(form);
		return await promise;
	}

	function complete(value: PromptCallbackData) {
		const cb = promptsCallbacks.pop();
		if (!cb) {
			return;
		}
		cb(value);
		prompts.pop();
	}

	function update(newForm: ModalFormProps, index?: number) {
		if (index !== undefined) {
			prompts[index] = newForm;
		} else {
			prompts[prompts.length - 1] = newForm;
		}
	}

	/**
	 * Popup prompt alert shown to the user when an operation fails.
	 * @param title The title of the failure message
	 * @param msg The message to display to the user
	 */
	async function failedAlert(title: string, msg?: string | undefined) {
		if (msg == undefined) msg = 'No information was provided for this error.';
		await show({
			title: title,
			additionalInfo: msg,
			entries: [],
			buttons: [
				{
					text: 'Ok',
					type: 'primary'
				}
			]
		});
	}

	/**
	 * Opens the modal popup window for 'About Graphex'
	 */
	async function openAboutGraphexModal() {
		aboutOpen.value = true;
	}

	/**
	 * Closes the modal popup window for 'About Graphex'
	 */
	async function closeAboutGraphexModal() {
		aboutOpen.value = false;
	}

	return {
		prompts,
		show,
		complete,
		update,
		aboutOpen,
		openAboutGraphexModal,
		closeAboutGraphexModal,
		failedAlert,
		openLogModalOpen
	};
});
