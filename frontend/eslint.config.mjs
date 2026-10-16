import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import reactHooks from 'eslint-plugin-react-hooks'

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: { parser: tsParser, parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { '@typescript-eslint': tsPlugin, 'react-hooks': reactHooks },
    rules: {
      'no-debugger': 'error',
      'no-unreachable': 'error',
      'no-constant-condition': 'error',
      'no-duplicate-case': 'error',
      'no-fallthrough': 'error',
      'no-async-promise-executor': 'error',
      'no-promise-executor-return': 'error',
      'prefer-const': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', caughtErrors: 'none' }],
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
    },
  },
]
