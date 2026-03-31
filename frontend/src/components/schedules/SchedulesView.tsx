import { useEffect, useState } from 'react'
import { clsx } from 'clsx'
import { Plus, Trash2, Clock, Play, Pause } from 'lucide-react'
import { listSchedules, createSchedule, updateSchedule, deleteSchedule } from '../../api/client'
import type { Schedule, LeadLane } from '../../types'
import { Spinner } from '../shared/Spinner'

const LANES: { value: LeadLane; label: string }[] = [
  { value: 'bankruptcy', label: 'Bankruptcy' },
  { value: 'charged_off', label: 'Charged Off' },
  { value: 'performing', label: 'Performing' },
  { value: 'capital_seeking', label: 'Capital Seeking' },
]

const INTERVALS = [
  { hours: 1, label: 'Every hour' },
  { hours: 6, label: 'Every 6 hours' },
  { hours: 12, label: 'Every 12 hours' },
  { hours: 24, label: 'Daily' },
  { hours: 168, label: 'Weekly' },
]

function formatInterval(hours: number): string {
  const match = INTERVALS.find((i) => i.hours === hours)
  if (match) return match.label
  if (hours < 24) return `Every ${hours}h`
  const days = Math.round(hours / 24)
  return days === 1 ? 'Daily' : `Every ${days} days`
}

function formatDate(iso: string | null): string {
  if (!iso) return 'Never'
  const d = new Date(iso)
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function timeUntil(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now()
  if (diff < 0) return 'Due now'
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `in ${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `in ${hours}h`
  const days = Math.floor(hours / 24)
  return `in ${days}d`
}

export function SchedulesView() {
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)

  // Create form state
  const [name, setName] = useState('')
  const [lane, setLane] = useState<LeadLane>('bankruptcy')
  const [intervalHours, setIntervalHours] = useState(24)
  const [limit, setLimit] = useState('25')
  const [creating, setCreating] = useState(false)

  const refresh = () => {
    listSchedules()
      .then(setSchedules)
      .catch(() => setSchedules([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    refresh()
  }, [])

  const handleCreate = async () => {
    if (!name.trim()) return
    setCreating(true)
    try {
      await createSchedule({
        name: name.trim(),
        lane,
        interval_hours: intervalHours,
        params: {
          source_type: 'web',
          save_discards: true,
          limit: limit ? parseInt(limit, 10) : undefined,
        },
      })
      setName('')
      setShowCreate(false)
      refresh()
    } catch {
      // Error handled silently
    } finally {
      setCreating(false)
    }
  }

  const handleToggle = async (sched: Schedule) => {
    await updateSchedule(sched.schedule_id, { enabled: !sched.enabled })
    refresh()
  }

  const handleDelete = async (scheduleId: string) => {
    await deleteSchedule(scheduleId)
    refresh()
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner message="Loading schedules..." />
      </div>
    )
  }

  return (
    <div className="overflow-auto h-full p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-text)]">Scheduled Runs</h3>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            Automatically run the pipeline on a recurring basis
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-md transition-colors',
            showCreate
              ? 'bg-[var(--color-accent)]/10 border border-[var(--color-accent)]/30 text-[var(--color-accent)]'
              : 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]',
          )}
        >
          <Plus className="w-3.5 h-3.5" />
          New Schedule
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="p-4 rounded-lg bg-[var(--color-background)] border border-[var(--color-border)] space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            {/* Name */}
            <div className="flex flex-col gap-1 flex-1 min-w-48">
              <label className="text-xs text-[var(--color-text-muted)]">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Daily bankruptcy scan"
                className="h-9 px-3 rounded-md bg-[var(--color-surface)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
              />
            </div>

            {/* Lane */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[var(--color-text-muted)]">Lane</label>
              <select
                value={lane}
                onChange={(e) => setLane(e.target.value as LeadLane)}
                className="h-9 px-3 rounded-md bg-[var(--color-surface)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
              >
                {LANES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>

            {/* Interval */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[var(--color-text-muted)]">Frequency</label>
              <select
                value={intervalHours}
                onChange={(e) => setIntervalHours(Number(e.target.value))}
                className="h-9 px-3 rounded-md bg-[var(--color-surface)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
              >
                {INTERVALS.map((i) => (
                  <option key={i.hours} value={i.hours}>{i.label}</option>
                ))}
              </select>
            </div>

            {/* Limit */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[var(--color-text-muted)]">Limit</label>
              <input
                type="number"
                value={limit}
                onChange={(e) => setLimit(e.target.value)}
                min={1}
                max={100}
                className="h-9 w-20 px-3 rounded-md bg-[var(--color-surface)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
              />
            </div>

            {/* Submit */}
            <button
              onClick={handleCreate}
              disabled={creating || !name.trim()}
              className={clsx(
                'h-9 px-4 text-sm font-medium rounded-md transition-colors',
                creating || !name.trim()
                  ? 'bg-[var(--color-border)] text-[var(--color-text-dim)] cursor-not-allowed'
                  : 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] cursor-pointer',
              )}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>
      )}

      {/* Schedule list */}
      {schedules.length === 0 ? (
        <div className="text-center py-12 text-[var(--color-text-dim)]">
          <Clock className="w-8 h-8 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No schedules configured</p>
          <p className="text-xs mt-1">Create one to automatically run the pipeline on a recurring basis</p>
        </div>
      ) : (
        <div className="space-y-2">
          {schedules.map((sched) => (
            <div
              key={sched.schedule_id}
              className={clsx(
                'flex items-center gap-4 px-4 py-3 rounded-lg border transition-colors',
                sched.enabled
                  ? 'bg-[var(--color-background)] border-[var(--color-border)]'
                  : 'bg-[var(--color-background)] border-[var(--color-border)] opacity-50',
              )}
            >
              {/* Toggle */}
              <button
                onClick={() => handleToggle(sched)}
                className={clsx(
                  'flex items-center justify-center w-8 h-8 rounded-md transition-colors',
                  sched.enabled
                    ? 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                    : 'bg-zinc-500/10 text-zinc-500 hover:bg-zinc-500/20',
                )}
                title={sched.enabled ? 'Pause schedule' : 'Resume schedule'}
              >
                {sched.enabled ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
              </button>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-[var(--color-text)] truncate">
                    {sched.name}
                  </span>
                  <span className="px-1.5 py-0.5 text-xs rounded bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text-muted)] capitalize">
                    {sched.lane.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-0.5 text-xs text-[var(--color-text-dim)]">
                  <span>{formatInterval(sched.interval_hours)}</span>
                  <span>Last: {formatDate(sched.last_run_at)}</span>
                  {sched.enabled && (
                    <span className="text-[var(--color-accent)]">
                      Next: {timeUntil(sched.next_run_at)}
                    </span>
                  )}
                </div>
              </div>

              {/* ID */}
              <span className="text-xs font-mono text-[var(--color-text-dim)] hidden md:block">
                {sched.schedule_id}
              </span>

              {/* Delete */}
              <button
                onClick={() => handleDelete(sched.schedule_id)}
                className="flex items-center justify-center w-8 h-8 rounded-md text-[var(--color-text-dim)] hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="Delete schedule"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
