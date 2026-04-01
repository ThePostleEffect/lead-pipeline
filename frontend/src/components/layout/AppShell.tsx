import { useEffect, useRef, useState } from 'react'
import { useRunStore } from '../../stores/runStore'
import { TopBar } from './TopBar'
import { TabBar } from './TabBar'
import { RunPanel } from '../run-panel/RunPanel'
import { ResultsTable } from '../results/ResultsTable'
import { LeadDrawer } from '../detail/LeadDrawer'
import { DiscardsTable } from '../discards/DiscardsTable'
import { RulesView } from '../rules/RulesView'
import { SchedulesView } from '../schedules/SchedulesView'
import { FishermanLoader } from '../shared/FishermanLoader'
import { downloadXlsx, downloadJson } from '../../api/client'
import { FileSpreadsheet, FileJson } from 'lucide-react'

export function AppShell() {
  const { activeTab, setActiveTab, leads, discards, currentRun, selectedLeadId, isRunning } = useRunStore()

  // Track reeling phase: fires briefly when run completes before loader unmounts
  const [reeling, setReeling] = useState(false)
  const [showLoader, setShowLoader] = useState(false)
  const wasRunning = useRef(false)

  useEffect(() => {
    if (isRunning) {
      setShowLoader(true)
      setReeling(false)
      wasRunning.current = true
    } else if (wasRunning.current) {
      // Run just finished — play reel animation then hide loader
      setReeling(true)
      wasRunning.current = false
      const t = setTimeout(() => setShowLoader(false), 1900)
      return () => clearTimeout(t)
    }
  }, [isRunning])

  const hasRun = currentRun?.status === 'completed'

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopBar />
      <RunPanel />

      {/* Export bar */}
      {hasRun && currentRun && leads.length > 0 && (
        <div className="flex items-center gap-2 px-6 py-2 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
          <button
            onClick={() => downloadXlsx(currentRun.run_id)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-accent)] transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Export Excel
          </button>
          <button
            onClick={() => downloadJson(currentRun.run_id)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-[var(--color-background)] border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-accent)] transition-colors"
          >
            <FileJson className="w-3.5 h-3.5" />
            Export JSON
          </button>
        </div>
      )}

      <TabBar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        leadCount={leads.length}
        discardCount={discards.length}
      />

      {/* Content area */}
      <main className="flex-1 overflow-hidden relative">
        {showLoader ? (
          <FishermanLoader reeling={reeling} />
        ) : (
          <>
            {activeTab === 'results' && <ResultsTable />}
            {activeTab === 'discards' && <DiscardsTable />}
            {activeTab === 'rules' && <RulesView />}
            {activeTab === 'schedules' && <SchedulesView />}
            {activeTab === 'activity' && <RulesView />}
          </>
        )}
      </main>

      {/* Detail drawer */}
      {selectedLeadId && <LeadDrawer />}
    </div>
  )
}
