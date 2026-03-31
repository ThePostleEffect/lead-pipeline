import { create } from 'zustand'
import type { CollectParams, DiscardRecord, Lead, RunListItem, RunResponse, SourceLog } from '../types'
import { getRunDiscards, getRunLeads, getRunSourceLogs, listRuns, pollRunStatus, startRun } from '../api/client'

export type ActiveTab = 'results' | 'discards' | 'rules' | 'schedules' | 'activity'

interface RunStore {
  // Current run
  currentRun: RunResponse | null
  leads: Lead[]
  discards: DiscardRecord[]
  sourceLogs: SourceLog[]

  // UI state
  selectedLeadId: string | null
  activeTab: ActiveTab
  isRunning: boolean
  error: string | null

  // Run history
  runHistory: RunListItem[]

  // Actions
  submitRun: (params: CollectParams, file?: File) => Promise<void>
  selectLead: (leadId: string | null) => void
  setActiveTab: (tab: ActiveTab) => void
  loadHistory: () => Promise<void>
  clearError: () => void
}

export const useRunStore = create<RunStore>((set, get) => ({
  currentRun: null,
  leads: [],
  discards: [],
  sourceLogs: [],
  selectedLeadId: null,
  activeTab: 'results',
  isRunning: false,
  error: null,
  runHistory: [],

  submitRun: async (params, file) => {
    set({ isRunning: true, error: null, leads: [], discards: [], sourceLogs: [], selectedLeadId: null })

    try {
      const run = await startRun(params, file)
      set({ currentRun: run })

      // Poll until complete
      pollRunStatus(run.run_id, async (updated) => {
        set({ currentRun: updated })

        if (updated.status === 'completed') {
          try {
            const [leads, discards, sourceLogs] = await Promise.all([
              getRunLeads(updated.run_id),
              getRunDiscards(updated.run_id),
              getRunSourceLogs(updated.run_id),
            ])
            set({ leads, discards, sourceLogs, isRunning: false, activeTab: 'results' })
            // Refresh history
            get().loadHistory()
          } catch (err) {
            set({ isRunning: false, error: String(err) })
          }
        } else if (updated.status === 'failed') {
          set({ isRunning: false, error: updated.error || 'Run failed' })
        }
      })
    } catch (err) {
      set({ isRunning: false, error: err instanceof Error ? err.message : String(err) })
    }
  },

  selectLead: (leadId) => set({ selectedLeadId: leadId }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  loadHistory: async () => {
    try {
      const history = await listRuns()
      set({ runHistory: history })
    } catch {
      // Silently ignore history load failures
    }
  },

  clearError: () => set({ error: null }),
}))
