import { RuleBadge, QualityBadge } from '../shared/Badge'
import { EmptyState } from '../shared/EmptyState'
import { useRunStore } from '../../stores/runStore'

export function DiscardsTable() {
  const { discards } = useRunStore()

  if (discards.length === 0) {
    return <EmptyState message="No discards to show." />
  }

  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-[var(--color-surface)] z-10">
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Company</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Lane</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">State</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Quality</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Rule</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)]">Reason</th>
          </tr>
        </thead>
        <tbody>
          {discards.map((d) => (
            <tr key={d.lead_id} className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)]">
              <td className="px-4 py-2.5 font-medium text-[var(--color-text)] max-w-56 truncate">{d.company_name}</td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)]">{d.lead_lane}</td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)]">{d.state}</td>
              <td className="px-4 py-2.5"><QualityBadge tier={d.quality_tier} /></td>
              <td className="px-4 py-2.5"><RuleBadge rule={d.rule} /></td>
              <td className="px-4 py-2.5 text-[var(--color-text-muted)] max-w-72 truncate">{d.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
