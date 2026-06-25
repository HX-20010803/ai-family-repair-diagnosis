import { defineStore } from 'pinia'
import { completeDiagnosis, createDiagnosisSession, sendDiagnosisMessage } from '../services/diagnosis'
import type { ChatMessage, DiagnosisResult, SessionStatus } from '../types/diagnosis'
import { useHousesStore } from './houses'

function messageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function welcomeMessage(): ChatMessage {
  return {
    id: messageId(),
    role: 'assistant',
    kind: 'text',
    text: '您好！我是您的家庭维修助手。\n\n请直接描述家里的故障现象，例如“卫生间天花板一直滴水”或“插座发黑还冒烟”，我会帮您判断风险和下一步建议。'
  }
}

export const useSessionStore = defineStore('session', {
  state: () => ({
    sessionId: '',
    status: 'idle' as SessionStatus,
    messages: [welcomeMessage()] as ChatMessage[],
    roundCount: 0,
    currentResult: null as DiagnosisResult | null,
    error: ''
  }),
  actions: {
    async send(text: string) {
      if (!text.trim()) return
      this.error = ''
      this.messages.push({ id: messageId(), role: 'user', text, kind: 'text' })
      this.status = this.sessionId ? 'asking' : 'creating'
      const cityTier = useHousesStore().activeCityTier
      try {
        const response = this.sessionId
          ? await sendDiagnosisMessage(this.sessionId, text, cityTier)
          : await createDiagnosisSession(text, cityTier)
        this.applyResponse(response)
      } catch (error) {
        this.status = 'error'
        this.error = error instanceof Error ? error.message : 'AI 暂时无法判断，请稍后重试。'
      }
    },
    async complete() {
      if (!this.sessionId) return
      this.status = 'completing'
      const cityTier = useHousesStore().activeCityTier
      try {
        const response = await completeDiagnosis(this.sessionId, cityTier)
        this.applyResponse(response)
      } catch (error) {
        this.status = 'error'
        this.error = error instanceof Error ? error.message : 'AI 暂时无法生成结果，请稍后重试。'
      }
    },
    applyResponse(response: any) {
      this.sessionId = response.session.id
      this.roundCount = response.session.question_round_count
      if (response.safety_notice) {
        this.messages.push({ id: messageId(), role: 'assistant', text: response.safety_notice, kind: 'safety' })
      }
      if (response.type === 'chat' && response.message) {
        // 阶段1：LLM 自然语言追问（维修顾问式），按普通 AI 气泡显示
        this.status = 'asking'
        this.messages.push({
          id: messageId(),
          role: 'assistant',
          text: response.message,
          kind: 'text'
        })
      }
      if (response.type === 'questions') {
        this.status = 'asking'
        this.messages.push({
          id: messageId(),
          role: 'assistant',
          text: response.questions.join('\n'),
          kind: 'questions'
        })
      }
      if (response.type === 'result' && response.result) {
        this.status = 'completed'
        this.currentResult = response.result
        this.messages.push({
          id: messageId(),
          role: 'assistant',
          text: `已生成诊断结果：紧急程度 ${response.result.urgency.level} 级。`,
          kind: 'result'
        })
      }
    },
    reset() {
      this.sessionId = ''
      this.status = 'idle'
      this.roundCount = 0
      this.currentResult = null
      this.error = ''
      this.messages = [welcomeMessage()]
    }
  }
})
