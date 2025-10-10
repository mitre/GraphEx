import { EditorView } from '@codemirror/view';

/**
 * The CodeMirror theme used to the style the editor.
 */
export default EditorView.theme({
	'.cm-content': {
		caretColor: 'var(--color-component-text-editor-caret)',
		fontSize: '0.9rem',
		fontFamily: 'Roboto Mono'
	},
	'.cm-scroller': {
		overflow: 'unset'
	},
	'&.cm-focused .cm-cursor': {
		borderLeftColor: 'var(--color-component-text-editor-caret)'
	},
	'.cm-lineNumbers .cm-gutterElement': {
		paddingRight: '1rem'
	},
	'.cm-gutters': {
		fontSize: '0.9rem',
		backgroundColor: 'transparent',
		color: 'var(--color-component-text-editor-gutter-text)',
		border: 'none'
	},
	'&.cm-focused .cm-selectionBackground, ::selection': {
		backgroundColor: 'var(--color-component-text-editor-selection)'
	},
	'.cm-activeLineGutter': {
		backgroundColor: 'var(--color-component-text-editor-active-line)'
	},
	'.cm-activeLine': {
		backgroundColor: 'var(--color-component-text-editor-active-line)'
	},
	'.cm-tooltip': {
		border: 'var(--color-foreground-tertiary)',
		backgroundColor: 'var(--color-foreground-secondary)',
		fontFamily: 'Roboto Mono',
		fontSize: '0.9rem'
	},
	'.cm-tooltip-autocomplete': {
		'& > ul > li[aria-selected]': {
			backgroundColor: 'var(--color-foreground-tertiary)'
		}
	},
	'.cm-panels, .cm-panel': {
		backgroundColor: 'var(--color-foreground-secondary)',
		border: 'none',
		color: 'var(--color-component-text-editor-text)',
		padding: '2px',
		zIndex: 1
	},
	'.cm-textfield': {
		backgroundColor: 'var(--color-foreground-primary)',
		border: 'none',
		padding: '4px 8px',
		fontSize: '0.8rem',
		fontFamily: 'Roboto Mono'
	},
	'.cm-button': {
		backgroundColor: 'transparent',
		color: 'var(--color-component-text-editor-text)',
		border: '1px solid var(--color-foreground-tertiary)',
		borderRadius: '3px',
		backgroundImage: 'none',
		fontSize: '0.8rem',
		fontFamily: 'Roboto',
		textTransform: 'capitalize'
	},
	'.cm-button:hover': {
		backgroundColor: 'var(--color-foreground-tertiary)',
		cursor: 'pointer'
	},
	'.cm-search label': {
		color: 'var(--color-component-text-editor-text)',
		fontSize: '0.8rem',
		fontFamily: 'Roboto',
		textTransform: 'capitalize'
	},
	'.cm-panel.cm-search [name="close"]': {
		fontSize: '1.4rem',
		color: 'var(--color-component-text-editor-text)',
		opacity: '0.6'
	},
	'.cm-panel.cm-search [name="close"]:hover': {
		opacity: '1',
		cursor: 'pointer'
	},
	'.cm-searchMatch': {
		backgroundColor: 'var(--color-component-text-editor-search-match)'
	},
	'.cm-searchMatch-selected': {
		outline: '2px solid var(--color-component-text-editor-search-match-selected)'
	},
	'&.cm-focused .cm-matchingBracket': {
		backgroundColor: 'var(--color-component-text-editor-selection)'
	},

	// Syntax Highlighting
	'.cm-line .tok-keyword': { color: 'var(--color-component-text-editor-syntax-keyword)' },
	'.cm-line .tok-punctuation': { color: 'var(--color-component-text-editor-syntax-punctuation)' },
	'.cm-line .tok-operator': { color: 'var(--color-component-text-editor-syntax-operator)' },
	'.cm-line .tok-typeName': { color: 'var(--color-component-text-editor-syntax-typeName)' },
	'.cm-line .tok-variableName, .cm-line .tok-variableName2': {
		color: 'var(--color-component-text-editor-syntax-variableName)'
	},
	'.cm-line .tok-atom': { color: 'var(--color-component-text-editor-syntax-atom)' },
	'.cm-line .tok-meta': { color: 'var(--color-component-text-editor-syntax-meta)' },
	'.cm-line .tok-className': { color: 'var(--color-component-text-editor-syntax-className)' },
	'.cm-line .tok-string, .cm-line .tok-string2': { color: 'var(--color-component-text-editor-syntax-string)' },
	'.cm-line .tok-bool': { color: 'var(--color-component-text-editor-syntax-bool)' },
	'.cm-line .tok-number': { color: 'var(--color-component-text-editor-syntax-number)' },
	'.cm-line .tok-comment': { color: 'var(--color-component-text-editor-syntax-comment)' }
});
