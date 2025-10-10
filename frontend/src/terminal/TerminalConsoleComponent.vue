<template>
	<div class="terminal-console-wrapper">
		<div
			class="terminal-console custom-scrollbar"
			ref="containerRef"
			@scroll.passive="onScroll"
			@wheel.passive="onWheel"
		>
			<div class="terminal-console-contents" :style="{ height: totalHeight + 'px' }" ref="contentsRef">
				<!-- When no context is provided for this console, show a default / placeholder. -->
				<template v-if="!props.contextId">
					<div class="terminal-console-line" :style="{ top: '0px' }">
						<span class="terminal-console-line-control material-icons">keyboard_double_arrow_right</span>
						<span class="terminal-console-line-text" type="control">Run a graph to see output displayed here.</span>
					</div>

					<div class="terminal-console-line" :style="{ top: LINE_SIZE + 'px' }">
						<span class="terminal-console-line-control material-icons">keyboard_double_arrow_right</span>

						<!-- Not a graph tab-->
						<span
							v-if="!editorStore.activeGraphTab"
							class="terminal-console-line-text terminal-console-line-unresolved-error"
							>The current tab is not a graph.</span
						>

						<!-- Not an executable graph-->
						<span
							v-else-if="!editorStore.activeGraphTab.contents.canExecute()"
							class="terminal-console-line-text terminal-console-line-unresolved-error"
							>The current graph is not executable since it contains a non-primitive input type.</span
						>

						<!-- Graph tab has errors -->
						<span
							v-else-if="errorStore.graphHasErrors(editorStore.activeGraphTab.id)"
							class="terminal-console-line-text terminal-console-line-unresolved-error"
							>You have errors in the current graph. Resolve them to enable the run option.</span
						>

						<!-- Provide a clickable hyperlink to run the graph. -->
						<span v-else class="terminal-console-line-text" type="hyperlink" @click="clickHyperlinkRun"
							>Or click here to execute the current graph in the editor.</span
						>
					</div>
				</template>

				<!-- Show the execution context. -->
				<template v-else v-for="content in consoleContents" :key="content.index">
					<div class="terminal-console-line" :style="{ top: content.offset + 'px' }">
						<!-- Show the line symbol -->
						<span
							class="terminal-console-line-error material-icons"
							v-if="(content.type == 'error' && !content.text.includes('errorLink://')) || content.type == 'critical'"
						>
							warning_amber
						</span>
						<span
							class="terminal-console-line-error-link-icon material-icons"
							v-else-if="content.type == 'error' && content.text.includes('errorLink://')"
						>
							error_outline
						</span>
						<span class="terminal-console-line-control material-icons" v-else-if="content.type == 'control'">
							keyboard_double_arrow_right
						</span>
						<span class="terminal-console-line-image material-icons" v-else-if="content.type == 'image'">
							insert_photo
						</span>
						<span class="terminal-console-line-marker material-icons" v-else>chevron_right</span>

						<!-- Display the line contents -->
						<span
							v-if="content.type == 'error' && content.text.includes('errorLink://')"
							class="terminal-console-line-text-error-link"
							:type="content.type"
							@click="editorStore.navigateToErroringNode(content.text)"
							>{{ createErrorLink(content.text) }}</span
						>
						<template v-else-if="content.type == 'critical' && content.text.includes('errorLink://')">
							<span class="terminal-console-line-text" :type="content.type">{{
								createCriticalMessage(content.text)
							}}</span>
							<span
								class="terminal-console-line-text-error-link"
								@click="editorStore.navigateToErroringNode(content.text)"
								>{{ createErrorLink(content.text) }}</span
							>
						</template>
						<span
							v-else-if="content.type == 'image'"
							class="terminal-console-line-text"
							:type="content.type"
							@click="openImage(content.text)"
							@mouseover="createPreview($event, content.text)"
							@mouseleave="removePreview()"
							>{{ createImageLink(content.text) }}</span
						>
						<span v-else class="terminal-console-line-text" :type="content.type" ref="terminalLineElements" :style="customSearchStyle(content.index)">{{ content.text }}</span>
					</div>
				</template>

				<!-- Blinking cursor when the socket is connected / graph is running. -->
				<template v-if="isRunning">
					<div
						class="terminal-console-line"
						:style="{
							top: (consoleContents.length ? consoleContents[consoleContents.length - 1].offset + LINE_SIZE : 0) + 'px'
						}"
					>
						<span class="terminal-console-line-marker material-icons" waiting>chevron_right</span>
					</div>
				</template>
			</div>
		</div>

		<div class="reset-scroll-container" v-show="!autoScroll">
			<div
				class="reset-scroll-button material-icons"
				title="Scroll to bottom and enable Auto-Scroll."
				@click.stop.prevent="onScrollButtonClick"
			>
				expand_more
			</div>
		</div>
		<div class="terminal-search-container" v-show="showSearch">
			<SearchField v-model="searchInput" placeholder="Search this tab" title="Press 'Enter' to cycle through matches and 'Shift+Enter' to cycle backwards." ref="searchFieldComponent" />
			<div class="terminal-search-button-bar">
				<span @click="reverseMatchIndex" title="Move backward in the search results (Shift+Enter keys in textbox)" class="terminal-search-button-icon material-icons">arrow_upward</span>
				<span @click="advanceMatchIndex" title="Move forward in the search results (Enter key in textbox)" class="terminal-search-button-icon material-icons">arrow_downward</span>
				<div class="terminal-search-case-sensitive-container" title="Check this box to enforce matching on upper and lower casing.">
					<BooleanCheckboxInput
						:value=caseSenSearch
						@update="caseSenSearch = ! caseSenSearch"
					/>
					<span class="terminal-search-case-sensitive-text no-select">Case Sensitive?</span>
				</div>
			</div>
			<div class="terminal-search-dropdown-wrapper" title="Filter on log messages matching a certain type of message">
				<DropdownComponent ref="dropdown" auto-width>
					<span class="dropdown-value no-select">{{ currentSearchFilterChoice }}</span>
					<div class="dropdown-icon material-icons">expand_more</div>

					<template v-slot:dropdown>
						<div class="dropdown-contents-container custom-scrollbar">
							<span
								v-for="option in searchFilterOptions"
								:key="option"
								class="dropdown-option no-select"
								@click.stop="selectOption(option)"
							>
								{{ option }}
							</span>
						</div>
					</template>
				</DropdownComponent>
			</div>
			<span v-if="searchMatches && searchMatches.length > 0" class="terminal-search-match-count">Match {{ currentMatchIndex + 1 }} of {{ numMatchesText }}</span>
			<span class="terminal-search-match-count" v-else> </span>
		</div>
	</div>
</template>

<script setup lang="ts">
	import DropdownComponent from '@/components/DropdownComponent.vue';
import type { MenuItem, MenuOptions } from '@/components/MenuComponent.vue';
import BooleanCheckboxInput from '@/editor/graph/inputs/BooleanCheckboxInput.vue';
import SearchField from '@/sidebar/nodePanel/SearchField.vue';
import {
	useContextmenuStore,
	useEditorStore,
	useErrorStore,
	useFileStore,
	usePromptStore,
	useTerminalStore,
	type MessageData
} from '@/stores';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type ComputedRef } from 'vue';

	interface ConsoleLineContents {
		index: number;
		offset: number;
		text: string;
		type: 'debug' | 'info' | 'notice' | 'warning' | 'error' | 'critical' | 'control' | 'hyperlink' | 'image';
	}

	const props = defineProps<{
		/** The execution context ID for this terminal console. If null, this console is not assigned any execution and a default behavior will be used. */
		contextId: string | null;

		/** The height percentage that this terminal console should occupy. */
		heightPercent: number;
	}>();

	const emit = defineEmits<{
		(e: 'maximize'): void;
		(e: 'shrink'): void;
		(e: 'imagePreview', b64string: string, mouseX: number, mouseY: number): void;
	}>();

	const LINE_SIZE = 19; /** Warning: Do not change this without changing the .terminal-console-line height value. */

	const containerRef = ref<HTMLDivElement>();
	const contentsRef = ref<HTMLDivElement>();

	const terminalStore = useTerminalStore();
	const contextmenuStore = useContextmenuStore();
	const editorStore = useEditorStore();
	const promptStore = usePromptStore();
	const errorStore = useErrorStore();
	const fileStore = useFileStore();

	/** The execution context for this console, if it exists. */
	const context = computed(() => (props.contextId ? terminalStore.getExecutionContextById(props.contextId) : null));

	/** Top coordinate of the visible terminal contents area. */
	const viewportTop = ref<number>(0);

	/** Bottom coordinate of the visible terminal contents area. */
	const viewportBottom = ref<number>(0);

	/** Whether to automatically scroll the console as new logs come in */
	const autoScroll = ref<boolean>(true);

	/** Whether to show searchbar or not*/
	const showSearch = ref<boolean>(false);

	/** Gets set by mouseover / mouseleave for image preview */
	const mouseOverImagePreview = ref<string>('');

	/** "Two-way-bound" value that holds the current value from the searchbar component */
	const searchInput = ref<string>('');

	/** References to the HTML Elements that contain each line in the terminal */
	const terminalLineElements = ref<(HTMLSpanElement)[]>();

	/** The match currently 'snapped to' in the terminal */
	const currentMatchIndex = ref<number>(-1);

	/** Output for the graph. */
	const executionLogs = computed(() => (context.value ? context.value.logs : []));

	/** Whether the open graph is running. */
	const isRunning = computed(() => (context.value ? context.value.connected : false));

	/** Reference to the searchbar component (for access to the 'focus' function) */
	const searchFieldComponent = ref<InstanceType<typeof SearchField>>();

	const caseSenSearch = ref<boolean>(false);
	const searchFilterOptions = ref<Array<string>>(["No Filter", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR / CRITICAL"]);
	const currentSearchFilterChoice = ref<string>("No Filter");
	const dropdown = ref<InstanceType<typeof DropdownComponent>>();

	onMounted(() => {
		window.addEventListener('resize', updateViewport);
		window.addEventListener('keydown', onKeyDown, true);

		// Update the viewport
		updateViewport();

		// Add the context menu
		contextmenuStore.getContextMenu('root').addHook(containerRef.value!, openContextMenu, true);
	});

	onBeforeUnmount(() => {
		window.removeEventListener('resize', updateViewport);
		window.removeEventListener('keydown', onKeyDown, true);
	});

	/** Update the viewport positions to allow for correct computation of the visible lines in the console. */
	function updateViewport() {
		if (!containerRef.value) return;
		const scrollTop = containerRef.value.scrollTop;
		viewportTop.value = scrollTop;
		viewportBottom.value = scrollTop + containerRef.value.clientHeight;
	}

	/** Callback for scroll events. */
	function onScroll() {
		updateViewport();
	}

	/** Callback for wheel events. */
	function onWheel(event: WheelEvent) {
		if (event.deltaY !== 0) {
			autoScroll.value = false;
		}
	}

	/**
	 * Callback function invoked when the user clicks on the 'hyperlink' text in the terminal UI.
	 * This text only appears if there are no terminal tabs currently being tracked.
	 */
	function clickHyperlinkRun() {
		if(!editorStore.activeGraphTab) return;
		terminalStore.promptGraphExecution(
			editorStore.activeGraphTab.contents,
			editorStore.activeGraphTab.name,
			editorStore.activeGraphTab.fileId ? fileStore.getFilePath(editorStore.activeGraphTab.fileId) || null : null
		);
	}

	/** Set the scroll top position of the terminal contents. */
	function setScrollPosition(value: number) {
		if (!containerRef.value) return;
		containerRef.value.scrollTop = value;
	}

	/** When the scroll button is clicked. Scrolls to the bottom and enables auto-scroll. */
	function onScrollButtonClick() {
		setScrollPosition(totalHeight.value);
		autoScroll.value = true;
	}

	/** The value to display to the user when an error link appears */
	function createErrorLink(b64str: string) {
		const b64Info = editorStore.extractErrorLink(b64str);
		const msg = 'Click here to navigate to the erroring node (GraphEX error code: ' + b64Info.b64string + ')';
		return msg;
	}

	function createCriticalMessage(criticalMsg: string) {
		const i = criticalMsg.indexOf('errorLink://');
		if (i >= 0) {
			return criticalMsg.slice(0, i);
		}
		return criticalMsg;
	}

	function createImageLink(b64str: string) {
		let msg = 'Click here to view an attached image.';
		if (b64str.includes(']')) {
			const lastIndexOfBracket = b64str.lastIndexOf(']');
			msg = b64str.slice(0, lastIndexOfBracket + 1).trim() + ' ' + msg;
		}
		return msg;
	}

	function openImage(b64str: string) {
		removePreview();
		let actualB64String = b64str;
		if (b64str.includes(']')) {
			const lastIndexOfBracket = b64str.lastIndexOf(']');
			actualB64String = b64str.slice(lastIndexOfBracket + 1).trim();
		}
		var win = window.open();
		if (win)
			win.document.write('<iframe src="' + actualB64String  + '" frameborder="0" style="border:0; top:0px; left:0px; bottom:0px; right:0px; width:100%; height:100%;" allowfullscreen></iframe>');
	}

	function createPreview(event: MouseEvent, b64str: string) {
		if (mouseOverImagePreview.value != '') return;
		let actualB64String = b64str;
		if (b64str.includes(']')) {
			const lastIndexOfBracket = b64str.lastIndexOf(']');
			actualB64String = b64str.slice(lastIndexOfBracket + 1).trim();
		}
		mouseOverImagePreview.value = actualB64String;
		emit('imagePreview', mouseOverImagePreview.value, event.clientX, event.clientY);
	}

	function removePreview() {
		if (mouseOverImagePreview.value == '') return;
		mouseOverImagePreview.value = '';
		emit('imagePreview', '', -1, -1);
	}

	/** Output for the graph, split on newlines. */
	const executionLogLines: ComputedRef<Array<MessageData>> = computed(() => {
		const lines = [];
		for (const message of executionLogs.value) {
			const splitMessage = message.msg.split('\n').map((val) => {
				return { msg: val, type: message.type };
			});

			lines.push(...splitMessage);
		}
		return lines;
	});

	/** Total height in pixels. This is used to determine to scrollable area available for the terminal based on the current content. */
	const totalHeight = computed(() => {
		let height = executionLogLines.value.length * LINE_SIZE;
		if (isRunning.value) {
			// If running, add an extra line to the height to display the blinking cursor
			height += LINE_SIZE;
		}
		return height;
	});

	/** Formatted console contents. Only 'renders' the lines currently able to be seen by the user in the terminal. */
	const consoleContents: ComputedRef<Array<ConsoleLineContents>> = computed(() => {
		const BUFFER_AMOUNT = 5;
		const lineStartIndex = Math.max(0, Math.floor(viewportTop.value / LINE_SIZE) - BUFFER_AMOUNT);
		const lineEndIndex = Math.min(
			executionLogLines.value.length,
			Math.floor(viewportBottom.value / LINE_SIZE) + BUFFER_AMOUNT
		);

		const visibleLines = executionLogLines.value.slice(lineStartIndex, lineEndIndex);
		return visibleLines.map((line, i) => {
			const index = lineStartIndex + i;

			return {
				index: index,
				offset: index * LINE_SIZE,
				text: line.msg,
				type: line.type
			};
		});
	});

	/** Dependencies to watch for updating the viewport. */
	const viewportDependencies = computed(() => {
		return [props.heightPercent, totalHeight.value];
	});

	/** Opens the custom context menu for the terminal. */
	function openContextMenu(): MenuOptions | null {
		if (!context.value) return null;
		const entries: Array<MenuItem> = [];

		if (autoScroll.value) {
			entries.push({
				label: 'Disable Auto-Scroll',
				description: 'Do not automatically scroll the terminal as new text appears.',
				callback: () => {
					autoScroll.value = false;
				},
				divider: true
			});
		} else {
			entries.push({
				label: 'Enable Auto-Scroll',
				description: 'Automatically scroll the terminal as new text appears.',
				callback: () => {
					autoScroll.value = true;
				},
				divider: true
			});
		}

		entries.push({
			label: 'Copy All Output',
			description: 'Copy all output to your clipboard.',
			callback: () => {
				const output = executionLogs.value.reduce((prevValue, val) => prevValue + val.msg + '\n', '');
				navigator.clipboard.writeText(output);
			}
		});

		entries.push({
			label: 'Download as Text File...',
			description: 'Download all output to a .txt file',
			callback: () => {
				if (!context.value) return;
				const output = executionLogs.value.reduce((prevValue, val) => prevValue + val.msg + '\n', '');
				const file = new Blob([output], { type: 'text/plain' });
				const a = document.createElement('a');
				const url = URL.createObjectURL(file);
				a.href = url;
				if (!context.value.name.endsWith('.txt'))
					a.download = `${context.value.name}.txt`;
				else
					a.download = context.value.name;
				document.body.appendChild(a);
				a.click();
				setTimeout(() => {
					document.body.removeChild(a);
					window.URL.revokeObjectURL(url);
				}, 10);
			}
		});

		entries.push({
			label: 'Export JSON log...',
			description: 'Download all output as a .log file',
			callback: () => {
				if (!context.value) return;
				// console.log(executionLogs.value);
				const output = JSON.stringify(executionLogs.value);
				// console.log(output);
				const file = new Blob([output], { type: 'text/json' });
				const a = document.createElement('a');
				const url = URL.createObjectURL(file);
				a.href = url;
				if (!context.value.name.endsWith('.log'))
					a.download = `${context.value.name}.log`;
				else
					a.download = context.value.name;
				document.body.appendChild(a);
				a.click();
				setTimeout(() => {
					document.body.removeChild(a);
					window.URL.revokeObjectURL(url);
				}, 10);
			},
			divider: true
		});

		entries.push({
			label: 'Toggle Searchbar',
			description: '(Ctrl+Shift+F) Search the terminal output for matching text.',
			callback: () => {
				toggleSearchbar();
			},
			divider: true
		});

		entries.push({
			label: 'Scroll To Top',
			description: 'Scroll the terminal to the top.',
			callback: () => {
				setScrollPosition(0);
			}
		});

		entries.push({
			label: 'Scroll To Bottom',
			description: 'Scroll the terminal to the bottom.',
			callback: () => {
				setScrollPosition(totalHeight.value);
			}
		});

		entries.push({
			label: 'Maximize',
			description: 'Maximize the terminal UI.',
			callback: () => {
				emit('maximize');
			}
		});

		entries.push({
			label: 'Shrink',
			description: 'Shrink the terminal UI.',
			callback: () => {
				emit('shrink');
			}
		});

		entries.push({
			label: 'Hide / Minimize',
			description: 'Hides the terminal UI.',
			callback: () => {
				terminalStore.setTerminalOpen(false);
			},
			divider: true
		});

		if (context.value.filepath) {
			entries.push({
				label: 'Show in Editor Panel',
				description: 'Sets the tab for this graph as active in the Editor',
				callback: async () => {
					if (!context.value || !context.value.filepath) return;
					const file = fileStore.findFileByPath(context.value.filepath);
					if (!file) {
						await promptStore.failedAlert(
							'Show in Editor Panel Failure',
							'Failed to find file from path "' + context.value.filepath + '" (file does not exist).'
						);
						return;
					}
					await editorStore.openFileInEditor(file.id);
				},
				divider: true
			});
		}

		entries.push({
			label: 'Clear',
			description: 'Clears the output in this terminal.',
			callback: () => {
				if (!props.contextId) return;
				terminalStore.clearOutput(props.contextId);
			}
		});

		if (isRunning.value) {
			entries.push({
				label: 'Cancel Execution',
				description: 'Attempt to gracefully stop this running graph.',
				callback: () => {
					if (!props.contextId) return;
					terminalStore.stopExecutingGraph(props.contextId);
				}
			});

			entries.push({
				label: 'Forcefully Stop Execution',
				description: 'Forcefully kill the process for this running graph.',
				callback: () => {
					if (!props.contextId) return;
					terminalStore.killExecutingGraph(props.contextId);
				}
			});
		}

		return { items: entries };
	}

	/**
	 * Function called whenever the searchbar is being toggled on/off (keybind, context menu, etc.)
	 */
	function toggleSearchbar() {
		showSearch.value = !showSearch.value;
		if (showSearch.value) {
			nextTick(() => {
				searchFieldComponent.value!.focus();
			});
		} else {
			currentMatchIndex.value = -1;
		}
	}

	/**
	 * Contains the index numbers of lines matching the search in the terminal
	 */
	const searchMatches = computed(() => {
		const matches: number[] = [];
		if ((searchInput.value != "" || currentSearchFilterChoice.value != 'No Filter') && executionLogLines.value && executionLogLines.value.length > 0) {
			if (caseSenSearch.value) {
				executionLogLines.value.forEach((messageData, i) => {
					if (messageData.msg.includes(searchInput.value)) {
						if (currentSearchFilterChoice.value == 'No Filter') {
							matches.push(i);
						} else {
							if (messageData.type == currentSearchFilterChoice.value.toLowerCase()) {
								matches.push(i);
							} else if ( (messageData.type == 'error' || messageData.type == 'critical') && currentSearchFilterChoice.value == 'ERROR') {
								matches.push(i);
							}
						}
					}
				});
			} else {
				const searchInputLowercase = searchInput.value.toLowerCase();
				executionLogLines.value.forEach((messageData, i) => {
					if (messageData.msg.toLowerCase().includes(searchInputLowercase)) {
						if (currentSearchFilterChoice.value == 'No Filter') {
							matches.push(i);
						} else {
							if (messageData.type == currentSearchFilterChoice.value.toLowerCase()) {
								matches.push(i);
							} else if (currentSearchFilterChoice.value == 'ERROR / CRITICAL' && (messageData.type == 'error' || messageData.type == 'critical')) {
								matches.push(i);
							}
						}
					}
				});
			}
		}
		return matches;
	});

	const numMatchesText = computed(() => {
		if (searchMatches.value && searchMatches.value.length > 0) {
			if (searchMatches.value.length > 9999) {
				return "9999+";
			} else {
				return String(searchMatches.value.length);
			}
		}
		return "0";
	});

	/**
	 * Keybindings allowed for this component and the callbacks upon key press
	 */
	const KEYBINDINGS: { [shorthand: string]: () => void } = {
		Enter: () => {
			if (showSearch.value && searchFieldComponent.value && searchFieldComponent.value.hasFocus()) {
				advanceMatchIndex();
			}
		},
		'Shift+Enter': () => {
			if (showSearch.value && searchFieldComponent.value && searchFieldComponent.value.hasFocus()) {
				reverseMatchIndex();
			}
		},
		'Ctrl+Shift+KeyF': () => {
			toggleSearchbar();
		}
	};

	/**
	 * Handles setting up and calling individual KEYBINDINGS
	 * @param event a KeyboardEvent fired by the event listener created in 'onMount'
	 */
	function onKeyDown(event: KeyboardEvent) {
		const keys: Array<string> = [];
		if (event.altKey) keys.push('Alt');
		if (event.ctrlKey) keys.push('Ctrl');
		if (event.metaKey) keys.push('Meta');
		if (event.shiftKey) keys.push('Shift');

		if (event.key != 'Alt' && event.key != 'Control' && event.key != 'Meta' && event.key != 'Shift') {
			keys.push(event.code); // See https://www.toptal.com/developers/keycode
		}

		const shorthand = keys.join('+');

		// Handle key binding
		if (shorthand in KEYBINDINGS) {
			if (shorthand == 'Ctrl+Shift+KeyF') {
				event.preventDefault();
				event.stopPropagation();
			}
			const callback = KEYBINDINGS[shorthand];
			callback();
			return;
		}
	}

	/**
	 * Moves to the next found search item in the terminal
	 */
	function advanceMatchIndex() {
		if (searchMatches.value && searchMatches.value.length > 0) {
			if (searchMatches.value.length - 1 > currentMatchIndex.value) {
				currentMatchIndex.value++;
			} else {
				currentMatchIndex.value = 0;
			}
			setScrollPosition(searchMatches.value[currentMatchIndex.value] * LINE_SIZE);
		}
	}

	/**
	 * Goes back one search item in the termianl
	 */
	function reverseMatchIndex() {
		if (searchMatches.value && searchMatches.value.length > 0) {
			if (currentMatchIndex.value - 1 < 0) {
				currentMatchIndex.value = searchMatches.value.length - 1;
			} else {
				currentMatchIndex.value--;
			}
			setScrollPosition(searchMatches.value[currentMatchIndex.value] * LINE_SIZE);
		}
	}

	/**
	 * The CSS (highlighting) applied to each matching search line
	 * @param lineIndex The index that line appears at in the list of all lines
	 */
	function customSearchStyle(lineIndex: number) {
		let styles: any = {};
		// If this is one of the match results: highlight it in a unique color that doesn't clash with the existing color set
		if (searchMatches.value.includes(lineIndex)) {
			styles['background'] = 'darkblue';
		}
		// If this is the currently viewed match: add a border around it to make it stand out further
		if (searchMatches.value[currentMatchIndex.value] == lineIndex) {
			styles['border'] = '2px solid orange';
			styles['z-index'] = '1';
		}
		return styles;
	}

	function selectOption(option: string) {
		currentSearchFilterChoice.value = option;
		dropdown.value?.close();
	}

	watch(viewportDependencies, () => {
		updateViewport();
		nextTick(() => {
			if (autoScroll.value) {
				setScrollPosition(totalHeight.value);
			}
		});
	});

	/**
	 * Set the default search index to 0 when the searchbar input changes and snap to the first position
	 * If no search values are found: reset the index to -1
	 */
	watch(searchMatches, () => {
		if (searchMatches.value) {
			if (searchMatches.value.length > 0) {
				currentMatchIndex.value = 0;
				setScrollPosition(searchMatches.value[currentMatchIndex.value] * LINE_SIZE);
			} else {
				currentMatchIndex.value = -1;
			}
		}
	});

	defineExpose({
		autoScroll,
		updateViewport,
		setScrollPosition,
		totalHeight
	});
</script>

<style scoped>
	.terminal-console-wrapper {
		width: 100%;
		flex: 1 0;
		position: relative;
		overflow: hidden;
	}

	.terminal-console {
		width: 100%;
		height: 100%;
		padding: 4px 6px;
		background-color: var(--color-component-terminal-background);
		border: 1px solid var(--color-component-terminal-border);
		border-radius: 10px;
		overflow: auto;
	}

	.terminal-console-contents {
		width: 100%;
		display: flex;
		flex-direction: column;
		position: relative;
	}

	.terminal-console-line {
		position: absolute;
		height: 19px; /** Warning: Do not change this without changing the LINE_SIZE variable. */
		font-size: 15px;
		font-family: 'Roboto Mono';
		white-space: pre;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	.terminal-console-line-marker {
		font-size: 15px;
		margin-right: 4px;
		color: var(--color-text);
		opacity: 0.7;
	}

	.terminal-console-line-marker[waiting] {
		animation: blink 0.6s infinite alternate;
	}

	@keyframes blink {
		from {
			color: var(--color-component-terminal-status-running);
		}
		to {
			color: var(--color-component-terminal-background);
		}
	}

	.terminal-console-line-error {
		font-size: 15px;
		margin-right: 4px;
		color: var(--color-component-terminal-text-error);
	}

	.terminal-console-line-error-link-icon {
		font-size: 15px;
		margin-right: 4px;
		color: var(--color-component-terminal-text-errorlink);
	}

	.terminal-console-line-text-error-link {
		color: var(--color-component-terminal-text-errorlink);
		padding-bottom: 2px;
		font-weight: bold;
	}

	.terminal-console-line-text-error-link:hover {
		text-decoration: underline;
		cursor: pointer;
	}

	.terminal-console-line-control {
		opacity: 0.7;
		font-size: 15px;
		margin-right: 6px;
		color: var(--color-component-terminal-text-control);
	}

	.terminal-console-line-image {
		opacity: 0.8;
		font-size: 15px;
		margin-right: 4px;
		color: var(--color-component-terminal-text-image);
	}

	.terminal-console-line-text {
		padding-bottom: 2px;
	}

	.terminal-console-line-text[type='debug'] {
		color: var(--color-component-terminal-text-debug);
	}

	.terminal-console-line-text[type='info'] {
		color: var(--color-component-terminal-text-info);
	}

	.terminal-console-line-text[type='notice'] {
		color: var(--color-component-terminal-text-notice);
	}

	.terminal-console-line-text[type='warning'] {
		color: var(--color-component-terminal-text-warning);
	}

	.terminal-console-line-text[type='error'] {
		color: var(--color-component-terminal-text-error);
	}

	.terminal-console-line-text[type='image'] {
		color: var(--color-component-terminal-text-image);
	}

	.terminal-console-line-text[type='critical'] {
		color: var(--color-component-terminal-text-critical);
		font-weight: bold;
	}

	.terminal-console-line-text[type='control'] {
		color: var(--color-component-terminal-text-control);
		font-style: italic;
	}

	.terminal-console-line-text[type='hyperlink'] {
		color: var(--color-component-terminal-text-hyperlink);
	}

	.terminal-console-line-text[type='hyperlink']:hover {
		text-decoration: underline;
		cursor: pointer;
	}

	.terminal-console-line-text[type='image']:hover {
		text-decoration: underline;
		cursor: pointer;
	}

	.reset-scroll-container {
		position: absolute;
		bottom: 0px;
		display: flex;
		flex-direction: row;
		justify-content: center;
		width: 100%;
		pointer-events: none;
	}

	.terminal-search-container {
		border: 1px solid var(--color-component-terminal-border);
		background-color: var(--color-component-sidebar-searchbar);
		position: absolute;
		top: 0px;
		right: 10px;
		display: flex;
		flex-direction: column;
		z-index: 2;
	}

	.terminal-search-button-bar {
		display: flex;
		flex-direction: row;
		padding-bottom: 5px;
	}

	.terminal-search-button-icon {
		font-size: 1.3rem;
		color: var(--color-text);
		opacity: .6;
		border: 1px solid var(--color-text);
		margin-left: 3px;
	}

	.terminal-search-button-icon:hover {
		opacity: 1;
		cursor: pointer;
	}

	.terminal-search-match-count {
		margin-left: 5px;
		margin-bottom: 3px;
		color: var(--color-text);
		padding-top: 1px;
	}

	.reset-scroll-button {
		font-size: 1.5rem;
		background-color: rgba(255, 255, 255, 0.08);
		width: 25%;
		text-align: center;
		transition: background-color 100ms linear;
		pointer-events: auto;
	}

	.reset-scroll-button:hover {
		background-color: rgba(255, 255, 255, 0.15);
		cursor: pointer;
	}

	.terminal-console-line-unresolved-error {
		color: var(--color-component-terminal-text-error);
	}

	.terminal-search-case-sensitive-container {
		display: flex;
		flex-direction: row;
		margin-left: 10px;
	}

	.terminal-search-case-sensitive-text {
		margin-left: 3px;
		margin-top: 2px;
	}

	.terminal-search-dropdown-wrapper {
		padding: 0.2rem;
		border: 1px solid grey;
		margin-left: 3px;
		margin-right: 3px;
	}

	.dropdown-value {
		flex: 1 0;
		font-size: 1rem;
		text-transform: inherit;
	}

	.dropdown-icon {
		margin: 0px 8px;
		font-size: 1.4rem;
		color: var(--color-text);
		opacity: 0.7;
	}

	.dropdown-contents-container {
		max-height: 400px;
		flex: 1 0;
		display: flex;
		flex-direction: column;
		padding: 6px 0px;
		background-color: var(--color-background-primary);
		border: 1px solid var(--color-foreground-secondary);
		box-shadow: 0px 0px 8px 4px rgba(0, 0, 0, 0.4);
		border-radius: 4px;
		overflow: auto;
	}

	.dropdown-option {
		flex: 1 0;
		padding: 2px;
		cursor: pointer;
	}

	.dropdown-option:hover {
		background-color: var(--color-foreground-secondary);
	}

	:deep(.dropdown-wrapper) {
		flex: 1 0;
	}

	:deep(.dropdown-target-container) {
		flex: 1 0;
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	:deep(.dropdown) {
		width: 100%;
	}
</style>
