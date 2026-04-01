// TypeScript interfaces mirroring pipeline Pydantic models

export type LeadLane = 'charged_off' | 'bankruptcy' | 'performing' | 'capital_seeking'
export type QualityTier = 'best_case' | 'mid_level' | 'weak'
export type SourceType = 'manual' | 'public_web' | 'pacer' | 'api'
export type LeadStatus = 'new' | 'reviewed' | 'contacted' | 'qualified' | 'disqualified' | 'discarded'
export type RunStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface ScoreEntry {
  field: string
  points: number
  reason: string
}

export interface Lead {
  lead_id: string
  collected_at: string
  company_name: string
  lead_lane: LeadLane
  portfolio_type: string
  private_company_confirmed: boolean
  public_company_confirmed: boolean
  trustee_related: boolean
  state: string
  city: string
  website: string
  business_phone: string
  reason_qualified: string
  quality_tier: QualityTier
  confidence_score: number
  source_type: SourceType
  source_url: string
  notes: string
  status: LeadStatus
  named_contact: string | null
  contact_title: string | null
  employee_estimate: number | null
  distress_signal: string | null
  financing_signal: string | null
  bankruptcy_chapter: string | null
  score_breakdown: ScoreEntry[]
  score_reasons: string[]
}

export interface DiscardRecord {
  // Discard metadata
  reason: string
  rule: string
  // Full lead fields
  lead_id: string
  company_name: string
  lead_lane: string
  portfolio_type: string
  state: string
  city: string
  quality_tier: string
  confidence_score: number
  website: string
  business_phone: string
  reason_qualified: string
  notes: string
  source_type: string
  source_url: string
  named_contact: string | null
  contact_title: string | null
  employee_estimate: number | null
  distress_signal: string | null
  financing_signal: string | null
  bankruptcy_chapter: string | null
  private_company_confirmed: boolean
  public_company_confirmed: boolean
  trustee_related: boolean
  collected_at: string
}

export interface RunResponse {
  run_id: string
  lane: string
  status: RunStatus
  created_at: string
  completed_at: string | null
  raw_signal_count: number | null
  kept_count: number | null
  discard_count: number | null
  output_json_path: string | null
  discard_json_path: string | null
  xlsx_path: string | null
  error: string | null
}

export interface RunListItem {
  run_id: string
  lane: string
  status: RunStatus
  created_at: string
  completed_at: string | null
  kept_count: number | null
  discard_count: number | null
}

export interface LeadInspection {
  lead_record: Lead
  quality_tier: string
  confidence_score: number
  score_breakdown: ScoreEntry[]
  score_reasons: string[]
  source_provenance: {
    source_type: string
    source_url: string
  }
  rule_flags: {
    private_company_confirmed: boolean
    public_company_confirmed: boolean
    trustee_related: boolean
  }
  notes: string
}

export interface RulesConfig {
  lanes: Record<string, {
    description: string
    excluded_states: string[]
  }>
  discard_rules: Array<{
    name: string
    condition: string
  }>
  quality_tiers: Record<string, {
    required_fields?: string[]
    description?: string
  }>
  scoring_weights: Record<string, number>
  preferred_employee_range: {
    min: number
    max: number
  }
}

export interface CollectParams {
  lane: LeadLane
  limit?: number
  min_quality?: 'best_case' | 'mid_level'
  source_type?: 'json' | 'csv' | 'web' | 'auto'
  save_discards: boolean
  export_xlsx: boolean
  // Search filters
  chapters?: string       // Comma-separated: "13,7"
  lookback_days?: number
  include_individuals?: boolean
  company_types?: string  // Comma-separated: "credit_extenders,auto_dealers"
}

// Source health

export type SourceStatus = 'ready' | 'fallback' | 'disabled' | 'missing_key'

export interface SourceInfo {
  name: string
  type: 'source' | 'enrichment'
  description: string
  configured: boolean
  env_vars: string[]
  lanes: string[]
  status: SourceStatus
  fallback_note?: string | null
}

export interface SourceHealthResponse {
  sources: SourceInfo[]
  summary: {
    ready: number
    total: number
    all_configured: boolean
  }
}

// Source logs (from completed runs)

export interface SourceLog {
  source_name: string
  source_type: string
  source_url: string
  collected_at: string
  leads_found: number
  leads_kept: number
  notes: string
}

// Schedules

export interface Schedule {
  schedule_id: string
  name: string
  lane: LeadLane
  interval_hours: number
  params: Record<string, unknown>
  enabled: boolean
  last_run_at: string | null
  next_run_at: string
  created_at: string
}

export interface CreateScheduleParams {
  name: string
  lane: LeadLane
  interval_hours: number
  params?: Record<string, unknown>
}
