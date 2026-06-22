import { getAnonymousToken } from './platform'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const anonymousToken = await getAnonymousToken()
  let response: Response

  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-Anonymous-Token': anonymousToken,
        ...(options.headers || {})
      }
    })
  } catch (error) {
    throw new Error('后端服务未启动，请先启动本地 8000 服务后重试。')
  }

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    throw new Error(detail?.detail?.message || detail?.detail?.code || 'AI 暂时无法判断，请稍后重试。')
  }

  return response.json() as Promise<T>
}
