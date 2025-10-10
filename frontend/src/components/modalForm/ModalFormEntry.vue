<template>
	<div class="modal-form-entry-container">
		<!-- Header -->
		<span class="modal-form-entry-header-container no-select" :togglable="props.togglable" @click.stop="updateToggled">
			<div class="modal-form-entry-header" :error="!!props.error">
				<div class="checkbox" v-if="props.togglable">
					<div class="check-icon material-icons" :checked="props.isToggled">check</div>
				</div>
				{{ props.label }}
				<span class="modal-form-entry-error-icon material-icons" v-if="props.error" :title="props.error"
					>error_outline</span
				>
			</div>
			<div class="icon-bar">
				<span
					class="material-icons modified-icon"
					v-if="props.modified"
					title="This value has been modified from its default value"
					>emergency</span
				>
				<span
					class="material-icons encrypted-icon"
					v-if="props.secret"
					title="This value is encrypted by the configuration file."
					>lock</span
				>
				<span class="material-icons help-icon" v-if="props.help" :title="help">help_outline</span>
			</div>
		</span>

		<!-- The logic here is for passing up the indicies so values can be accessed in a nested structrure
		 input1:
  		 >input2:
         >>input3: 
         >>input4:
         input2:
		
		 If input4's value is update, this is chain of emits:
		 input4 emits
		 {metadata:{name:'',index:-1},value:'new value'}
		 input2 emit2
		 {metadata:{name:input4,index:1},value:'new value'}
		 input1 will emit
		 {metadata:{name:input2,index:0, subMetadata:{name:input4,index:1}},value:'new value'} }
		 The form will emit
	     {metadata:{name:input1,index:0}, subMetadata:{metadata:{name:input2,index:0, subMetadata:{name:input4,index:1}}}},value:'new value'} }

		 For any entry emmited from a form, we can then use this recursive structure to recursively traverse a nested datastructure
		-->
		<template v-if="props.subEntries && props.subEntries.length > 0">
			<div :class="[(props.level || 0) % 2 === 0 ? 'subentries-box-grey' : 'subentries-box-black']">
				<ModalFormEntry
					v-for="(subEntry, index) in props.subEntries"
					:key="index"
					v-bind="{...subEntry,level:(subEntry.level || 0)+1}"
					@toggled="(data:ToggleValue) => emit('toggled', {metadata:subEntryMetadata(index,data.metadata),value: data.value})"
					@update-value="(data:InputValue)=>emit('updateValue', {metadata:subEntryMetadata(index,data.metadata),value: data.value})"
					@remove-list-entry="(data:ListIndexValue) => emit('removeListEntry', {metadata:subEntryMetadata(index,data.metadata),index: data.index })"
					@add-list-entry="(data?:CompositeEntryMetadata) => emit('addListEntry', subEntryMetadata(index,data))"
					@update-list-value="(data:ListInputValue)=>emit('updateListValue', {metadata:subEntryMetadata(index,data.metadata),value: data.value,index:data.index})"
				/>
			</div>
		</template>
		<template v-else>
			<div class="modal-form-entry-field-container" v-if="props.field || Array.isArray(props.fieldList)">
				<!-- Field (non-list) -->
				<template v-if="!props.list && props.field">
					<ModalFormField
						v-bind="props.field"
						@update-value="(value:string)=>emit('updateValue',{value:value, metadata:{name:'',index:-1}})"
						:focus="focus"
					/>
				</template>

				<!-- Field (list) -->
				<template v-if="props.list && Array.isArray(props.fieldList)">
					<span class="modal-form-field-list-item" v-for="(item, index) in props.fieldList" :key="index">
						<ModalFormField
							v-bind="item"
							@update-value="(value: string) => emit('updateListValue', { index: index, value: value, metadata:{name:'',index:-1} })"
						/>
						<span
							class="remove-item-icon material-icons"
							title="Remove value from list."
							@click.stop="() => emit('removeListEntry', { index: index, metadata: { name: '', index: -1 } })"
						>
							close
						</span>
					</span>

					<div class="model-form-field-list-footer">
						<span class="model-form-field-list-empty no-select" v-if="props.fieldList.length == 0"
							>(Empty List...)</span
						>
						<span class="add-item-button" title="Add new value to list." @click.stop="emit('addListEntry')">
							+ Add
						</span>
					</div>
				</template>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
	import type { ModalFormFieldProps } from '@/components/modalForm/ModalFormField.vue';
	import ModalFormField from '@/components/modalForm/ModalFormField.vue';

	export interface ModalFormEntryProps {
		label: string;
		togglable?: true;
		isToggled?: boolean;
		help?: string;
		field?: ModalFormFieldProps;
		list?: boolean;
		fieldList?: Array<ModalFormFieldProps>;
		error?: string | null;
		focus?: boolean;
		category?: string;
		secret?: boolean;
		modified?: boolean;
		subEntries?: Array<ModalFormEntryProps>;
		level?: number;
	}

	export interface EntryMetadata {
		index: number;
		name: string;
	}

	export interface CompositeEntryMetadata {
		name: string;
		index: number;
		subMetadata?: CompositeEntryMetadata;
	}

	export interface InputValue {
		metadata: CompositeEntryMetadata;
		value: string;
	}

	export interface ListInputValue {
		index: number;
		metadata: CompositeEntryMetadata;
		value: string;
	}

	export interface ListIndexValue {
		index: number;
		metadata: CompositeEntryMetadata;
	}

	export interface ToggleValue {
		metadata: CompositeEntryMetadata;
		value: boolean;
	}

	const props = defineProps<ModalFormEntryProps>();

	const emit = defineEmits<{
		(e: 'toggled', newValue: ToggleValue): void;
		(e: 'updateValue', inputValue: InputValue): void;
		(e: 'removeListEntry', index: ListIndexValue): void;
		(e: 'addListEntry', metadata?: CompositeEntryMetadata): void;
		(e: 'updateListValue', data: ListInputValue): void;
	}>();

	function updateToggled() {
		if (!props.togglable) {
			return;
		}

		emit('toggled', { value: !props.isToggled, metadata: { name: '', index: -1, subMetadata: undefined } });
	}

	function subEntryMetadata(index: number, subData?: CompositeEntryMetadata): CompositeEntryMetadata {
		if (props.subEntries) {
			return {
				name: props.subEntries[index].label,
				index: index,
				subMetadata: !subData || subData.index === -1 ? undefined : subData // This is just to get Typescript being annoying.
			};
		} else {
			throw 'subEntryMetadata can not be called if props.subEntries is not defined';
		}
	}
</script>

<style scoped>
	.modal-form-entry-container {
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.modal-form-entry-header-container {
		margin-bottom: 6px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
	}

	.modal-form-entry-header-container:not(:first-child) {
		margin-top: 16px;
	}

	.modal-form-entry-header-container[togglable='false'] {
		padding-left: 2px;
	}

	.modal-form-entry-header-container[togglable='true'] {
		cursor: pointer;
	}

	.modal-form-entry-header {
		font-size: 0.9rem;
		letter-spacing: 1px;
		color: var(--color-primary);
		display: flex;
		flex-direction: row;
		align-items: center;
		flex: 1;
	}

	.modal-form-entry-header[error='true'] {
		color: var(--color-error);
	}

	.modal-form-entry-error-icon {
		margin-left: 3px;
		font-size: 1rem;
		color: var(--color-error);
		cursor: help;
	}

	.modal-form-entry-field-container {
		width: 100%;
		display: flex;
		flex-direction: column;
	}

	.modal-form-entry-container:not(:last-child) .modal-form-entry-field-container {
		margin-bottom: 20px;
	}

	.checkbox {
		margin-right: 6px;
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
		background-color: var(--color-foreground-secondary);
		border: 1px solid var(--color-foreground-tertiary);
		border-radius: 3px;
		padding: 2px;
		cursor: pointer;
	}

	.check-icon {
		font-size: 10px;
		opacity: 0;
	}

	.check-icon[checked='true'] {
		opacity: 1;
	}

	.help-icon {
		margin-left: 6px;
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.6;
		cursor: help;
	}

	.modified-icon {
		margin-left: 6px;
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.6;
	}

	.encrypted-icon {
		margin-left: 6px;
		font-size: 1rem;
		color: var(--color-text);
		opacity: 0.6;
		cursor: help;
	}

	.modal-form-field-list-item {
		margin-top: 4px;
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.remove-item-icon {
		padding: 2px;
		margin-left: 4px;
		font-size: 1rem;
		opacity: 0.6;
		cursor: pointer;
		border-radius: 4px;
	}

	.remove-item-icon:hover {
		background-color: var(--color-foreground-secondary);
		opacity: 1;
	}

	.model-form-field-list-footer {
		flex: 1 0;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		justify-content: flex-start;
	}

	.model-form-field-list-empty {
		font-size: 0.8rem;
		color: var(--color-text-secondary);
		font-style: italic;
		opacity: 0.7;
	}

	.add-item-button {
		margin-top: 6px;
		display: flex;
		padding: 2px 6px;
		font-size: 0.9rem;
		cursor: pointer;
		color: var(--color-text);
		border-radius: 4px;
		opacity: 0.6;
	}

	.add-item-button:hover {
		background-color: var(--color-foreground-secondary);
		opacity: 1;
	}

	.subentries-box-grey {
		border: 2px solid rgb(0, 0, 0); /* Light gray border */
		padding: 16px; /* Space inside the box */
		border-radius: 8px; /* Rounded corners */
		background-color: var(--color-foreground-secondary);/* Light background color */
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Subtle shadow for depth */
		margin-bottom: 16px; /* Space below the box */
	}

	.subentries-box-black {
		border: 2px solid rgb(0, 0, 0); /* Light gray border */
		padding: 16px; /* Space inside the box */
		border-radius: 8px; /* Rounded corners */
		background-color: var(--color-foreground-primary);/* Light background color */
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1); /* Subtle shadow for depth */
		margin-bottom: 16px; /* Space below the box */
	}
</style>
