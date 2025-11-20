/* eslint-env node */
const js = require('@eslint/js');
const vue = require('eslint-plugin-vue');
const tseslint = require('@typescript-eslint/eslint-plugin');
const tsParser = require('@typescript-eslint/parser');

module.exports = [
  // Base JS rules
  js.configs.recommended,

  // Vue 3 essential rules (flat config)
  ...vue.configs['flat/essential'],

  // TypeScript recommended rules (no type-checking)
  ...tseslint.configs.recommended,

  // Project-specific tweaks
  {
    files: ['**/*.{js,jsx,ts,tsx,vue,cjs,mjs,cts,mts}'],
    languageOptions: {
      parser: require('vue-eslint-parser'),
      parserOptions: {
        parser: tsParser,
        ecmaVersion: 'latest',
        sourceType: 'module',
        extraFileExtensions: ['.vue']
      }
    },
    plugins: {
      '@typescript-eslint': tseslint,
      vue
    },
    rules: {
      'vue/script-indent': ['warn', 'tab', { baseIndent: 1 }]
    }
  }
];
