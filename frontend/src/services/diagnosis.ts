import { apiRequest } from './api'
import type { DiagnosisApiResponse, FeedbackRating, FeedbackResponse } from '../types/diagnosis'

export function createDiagnosisSession(text: string, cityTier?: string | null): Promise<DiagnosisApiResponse> {
  return apiRequest('/diagnosis/sessions', {
    method: 'POST',
    body: JSON.stringify({ text, city_tier: cityTier ?? null })
  })
}

export function sendDiagnosisMessage(sessionId: string, text: string, cityTier?: string | null): Promise<DiagnosisApiResponse> {
  return apiRequest(`/diagnosis/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ text, city_tier: cityTier ?? null })
  })
}

export function completeDiagnosis(sessionId: string, cityTier?: string | null): Promise<DiagnosisApiResponse> {
  return apiRequest(`/diagnosis/sessions/${sessionId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ city_tier: cityTier ?? null })
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
