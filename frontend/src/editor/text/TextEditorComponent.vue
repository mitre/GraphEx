<template>
	<div class="text-editor-container custom-scrollbar" ref="containerRef"></div>
</template>

<script setup lang="ts">
	import { useContextmenuStore, useEditorStore } from '@/stores';
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

	import { autocompletion, closeBrackets } from '@codemirror/autocomplete';
import {
	redo as cmRedo,
	undo as cmUndo,
	defaultKeymap,
	history,
	historyKeymap,
	insertNewline,
	redoDepth,
	undoDepth
} from '@codemirror/commands';
import { bracketMatching, indentOnInput, indentUnit, syntaxHighlighting } from '@codemirror/language';
import { search, searchKeymap } from '@codemirror/search';
import { Compartment, Prec } from '@codemirror/state';
import {
	EditorView,
	ViewUpdate,
	highlightActiveLine,
	highlightActiveLineGutter,
	keymap,
	lineNumbers
} from '@codemirror/view';
import { classHighlighter } from '@lezer/highlight';

	import { LANGUAGE_MAP, detectLanguage, getLanguageObject } from '@/editor/text/languages';
import EditorTheme from '@/editor/text/theme';

	const props = defineProps<{
		tabId: string;
	}>();

	const editorStore = useEditorStore();
	const contextmenuStore = useContextmenuStore();

	const containerRef = ref<HTMLDivElement>();
	const indentUnitValue = ref<string>('');
	const languageOverride = ref<string>();

	const tab = computed(() => editorStore.getTabById(props.tabId));
	const tabContents = computed(() => (tab.value && typeof tab.value.contents === 'string' ? tab.value.contents : ''));

	const languageConf = new Compartment();
	const indentUnitConf = new Compartment();
	let editorView: EditorView | undefined = undefined;

	onMounted(() => {
		// We can't use a custom context menu here since if we want copy/cut/paste options,
		// our only option is to use the default browser context menu.
		// There is no cross-browser solution for manipulating the clipboard on modern browsers
		// i.e. document.execCommand is deprecated and will not always work, and navigator.clipboard
		// does not support non-HTTPs web pages (also, FireFox does not support all functions).
		contextmenuStore.useDefault(containerRef.value!, true);

		// Try to auto-detect the indent unit
		let detectedIndentUnit: string | null = null;
		for (const line of tabContents.value.split('\n')) {
			const match = line.match(/^\s+/g);
			if (!match) {
				continue;
			}

			const value = match[0];
			if (value.length > 0 && (!detectedIndentUnit || value.length < detectedIndentUnit.length)) {
				detectedIndentUnit = value;
			}
		}

		if (!detectedIndentUnit) {
			detectedIndentUnit = '    ';
		}

		indentUnitValue.value = detectedIndentUnit;

		editorView = new EditorView({
			parent: containerRef.value!,
			doc: tabContents.value,
			extensions: [
				history(),
				Prec.highest(
					keymap.of([
						{ mac: "Return", run: insertNewline}
					])
				),
				keymap.of(defaultKeymap),
				keymap.of(historyKeymap),
				keymap.of(searchKeymap),
				keymap.of([
					{
						key: 'Tab',
						preventDefault: true,
						stopPropagation: true,
						run: (target: EditorView) => {
							target.dispatch({
								changes: {
									from: target.state.selection.main.from,
									to: target.state.selection.main.to,
									insert: '\t'
								},
								selection: { anchor: target.state.selection.main.from + 1 }
							});
							return true;
						}
					}
				]),
				languageConf.of(getLanguageObject(editorLanguage.value)),
				autocompletion({ closeOnBlur: false }),
				indentOnInput(),
				indentUnitConf.of(indentUnit.of(indentUnitValue.value)),
				closeBrackets(),
				bracketMatching(),
				search({ top: true }),
				lineNumbers(),
				highlightActiveLine(),
				highlightActiveLineGutter(),
				syntaxHighlighting(classHighlighter),
				EditorView.updateListener.of(onStateChange),
				EditorTheme
			]
		});
	});

	onUnmounted(() => {
		editorView?.destroy();
	});

	/**
	 * Set the indent unit.
	 *
	 * @param v The indent unit string.
	 */
	function setIndentUnit(v: string) {
		indentUnitValue.value = v;
		editorView?.dispatch({
			effects: indentUnitConf.reconfigure(indentUnit.of(indentUnitValue.value))
		});
	}

	/**
	 * Set the language mode for the editor.
	 *
	 * @param name The name of the language.
	 */
	function setLanguageMode(name: string) {
		if (!(name in LANGUAGE_MAP)) {
			console.warn(`Unable to switch language mode: Language ${name} not found.`);
			return;
		}
		languageOverride.value = name;
	}

	function goToLine(line: number) {
		if (!editorView) return;
		const pos = editorView.state.doc.line(line);

		editorView.dispatch({
			selection: { head: pos.from, anchor: pos.to },
			scrollIntoView: true
		});
	}

	/**
	 * Get the amount of undoable changes.
	 *
	 * @returns The number of undoable changes. `0` if there is no undo history.
	 */
	function getUndoDepth(): number {
		if (!editorView) return 0;
		return undoDepth(editorView.state);
	}

	/**
	 * Undo a single group of history events. Returns false if no group was available.
	 *
	 * @returns A boolean whether a history event was undone.
	 */
	function undo(): boolean {
		if (!editorView) return false;
		return cmUndo(editorView);
	}

	/**
	 * Redo a single group of history events. Returns false if no group was available.
	 *
	 * @returns A boolean whether a history event was redone.
	 */
	function redo(): boolean {
		if (!editorView) return false;
		return cmRedo(editorView);
	}

	/**
	 * Get the amount of redoable changes.
	 *
	 * @returns The number of redoable changes. `0` if there is no redo history.
	 */
	function getRedoDepth(): number {
		if (!editorView) return 0;
		return redoDepth(editorView.state);
	}

	/**
	 * Callback for when document in the CodeMirror editor changes / updates. Automatically called
	 * as part of the state extension.
	 *
	 * @param v The update object.
	 */
	function onStateChange(v: ViewUpdate) {
		if (!v.docChanged || !tab.value) {
			return;
		}

		tab.value.contents = v.state.doc.toString();
	}

	/**
	 * Language (name) for the document in the editor.
	 */
	const editorLanguage = computed(() =>
		languageOverride.value ? languageOverride.value : detectLanguage(tab.value?.name || '', tabContents.value)
	);

	watch(editorLanguage, () => {
		console.log('Reconfiguring to language: ' + editorLanguage.value);
		editorView?.dispatch({
			effects: languageConf.reconfigure(getLanguageObject(editorLanguage.value))
		});
	});

	defineExpose({
		indentUnitValue,
		editorLanguage,
		setIndentUnit,
		setLanguageMode,
		getUndoDepth,
		getRedoDepth,
		undo,
		redo,
		goToLine
	});
</script>

<style scoped>
	.text-editor-container {
		flex: 1 0;
		background-color: var(--color-foreground-primary);
		color: var(--color-component-text-editor-text);
		border-radius: 10px;
		overflow: auto;
	}
</style>
