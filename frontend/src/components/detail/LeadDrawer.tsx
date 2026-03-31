import { useEffect, useState } from 'react'
import { X, ExternalLink, ChevronLeft, ChevronRight, Copy, Check } from 'lucide-react'
import { clsx } from 'clsx'
import { useRunStore } from '../../stores/runStore'
import { getLeadDetail } from '../../api/client'
import { LaneBadge, QualityBadge, ConfidenceScore } from '../shared/Badge'
import { Spinner } from '../shared/Spinner'
import type { LeadInspection } from '../../types'

export function LeadDrawer() {
  const { selectedLeadId, selectLead, leads, currentRun } = useRunStore()
  const [inspection, setInspection] = useState<LeadInspection | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const currentIndex = leads.findIndex((l) => l.lead_id === selectedLeadId)

  useEffect(() => {
    if (!selectedLeadId || !currentRun) {
      setInspection(null)
      return
    }
    setLoading(true)
    getLeadDetail(selectedLeadId, currentRun.run_id)
      .then(setInspection)
      .catch(() => setInspection(null))
      .finally(() => setLoading(false))
  }, [selectedLeadId, currentRun])

  if (!selectedLeadId) return null

  const lead = inspection?.lead_record
  const goPrev = () => {
    if (currentIndex > 0) selectLead(leads[currentIndex - 1].lead_id)
  }
  const goNext = () => {
    if (currentIndex < leads.length - 1) selectLead(leads[currentIndex + 1].lead_id)
  }

  const copyPhone = () => {
    if (lead?.business_phone) {
      navigator.clipboard.writeText(lead.business_phone)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/40 z-40"
        onClick={() => selectLead(null)}
      />

      {/* Drawer */}
      <div className="fixed top-0 right-0 h-full w-[480px] max-w-[90vw] bg-[var(--color-surface)] border-l border-[var(--color-border)] z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <button onClick={goPrev} disabled={currentIndex <= 0} className="p-1 rounded hover:bg-[var(--color-surface-hover)] disabled:opacity-20">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs text-[var(--color-text-dim)]">
              {currentIndex + 1} / {leads.length}
            </span>
            <button onClick={goNext} disabled={currentIndex >= leads.length - 1} className="p-1 rounded hover:bg-[var(--color-surface-hover)] disabled:opacity-20">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <button onClick={() => selectLead(null)} className="p-1 rounded hover:bg-[var(--color-surface-hover)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex justify-center py-16">
              <Spinner message="Loading lead details..." />
            </div>
          ) : lead ? (
            <div className="p-5 space-y-5">
              {/* Title */}
              <div>
                <h2 className="text-lg font-semibold">{lead.company_name}</h2>
                <div className="flex items-center gap-2 mt-1.5">
                  <LaneBadge lane={lead.lead_lane} />
                  <QualityBadge tier={lead.quality_tier} />
                  <ConfidenceScore score={lead.confidence_score} />
                </div>
              </div>

              {/* Contact */}
              <Section title="Contact">
                <Field label="Website">
                  {lead.website ? (
                    <a href={lead.website} target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] inline-flex items-center gap-1">
                      {lead.website} <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : '--'}
                </Field>
                <Field label="Phone">
                  {lead.business_phone ? (
                    <span className="inline-flex items-center gap-2 font-mono">
                      {lead.business_phone}
                      <button onClick={copyPhone} className="p-0.5 rounded hover:bg-[var(--color-surface-hover)]">
                        {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3 text-[var(--color-text-dim)]" />}
                      </button>
                    </span>
                  ) : '--'}
                </Field>
                <Field label="Contact">{lead.named_contact || '--'}</Field>
                <Field label="Title">{lead.contact_title || '--'}</Field>
                <Field label="Location">{[lead.city, lead.state].filter(Boolean).join(', ') || '--'}</Field>
              </Section>

              {/* Qualification */}
              <Section title="Qualification">
                <Field label="Reason">{lead.reason_qualified || '--'}</Field>
                <Field label="Distress Signal">{lead.distress_signal || '--'}</Field>
                <Field label="Financing Signal">{lead.financing_signal || '--'}</Field>
                <Field label="Portfolio Type">{lead.portfolio_type || '--'}</Field>
                <Field label="Bankruptcy Ch.">{lead.bankruptcy_chapter || '--'}</Field>
              </Section>

              {/* Score Breakdown */}
              {inspection && (
                <Section title="Score Breakdown">
                  <div className="space-y-1.5">
                    {inspection.score_breakdown.map((entry, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <div className="w-20 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[var(--color-accent)]"
                            style={{ width: `${(entry.points / 15) * 100}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-[var(--color-accent)] w-6">+{entry.points}</span>
                        <span className="text-xs text-[var(--color-text-muted)]">{entry.reason}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t border-[var(--color-border)]">
                    <span className="text-xs text-[var(--color-text-dim)]">Total: </span>
                    <span className="text-sm font-semibold">{inspection.confidence_score}</span>
                    <span className="text-xs text-[var(--color-text-dim)]"> / 100</span>
                  </div>
                </Section>
              )}

              {/* Flags */}
              {inspection && (
                <Section title="Flags">
                  <div className="flex flex-wrap gap-2">
                    <FlagChip label="Private" active={inspection.rule_flags.private_company_confirmed} />
                    <FlagChip label="Public" active={inspection.rule_flags.public_company_confirmed} negative />
                    <FlagChip label="Trustee" active={inspection.rule_flags.trustee_related} negative />
                  </div>
                </Section>
              )}

              {/* Provenance */}
              <Section title="Source">
                <Field label="Type">{lead.source_type}</Field>
                <Field label="URL">
                  {lead.source_url ? (
                    <a href={lead.source_url} target="_blank" rel="noopener noreferrer" className="text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] inline-flex items-center gap-1 break-all">
                      {lead.source_url} <ExternalLink className="w-3 h-3 shrink-0" />
                    </a>
                  ) : '--'}
                </Field>
                <Field label="Collected">{new Date(lead.collected_at).toLocaleString()}</Field>
                <Field label="Lead ID">
                  <span className="font-mono text-xs">{lead.lead_id}</span>
                </Field>
              </Section>

              {/* Notes */}
              {lead.notes && (
                <Section title="Notes">
                  <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-wrap break-words">{lead.notes}</p>
                </Section>
              )}
            </div>
          ) : (
            <div className="flex justify-center py-16 text-[var(--color-text-dim)] text-sm">
              Failed to load lead details.
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ---- Section ----

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider mb-2">{title}</h3>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

// ---- Field ----

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="text-xs text-[var(--color-text-dim)] w-24 shrink-0 pt-0.5">{label}</span>
      <span className="text-sm text-[var(--color-text)] min-w-0">{children}</span>
    </div>
  )
}

// ---- Flag Chip ----

function FlagChip({ label, active, negative }: { label: string; active: boolean; negative?: boolean }) {
  return (
    <span
      className={clsx(
        'px-2 py-0.5 rounded text-xs border',
        active
          ? negative
            ? 'bg-red-500/15 text-red-400 border-red-500/30'
            : 'bg-green-500/15 text-green-400 border-green-500/30'
          : 'bg-[var(--color-background)] text-[var(--color-text-dim)] border-[var(--color-border)]',
      )}
    >
      {label}: {active ? 'Yes' : 'No'}
    </span>
  )
}
