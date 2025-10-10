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
</template>

<script setup lang="ts">
	import type { ButtonProps } from '@/components/ButtonComponent.vue';
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
	import { DYNAMIC_DATATYPE, type CompositeGraphInputMetadata, type Graph, type GraphInputMetadata } from '@/graph';
	import { useEditorStore, useFileStore, useMetadataStore, usePromptStore, useTerminalStore } from '@/stores';
	import type { InputValueMetadata } from '@/stores/terminal';
	import { computed, onMounted, ref, type ComputedRef } from 'vue';
	const props = defineProps<{
		/** The graph that this input belongs to */
		graph: Graph;

		/** The input metadata to configure. */
		metadata: GraphInputMetadata;

		/** Whether to treat this as a new input rather than configuring an existing one. */
		isNew?: boolean;
	}>();

	const emit = defineEmits<{
		(e: 'close'): void;
		(e: 'save', metadata: GraphInputMetadata): void;
	}>();

	const metadataStore = useMetadataStore();
	const promptStore = usePromptStore();
	const terminalStore = useTerminalStore();
	const editorStore = useEditorStore();
	const fileStore = useFileStore();

	/** The current values from the config file, it is updated via the function: fetchConfigData() */
	const configFileValues = ref<{ [inputName: string]: any }>({});
	const secretValues = ref<string[]>([]);

	async function onButtonClick(data: { buttonIndex: number; buttonName: string }) {
		if (data.buttonName == 'Save') {
			await onSave();
		}

		if (data.buttonName == 'Close') {
			await onClose();
		}
	}

	async function onClose() {
		if (hasChanges.value) {
			const buttons: Array<ButtonProps> = [
				{
					text: 'Discard Changes',
					type: 'warning'
				},
				{
					text: 'Cancel',
					type: 'secondary'
				}
			];

			if (!hasError.value) {
				buttons.unshift({
					text: 'Save Changes',
					type: 'primary'
				});
			}

			const value = await promptStore.show({
				title: 'Unsaved Changes',
				additionalInfo: 'You have unsaved changes to this graph input.',
				entries: [],
				buttons: buttons
			});

			if (!value || value.buttonName == 'Cancel') {
				return;
			}

			if (value.buttonName == 'Save Changes') {
				await onSave();
				return;
			}
		}

		emit('close');
	}

	async function onSave() {
		// Check if adding this input will make this graph not directly executable
		// This occurs if the datatype for this graph is a non-primitive, and if the graph isn't already non-directly executable
		// Show an alert if this is the case
		const isNonPrimitive = (datatype: string) => !['String', 'Number', 'Boolean'].includes(datatype);
		const alreadyHasNonPrimitives = !!props.graph.inputMetadata.find((metadata) => isNonPrimitive(metadata.datatype));
		if (!alreadyHasNonPrimitives && isNonPrimitive(datatype.value) && !metadataStore.hasCompositeInput(datatype.value)) {
			const value = await promptStore.show({
				title: 'Warning: Non-Primitive Data Type Selected',
				additionalInfo:
					'You have selected a non-primitive data type for this graph input.\n\nBy adding this input, this graph will no longer be directly executable and will only be able to be executed by other graphs (this behavior can be overwritten by a developer in the future).',
				entries: [],
				buttons: [
					{
						text: 'Add Input',
						type: 'warning'
					},
					{
						text: 'Cancel',
						type: 'secondary'
					}
				]
			});

			if (!value || value.buttonName === 'Cancel') {
				return;
			}
		}

		// Save and exit
		emit('save', {
			name: inputName.value,
			datatype: datatype.value,
			isList: isList.value,
			isPassword: isPassword.value,
			description: description.value,
			defaultValue: defaultValue.value,
			category: category.value,
			enumOptions: enumOptions.value
		});

		emit('close');
	}

	function onToggled(data: ToggleValue) {
		if (!data.metadata.subMetadata) {
			if (data.metadata.name == 'Default Value' || data.metadata.name == 'Default Value (List)') {
				onDefaultValueToggle();
			}

			if (data.metadata.name == 'Fix Input From Preset Values?') {
				onToggleIsEnum();
			}
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onUpdateValue(data: InputValue) {
		if (!data.metadata.subMetadata) {
			if (data.metadata.name == 'Input Name') updateInputName(data.value);
			if (data.metadata.name == 'Data Type') updateDataType(data.value);
			if (data.metadata.name == 'Is List?') updateIsList(data.value);
			//if (data.entryName == 'Fix Input From Preset Values?') updateIsEnum(data.value);
			if (data.metadata.name == 'Hide Text?') updateIsPassword(data.value);
			if (data.metadata.name == 'Description') updateDescription(data.value);
			if (data.metadata.name == 'Category') updateCategory(data.value);
			if (data.metadata.name == 'Default Value') updateDefaultValue(data.value);
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onRemoveListEntry(data: ListIndexValue) {
		if (!data.metadata.subMetadata) {
			if (data.metadata.name == 'Default Value (List)') removeDefaultValue(data.index);

			if (data.metadata.name == 'Fixed Values') removeEnumValue(data.index);
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onAddListEntry(data: CompositeEntryMetadata) {
		if (!data.subMetadata) {
			if (data.name == 'Default Value (List)') addNewDefaultValue();

			if (data.name == 'Fixed Values') addEnumDefaultValue();
		} else {
			throw 'Recursion not implemented';
		}
	}

	function onUpdateListValue(data: ListInputValue) {
		if (!data.metadata.subMetadata) {
			if (data.metadata.name == 'Default Value (List)') updateDefaultValue(data.value, data.index);

			if (data.metadata.name == 'Fixed Values') updateEnumValue(data.value, data.index);
		} else {
			throw 'Recursion not Implemented';
		}
	}

	/****************
	 * Input Name
	 ****************/
	const inputName = ref<string>(props.metadata.name);
	function updateInputName(value: string) {
		inputName.value = value;
	}

	const inputNameError = computed(() => {
		if (inputName.value.trim().length == 0) {
			return 'Name cannot be empty.';
		}

		// Ensure no duplicate name
		if (props.graph.inputMetadata.some((x) => x.name.trim() == inputName.value.trim() && x !== props.metadata)) {
			return 'Another input exists with the same name.';
		}

		// Check for name validity
		if (!/^[a-zA-Z0-9]+$/.test(inputName.value.trim())) {
			return 'Name must consist of letters and numbers only.';
		}

		return null;
	});

	/****************
	 * Data Type
	 ****************/
	const datatype = ref<string>(props.metadata.datatype);
	function updateDataType(option: string) {
		datatype.value = option;
		defaultValue.value = undefined;
	}

	const dataTypeOptions = computed(() => {
		return metadataStore.dataTypes
			.filter((dt) => dt.name != DYNAMIC_DATATYPE)
			.map((dt) => dt.name)
			.sort((a, b) => a.localeCompare(b));
	});

	const datatypeIsBasicType = computed(() => {
		return datatype.value == 'String' || datatype.value == 'Number' || datatype.value == 'Boolean';
	});

	/****************
	 * Is List
	 ****************/
	const isList = ref<boolean | undefined>(props.metadata.isList);
	function updateIsList(option: string) {
		isList.value = option === 'True' ? true : undefined;
		if (isList.value && defaultValue.value !== undefined && !Array.isArray(defaultValue.value)) {
			defaultValue.value = [defaultValue.value];
		} else if (!isList.value && Array.isArray(defaultValue.value)) {
			defaultValue.value = defaultValue.value.length > 0 ? defaultValue.value[0] : undefined;
		}
	}

	/****************
	 * Is Enum
	 ****************/
	const enumOptions = ref<string[] | undefined>(
		props.metadata.enumOptions !== undefined ? JSON.parse(JSON.stringify(props.metadata.enumOptions)) : undefined
	);

	function onToggleIsEnum() {
		//If we are toggeling on, we want to erase all entered default values
		defaultValue.value = enumOptions.value === undefined ? undefined : defaultValue.value;

		if (enumOptions.value === undefined) {
			enumOptions.value = [];
			//Add a value
			addEnumDefaultValue();
		} else if (enumOptions.value !== undefined) {
			enumOptions.value = undefined;
		}
	}

	/****************
	 * Is Password
	 ****************/
	const isPassword = ref<boolean | undefined>(props.metadata.isPassword);
	function updateIsPassword(option: string) {
		isPassword.value = option === 'True' ? true : undefined;
	}

	/****************
	 * Description
	 ****************/
	const description = ref<string | undefined>(props.metadata.description);
	function updateDescription(value: string) {
		if (value.trim() == '') {
			description.value = undefined;
			return;
		}
		description.value = value;
	}

	/****************
	 * Category
	 ****************/
	const category = ref<string | undefined>(props.metadata.category);
	function updateCategory(value: string) {
		if (value.trim() == '') {
			category.value = undefined;
			return;
		}
		category.value = value;
	}

	const categoryError = computed(() => {
		if ((category.value || '').trim().toLowerCase() == 'default') {
			return 'Category with name "Default" is reserved';
		}
		return null;
	});

	/****************
	 * Default Value
	 ****************/
	const defaultValue = ref<string | number | boolean | Array<string | number | boolean> | undefined>(
		props.metadata.defaultValue !== undefined ? JSON.parse(JSON.stringify(props.metadata.defaultValue)) : undefined
	);

	function onDefaultValueToggle() {
		if (defaultValue.value === undefined) {
			// Enable default value
			addNewDefaultValue();
			return;
		}

		// Disable default value
		defaultValue.value = undefined;
		return;
	}

	function addNewDefaultValue() {
		const defaults: { [datatype: string]: string | number | boolean } = { String: '', Number: 0, Boolean: false };
		if (!(datatype.value in defaults)) {
			throw `Unhandled data type ${datatype.value}`;
		}

		const valueToAdd = enumOptions.value ? enumOptions.value[0] : defaults[datatype.value];

		if (isList.value) {
			if (Array.isArray(defaultValue.value)) {
				defaultValue.value.push(valueToAdd);
			} else {
				defaultValue.value = [valueToAdd];
			}
		} else {
			defaultValue.value = valueToAdd;
		}
	}

	function addEnumDefaultValue() {
		const defaults: { [datatype: string]: string | number } = { String: '', Number: 0 };

		if (!(datatype.value in defaults)) {
			throw `Unhandled data type ${datatype.value}`;
		}

		const valueToAdd = defaults[datatype.value];

		if (Array.isArray(enumOptions.value)) {
			enumOptions.value.push(String(valueToAdd));
		} else {
			enumOptions.value = [String(valueToAdd)];
		}
	}

	function removeDefaultValue(index: number) {
		if (!Array.isArray(defaultValue.value)) {
			return;
		}

		defaultValue.value.splice(index, 1);

		//	if (isEnum.value && defaultValue.value.length==0){
		//		onDefaultValueToggle()
		//	}
	}

	function removeEnumValue(index: number) {
		if (!enumOptions.value) {
			throw 'enumOptions is undefined.';
		}

		if (index < 0 || index > enumOptions.value.length) {
			throw 'index is out of range of enumOptions';
		}

		const enum_value = enumOptions.value[index];

		//If we remove an enum value, we need to remove the value from the default value if it was set to that
		if (defaultValue.value !== undefined) {
			if (Array.isArray(defaultValue.value)) {
				if (defaultValue.value.includes(enum_value)) removeDefaultValue(defaultValue.value.indexOf(enum_value));
			} else {
				if (defaultValue.value === enum_value) onDefaultValueToggle();
			}
		}

		enumOptions.value.splice(index, 1);

		if (enumOptions.value.length == 0) {
			onToggleIsEnum();
		}
	}

	function updateDefaultValue(newValue: string, index?: number) {
		if (defaultValue.value === undefined) {
			throw 'Cannot update undefined default value';
		}

		let valueToSet: string | number | boolean;

		if (datatype.value == 'String') {
			valueToSet = newValue;
		} else if (datatype.value == 'Number') {
			valueToSet = newValue.trim().length && !isNaN(Number(newValue.trim())) ? Number(newValue) : newValue;
		} else if (datatype.value == 'Boolean') {
			valueToSet = newValue === 'True';
		} else {
			throw `Unhandled data type ${datatype.value}`;
		}

		if (Array.isArray(defaultValue.value)) {
			if (index === undefined) throw `Index required when updating array default value`;
			defaultValue.value[index] = valueToSet;
		} else {
			defaultValue.value = valueToSet;
		}
	}

	function updateEnumValue(newValue: string, index: number) {
		if (!enumOptions.value) {
			throw 'EnumOptions is not defined';
		}
		//grab the old value
		const enum_value = enumOptions.value[index];

		enumOptions.value[index] = newValue;

		if (defaultValue.value !== undefined) {
			if (Array.isArray(defaultValue.value)) {
				if (defaultValue.value.includes(enum_value)) removeDefaultValue(defaultValue.value.indexOf(enum_value));
			} else {
				if (defaultValue.value === enum_value) onDefaultValueToggle();
			}
		}
	}

	const defaultValueErrors = computed(() => {
		if (defaultValue.value === undefined) {
			return [];
		}

		const defaultValueArray = Array.isArray(defaultValue.value) ? defaultValue.value : [defaultValue.value];
		return defaultValueArray.map((val) => {
			if (datatype.value == 'String' && typeof val !== 'string') {
				return 'Not a string';
			}

			if (datatype.value == 'Boolean' && typeof val !== 'boolean') {
				return 'Not a boolean';
			}

			if (datatype.value == 'Number') {
				if (typeof val === 'number') {
					return; // Valid number, no need to return anything specific.
				}

				if (enumOptions.value === undefined) {
					return 'not a number';
				}

				if (typeof val === 'string') {
					let valueToCheck: number | undefined;
					valueToCheck = val.trim().length && !isNaN(Number(val.trim())) ? Number(val.trim()) : undefined;
					if (valueToCheck === undefined) {
						return 'not a number';
					}
				} else {
					return 'not a number'; //not sure how this case can happen, but putting it here
				}
			}
		});
	});

	const enumEntryErrors = computed(() => {
		if (enumOptions.value === undefined) {
			return [];
		}

		const enumOptionsValueArray = Array.isArray(enumOptions.value) ? enumOptions.value : [enumOptions.value];
		const seenValues = new Set(); // This Set will store the values we've seen so far

		return enumOptionsValueArray.map((val) => {
			// Check if the current value has already been seen
			if (seenValues.has(val.toUpperCase())) {
				return 'Value has been previously added (must be case sensitive)';
			}
			// Add the current value to the Set
			seenValues.add(val.toUpperCase());

			if (datatype.value == 'String' && typeof val !== 'string') {
				return 'Not a string';
			} else if (datatype.value == 'Number') {
				let valueToCheck: number | undefined;
				valueToCheck = val.trim().length && !isNaN(Number(val.trim())) ? Number(val) : undefined;
				if (valueToCheck === undefined) {
					return 'not a number';
				}
			}

			return null;
		});
	});
	function computeConfigEntry(
		name: string,
		inputValue: InputValueMetadata | undefined,
		compositeInput: CompositeGraphInputMetadata | undefined
	): ModalFormEntryProps {
		// We could not find a value of a input
		if (!inputValue) {
			if (secretValues.value.includes(name)) {
				return {
					label: name,
					help: 'This secret is being set by the configuration file. It can only be viewed using the \'vault\' option on the GraphEx CLI. This overwrites any default value set in this popup modal.',
					field: {
						value: "This value is an encrypted secret.",
						disabled: true
					},
					secret: true
				};
			} else {
				return {
					label: name,
					help: 'This input was not found in the configuration input or it\'s value is empty.',
					field: {
						value: 'Unset Value',
						disabled: true
					},
					secret: true
				};
			}
		} else if (!compositeInput) {
			if (
				'fromSecret' in inputValue &&
				inputValue['fromSecret'] &&
				secretValues.value.includes(inputValue['fromSecret'])
			) {
				return {
					label: name,
					help: "This secret is being set by the configuration file. It can only be viewed using the 'vault' option on the GraphEx CLI. This overwrites any default value set in this popup modal.",
					field: {
						value: 'This value is an encrypted secret.',
						disabled: true
					},
					secret: true
				};
			} else if ('value' in inputValue) {
				return {
					label: name,
					help: 'This is the value that is being set by the configuration file. This overwrites any default value set in this popup modal.',
					field: {
						value: String(inputValue['value']),
						disabled: true,
						password: isPassword.value
					}
				};
			} else {
				throw 'Something is not right here!';
			}
		} else {
			/**
			 * The logic for config values on composite is lenient. That is it will try and pick up all datatypes that exist for a config value,
			 * and ignore inputs that aren't needed.
			 *
			 * For example, if we had a version to ESXiClient
			 *
			 * ip: ...
			 * username: ...
			 * password: ...
			 * -> version: ...
			 *
			 * We will still assign the values for ip, username, password from the config if version is not defined.
			 *
			 * Similarly, if we decided later on to remove 'version' and it is still in the config, 'version' is just ignored.
			 */
			return {
				label: name,
				help: 'This is the value that is being set by the configuration file. This overwrites any default value set in this popup modal.',
				subEntries: compositeInput.InputMetadata.map((input) =>
					computeConfigEntry(
						input.name,
						inputValue['childValues'][input.name] ?? undefined,
						metadataStore.hasCompositeInput(input.datatype)
							? metadataStore.getCompositeInput(input.datatype)
							: undefined
					)
				)
			};
		}
	}

	/****************
	 * Form
	 ****************/
	const hasChanges = computed(() => {
		return (
			inputName.value.trim() !== props.metadata.name ||
			datatype.value !== props.metadata.datatype ||
			isList.value !== props.metadata.isList ||
			isPassword.value !== props.metadata.isPassword ||
			description.value !== props.metadata.description ||
			category.value !== props.metadata.category ||
			JSON.stringify(defaultValue.value) !== JSON.stringify(props.metadata.defaultValue) ||
			JSON.stringify(enumOptions.value) !== JSON.stringify(props.metadata.enumOptions)
		);
	});

	const hasError = computed(() => {
		return !!(
			inputNameError.value ||
			categoryError.value ||
			defaultValueErrors.value.some((val) => !!val) ||
			enumEntryErrors.value.some((val) => !!val)
		);
	});

	const form: ComputedRef<ModalFormProps> = computed(() => {
		const entries: Array<ModalFormEntryProps> = [];

		entries.push({
			label: 'Input Name',
			help: 'The name of the input as used in the graph. Changing this value here will update all nodes in the graph.',
			field: {
				value: inputName.value,
				error: inputNameError.value
			},
			focus: true
		});

		entries.push({
			label: 'Data Type',
			help: 'The data type for this graph input.',
			field: {
				value: datatype.value,
				options: dataTypeOptions.value
			}
		});

		entries.push({
			label: 'Is List?',
			help: 'Whether this input should accept a list of values rather than just a single value.',
			field: {
				value: isList.value ? 'True' : 'False',
				options: ['True', 'False']
			}
		});

		if (datatype.value == 'String' && enumOptions.value === undefined) {
			entries.push({
				label: 'Hide Text?',
				help: 'Whether this input should have its text obfuscated or not.',
				field: {
					value: isPassword.value ? 'True' : 'False',
					options: ['True', 'False']
				}
			});
		}

		entries.push({
			label: 'Description',
			help: 'The description for graph input. Meant solely for informational purposes.',
			field: {
				value: description.value || ''
			}
		});

		entries.push({
			label: 'Category',
			help: 'Which tab to organize this input under when running from the UI.',
			field: {
				value: category.value || '',
				error: categoryError.value
			}
		});

		if (datatype.value == 'String' || datatype.value == 'Number') {
			entries.push({
				label: 'Fix Input From Preset Values?',
				help: 'Whether this input should be selected from a list of values.',
				togglable: true,
				isToggled: enumOptions.value !== undefined
			});

			if (enumOptions.value !== undefined) {
				const entry: ModalFormEntryProps = {
					label: 'Fixed Values',
					list: true,
					help: 'The enum values'
				};

				if (enumOptions.value !== undefined) {
					const fieldList = enumOptions.value.map((value, index) => {
						return {
							value: String(value),
							error: enumEntryErrors.value[index]
						};
					});
					entry.fieldList = fieldList;
				}
				entries.push(entry);
			}
		}

		if (
			datatypeIsBasicType.value ||
			(datatypeIsBasicType.value && enumOptions.value !== undefined && enumOptions.value.length)
		) {
			const entry: ModalFormEntryProps = {
				label: 'Default Value' + (isList.value ? ' (List)' : ''),
				togglable: true,
				isToggled: defaultValue.value !== undefined,
				list: !!isList.value,
				help: 'The default value for this graph input. By providing a default value, the user will no longer be required to provide an input value (i.e. this graph input will not be required).'
			};

			if (defaultValue.value !== undefined) {
				const defaultValues = Array.isArray(defaultValue.value) ? defaultValue.value : [defaultValue.value];

				const fieldList = defaultValues.map((value, index) => {
					if (enumOptions.value !== undefined) {
						return {
							value: String(value),
							error: defaultValueErrors.value[index],
							options: enumOptions.value,
							textTransform: 'none'
						};
					} else {
						return {
							value: String(value),
							error: defaultValueErrors.value[index],
							options: datatype.value === 'Boolean' ? ['True', 'False'] : undefined
						};
					}
				});

				if (isList.value) {
					entry.fieldList = fieldList;
				} else {
					entry.field = fieldList[0];
				}
			}

			entries.push(entry);
		}

		if (secretValues.value.includes(inputName.value) || inputName.value in configFileValues.value) {
			let entry = computeConfigEntry(
				inputName.value,
				configFileValues.value[inputName.value],
				metadataStore.hasCompositeInput(datatype.value) ? metadataStore.getCompositeInput(datatype.value) : undefined
			);

			entry.label = 'Current Configuration File Value:';
			entries.push(entry);
		}

		return {
			title: props.isNew ? 'New Graph Input' : `Graph Input Settings for '${props.metadata.name}'`,
			entries: entries,
			buttons: [
				{
					text: 'Save',
					type: 'primary',
					disabled: (!hasChanges.value && !props.isNew) || hasError.value
				},
				{
					text: 'Close',
					type: 'secondary'
				}
			]
		};
	});

	/**
	 * Grabs the current values from the configuration file (expensive)
	 */
	async function fetchConfigData() {
		const pathOrName = editorStore.activeGraphTab!.fileId
			? fileStore.getFilePath(editorStore.activeGraphTab!.fileId)
			: editorStore.activeGraphTab!.name;
		const payloadResponse = await terminalStore.fetchGraphInputData(props.graph, pathOrName, true);
		configFileValues.value = payloadResponse['inputs'];
		secretValues.value = payloadResponse['secrets'];
	}

	onMounted(async () => {
		fetchConfigData();
	});
</script>

<style scoped></style>
