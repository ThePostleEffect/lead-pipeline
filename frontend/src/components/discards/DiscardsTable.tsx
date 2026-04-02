import { useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { clsx } from 'clsx'
import { LaneBadge, QualityBadge, ConfidenceScore, RuleBadge } from '../shared/Badge'
import { EmptyState } from '../shared/EmptyState'
import { DiscardDrawer } from '../detail/DiscardDrawer'
import { useRunStore } from '../../stores/runStore'
import type { DiscardRecord } from '../../types'

function truncate(text: string, len = 60): string {
  if (!text) return '--'
  return text.length > len ? text.slice(0, len) + '...' : text
}

function BoolDot({ value }: { value: boolean }) {
  return (
    <span
      className={clsx('inline-block w-2 h-2 rounded-full', value ? 'bg-green-400' : 'bg-zinc-600')}
      title={value ? 'Yes' : 'No'}
    />
  )
}

export function DiscardsTable() {
  const { discards } = useRunStore()
  const [selected, setSelected] = useState<DiscardRecord | null>(null)
  const selectedIdx = selected ? discards.findIndex((d) => d.lead_id === selected.lead_id) : -1

  if (discards.length === 0) {
    return <EmptyState message="No discards to show." />
  }

  return (
    <>
    <div className="overflow-auto h-full">
      <table className="w-max min-w-full text-sm">
        <thead className="sticky top-0 bg-[var(--color-surface)] z-10">
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Company</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Lane</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Portfolio Type</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">State</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">City</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Website</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Phone</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Email</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Contact</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Title</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Employees</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Distress Signal</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Financing Signal</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">BK Ch.</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Reason Qualified</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Quality</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Score</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Private</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Notes</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Rule</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Discard Reason</th>
          </tr>
        </thead>
        <tbody>
          {discards.map((d) => (
            <tr
              key={d.lead_id}
              onClick={() => setSelected(d)}
              className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] opacity-70 hover:opacity-100 transition-opacity cursor-pointer"
            >
              <td className="px-4 py-2.5 font-medium text-[var(--color-text)] whitespace-nowrap max-w-48 truncate">
                {d.company_name}
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                <LaneBadge lane={d.lead_lane} />
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.portfolio_type || '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.state || '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.city || '--'}
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                {d.website ? (
                  <a
                    href={d.website.startsWith('http') ? d.website : `https://${d.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[var(--color-accent)] hover:underline max-w-36 truncate"
                  >
                    <span className="truncate">{d.website.replace(/^https?:\/\//, '')}</span>
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                ) : '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.business_phone || '--'}
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                {d.email ? (
                  <a href={`mailto:${d.email}`} className="text-xs text-[var(--color-accent)] hover:underline font-mono">
                    {d.email}
                  </a>
                ) : '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.named_contact || '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.contact_title || '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.employee_estimate ?? '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap max-w-40 truncate" title={d.distress_signal ?? ''}>
                {d.distress_signal || '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap max-w-40 truncate" title={d.financing_signal ?? ''}>
                {d.financing_signal || '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap">
                {d.bankruptcy_chapter || '--'}
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap max-w-56 truncate" title={d.reason_qualified}>
                {truncate(d.reason_qualified, 50)}
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                <QualityBadge tier={d.quality_tier} />
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                <ConfidenceScore score={d.confidence_score} />
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                <BoolDot value={d.private_company_confirmed} />
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap max-w-48 truncate" title={d.notes}>
                {truncate(d.notes, 40)}
              </td>
              <td className="px-4 py-2.5 whitespace-nowrap">
                <RuleBadge rule={d.rule} />
              </td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] whitespace-nowrap max-w-64 truncate" title={d.reason}>
                {d.reason}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>

    {selected && (
      <DiscardDrawer
        discard={selected}
        index={selectedIdx}
        total={discards.length}
        onClose={() => setSelected(null)}
        onPrev={() => selectedIdx > 0 && setSelected(discards[selectedIdx - 1])}
        onNext={() => selectedIdx < discards.length - 1 && setSelected(discards[selectedIdx + 1])}
      />
    )}
    </>
  )
}
