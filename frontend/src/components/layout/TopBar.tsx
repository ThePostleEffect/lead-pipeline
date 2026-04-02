import { Archive, Database } from 'lucide-react'
import { clsx } from 'clsx'
import { SourceHealthBar } from '../shared/SourceHealthBar'

interface TopBarProps {
  vaultOpen: boolean
  onVaultToggle: () => void
}

export function TopBar({ vaultOpen, onVaultToggle }: TopBarProps) {
  return (
    <header className="flex items-center gap-3 px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
      <Database className="w-5 h-5 text-[var(--color-accent)]" />
      <h1 className="text-base font-semibold tracking-tight">Lead Pipeline</h1>
      <span className="text-xs text-[var(--color-text-dim)] ml-1">v0.1</span>

      <button
        onClick={onVaultToggle}
        title="Discard Vault"
        className={clsx(
          'ml-4 flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border transition-colors',
          vaultOpen
            ? 'bg-[var(--color-accent)]/15 border-[var(--color-accent)]/40 text-[var(--color-accent)]'
            : 'bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-accent)]',
        )}
      >
        <Archive className="w-3.5 h-3.5" />
        Discard Vault
      </button>

      <div className="ml-auto">
        <SourceHealthBar />
      </div>
    </header>
  )
}
