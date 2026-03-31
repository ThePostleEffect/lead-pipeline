import { clsx } from 'clsx'
import type { LeadLane, QualityTier } from '../../types'

// ---- Lane Badge ----

const laneColors: Record<LeadLane, string> = {
  bankruptcy: 'bg-red-500/15 text-red-400 border-red-500/30',
  charged_off: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  performing: 'bg-green-500/15 text-green-400 border-green-500/30',
  capital_seeking: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
}

const laneLabels: Record<LeadLane, string> = {
  bankruptcy: 'Bankruptcy',
  charged_off: 'Charged Off',
  performing: 'Performing',
  capital_seeking: 'Capital Seeking',
}

export function LaneBadge({ lane }: { lane: LeadLane | string }) {
  const key = lane as LeadLane
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
        laneColors[key] || 'bg-gray-500/15 text-gray-400 border-gray-500/30',
      )}
    >
      {laneLabels[key] || lane}
    </span>
  )
}

// ---- Quality Badge ----

const qualityColors: Record<QualityTier, string> = {
  best_case: 'bg-green-500/15 text-green-400 border-green-500/30',
  mid_level: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  weak: 'bg-red-500/15 text-red-400 border-red-500/30',
}

const qualityLabels: Record<QualityTier, string> = {
  best_case: 'Best Case',
  mid_level: 'Mid Level',
  weak: 'Weak',
}

export function QualityBadge({ tier }: { tier: QualityTier | string }) {
  const key = tier as QualityTier
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
        qualityColors[key] || 'bg-gray-500/15 text-gray-400 border-gray-500/30',
      )}
    >
      {qualityLabels[key] || tier}
    </span>
  )
}

// ---- Confidence Score ----

export function ConfidenceScore({ score }: { score: number }) {
  const color =
    score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'
  const barColor =
    score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-[var(--color-border)] overflow-hidden">
        <div className={clsx('h-full rounded-full', barColor)} style={{ width: `${score}%` }} />
      </div>
      <span className={clsx('text-xs font-mono font-medium', color)}>{score}</span>
    </div>
  )
}

// ---- Status Badge ----

const statusColors: Record<string, string> = {
  pending: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
  running: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  completed: 'bg-green-500/15 text-green-400 border-green-500/30',
  failed: 'bg-red-500/15 text-red-400 border-red-500/30',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
        statusColors[status] || statusColors.pending,
      )}
    >
      {status}
    </span>
  )
}

// ---- Rule Badge ----

export function RuleBadge({ rule }: { rule: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-rose-500/15 text-rose-400 border-rose-500/30">
      {rule}
    </span>
  )
}
