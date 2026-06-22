import { apiRequest } from './api'
import type { DiagnosisApiResponse, FeedbackRating, FeedbackResponse } from '../types/diagnosis'

export function createDiagnosisSession(text: string): Promise<DiagnosisApiResponse> {
  return apiRequest('/diagnosis/sessions', {
    method: 'POST',
    body: JSON.stringify({ text })
  })
}

export function sendDiagnosisMessage(sessionId: string, text: string): Promise<DiagnosisApiResponse> {
  return apiRequest(`/diagnosis/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text })
  })
}

export function completeDiagnosis(sessionId: string): Promise<DiagnosisApiResponse> {
  return apiRequest(`/diagnosis/sessions/${sessionId}/complete`, {
    method: 'POST'
  })
}

export function submitDiagnosisFeedback(
  resultId: string,
  rating: FeedbackRating,
  reasonTags: string[]
): Promise<FeedbackResponse> {
  return apiRequest(`/diagnosis/results/${resultId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({
      rating,
      reason_tags: reasonTags
    })
  })
}
