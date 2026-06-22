import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const source = readFileSync(resolve('src/services/api.ts'), 'utf8')

if (!source.includes('catch (error)')) {
  throw new Error('apiRequest should catch network failures from fetch')
}

if (!source.includes('后端服务未启动')) {
  throw new Error('apiRequest should show a clear backend-offline message')
}

console.log('api error source check ok')
