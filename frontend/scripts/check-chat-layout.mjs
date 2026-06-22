import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const chatPage = readFileSync(resolve(here, '../src/pages/chat/index.vue'), 'utf8')
const quickFaultChips = readFileSync(resolve(here, '../src/pages/chat/components/QuickFaultChips.vue'), 'utf8')

if (chatPage.includes('class="section-title">常见问题')) {
  throw new Error('Quick fault prompts must not be rendered as a standalone 常见问题 section.')
}

const chatPanelIndex = chatPage.indexOf('class="chat-panel panel"')
const quickChipsIndex = chatPage.indexOf('<QuickFaultChips')
if (chatPanelIndex === -1 || quickChipsIndex === -1 || quickChipsIndex < chatPanelIndex) {
  throw new Error('Quick fault prompts must be rendered inside the chat panel.')
}

if (!quickFaultChips.includes('scroll-x') || !quickFaultChips.includes('class="quick-strip"')) {
  throw new Error('Quick fault prompts must be rendered as a horizontal scroll strip.')
}

if (quickFaultChips.includes('grid-template-columns')) {
  throw new Error('Quick fault prompts must not be rendered as a two-column grid.')
}

console.log('chat layout source check ok')
