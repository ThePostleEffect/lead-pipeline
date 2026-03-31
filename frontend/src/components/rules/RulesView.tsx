import { useEffect, useState } from 'react'
import { getRules } from '../../api/client'
import type { RulesConfig } from '../../types'
import { Spinner } from '../shared/Spinner'
import { useRunStore } from '../../stores/runStore'
import { StatusBadge } from '../shared/Badge'

export function RulesView() {
  const [rules, setRules] = useState<RulesConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const { runHistory, loadHistory } = useRunStore()

  useEffect(() => {
    getRules()
      .then(setRules)
      .catch(() => setRules(null))
      .finally(() => setLoading(false))
    loadHistory()
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner message="Loading rules..." />
      </div>
    )
  }

  if (!rules) {
    return <div className="px-6 py-8 text-[var(--color-text-dim)]">Failed to load rules.</div>
  }

  return (
    <div className="overflow-auto h-full p-6 space-y-8">
      {/* Lanes */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Lanes</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(rules.lanes).map(([name, cfg]) => (
            <div key={name} className="p-3 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)]">
              <h4 className="text-sm font-medium text-[var(--color-text)] capitalize">{name.replace('_', ' ')}</h4>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">{cfg.description}</p>
              {cfg.excluded_states.length > 0 && (
                <div className="mt-2">
                  <span className="text-xs text-[var(--color-text-dim)]">Excluded: </span>
                  <span className="text-xs text-rose-400">{cfg.excluded_states.join(', ')}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Discard Rules */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Discard Rules</h3>
        <div className="space-y-2">
          {rules.discard_rules.map((rule) => (
            <div key={rule.name} className="flex items-center gap-3 px-3 py-2 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
              <span className="text-sm font-medium text-rose-400 w-40">{rule.name}</span>
              <span className="text-xs text-[var(--color-text-muted)]">{rule.condition}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Quality Tiers */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Quality Tiers</h3>
        <div className="space-y-2">
          {Object.entries(rules.quality_tiers).map(([tier, cfg]) => (
            <div key={tier} className="px-3 py-2 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
              <span className="text-sm font-medium text-[var(--color-text)] capitalize">{tier.replace('_', ' ')}</span>
              {cfg.required_fields && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {cfg.required_fields.map((f) => (
                    <span key={f} className="px-1.5 py-0.5 text-xs rounded bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)]">
                      {f}
                    </span>
                  ))}
                </div>
              )}
              {cfg.description && (
                <p className="text-xs text-[var(--color-text-dim)] mt-1">{cfg.description}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Scoring Weights */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Scoring Weights</h3>
        <div className="space-y-1.5">
          {Object.entries(rules.scoring_weights)
            .sort(([, a], [, b]) => b - a)
            .map(([field, weight]) => (
              <div key={field} className="flex items-center gap-3">
                <span className="text-xs text-[var(--color-text-muted)] w-36">{field}</span>
                <div className="w-32 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
                  <div className="h-full rounded-full bg-[var(--color-accent)]" style={{ width: `${(weight / 15) * 100}%` }} />
                </div>
                <span className="text-xs font-mono text-[var(--color-accent)]">+{weight}</span>
              </div>
            ))}
        </div>
      </div>

      {/* Run History */}
      {runHistory.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">Recent Runs</h3>
          <div className="space-y-2">
            {runHistory.map((run) => (
              <div key={run.run_id} className="flex items-center gap-4 px-3 py-2 rounded-md bg-[var(--color-background)] border border-[var(--color-border)]">
                <span className="text-xs font-mono text-[var(--color-text-dim)] w-32">{run.run_id}</span>
                <span className="text-xs text-[var(--color-text-muted)] capitalize">{run.lane.replace('_', ' ')}</span>
                <StatusBadge status={run.status} />
                {run.kept_count != null && (
                  <span className="text-xs text-green-400">{run.kept_count} kept</span>
                )}
                {run.discard_count != null && (
                  <span className="text-xs text-rose-400">{run.discard_count} discarded</span>
                )}
                <span className="ml-auto text-xs text-[var(--color-text-dim)]">
                  {new Date(run.created_at).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
