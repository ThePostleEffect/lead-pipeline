import { Loader2 } from 'lucide-react'

export function Spinner({ message }: { message?: string }) {
  return (
    <div className="flex items-center gap-3 text-[var(--color-text-muted)]">
      <Loader2 className="w-5 h-5 animate-spin" />
      {message && <span className="text-sm">{message}</span>}
    </div>
  )
}
