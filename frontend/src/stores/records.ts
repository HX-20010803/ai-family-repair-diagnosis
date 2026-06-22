import { defineStore } from 'pinia'
import { fetchRepairRecords, saveRepairRecord, type RepairRecord } from '../services/records'

export const useRecordsStore = defineStore('records', {
  state: () => ({
    items: [] as RepairRecord[],
    total: 0,
    loading: false,
    error: ''
  }),
  actions: {
    async fetchList() {
      this.loading = true
      this.error = ''
      try {
        const response = await fetchRepairRecords()
        this.items = response.items
        this.total = response.total
      } catch (error) {
        this.error = error instanceof Error ? error.message : '维修记录加载失败'
      } finally {
        this.loading = false
      }
    },
    async saveRecord(diagnosisResultId: string) {
      const record = await saveRepairRecord(diagnosisResultId)
      this.items = [record, ...this.items.filter((item) => item.id !== record.id)]
      this.total = this.items.length
      return record
    }
  }
})
