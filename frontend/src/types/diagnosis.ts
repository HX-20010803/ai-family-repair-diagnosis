export type SessionStatus = 'idle' | 'creating' | 'asking' | 'completing' | 'completed' | 'saved' | 'error'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  kind?: 'text' | 'questions' | 'result' | 'safety'
}

export interface DiagnosisResult {
  id: string
  session_id: string
  fault_type: {
    primary: string
    secondary: string
    confidence: number
    evidence: string[]
  }
  urgency: {
    level: 'S' | 'A' | 'B' | 'C'
    reason: string
  }
  possible_causes: string[]
  recommended_actions: string[]
  forbidden_actions: string[]
  self_check_steps: string[]
  need_professional: 'yes' | 'no' | 'conditional'
  need_professional_reason: string
  price_reference: {
    range: string
    disclaimer: string
    has_reliable_price: boolean
    city_tier: string
    version: string
  } | null
  uncertainty_note: string | null
  advisor_summary: string | null
  cost_total: number
}

export interface DiagnosisApiResponse {
  type: 'questions' | 'result'
  session: {
    id: string
    question_round_count: number
    status: string
  }
  questions: string[]
  result: DiagnosisResult | null
  safety_notice: string | null
}

export type FeedbackRating = 'useful' | 'neutral' | 'not_useful'

export interface FeedbackResponse {
  id: string
  result_id: string
  rating: FeedbackRating
  reason_tags: string[]
  comment: string | null
}
