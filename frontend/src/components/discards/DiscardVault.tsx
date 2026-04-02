import { useEffect, useState } from 'react'
import { ExternalLink, RefreshCw } from 'lucide-react'
import { clsx } from 'clsx'
import { LaneBadge, QualityBadge, RuleBadge, ConfidenceScore } from '../shared/Badge'
import { getVaultDiscards } from '../../api/client'
import type { DiscardRecord } from '../../types'

function truncate(text: string, len = 50): string {
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

export function DiscardVault() {
  const [discards, setDiscards] = useState<DiscardRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getVaultDiscards()
      setDiscards(data)
    } catch (e) {
      setError('Failed to load discard vault.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-[var(--color-border)]">
        <div>
          <h2 className="text-sm font-semibold text-[var(--color-text)]">Discard Vault</h2>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            Rolling log of the 100 most recent discarded leads across all runs
          </p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {!loading && (
            <span className="text-xs text-[var(--color-text-dim)]">
              {discards.length} / 100 entries
            </span>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-accent)] transition-colors disabled:opacity-40"
          >
            <RefreshCw className={clsx('w-3.5 h-3.5', loading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center flex-1 text-sm text-[var(--color-text-muted)]">
          Loading vault...
        </div>
      ) : error ? (
        <div className="flex items-center justify-center flex-1 text-sm text-red-400">{error}</div>
      ) : discards.length === 0 ? (
        <div className="flex items-center justify-center flex-1 text-sm text-[var(--color-text-muted)]">
          No discards yet. Run the pipeline to populate the vault.
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
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
                <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Distress Signal</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Reason Qualified</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Quality</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Score</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Private</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Rule</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-[var(--color-text-muted)] whitespace-nowrap">Discard Reason</th>
              </tr>
            </thead>
            <tbody>
              {discards.map((d) => (
                <tr
                  key={d.lead_id}
                  className="border-b border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] opacity-75 hover:opacity-100 transition-opacity"
                >
                  <td className="px-4 py-2.5 font-medium text-[var(--color-text)] whitespace-nowrap max-w-48 truncate">
                    {d.company_name}
                  </td>
                  <td className="px-4 py-2.5 whitespace-nowrap">
                    <LaneBadge lane={d.lead_lane} />
                  </td>
                  <td className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                    {d.portfolio_type ? d.portfolio_type.replace(/_/g, ' ') : '--'}
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
                        className="flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline max-w-36 truncate"
                      >
                        <span className="truncate">{d.website.replace(/^https?:\/\//, '')}</span>
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                    ) : '--'}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] font-mono whitespace-nowrap">
                    {d.business_phone || '--'}
                  </td>
                  <td className="px-4 py-2.5 whitespace-nowrap">
                    {d.email ? (
                      <a href={`mailto:${d.email}`} className="text-xs text-[var(--color-accent)] hover:underline font-mono">
                        {d.email}
                      </a>
                    ) : '--'}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                    {d.named_contact || '--'}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                    {d.contact_title || '--'}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-amber-400 whitespace-nowrap max-w-48 truncate" title={d.distress_signal ?? ''}>
                    {d.distress_signal || '--'}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] max-w-56 truncate" title={d.reason_qualified}>
                    {truncate(d.reason_qualified, 45)}
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
                  <td className="px-4 py-2.5 whitespace-nowrap">
                    <RuleBadge rule={d.rule} />
                  </td>
                  <td className="px-4 py-2.5 text-xs text-[var(--color-text-muted)] whitespace-nowrap max-w-64 truncate" title={d.reason}>
                    {d.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
