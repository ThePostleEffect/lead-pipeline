import { useEffect, useState } from 'react'
import { clsx } from 'clsx'
import { getSourceHealth } from '../../api/client'
import type { SourceHealthResponse, SourceInfo } from '../../types'

const statusColor: Record<string, string> = {
  ready: 'bg-green-400',
  fallback: 'bg-yellow-400',
  disabled: 'bg-zinc-500',
  missing_key: 'bg-red-400',
}

const statusLabel: Record<string, string> = {
  ready: 'Ready',
  fallback: 'Fallback',
  disabled: 'Not configured',
  missing_key: 'Missing API key',
}

function SourceDot({ source }: { source: SourceInfo }) {
  return (
    <div className="group relative flex items-center">
      <div className={clsx('w-2 h-2 rounded-full', statusColor[source.status] || 'bg-zinc-500')} />

      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-50">
        <div className="px-3 py-2 rounded-md bg-zinc-800 border border-zinc-700 shadow-lg whitespace-nowrap">
          <div className="text-xs font-medium text-zinc-100">{source.name}</div>
          <div className="text-[11px] text-zinc-400 mt-0.5">{statusLabel[source.status]}</div>
          {source.fallback_note && (
            <div className="text-[11px] text-yellow-400 mt-0.5">{source.fallback_note}</div>
          )}
          {source.env_vars.length > 0 && source.status !== 'ready' && (
            <div className="text-[11px] text-zinc-500 mt-0.5">
              Set: {source.env_vars.join(', ')}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function SourceHealthBar() {
  const [health, setHealth] = useState<SourceHealthResponse | null>(null)

  useEffect(() => {
    getSourceHealth().then(setHealth).catch(() => {})
  }, [])

  if (!health) return null

  const { sources, summary } = health
  const dataSources = sources.filter((s) => s.type === 'source')
  const enrichers = sources.filter((s) => s.type === 'enrichment')

  return (
    <div className="flex items-center gap-3 text-xs text-[var(--color-text-dim)]">
      {/* Sources group */}
      <div className="flex items-center gap-1.5">
        <span className="text-[var(--color-text-muted)]">Sources</span>
        {dataSources.map((s) => (
          <SourceDot key={s.name} source={s} />
        ))}
      </div>

      <span className="text-[var(--color-border)]">|</span>

      {/* Enrichment group */}
      <div className="flex items-center gap-1.5">
        <span className="text-[var(--color-text-muted)]">Enrichment</span>
        {enrichers.map((s) => (
          <SourceDot key={s.name} source={s} />
        ))}
      </div>

      {/* Summary */}
      <span className={clsx(
        'text-[11px]',
        summary.all_configured ? 'text-green-400/60' : 'text-yellow-400/60',
      )}>
        {summary.ready}/{summary.total}
      </span>
    </div>
  )
}
