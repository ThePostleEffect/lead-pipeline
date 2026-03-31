import { clsx } from 'clsx'
import { BarChart3, FileX2, Scale, Clock, ListChecks } from 'lucide-react'
import type { ActiveTab } from '../../stores/runStore'

const tabs: { id: ActiveTab; label: string; icon: typeof BarChart3 }[] = [
  { id: 'results', label: 'Results', icon: BarChart3 },
  { id: 'discards', label: 'Discards', icon: FileX2 },
  { id: 'rules', label: 'Rules', icon: Scale },
  { id: 'schedules', label: 'Schedules', icon: Clock },
  { id: 'activity', label: 'Activity', icon: ListChecks },
]

interface TabBarProps {
  activeTab: ActiveTab
  onTabChange: (tab: ActiveTab) => void
  discardCount?: number
  leadCount?: number
}

export function TabBar({ activeTab, onTabChange, discardCount, leadCount }: TabBarProps) {
  return (
    <div className="flex items-center gap-1 px-6 py-1 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onTabChange(id)}
          className={clsx(
            'flex items-center gap-1.5 px-3 py-2 text-sm rounded-md transition-colors',
            activeTab === id
              ? 'text-[var(--color-text)] bg-[var(--color-surface-hover)]'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]',
          )}
        >
          <Icon className="w-4 h-4" />
          {label}
          {id === 'results' && leadCount != null && leadCount > 0 && (
            <span className="ml-1 px-1.5 py-0 text-xs rounded-full bg-[var(--color-accent)]/20 text-[var(--color-accent)]">
              {leadCount}
            </span>
          )}
          {id === 'discards' && discardCount != null && discardCount > 0 && (
            <span className="ml-1 px-1.5 py-0 text-xs rounded-full bg-rose-500/20 text-rose-400">
              {discardCount}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
