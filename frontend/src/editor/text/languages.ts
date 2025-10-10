import { html } from '@codemirror/lang-html';
import { javascript } from '@codemirror/lang-javascript';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { python } from '@codemirror/lang-python';
import { xml } from '@codemirror/lang-xml';
import { dockerFile } from '@codemirror/legacy-modes/mode/dockerfile';
import { jinja2 } from '@codemirror/legacy-modes/mode/jinja2';
import { powerShell } from '@codemirror/legacy-modes/mode/powershell';
import { properties } from '@codemirror/legacy-modes/mode/properties';
import { shell } from '@codemirror/legacy-modes/mode/shell';
import { toml } from '@codemirror/legacy-modes/mode/toml';
import { yaml } from '@codemirror/legacy-modes/mode/yaml';

import { StreamLanguage } from '@codemirror/language';
import type { Extension } from '@codemirror/state';
import { ViewPlugin } from '@codemirror/view';

interface LanguageProvider {
	/** List of file extensions (lowercase, no leading `.`) that this language is associated with. */
	extensions: Array<string>;

	/**
	 * Custom heuristic function to detect this language. This only applies after the file extension is checked against all candidates (i.e. this is a last-resort check).
	 * This should be a function that takes the file contents in as a string (trimmed and lower-cased), and outputs a boolean whether the contents match this language.
	 */
	heuristic?: (contents: string) => boolean;

	/** Function that provides the handler (CodeMirror Extension) for this language. */
	handler: () => Extension;
}

/**
 * Language map, mapping a language name to a provider.
 *
 * The `Plaintext` key is reserved as the default for any language not otherwise supported.
 */
const LANGUAGE_MAP: { [key: string]: LanguageProvider } = {
	HTML: {
		extensions: ['html'],
		handler: () => html()
	},
	JavaScript: {
		extensions: ['js'],
		handler: () => javascript()
	},
	JSX: {
		extensions: ['jsx'],
		handler: () => javascript({ jsx: true })
	},
	TypeScript: {
		extensions: ['ts'],
		handler: () => javascript({ typescript: true })
	},
	Python: {
		extensions: ['py'],
		handler: () => python()
	},
	Markdown: {
		extensions: ['md'],
		handler: () => markdown()
	},
	JSON: {
		extensions: ['json'],
		handler: () => json()
	},
	XML: {
		extensions: ['xml'],
		handler: () => xml()
	},
	Jinja2: {
		extensions: ['j2'],
		handler: () => StreamLanguage.define(jinja2)
	},
	PowerShell: {
		extensions: ['ps1'],
		handler: () => StreamLanguage.define(powerShell)
	},
	Shell: {
		extensions: ['sh', 'bash'],
		heuristic: (contents: string) => contents.startsWith('#!/bin/bash') || contents.startsWith('#!/bin/sh'),
		handler: () => StreamLanguage.define(shell)
	},
	TOML: {
		extensions: ['toml'],
		handler: () => StreamLanguage.define(toml)
	},
	YAML: {
		extensions: ['yml', 'yaml'],
		heuristic: (contents: string) => contents.startsWith('---'),
		handler: () => StreamLanguage.define(yaml)
	},
	Dockerfile: {
		extensions: ['docker', 'dockerfile'],
		handler: () => StreamLanguage.define(dockerFile)
	},
	Config: {
		extensions: ['ini', 'cfg', 'conf', 'config', 'service'],
		handler: () => StreamLanguage.define(properties)
	},
	Plaintext: {
		extensions: ['', 'txt'],
		handler: () => ViewPlugin.fromClass(class {}) // A dummy extension, effectively disabling language support (there may be a better way to do this)
	}
};

/**
 * Get the language object corresponding to the given key.
 *
 * @param key The language key.
 */
function getLanguageObject(key: string) {
	if (key in LANGUAGE_MAP) {
		return LANGUAGE_MAP[key].handler();
	}

	console.warn('Unhandled editor language key: ' + key);
	return LANGUAGE_MAP['Plaintext'].handler();
}

/**
 * Detect the language given the filename and contents.
 *
 * @param filename The name of the file (including extension).
 * @param contents The contents of the file.
 *
 * @returns The language key (name).
 */
function detectLanguage(filename: string, contents: string): string {
	const ext = filename.includes('.') ? filename.split('.').pop()!.toLowerCase() : '';
	for (const key of Object.keys(LANGUAGE_MAP)) {
		if (LANGUAGE_MAP[key].extensions.includes(ext)) {
			return key;
		}
	}

	// Try to auto-detect based on content
	const formattedContents = contents.trim().toLowerCase();
	for (const key of Object.keys(LANGUAGE_MAP)) {
		const heuristic = 'heuristic' in LANGUAGE_MAP[key] ? LANGUAGE_MAP[key].heuristic : undefined;
		if (heuristic && heuristic(formattedContents)) {
			return key;
		}
	}

	// Default
	return 'Plaintext';
}

export { LANGUAGE_MAP, detectLanguage, getLanguageObject };

