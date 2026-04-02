import { X, ExternalLink, ChevronLeft, ChevronRight, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { clsx } from 'clsx'
import { LaneBadge, QualityBadge, RuleBadge, ConfidenceScore } from '../shared/Badge'
import type { DiscardRecord } from '../../types'

interface DiscardDrawerProps {
  discard: DiscardRecord
  index: number
  total: number
  onClose: () => void
  onPrev: () => void
  onNext: () => void
}

export function DiscardDrawer({ discard: d, index, total, onClose, onPrev, onNext }: DiscardDrawerProps) {
  const [copied, setCopied] = useState(false)

  const copyPhone = () => {
    if (d.business_phone) {
      navigator.clipboard.writeText(d.business_phone)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-[480px] max-w-[90vw] bg-[var(--color-surface)] border-l border-[var(--color-border)] z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <button onClick={onPrev} disabled={index <= 0} className="p-1 rounded hover:bg-[var(--color-surface-hover)] disabled:opacity-20">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-[var(--color-text-dim)]">{index + 1} / {total}</span>
            <button onClick={onNext} disabled={index >= total - 1} className="p-1 rounded hover:bg-[var(--color-surface-hover)] disabled:opacity-20">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-[var(--color-surface-hover)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-5 space-y-5">

            {/* Title */}
            <div>
              <h2 className="text-lg font-semibold">{d.company_name}</h2>
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                <LaneBadge lane={d.lead_lane} />
                <QualityBadge tier={d.quality_tier} />
                <ConfidenceScore score={d.confidence_score} />
              </div>
            </div>

            {/* Discard reason — prominent */}
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/25">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider">Discard Reason</span>
                <RuleBadge rule={d.rule} />
              </div>
              <p className="text-sm text-[var(--color-text-muted)]">{d.reason}</p>
            </div>

            {/* Contact */}
            <Section title="Contact">
              <Field label="Website">
                {d.website ? (
                  <a href={d.website.startsWith('http') ? d.website : `https://${d.website}`} target="_blank" rel="noopener noreferrer"
                    className="text-[var(--color-accent)] hover:underline inline-flex items-center gap-1">
                    {d.website} <ExternalLink className="w-3 h-3" />
                  </a>
                ) : '--'}
              </Field>
              <Field label="Phone">
                {d.business_phone ? (
                  <span className="inline-flex items-center gap-2 font-mono">
                    {d.business_phone}
                    <button onClick={copyPhone} className="p-0.5 rounded hover:bg-[var(--color-surface-hover)]">
                      {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3 text-[var(--color-text-dim)]" />}
                    </button>
                  </span>
                ) : '--'}
              </Field>
              <Field label="Email">
                {d.email ? (
                  <a href={`mailto:${d.email}`} className="text-[var(--color-accent)] hover:underline font-mono text-sm">
                    {d.email}
                  </a>
                ) : '--'}
              </Field>
              <Field label="Contact">{d.named_contact || '--'}</Field>
              <Field label="Title">{d.contact_title || '--'}</Field>
              <Field label="Location">{[d.city, d.state].filter(Boolean).join(', ') || '--'}</Field>
            </Section>

            {/* Qualification */}
            <Section title="Qualification">
              <Field label="Reason">{d.reason_qualified || '--'}</Field>
              <Field label="Distress Signal">{d.distress_signal || '--'}</Field>
              <Field label="Financing Signal">{d.financing_signal || '--'}</Field>
              <Field label="Portfolio Type">{d.portfolio_type ? d.portfolio_type.replace(/_/g, ' ') : '--'}</Field>
              <Field label="Bankruptcy Ch.">{d.bankruptcy_chapter || '--'}</Field>
            </Section>

            {/* Score Breakdown */}
            {d.score_breakdown && d.score_breakdown.length > 0 && (
              <Section title="Score Breakdown">
                <div className="space-y-1.5">
                  {d.score_breakdown.map((entry, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="w-20 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                        <div className="h-full rounded-full bg-[var(--color-accent)]" style={{ width: `${(entry.points / 15) * 100}%` }} />
                      </div>
                      <span className="text-xs font-mono text-[var(--color-accent)] w-6">+{entry.points}</span>
                      <span className="text-xs text-[var(--color-text-muted)]">{entry.reason}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
                  <span className="text-xs text-[var(--color-text-dim)]">Total: </span>
                  <span className="text-sm font-semibold">{d.confidence_score}</span>
                  <span className="text-xs text-[var(--color-text-dim)]"> / 100</span>
                </div>
              </Section>
            )}

            {/* Flags */}
            <Section title="Flags">
              <div className="flex flex-wrap gap-2">
                <FlagChip label="Private" active={d.private_company_confirmed} />
                <FlagChip label="Public" active={d.public_company_confirmed} negative />
                <FlagChip label="Trustee" active={d.trustee_related} negative />
              </div>
            </Section>

            {/* Source */}
            <Section title="Source">
              <Field label="Type">{d.source_type || '--'}</Field>
              <Field label="URL">
                {d.source_url ? (
                  <a href={d.source_url} target="_blank" rel="noopener noreferrer"
                    className="text-[var(--color-accent)] hover:underline inline-flex items-center gap-1 break-all">
                    {d.source_url} <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                ) : '--'}
              </Field>
              {d.collected_at && (
                <Field label="Collected">{new Date(d.collected_at).toLocaleString()}</Field>
              )}
              <Field label="Lead ID"><span className="font-mono text-xs">{d.lead_id}</span></Field>
            </Section>

            {/* Notes */}
            {d.notes && (
              <Section title="Notes">
                <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-wrap break-words">{d.notes}</p>
              </Section>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">{title}</h3>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="text-xs text-[var(--color-text-dim)] w-24 shrink-0 pt-0.5">{label}</span>
      <span className="text-sm text-[var(--color-text)] min-w-0">{children}</span>
    </div>
  )
}

function FlagChip({ label, active, negative }: { label: string; active: boolean; negative?: boolean }) {
  return (
    <span className={clsx(
      'px-2 py-0.5 rounded text-xs border',
      active
        ? negative
          ? 'bg-red-500/15 text-red-400 border-red-500/30'
          : 'bg-green-500/15 text-green-400 border-green-500/30'
        : 'bg-[var(--color-background)] text-[var(--color-text-dim)] border-[var(--color-border)]',
    )}>
      {label}: {active ? 'Yes' : 'No'}
    </span>
  )
}
