import { apiRequest } from './api'

export interface RepairRecord {
  id: string
  diagnosis_result_id: string
  house_area: string | null
  actual_solution: string | null
  actual_cost: number | null
  provider_name: string | null
  reminder_status: string
  is_resolved: boolean | null
  is_recurred: boolean | null
  created_at: string | null
}

export function saveRepairRecord(diagnosisResultId: string): Promise<RepairRecord> {
  return apiRequest<RepairRecord>('/repair-records', {
    method: 'POST',
    body: JSON.stringify({ diagnosis_result_id: diagnosisResultId })
  })
}

export function fetchRepairRecords(): Promise<{ items: RepairRecord[]; total: number }> {
  return apiRequest('/repair-records')
}
