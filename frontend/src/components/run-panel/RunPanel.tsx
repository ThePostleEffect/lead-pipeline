import { useState } from 'react'
import { Play, CheckCircle2, XCircle, Upload, AlertTriangle, SlidersHorizontal } from 'lucide-react'
import { clsx } from 'clsx'
import { useRunStore } from '../../stores/runStore'
import { Spinner } from '../shared/Spinner'
import type { CollectParams, LeadLane } from '../../types'

const LANES: { value: LeadLane; label: string }[] = [
  { value: 'bankruptcy', label: 'Bankruptcy' },
  { value: 'charged_off', label: 'Charged Off' },
  { value: 'performing', label: 'Performing' },
  { value: 'capital_seeking', label: 'Capital Seeking' },
]

const SOURCE_TYPES = [
  { value: 'web', label: 'Live Sources' },
  { value: 'auto', label: 'Auto-detect' },
  { value: 'json', label: 'JSON File' },
  { value: 'csv', label: 'CSV File' },
]

export function RunPanel() {
  const { submitRun, isRunning, currentRun, sourceLogs, error, clearError } = useRunStore()

  const [lane, setLane] = useState<LeadLane>('bankruptcy')
  const [limit, setLimit] = useState<string>('25')
  const [minQuality, setMinQuality] = useState<string>('')
  const [sourceType, setSourceType] = useState<string>('web')
  const [saveDiscards, setSaveDiscards] = useState(true)
  const [exportXlsx, setExportXlsx] = useState(false)
  const [file, setFile] = useState<File | null>(null)

  // Search filters
  const [showFilters, setShowFilters] = useState(false)
  const [chapters, setChapters] = useState('13,7')
  const [lookbackDays, setLookbackDays] = useState('30')
  const [includeIndividuals, setIncludeIndividuals] = useState(true)
  const [companyTypes, setCompanyTypes] = useState<string[]>([])

  const handleRun = () => {
    const params: CollectParams = {
      lane,
      limit: limit ? parseInt(limit, 10) : undefined,
      min_quality: minQuality ? (minQuality as 'best_case' | 'mid_level') : undefined,
      source_type: sourceType as CollectParams['source_type'],
      save_discards: saveDiscards,
      export_xlsx: exportXlsx,
      chapters: chapters || undefined,
      lookback_days: lookbackDays ? parseInt(lookbackDays, 10) : undefined,
      include_individuals: includeIndividuals,
      company_types: companyTypes.length > 0 ? companyTypes.join(',') : undefined,
    }
    clearError()
    submitRun(params, file || undefined)
  }

  const needsFile = sourceType === 'json' || sourceType === 'csv'

  return (
    <div className="px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
      {/* Controls row */}
      <div className="flex flex-wrap items-end gap-4">
        {/* Lane */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--color-text-muted)]">Lane</label>
          <select
            value={lane}
            onChange={(e) => setLane(e.target.value as LeadLane)}
            disabled={isRunning}
            className="h-9 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
          >
            {LANES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>

        {/* Limit */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--color-text-muted)]">Leads</label>
          <input
            type="number"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            disabled={isRunning}
            min={1}
            max={100}
            className="h-9 w-20 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
          />
        </div>

        {/* Min Quality */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--color-text-muted)]">Min Quality</label>
          <select
            value={minQuality}
            onChange={(e) => setMinQuality(e.target.value)}
            disabled={isRunning}
            className="h-9 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
          >
            <option value="">Any</option>
            <option value="mid_level">Mid Level+</option>
            <option value="best_case">Best Case</option>
          </select>
        </div>

        {/* Source Type */}
        <div className="flex flex-col gap-1">
          <label className="text-xs text-[var(--color-text-muted)]">Source</label>
          <select
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            disabled={isRunning}
            className="h-9 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
          >
            {SOURCE_TYPES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* File upload */}
        {needsFile && (
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[var(--color-text-muted)]">File</label>
            <label className="flex items-center gap-1.5 h-9 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text-muted)] cursor-pointer hover:border-[var(--color-accent)] transition-colors">
              <Upload className="w-3.5 h-3.5" />
              <span className="truncate max-w-32">{file ? file.name : 'Choose file'}</span>
              <input
                type="file"
                accept={sourceType === 'csv' ? '.csv' : '.json,.jsonl'}
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="hidden"
              />
            </label>
          </div>
        )}

        {/* Checkboxes */}
        <div className="flex items-center gap-4 h-9">
          <label className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] cursor-pointer">
            <input
              type="checkbox"
              checked={saveDiscards}
              onChange={(e) => setSaveDiscards(e.target.checked)}
              disabled={isRunning}
              className="rounded"
            />
            Save discards
          </label>
          <label className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] cursor-pointer">
            <input
              type="checkbox"
              checked={exportXlsx}
              onChange={(e) => setExportXlsx(e.target.checked)}
              disabled={isRunning}
              className="rounded"
            />
            Export Excel
          </label>
        </div>

        {/* Filters toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={clsx(
            'flex items-center gap-1.5 h-9 px-3 rounded-md text-xs font-medium border transition-colors',
            showFilters
              ? 'bg-[var(--color-accent)]/10 border-[var(--color-accent)]/30 text-[var(--color-accent)]'
              : 'bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-accent)]',
          )}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          Filters
        </button>

        {/* Run button */}
        <button
          onClick={handleRun}
          disabled={isRunning || (needsFile && !file)}
          className={clsx(
            'flex items-center gap-2 h-9 px-5 rounded-md text-sm font-medium transition-colors',
            isRunning
              ? 'bg-[var(--color-border)] text-[var(--color-text-dim)] cursor-not-allowed'
              : 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] cursor-pointer',
          )}
        >
          {isRunning ? (
            <Spinner message="Running..." />
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Pipeline
            </>
          )}
        </button>
      </div>

      {/* Filter controls */}
      {showFilters && (
        <div className="flex flex-wrap items-end gap-4 mt-3 pt-3 border-t border-[var(--color-border)]">
          {/* Chapters */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[var(--color-text-muted)]">Chapters</label>
            <input
              type="text"
              value={chapters}
              onChange={(e) => setChapters(e.target.value)}
              disabled={isRunning}
              placeholder="13,7"
              className="h-9 w-24 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>

          {/* Lookback */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[var(--color-text-muted)]">Lookback (days)</label>
            <input
              type="number"
              value={lookbackDays}
              onChange={(e) => setLookbackDays(e.target.value)}
              disabled={isRunning}
              min={1}
              max={365}
              className="h-9 w-20 px-3 rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-sm text-[var(--color-text)] focus:outline-none focus:border-[var(--color-accent)]"
            />
          </div>

          {/* Include individuals */}
          <div className="flex items-center gap-4 h-9">
            <label className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] cursor-pointer">
              <input
                type="checkbox"
                checked={includeIndividuals}
                onChange={(e) => setIncludeIndividuals(e.target.checked)}
                disabled={isRunning}
                className="rounded"
              />
              Include Ch.13 individuals
            </label>
          </div>

          {/* Company type filter */}
          <div className="flex flex-col gap-1 w-full pt-1">
            <label className="text-xs text-[var(--color-text-muted)]">Company Type (leave blank for all)</label>
            <div className="flex flex-wrap gap-2">
              {[
                { value: 'credit_extenders', label: 'Credit Extenders' },
                { value: 'auto_dealers',     label: 'Auto Dealers' },
                { value: 'real_estate',      label: 'Real Estate' },
                { value: 'healthcare',       label: 'Healthcare' },
              ].map(({ value, label }) => {
                const active = companyTypes.includes(value)
                return (
                  <button
                    key={value}
                    type="button"
                    disabled={isRunning}
                    onClick={() =>
                      setCompanyTypes((prev) =>
                        active ? prev.filter((t) => t !== value) : [...prev, value],
                      )
                    }
                    className={clsx(
                      'px-3 py-1 text-xs rounded-full border transition-colors',
                      active
                        ? 'bg-[var(--color-accent)]/15 border-[var(--color-accent)]/40 text-[var(--color-accent)]'
                        : 'bg-[var(--color-background)] border-[var(--color-border)] text-[var(--color-text-muted)] hover:border-[var(--color-accent)]/40 hover:text-[var(--color-text)]',
                    )}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Status strip */}
      {currentRun && currentRun.status === 'completed' && (
        <div className="mt-3 px-3 py-2 rounded-md bg-green-500/10 border border-green-500/20">
          <div className="flex items-center gap-4">
            <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />
            <span className="text-sm text-green-400">
              {currentRun.kept_count} kept, {currentRun.discard_count} discarded
              {currentRun.raw_signal_count != null && (
                <span className="text-green-400/60"> (from {currentRun.raw_signal_count} raw signals)</span>
              )}
            </span>
          </div>

          {/* Source log details */}
          {sourceLogs.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-3 ml-8">
              {sourceLogs.map((log, i) => {
                const hasError = log.notes.toLowerCase().includes('error')
                const hasWarning = log.leads_found === 0 && !hasError
                return (
                  <div
                    key={i}
                    className={clsx(
                      'flex items-center gap-1.5 px-2 py-1 rounded text-xs border',
                      hasError
                        ? 'bg-red-500/10 border-red-500/20 text-red-400'
                        : hasWarning
                          ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
                          : 'bg-zinc-500/10 border-zinc-500/20 text-zinc-400',
                    )}
                  >
                    {hasError && <XCircle className="w-3 h-3" />}
                    {hasWarning && <AlertTriangle className="w-3 h-3" />}
                    <span className="font-medium">{log.source_name}</span>
                    <span className="opacity-60">
                      {log.leads_found} found
                    </span>
                    {hasError && (
                      <span className="opacity-80 max-w-48 truncate" title={log.notes}>
                        {log.notes}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-4 mt-3 px-3 py-2 rounded-md bg-red-500/10 border border-red-500/20">
          <XCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}
    </div>
  )
}
