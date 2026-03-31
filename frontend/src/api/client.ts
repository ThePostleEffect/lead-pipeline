// Typed API client — all calls go through Vite proxy (/api → localhost:8000)

import type {
  CollectParams,
  CreateScheduleParams,
  DiscardRecord,
  Lead,
  LeadInspection,
  RunListItem,
  RunResponse,
  RulesConfig,
  Schedule,
  SourceHealthResponse,
  SourceLog,
} from '../types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ---- Runs ----

export async function startRun(
  params: CollectParams,
  file?: File,
): Promise<RunResponse> {
  const form = new FormData()
  form.append('lane', params.lane)
  if (params.limit) form.append('limit', String(params.limit))
  if (params.min_quality) form.append('min_quality', params.min_quality)
  if (params.source_type) form.append('source_type', params.source_type)
  form.append('save_discards', String(params.save_discards))
  form.append('export_xlsx', String(params.export_xlsx))
  if (params.chapters) form.append('chapters', params.chapters)
  if (params.lookback_days) form.append('lookback_days', String(params.lookback_days))
  if (params.include_individuals !== undefined) form.append('include_individuals', String(params.include_individuals))
  if (params.company_types) form.append('company_types', params.company_types)
  if (file) form.append('source_file', file)

  return request<RunResponse>('/runs/collect', { method: 'POST', body: form })
}

export async function getRunStatus(runId: string): Promise<RunResponse> {
  return request<RunResponse>(`/runs/${runId}`)
}

export async function getRunLeads(runId: string): Promise<Lead[]> {
  return request<Lead[]>(`/runs/${runId}/leads`)
}

export async function getRunDiscards(runId: string): Promise<DiscardRecord[]> {
  return request<DiscardRecord[]>(`/runs/${runId}/discards`)
}

export async function listRuns(): Promise<RunListItem[]> {
  return request<RunListItem[]>('/runs')
}

// ---- Leads ----

export async function getLeadDetail(
  leadId: string,
  runId: string,
): Promise<LeadInspection> {
  return request<LeadInspection>(`/leads/${leadId}?run_id=${runId}`)
}

// ---- Rules ----

export async function getRules(): Promise<RulesConfig> {
  return request<RulesConfig>('/rules')
}

// ---- Health ----

export async function getSourceHealth(): Promise<SourceHealthResponse> {
  return request<SourceHealthResponse>('/health/sources')
}

// ---- Source Logs ----

export async function getRunSourceLogs(runId: string): Promise<SourceLog[]> {
  return request<SourceLog[]>(`/runs/${runId}/source-logs`)
}

// ---- Exports ----

export async function downloadXlsx(runId: string): Promise<void> {
  const res = await fetch(`${BASE}/exports/xlsx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId }),
  })
  if (!res.ok) throw new Error(`Export failed: HTTP ${res.status}`)

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `run_${runId}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

export async function downloadJson(runId: string): Promise<void> {
  const res = await fetch(`${BASE}/exports/json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId }),
  })
  if (!res.ok) throw new Error(`Export failed: HTTP ${res.status}`)

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `run_${runId}_leads.json`
  a.click()
  URL.revokeObjectURL(url)
}

// ---- Schedules ----

export async function listSchedules(): Promise<Schedule[]> {
  return request<Schedule[]>('/schedules')
}

export async function createSchedule(params: CreateScheduleParams): Promise<Schedule> {
  return request<Schedule>('/schedules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
}

export async function updateSchedule(
  scheduleId: string,
  updates: Partial<Pick<Schedule, 'name' | 'lane' | 'interval_hours' | 'params' | 'enabled'>>,
): Promise<Schedule> {
  return request<Schedule>(`/schedules/${scheduleId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
}

export async function deleteSchedule(scheduleId: string): Promise<void> {
  await fetch(`${BASE}/schedules/${scheduleId}`, { method: 'DELETE' })
}

// ---- Polling ----

export function pollRunStatus(
  runId: string,
  onUpdate: (run: RunResponse) => void,
  intervalMs = 2000,
): () => void {
  const id = setInterval(async () => {
    try {
      const run = await getRunStatus(runId)
      onUpdate(run)
      if (run.status === 'completed' || run.status === 'failed') {
        clearInterval(id)
      }
    } catch {
      clearInterval(id)
    }
  }, intervalMs)
  return () => clearInterval(id)
}
