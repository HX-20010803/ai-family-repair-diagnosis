import { defineStore } from 'pinia'
import { getAnonymousToken } from '../services/platform'

export const useUserStore = defineStore('user', {
  state: () => ({
    anonymousToken: '',
    user: null as null | { id: string; nickname?: string },
    isLoggedIn: false
  }),
  actions: {
    async ensureAnonymousToken() {
      this.anonymousToken = await getAnonymousToken()
    }
  }
})
