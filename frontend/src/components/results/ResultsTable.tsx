import { useState, useMemo } from 'react'
import { ArrowUpDown, ExternalLink } from 'lucide-react'
import { clsx } from 'clsx'
import { LaneBadge, QualityBadge, ConfidenceScore } from '../shared/Badge'
import { EmptyState } from '../shared/EmptyState'
import { useRunStore } from '../../stores/runStore'
import type { Lead } from '../../types'

type SortField = 'company_name' | 'state' | 'confidence_score' | 'quality_tier'
type SortDir = 'asc' | 'desc'

function truncate(text: string, len = 60): string {
  if (!text) return '--'
  return text.length > len ? text.slice(0, len) + '...' : text
}

function fmtDate(iso: string): string {
  if (!iso) return '--'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function BoolDot({ value }: { value: boolean }) {
  return (
    <span className={clsx(
      'inline-block w-2 h-2 rounded-full',
      value ? 'bg-green-400' : 'bg-zinc-600',
    )} title={value ? 'Yes' : 'No'} />
  )
}

export function ResultsTable() {
  const { leads, selectLead, selectedLeadId } = useRunStore()
  const [sortField, setSortField] = useState<SortField>('confidence_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [filterLane, setFilterLane] = useState<string>('')
  const [filterQuality, setFilterQuality] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState('')

  const filtered = useMemo(() => {
    let result = [...leads]
    if (filterLane) result = result.filter((l) => l.lead_lane === filterLane)
    if (filterQuality) result = result.filter((l) => l.quality_tier === filterQuality)
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      result = result.filter(
        (l) =>
          l.company_name.toLowerCase().includes(q) ||
          l.state.toLowerCase().includes(q) ||
          (l.notes || '').toLowerCase().includes(q) ||
          (l.reason_qualified || '').toLowerCase().includes(q),
      )
    }
    return result
  }, [leads, filterLane, filterQuality, searchTerm])

  const sorted = useMemo(() => {
    const tierRank: Record<string, number> = { best_case: 0, mid_level: 1, weak: 2 }
    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sortField === 'confidence_score') {
        cmp = a.confidence_score - b.confidence_score
      } else if (sortField === 'quality_tier') {
        cmp = (tierRank[a.quality_tier] ?? 9) - (tierRank[b.quality_tier] ?? 9)
      } else if (sortField === 'company_name') {
        cmp = a.company_name.localeCompare(b.company_name)
      } else if (sortField === 'state') {
        cmp = a.state.localeCompare(b.state)
      }
      return sortDir === 'desc' ? -cmp : cmp
    })
  }, [filtered, sortField, sortDir])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir(field === 'confidence_score' ? 'desc' : 'asc')
    }
  }

  if (leads.length === 0) {
    return <EmptyState message="No results yet. Run the pipeline to see leads." />
  }

  return (
    <div className="flex flex-col h-full">
      {/* Filters */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-[var(--color-border)]">
        <input
          type="text"
          placeholder="Search company, notes..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="h-8 w-56 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] focus:outline-none focus:border-[var(--color-accent)]"
        />
        <select
          value={filterLane}
          onChange={(e) => setFilterLane(e.target.value)}
          className="h-8 px-2 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none"
        >
          <option value="">All Lanes</option>
          <option value="bankruptcy">Bankruptcy</option>
          <option value="charged_off">Charged Off</option>
          <option value="performing">Performing</option>
          <option value="capital_seeking">Capital Seeking</option>
        </select>
        <select
          value={filterQuality}
          onChange={(e) => setFilterQuality(e.target.value)}
          className="h-8 px-2 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none"
        >
          <option value="">All Quality</option>
          <option value="best_case">Best Case</option>
          <option value="mid_level">Mid Level</option>
        </select>
        <span className="ml-auto text-xs text-[var(--color-text-dim)]">
          {sorted.length} of {leads.length} leads
        </span>
      </div>

      {/* Table — horizontally scrollable to fit all columns */}
      <div className="flex-1 overflow-auto">
        <table className="w-max min-w-full text-sm">
          <thead className="sticky top-0 bg-[var(--color-surface)] z-10">
            <tr className="border-b border-[var(--color-border)]">
              <SortHeader field="company_name" label="Company" current={sortField} dir={sortDir} onSort={toggleSort} />
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Lane</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Portfolio Type</th>
              <SortHeader field="state" label="State" current={sortField} dir={sortDir} onSort={toggleSort} />
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">City</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Website</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Phone</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Contact</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Title</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Employees</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Distress Signal</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Financing Signal</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">BK Ch.</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Reason Qualified</th>
              <SortHeader field="quality_tier" label="Quality" current={sortField} dir={sortDir} onSort={toggleSort} />
              <SortHeader field="confidence_score" label="Score" current={sortField} dir={sortDir} onSort={toggleSort} />
              <th className="px-3 py-2 text-center text-xs font-medium text-[var(--color-text-muted)]">Private</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Source</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Source URL</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Notes</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Status</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Collected</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Lead ID</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((lead) => (
              <tr
                key={lead.lead_id}
                onClick={() => selectLead(lead.lead_id)}
                className={clsx(
                  'border-b border-[var(--color-border)] cursor-pointer transition-colors',
                  selectedLeadId === lead.lead_id
                    ? 'bg-[var(--color-accent)]/10'
                    : 'hover:bg-[var(--color-surface-hover)]',
                )}
              >
                {/* Company */}
                <td className="px-3 py-2.5 font-medium text-[var(--color-text)] whitespace-nowrap max-w-56 truncate">
                  {lead.company_name}
                </td>

                {/* Lane */}
                <td className="px-3 py-2.5">
                  <LaneBadge lane={lead.lead_lane} />
                </td>

                {/* Portfolio Type */}
                <td className="px-3 py-2.5 text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                  {lead.portfolio_type ? lead.portfolio_type.replace(/_/g, ' ') : '--'}
                </td>

                {/* State */}
                <td className="px-3 py-2.5 text-[var(--color-text-muted)]">{lead.state || '--'}</td>

                {/* City */}
                <td className="px-3 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">{lead.city || '--'}</td>

                {/* Website */}
                <td className="px-3 py-2.5">
                  <WebsiteCell url={lead.website} />
                </td>

                {/* Phone */}
                <td className="px-3 py-2.5 text-[var(--color-text-muted)] font-mono text-xs whitespace-nowrap">
                  {lead.business_phone || '--'}
                </td>

                {/* Contact */}
                <td className="px-3 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap max-w-36 truncate">
                  {lead.named_contact || '--'}
                </td>

                {/* Title */}
                <td className="px-3 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap max-w-36 truncate">
                  {lead.contact_title || '--'}
                </td>

                {/* Employees */}
                <td className="px-3 py-2.5 text-[var(--color-text-muted)] text-center">
                  {lead.employee_estimate ?? '--'}
                </td>

                {/* Distress Signal */}
                <td className="px-3 py-2.5 text-xs text-amber-400 whitespace-nowrap max-w-48 truncate" title={lead.distress_signal || ''}>
                  {lead.distress_signal || '--'}
                </td>

                {/* Financing Signal */}
                <td className="px-3 py-2.5 text-xs text-blue-400 whitespace-nowrap max-w-40 truncate" title={lead.financing_signal || ''}>
                  {lead.financing_signal || '--'}
                </td>

                {/* Bankruptcy Chapter */}
                <td className="px-3 py-2.5 text-[var(--color-text-muted)] text-center">
                  {lead.bankruptcy_chapter || '--'}
                </td>

                {/* Reason Qualified */}
                <td className="px-3 py-2.5 text-xs text-[var(--color-text-muted)] max-w-64 truncate" title={lead.reason_qualified}>
                  {lead.reason_qualified || '--'}
                </td>

                {/* Quality */}
                <td className="px-3 py-2.5">
                  <QualityBadge tier={lead.quality_tier} />
                </td>

                {/* Score */}
                <td className="px-3 py-2.5">
                  <ConfidenceScore score={lead.confidence_score} />
                </td>

                {/* Private */}
                <td className="px-3 py-2.5 text-center">
                  <BoolDot value={lead.private_company_confirmed} />
                </td>

                {/* Source Type */}
                <td className="px-3 py-2.5 text-xs text-[var(--color-text-dim)] whitespace-nowrap">
                  {lead.source_type || '--'}
                </td>

                {/* Source URL */}
                <td className="px-3 py-2.5">
                  <SourceUrlCell url={lead.source_url} />
                </td>

                {/* Notes */}
                <td className="px-3 py-2.5 text-xs text-[var(--color-text-muted)] max-w-72 truncate" title={lead.notes}>
                  {lead.notes || '--'}
                </td>

                {/* Status */}
                <td className="px-3 py-2.5 text-xs text-[var(--color-text-muted)] capitalize">
                  {lead.status || '--'}
                </td>

                {/* Collected At */}
                <td className="px-3 py-2.5 text-xs text-[var(--color-text-dim)] whitespace-nowrap">
                  {fmtDate(lead.collected_at)}
                </td>

                {/* Lead ID */}
                <td className="px-3 py-2.5 text-xs font-mono text-[var(--color-text-dim)] whitespace-nowrap">
                  {lead.lead_id}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ---- Subcomponents ----

function WebsiteCell({ url }: { url: string }) {
  if (!url) return <span className="text-[var(--color-text-dim)]">--</span>
  let hostname = url
  try { hostname = new URL(url).hostname.replace('www.', '') } catch { /* keep raw */ }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      className="inline-flex items-center gap-1 text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] whitespace-nowrap max-w-40 truncate"
    >
      {hostname}
      <ExternalLink className="w-3 h-3 shrink-0" />
    </a>
  )
}

function SourceUrlCell({ url }: { url: string }) {
  if (!url) return <span className="text-[var(--color-text-dim)]">--</span>
  let hostname = url
  try { hostname = new URL(url).hostname.replace('www.', '') } catch { /* keep raw */ }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(e) => e.stopPropagation()}
      className="inline-flex items-center gap-1 text-xs text-[var(--color-text-dim)] hover:text-[var(--color-accent)] whitespace-nowrap max-w-32 truncate"
      title={url}
    >
      {hostname}
      <ExternalLink className="w-3 h-3 shrink-0" />
    </a>
  )
}

function SortHeader({
  field,
  label,
  current,
  dir,
  onSort,
}: {
  field: SortField
  label: string
  current: SortField
  dir: SortDir
  onSort: (f: SortField) => void
}) {
  const active = current === field
  return (
    <th
      onClick={() => onSort(field)}
      className="px-3 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] cursor-pointer select-none hover:text-[var(--color-text)] whitespace-nowrap"
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <ArrowUpDown
          className={clsx(
            'w-3 h-3',
            active ? 'text-[var(--color-accent)]' : 'opacity-30',
          )}
        />
        {active && (
          <span className="text-[var(--color-accent)] text-[10px]">
            {dir === 'asc' ? '\u2191' : '\u2193'}
          </span>
        )}
      </span>
    </th>
  )
}
