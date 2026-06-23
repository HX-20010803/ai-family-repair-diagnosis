import { apiRequest } from './api'

// Human-readable labels for secondary category codes (PRD §6.1).
export const SECONDARY_CATEGORY_LABELS: Record<string, string> = {
  water_leak: '漏水渗水',
  drain_blocked: '马桶/下水堵塞',
  ac_not_cooling: '空调不制冷',
  circuit_trip: '电路跳闸',
  lock_failure: '门锁故障',
  wall_mold: '墙面发霉',
  water_heater_failure: '热水器故障',
  range_hood_gas_stove: '油烟机/燃气灶',
  floor_drain_smell: '地漏反味',
  window_hardware: '门窗五金'
}

export function secondaryLabel(code: string | null): string {
  if (!code) return '未知故障'
  return SECONDARY_CATEGORY_LABELS[code] || code
}

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
  updated_at: string | null
  // Diagnosis summary joined from diagnosis_results (P1-2)
  primary_category: string | null
  secondary_category: string | null
  urgency_level: string | null
  possible_causes: string[] | null
  recommended_actions: string[] | null
  forbidden_actions: string[] | null
  price_range: string | null
}

export interface RepairRecordPatch {
  actual_solution?: string
  actual_cost?: number
  provider_name?: string
  is_resolved?: boolean
  is_recurred?: boolean
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

export function fetchRepairRecord(id: string): Promise<RepairRecord> {
  return apiRequest<RepairRecord>(`/repair-records/${id}`)
}

export function updateRepairRecord(id: string, patch: RepairRecordPatch): Promise<RepairRecord> {
  return apiRequest<RepairRecord>(`/repair-records/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(patch)
  })
}
