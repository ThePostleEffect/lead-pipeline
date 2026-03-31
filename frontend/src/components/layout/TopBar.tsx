import { Database } from 'lucide-react'
import { SourceHealthBar } from '../shared/SourceHealthBar'

export function TopBar() {
  return (
    <header className="flex items-center gap-3 px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
      <Database className="w-5 h-5 text-[var(--color-accent)]" />
      <h1 className="text-base font-semibold tracking-tight">Lead Pipeline</h1>
      <span className="text-xs text-[var(--color-text-dim)] ml-1">v0.1</span>
      <div className="ml-auto">
        <SourceHealthBar />
      </div>
    </header>
  )
}
