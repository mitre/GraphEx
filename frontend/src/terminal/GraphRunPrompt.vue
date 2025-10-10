<template>
	<ModalFormComponent
		v-bind="form"
		@close="onClose"
		@toggled="onToggled"
		@update-value="onUpdateValue"
		@remove-list-entry="onRemoveListEntry"
		@add-list-entry="onAddListEntry"
		@update-list-value="onUpdateListValue"
		@button-click="onButtonClick"
	/>
	<ModalConfirmResetDefaultValues
		v-if="showResetConfirmation"
		v-bind="confirmationModalForm"
		@close="showResetConfirmation = false"
		@buttonClick="onConfirmModalButtonClick"
	/>
</template>

<script setup lang="ts">
	import type { ModalConfirmResetDefaultValuesProps } from '@/components/modalForm/ModalConfirmResetDefaultValues.vue';
	import ModalConfirmResetDefaultValues from '@/components/modalForm/ModalConfirmResetDefaultValues.vue';
	import type { ModalFormProps } from '@/components/modalForm/ModalFormComponent.vue';
	import ModalFormComponent from '@/components/modalForm/ModalFormComponent.vue';
	import type {
		CompositeEntryMetadata,
		InputValue,
		ListIndexValue,
		ListInputValue,
		ModalFormEntryProps,
		ToggleValue
	} from '@/components/modalForm/ModalFormEntry.vue';
	// Import types using 'import type'
	import type { CompositeValue, Graph, GraphInputMetadata } from '@/graph';
	import { useMetadataStore, usePromptStore, useSettingsStore, useTerminalStore } from '@/stores';
	import { deepMergeInputValues, type InputValueMetadata } from '@/stores/terminal';
	import { computed, onBeforeUnmount, onMounted, reactive, ref, type ComputedRef } from 'vue';

	const props = defineProps<{
		/** The graph to run. */
		graph: Graph;

		/** The name of this execution. This is typically the graph name. */
		name: string;

		/** The path to the graph on disk for this execution, if available */
		filepath: string | null;
	}>();

	const terminalStore = useTerminalStore();
	const promptStore = usePromptStore();
	const settingsStore = useSettingsStore();
	const metadataStore = useMetadataStore();

	const loading = ref<boolean>(true);

	const inputValues = reactive<Array<CompositeValue>>([]);
	const verboseMode = ref<boolean>(true);
	const showInputs = ref<boolean>(false);
	const saveValues = ref<boolean>(true);
	const minimapWasOpen = ref<boolean>(false);

	const baseValues = ref<{ [inputName: string]: InputValueMetadata }>({});
	const showResetConfirmation = ref<boolean>(false);
	const valuesModifiedFromDefault = ref<boolean>(false);

	const savedRunSettingsKey = computed(() => props.filepath || props.name);

	onMounted(async () => {
		/**
		 * Note: Ensure that this component is re-mounted for each use of this prompt to ensure correct population of `inputValues`
		 */

		loading.value = true;

		if (settingsStore.showMinimap) {
			settingsStore.toggleMinimap();
			minimapWasOpen.value = true;
		}

		// Get the config values for this file
		const payloadResponse = await terminalStore.fetchGraphInputData(props.graph, props.filepath || props.name);

		async function addSubBaseValues(inputMetadata: GraphInputMetadata) {
			if (metadataStore.hasCompositeInput(inputMetadata.datatype)) {
				let compositeData = metadataStore.getCompositeInput(inputMetadata.datatype);

				// Find the config values for the subvalues
				let subPayloadResponse = await terminalStore.fetchGraphInputByNames(
					compositeData.InputMetadata.map((input) => input.name),
					props.filepath || props.name,
					true
				);

				/**
				 * Give precedence to:
				 *  1. Default values or previously entered values
				 *  2. Composite config values within the config file
				 *  3. Primitive inputs found within the config file
				 *
				 *  sshUsername: john
				 *
				 *  sshObject:
				 *	datatype: sshObject
				 *  values:
				 *		sshIP: 1.2.3.4
				 *		sshPassword: password1!
				 *		sshUsername: bob
				 *
				 * In this case, the sshUsername would default to bob. If sshObject composite values was not defined, sshUsername would default to john.
				 */
				baseValues.value = { ...subPayloadResponse['inputs'], ...baseValues.value };
				secretValues.values = { ...subPayloadResponse['secrets'], ...secretValues.values };

				for (const child of compositeData.InputMetadata) {
					addSubBaseValues(child);
				}
			}
		}

		baseValues.value = payloadResponse['inputs'];
		const secretValues: string[] = payloadResponse['secrets'];

		//Get subvalues recursively
		for (const input of props.graph.inputMetadata) {
			await addSubBaseValues(input);
		}

		// Load previous run values
		if (savedRunSettingsKey.value in terminalStore.savedRunSettings) {
			baseValues.value = deepMergeInputValues(
				baseValues.value,
				terminalStore.savedRunSettings[savedRunSettingsKey.value].inputValues
			);
			verboseMode.value = terminalStore.savedRunSettings[savedRunSettingsKey.value].verbose;
			showInputs.value = terminalStore.savedRunSettings[savedRunSettingsKey.value].showInputs;
		}

		const typeToDatatypeMap: { [key: string]: string } = {
			string: 'String',
			number: 'Number',
			boolean: 'Boolean'
		};

		function processCompositeValue(inputMetadata: GraphInputMetadata, baseInput?: InputValueMetadata): CompositeValue {
			const name = inputMetadata.name;
			let value: CompositeValue['value'];
			let presetValue: CompositeValue['presetValue'];
			let children: CompositeValue[] = [];

			// Determine presetValue
			if (inputMetadata.defaultValue !== undefined) {
				presetValue = JSON.parse(JSON.stringify(inputMetadata.defaultValue));
			} else if (baseInput?.value !== undefined) {
				presetValue = JSON.parse(JSON.stringify(baseInput.value));
			} else {
				presetValue = undefined;
			}

			// If the input is a composite
			if (metadataStore.hasCompositeInput(inputMetadata.datatype)) {
				children = metadataStore
					.getCompositeInput(inputMetadata.datatype)
					.InputMetadata.map((childMetadata) => {
						const clone = JSON.parse(JSON.stringify(childMetadata)) as GraphInputMetadata;

						// See if the child value is in the config if there is no baseInput
						const baseChildInput = baseInput?.childValues?.[clone.name] ?? baseValues.value?.[clone.name];
						return processCompositeValue(clone, baseChildInput);
					})
					.filter((child) => child) as CompositeValue[];
			} else {
				// If the input is not a composite
				value = baseInput?.value ?? inputMetadata.defaultValue ?? (inputMetadata.isList ? [] : '');

				// If base input exists and is not a list, align types
				if (baseInput) {
					if (
						!inputMetadata.isList &&
						!Array.isArray(baseInput.value) &&
						typeToDatatypeMap[typeof baseInput.value] === inputMetadata.datatype
					) {
						value = baseInput.value;
					}

					// If base input exists and is a list, align list types
					if (
						inputMetadata.isList &&
						Array.isArray(baseInput.value) &&
						baseInput.value.length > 0 &&
						typeToDatatypeMap[typeof baseInput.value[0]] === inputMetadata.datatype
					) {
						value = baseInput.value;
					}

					// Mark as secret if necessary
					if (baseInput.fromSecret && secretValues.includes(baseInput.fromSecret)) {
						inputMetadata.isSecret = true;
					}
				}
			}

			// Additional secret check for string datatypes
			if (inputMetadata.datatype === 'String' && secretValues.includes(name)) {
				inputMetadata.isSecret = true;
			}

			// Return the composite value as a reactive object
			return reactive({ name, value, metadata: inputMetadata, presetValue: presetValue, children: children });
		}

		// Begin populating values
		const graphInputMetadata: GraphInputMetadata[] = JSON.parse(JSON.stringify(props.graph.inputMetadata));

		for (const inputMetadata of graphInputMetadata) {
			inputValues.push(processCompositeValue(inputMetadata, baseValues.value[inputMetadata.name] ?? undefined));
		}

		loading.value = false;
	});

	function resetDefaultValues(compositeValue: CompositeValue) {
		for (const child of compositeValue.children) {
			resetDefaultValues(child);
		}

		if (compositeValue.presetValue) {
			compositeValue.value = JSON.parse(JSON.stringify(compositeValue.presetValue));
		}
	}

	function onConfirmModalButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (data.buttonName == 'Cancel') {
			showResetConfirmation.value = false;
			return;
		}

		if (data.buttonName == 'Confirm') {
			inputValues.forEach(resetDefaultValues);
			showResetConfirmation.value = false;
		}
	}

	function onButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (data.buttonName == 'Cancel') {
			onClose();
			return;
		}

		if (data.buttonName == 'Run') {
			// Run the graph
			onRun();
			onClose();
		}

		if (data.buttonName === 'Reset Default Values') {
			showResetConfirmation.value = true;
		}
	}

	function onClose() {
		terminalStore.cancelGraphPrompt();
	}

	function defineRunInputs(value: CompositeValue, baseInput: InputValueMetadata | undefined): InputValueMetadata {
		if (value.children.length > 0) {
			let children: { [key: string]: InputValueMetadata } = {};

			for (const child of value.children) {
				let compositeChild = child as CompositeValue;
				children[compositeChild.name] = defineRunInputs(
					compositeChild,
					baseInput?.childValues?.[compositeChild.name] ?? undefined
				);
			}

			return {
				childValues: children,
				datatype: value.metadata.datatype
			};
		} else {
			let inputValue: InputValueMetadata = {
				childValues: {},
				datatype: value.metadata.datatype
			};

			if (baseInput && baseInput.fromSecret) {
				inputValue.fromSecret = baseInput.fromSecret;
			} else if (value.metadata.isSecret) {
				inputValue.fromSecret = value.metadata.name;
			} else {
				inputValue.value = value.value;
			}

			return inputValue;
		}
	}

	function onRun() {
		// Format the values
		const values: { [inputName: string]: InputValueMetadata } = {};
		for (const item of inputValues) {
			values[item.name] = defineRunInputs(item, baseValues.value[item.name] ?? undefined);
		}

		// Save the settings (if requested)
		if (saveValues.value) {
			terminalStore.savedRunSettings[savedRunSettingsKey.value] = {
				inputValues: values,
				verbose: verboseMode.value,
				showInputs: showInputs.value
			};
		}

		// Run graph
		terminalStore.runGraph(props.graph, props.name, props.filepath, {
			inputValues: values,
			verbose: verboseMode.value,
			showInputs: showInputs.value
		});
	}

	function onToggled(data: ToggleValue) {
		if (!data.metadata.subMetadata) {
			if (data.metadata.name == 'Verbose Logs') {
				verboseMode.value = !verboseMode.value;
			} else if (data.metadata.name == 'Save Values') {
				saveValues.value = !saveValues.value;
			} else if (data.metadata.name == 'Show Inputs') {
				showInputs.value = !showInputs.value;
			}
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onUpdateValue(data: InputValue) {
		let baseValue = data.value;

		function setRecursiveValue(data: CompositeEntryMetadata, value: CompositeValue) {
			if (!data.subMetadata) {
				//we are at a base entry
				const valueToSet = coerceValue(value.metadata.datatype, baseValue);
				value.value = valueToSet;
			} else {
				//step through the datastructure to get the input
				setRecursiveValue(data.subMetadata, value.children[data.subMetadata.index]);
			}
		}

		setRecursiveValue(data.metadata, inputValues[data.metadata.index]);
	}

	function onRemoveListEntry(data: ListIndexValue) {
		let baseIndex = data.index;

		function spliceRecursiveValue(data: CompositeEntryMetadata, value: CompositeValue) {
			if (!data.subMetadata) {
				value.value.splice(baseIndex, 1);
			} else {
				spliceRecursiveValue(data.subMetadata, value.children[data.subMetadata.index]);
			}
		}

		spliceRecursiveValue(data.metadata, inputValues[data.metadata.index]);
	}

	function onAddListEntry(data: CompositeEntryMetadata) {
		function addToListRecursive(data: CompositeEntryMetadata, value: CompositeValue) {
			if (!data.subMetadata) {
				const datatype = value.metadata.datatype;
				const enumOptions = value.metadata.enumOptions;
				let valueToAdd: string | number | boolean;
				if (enumOptions !== undefined) {
					valueToAdd = '';
				} else if (datatype == 'String') {
					valueToAdd = '';
				} else if (datatype == 'Number') {
					valueToAdd = 0;
				} else if (datatype == 'Boolean') {
					valueToAdd = false;
				} else {
					throw `Unhandled data type ${datatype}`;
				}
				value.value.push(valueToAdd);
			} else {
				addToListRecursive(data.subMetadata, value.children[data.subMetadata.index]);
			}
		}

		addToListRecursive(data, inputValues[data.index]);
	}

	function onUpdateListValue(data: ListInputValue) {
		let baseValue = data.value;
		let baseIndex = data.index;

		function updateListValueRecursive(data: CompositeEntryMetadata, compositeValue: CompositeValue) {
			if (!data.subMetadata) {
				const valueToSet = coerceValue(compositeValue.metadata.datatype, baseValue);
				compositeValue.value[baseIndex] = valueToSet;
			} else {
				updateListValueRecursive(data.subMetadata, compositeValue.children[data.subMetadata.index]);
			}
		}

		updateListValueRecursive(data.metadata, inputValues[data.metadata.index]);
	}

	/**
	 * Coerce the given string value to the given datatype.
	 *
	 * @param datatype The datatype to coerce to.
	 * @param value The value.
	 *
	 * @returns The value as the given datatype (if possible).
	 */
	function coerceValue(datatype: string, value: string): string | number | boolean {
		if (datatype == 'String') {
			return value;
		}

		if (datatype == 'Number') {
			return value.trim().length && !isNaN(Number(value.trim())) ? Number(value) : value;
		}

		if (datatype == 'Boolean') {
			return value === 'True';
		}

		throw `Unhandled data type ${datatype}`;
	}

	/**
	 * Check whether the given value has an error under the given metadata.
	 *
	 * @param datatype The datatype to associate with this value.
	 * @param value The value to check
	 *
	 * @returns The string error message (if an error exists), or `null` if the value is valid.
	 */
	function getValueError(datatype: string, value: any, isEnum: boolean): string | null {
		if (isEnum) {
			if (String(value).length == 0) {
				return 'This value is required';
			}
		}

		if (datatype === 'String') {
			if (!(typeof value === 'string')) {
				return 'Not a valid string.';
			}

			return null;
		}

		if (datatype == 'Number') {
			if (typeof value === 'number') {
				return null; // Valid number, no need to return anything specific.
			}

			if (!isEnum) {
				return 'not a number';
			}

			if (typeof value === 'string') {
				let valueToCheck: number | undefined;
				valueToCheck = value.trim().length && !isNaN(Number(value.trim())) ? Number(value.trim()) : undefined;
				if (valueToCheck === undefined) {
					return 'not a number';
				}
			} else {
				return 'not a number'; //not sure how this case can happen, but putting it here
			}

			return null;
		}

		if (datatype === 'Boolean') {
			if (!(typeof value === 'boolean')) {
				return 'Not a valid boolean.';
			}

			return null;
		}

		return `Unrecognized datatype: ${datatype}`;
	}
	/**
	 * Test if a primitive type is modified.
	 * @param compositeValue
	 */
	function isModified(compositeValue: CompositeValue): boolean {
		let metadata: GraphInputMetadata = compositeValue.metadata;
		/**
		 * If there is not presetValue, modified is always false.
		 *
		 * We only check if a value is modified for primitives
		 */
		if (
			!compositeValue.presetValue ||
			metadataStore.hasCompositeInput(metadata.datatype) ||
			!['String', 'Number', 'Boolean'].includes(metadata.datatype)
		) {
			return false;
		}

		//See if the list values are modified
		if (metadata.isList) {
			//If they are different sizes it is modified
			if (compositeValue.presetValue.length !== compositeValue.value.length) {
				return true;
			}
			//Otherwise compare every element.
			return !compositeValue.presetValue.every((val: any, index: number) => val === compositeValue.value[index]);
		} else {
			return compositeValue.presetValue !== compositeValue.value;
		}
	}

	//We can assume that any composite input can be filled out with primitives
	function computeEntry(value: CompositeValue): ModalFormEntryProps {
		const entry: ModalFormEntryProps = {
			label: `${value.name}`,
			help: value.metadata.description,
			category: value.metadata.category,
			modified: false
		};

		//Just do a running logical or to keep track if any entry has changed

		if (value.children.length > 0) {
			entry.subEntries = value.children.map(computeEntry);

			if (entry.subEntries.some((subentry) => subentry.error)) {
				entry.error = 'Sub-entries have one or more errors that require resolving';
			}

			entry.modified = entry.subEntries.some((subentry) => subentry.modified);
		} else {
			entry.modified = isModified(value);

			if (value.metadata.isList) {
				entry.list = true;
				entry.fieldList = [];

				const fieldListErrors = [];
				for (const val of value.value || []) {
					const error = getValueError(value.metadata.datatype, val, value.metadata.enumOptions !== undefined);
					if (error) {
						fieldListErrors.push(error);
					}

					if (value.metadata.enumOptions) {
						entry.fieldList.push({
							value: String(val),
							error: error,
							options: value.metadata.enumOptions,
							password: value.metadata.isPassword,
							textTransform: 'none'
						});
					} else {
						entry.fieldList.push({
							value: String(val),
							error: error,
							options: value.metadata.datatype === 'Boolean' ? ['True', 'False'] : undefined,
							password: value.metadata.isPassword
						});
					}
				}

				if (fieldListErrors.length) {
					entry.error = `${fieldListErrors.length} errors.`;
				} else if (value.metadata.defaultValue == undefined && entry.fieldList.length == 0) {
					entry.error = 'At least one value is required.';
				}
			} else {
				let error: string | undefined | null;
				if (value.metadata.defaultValue == undefined && String(value.value).length == 0 && !value.metadata.isSecret) {
					error = 'This value is required.';
				} else {
					error = getValueError(value.metadata.datatype, value.value, value.metadata.enumOptions !== undefined);
				}

				if (error) {
					entry.error = error;
				}

				if (value.metadata.enumOptions) {
					entry.field = {
						value: String(value.value),
						error: error,
						options: value.metadata.enumOptions,
						password: value.metadata.isPassword,
						textTransform: 'none'
					};
				} else {
					entry.field = {
						value:
							value.value === false ? 'False' : String(value.value !== undefined && value !== null ? value.value : ''),
						error: error,
						options: value.metadata.datatype === 'Boolean' ? ['True', 'False'] : undefined,
						password: value.metadata.isPassword
					};
					if (value.metadata.isSecret) {
						entry.field.value = 'Secret will be applied from the config file';
						entry.field.disabled = true;
						if (!entry.help) entry.help = '';
						entry.help += ' This value is being set by an encrypted secret in the configuration file.';
						entry.field.password = false;
						entry.error = null;
						entry.secret = true;
					}
				}
			}
		}

		value.isModified = entry.modified;

		return entry;
	}
	const form: ComputedRef<ModalFormProps> = computed(() => {
		const entries: Array<ModalFormEntryProps> = inputValues.map(computeEntry);

		entries.push({
			label: 'Verbose Logs',
			togglable: true,
			isToggled: verboseMode.value,
			help: 'Whether to enable verbose logs (debug mode).'
		});

		entries.push({
			label: 'Save Values',
			togglable: true,
			isToggled: saveValues.value,
			help: 'Whether to save values for future runs.'
		});

		entries.push({
			label: 'Show Inputs',
			togglable: true,
			isToggled: showInputs.value,
			help: 'Whether to show the provided inputs at the top of the terminal (passwords will be replaced with asterisks of equal length).'
		});

		return {
			title: `Graph Input Values for '${props.filepath || props.name}'`,
			entries: entries,
			buttons: [
				{
					text: 'Run',
					type: 'primary',
					disabled: entries.some((entry) => entry.error)
				},
				{
					text: 'Cancel',
					type: 'warning'
				},
				{
					text: 'Reset Default Values',
					type: 'secondary',
					disabled: !entries.some((entry) => entry.modified)
				}
			],
			loading: loading.value
		};
	});

	const confirmationModalForm: ComputedRef<ModalConfirmResetDefaultValuesProps> = computed(() => {
		return {
			title: 'Reset Fields',
			content: inputValues,
			buttons: [
				{
					text: 'Confirm',
					type: 'primary'
				},
				{
					text: 'Cancel',
					type: 'secondary'
				}
			]
		};
	});

	onBeforeUnmount(() => {
		if (minimapWasOpen.value) {
			settingsStore.toggleMinimap();
		}
	});
</script>

<style scoped></style>
