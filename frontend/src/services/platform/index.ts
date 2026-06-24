const STORAGE_KEY = 'repair_ai_anonymous_token'

export async function getAnonymousToken(): Promise<string> {
  // #ifdef H5
  const currentH5 = localStorage.getItem(STORAGE_KEY)
  if (currentH5) return currentH5
  // crypto.randomUUID 仅在 secure context (https/localhost) 可用；HTTP 局域网访问降级
  const tokenH5 =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  localStorage.setItem(STORAGE_KEY, tokenH5)
  return tokenH5
  // #endif

  // #ifdef MP-WEIXIN
  const currentMp = uni.getStorageSync(STORAGE_KEY) as string | undefined
  if (currentMp) return String(currentMp)
  const tokenMp = `${Date.now()}-${Math.random().toString(16).slice(2)}`
  uni.setStorageSync(STORAGE_KEY, tokenMp)
  return tokenMp
  // #endif

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export async function recordAudio(): Promise<never> {
  throw new Error('语音输入将在第 2 版支持')
}

export async function chooseImage(): Promise<never> {
  throw new Error('图片上传将在第 2 版支持')
}

export function makePhoneCall(tel: string): void {
  // #ifdef H5
  window.location.href = `tel:${tel}`
  // #endif

  // #ifdef MP-WEIXIN
  uni.makePhoneCall({ phoneNumber: tel })
  // #endif
}
