import React, { useEffect, useState } from 'react'

interface TimeEstimate {
  estimated_minutes: number
  actual_minutes: number
  buffer_minutes: number
  remaining_minutes: number
  completion_percentage: number
  is_over_estimate: boolean
}

interface ChecklistItem {
  id: string
  description: string
  is_completed: boolean
  completed_by: string | null
}

interface Checkpoint {
  id: string
  checklist: ChecklistItem[]
  status: string
  all_checked: boolean
}

interface Phase {
  id: string
  name: string
  objective: string
  sequence: number
  status: string
  progress: number
  time_estimate: TimeEstimate
  elapsed_minutes: number
  deadline: string | null
  is_overdue: boolean
  checkpoint: Checkpoint | null
  assignee: string | null
}

interface Goal {
  id: string
  title: string
  objective: string
  status: string
  priority: string
  progress: number
  health: string
  time_estimate: TimeEstimate
  elapsed_minutes: number
  deadline: string | null
  is_overdue: boolean
  phases: Phase[]
  current_phase: Phase | null
  owner: string
  total_estimated_minutes: number
  total_actual_minutes: number
}

interface GoalSummary {
  id: string
  title: string
  status: string
  priority: string
  progress: number
  health: string
  is_overdue: boolean
  elapsed_minutes: number
  total_estimated_minutes: number
  phases_completed: number
  phases_total: number
}

interface GoalDashboardProps {
  apiUrl: string
}

export default function GoalDashboard({ apiUrl }: GoalDashboardProps) {
  const [goals, setGoals] = useState<GoalSummary[]>([])
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchGoals = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/goals`)
      if (response.ok) {
        const data = await response.json()
        setGoals(data)
      }
    } catch (err) {
      setError('Failed to fetch goals')
    } finally {
      setLoading(false)
    }
  }

  const fetchGoalDetail = async (goalId: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/goals/${goalId}`)
      if (response.ok) {
        const data = await response.json()
        setSelectedGoal(data)
      }
    } catch (err) {
      setError('Failed to fetch goal details')
    }
  }

  useEffect(() => {
    fetchGoals()
    // Refresh every 30 seconds
    const interval = setInterval(fetchGoals, 30000)
    return () => clearInterval(interval)
  }, [])

  const startGoal = async (goalId: string) => {
    setActionLoading(goalId)
    try {
      const response = await fetch(`${apiUrl}/api/v1/goals/${goalId}/start`, {
        method: 'POST',
      })
      if (response.ok) {
        await fetchGoals()
        if (selectedGoal?.id === goalId) {
          await fetchGoalDetail(goalId)
        }
      }
    } catch (err) {
      setError('Failed to start goal')
    } finally {
      setActionLoading(null)
    }
  }

  const completePhase = async (phaseId: string) => {
    setActionLoading(phaseId)
    try {
      const response = await fetch(`${apiUrl}/api/v1/goals/phases/${phaseId}/complete`, {
        method: 'POST',
      })
      if (response.ok) {
        await fetchGoals()
        if (selectedGoal) {
          await fetchGoalDetail(selectedGoal.id)
        }
      }
    } catch (err) {
      setError('Failed to complete phase')
    } finally {
      setActionLoading(null)
    }
  }

  const checkItem = async (phaseId: string, itemId: string) => {
    try {
      await fetch(`${apiUrl}/api/v1/goals/phases/${phaseId}/checklist/${itemId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed_by: 'CEO' }),
      })
      if (selectedGoal) {
        await fetchGoalDetail(selectedGoal.id)
      }
    } catch (err) {
      setError('Failed to check item')
    }
  }

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'on_track': return 'text-green-400'
      case 'at_risk': return 'text-yellow-400'
      case 'overdue': return 'text-red-400'
      case 'completed': return 'text-cyan-400'
      default: return 'text-gray-400'
    }
  }

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'on_track': return '🟢'
      case 'at_risk': return '🟡'
      case 'overdue': return '🔴'
      case 'completed': return '✅'
      default: return '⚪'
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-600',
      pending: 'bg-slate-600',
      active: 'bg-green-600',
      completed: 'bg-cyan-600',
      cancelled: 'bg-red-600',
      on_hold: 'bg-yellow-600',
    }
    return colors[status] || 'bg-gray-600'
  }

  const getPhaseStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✅'
      case 'in_progress': return '🔄'
      case 'pending': return '⏳'
      case 'blocked': return '🚫'
      case 'review': return '👁️'
      default: return '⚪'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'text-red-400'
      case 'high': return 'text-orange-400'
      case 'medium': return 'text-yellow-400'
      case 'low': return 'text-gray-400'
      default: return 'text-gray-400'
    }
  }

  const formatMinutes = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  }

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="text-center text-gray-400 py-8">
          載入中...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-cyan-300 flex items-center gap-2">
            🎯 Goal Dashboard
          </h2>
          <button
            onClick={fetchGoals}
            className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors"
          >
            🔄 重新整理
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded-lg text-red-300 text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-400 hover:text-red-300">✕</button>
          </div>
        )}

        {/* Goal List */}
        {goals.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-4xl mb-2">📋</div>
            <div>目前沒有目標</div>
            <div className="text-sm mt-1">透過 API 建立新目標</div>
          </div>
        ) : (
          <div className="space-y-3">
            {goals.map((goal) => (
              <div
                key={goal.id}
                onClick={() => fetchGoalDetail(goal.id)}
                className={`p-4 rounded-lg cursor-pointer transition-all ${
                  selectedGoal?.id === goal.id
                    ? 'bg-cyan-900/30 border border-cyan-500'
                    : 'bg-slate-700 hover:bg-slate-600 border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span>{getHealthIcon(goal.health)}</span>
                    <span className="font-medium">{goal.title}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${getStatusBadge(goal.status)}`}>
                      {goal.status}
                    </span>
                    <span className={`text-sm ${getPriorityColor(goal.priority)}`}>
                      [{goal.priority}]
                    </span>
                  </div>
                  <div className="text-sm text-gray-400">
                    {goal.phases_completed}/{goal.phases_total} phases
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        goal.is_overdue ? 'bg-red-500' :
                        goal.health === 'at_risk' ? 'bg-yellow-500' :
                        'bg-cyan-500'
                      }`}
                      style={{ width: `${goal.progress}%` }}
                    />
                  </div>
                  <span className="text-sm text-gray-400 w-16 text-right">
                    {goal.progress.toFixed(0)}%
                  </span>
                </div>

                {/* Time Info */}
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                  <span>⏱️ {formatMinutes(goal.elapsed_minutes)} / {formatMinutes(goal.total_estimated_minutes)}</span>
                  {goal.is_overdue && <span className="text-red-400">⚠️ 超時</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Goal Detail */}
      {selectedGoal && (
        <div className="bg-slate-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-cyan-300">
              {selectedGoal.title}
            </h3>
            <button
              onClick={() => setSelectedGoal(null)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          {/* Goal Info */}
          <div className="mb-6 p-4 bg-slate-700/50 rounded-lg">
            <div className="text-sm text-gray-300 mb-2">{selectedGoal.objective}</div>
            <div className="flex items-center gap-4 text-sm">
              <span className={getHealthColor(selectedGoal.health)}>
                {getHealthIcon(selectedGoal.health)} {selectedGoal.health}
              </span>
              <span className="text-gray-400">Owner: {selectedGoal.owner}</span>
              <span className="text-gray-400">
                時間: {formatMinutes(selectedGoal.elapsed_minutes)} / {formatMinutes(selectedGoal.total_estimated_minutes)}
              </span>
            </div>

            {/* Start Button */}
            {selectedGoal.status === 'draft' && (
              <button
                onClick={() => startGoal(selectedGoal.id)}
                disabled={actionLoading === selectedGoal.id}
                className="mt-3 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-slate-600 rounded-lg text-sm transition-colors"
              >
                {actionLoading === selectedGoal.id ? '啟動中...' : '🚀 開始執行'}
              </button>
            )}
          </div>

          {/* Phases */}
          <div>
            <h4 className="text-sm font-medium text-gray-400 mb-3">📍 執行階段</h4>
            <div className="space-y-3">
              {selectedGoal.phases
                .sort((a, b) => a.sequence - b.sequence)
                .map((phase) => (
                  <div
                    key={phase.id}
                    className={`p-4 rounded-lg border ${
                      phase.status === 'in_progress'
                        ? 'bg-cyan-900/20 border-cyan-500'
                        : phase.status === 'completed'
                        ? 'bg-green-900/20 border-green-500/50'
                        : 'bg-slate-700/50 border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span>{getPhaseStatusIcon(phase.status)}</span>
                        <span className="font-medium">{phase.name}</span>
                        {phase.assignee && (
                          <span className="text-xs text-gray-500">@{phase.assignee}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-400">
                          {formatMinutes(phase.time_estimate.estimated_minutes)}
                        </span>
                        {phase.is_overdue && (
                          <span className="text-xs text-red-400">超時</span>
                        )}
                      </div>
                    </div>

                    <div className="text-sm text-gray-400 mb-2">{phase.objective}</div>

                    {/* Phase Progress */}
                    <div className="flex items-center gap-3 mb-2">
                      <div className="flex-1 h-1.5 bg-slate-600 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${
                            phase.status === 'completed' ? 'bg-green-500' :
                            phase.is_overdue ? 'bg-red-500' :
                            'bg-cyan-500'
                          }`}
                          style={{ width: `${phase.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{phase.progress.toFixed(0)}%</span>
                    </div>

                    {/* Checkpoint Checklist */}
                    {phase.checkpoint && phase.status === 'in_progress' && (
                      <div className="mt-3 pt-3 border-t border-slate-600">
                        <div className="text-xs text-gray-500 mb-2">
                          ✓ 驗收項目 ({phase.checkpoint.checklist.filter(i => i.is_completed).length}/{phase.checkpoint.checklist.length})
                        </div>
                        <div className="space-y-1">
                          {phase.checkpoint.checklist.map((item) => (
                            <div
                              key={item.id}
                              onClick={() => !item.is_completed && checkItem(phase.id, item.id)}
                              className={`flex items-center gap-2 text-sm p-2 rounded cursor-pointer transition-colors ${
                                item.is_completed
                                  ? 'text-green-400 bg-green-900/20'
                                  : 'text-gray-400 hover:bg-slate-600'
                              }`}
                            >
                              <span>{item.is_completed ? '☑️' : '☐'}</span>
                              <span>{item.description}</span>
                            </div>
                          ))}
                        </div>

                        {/* Complete Phase Button */}
                        {phase.checkpoint.all_checked && (
                          <button
                            onClick={() => completePhase(phase.id)}
                            disabled={actionLoading === phase.id}
                            className="mt-3 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-slate-600 rounded-lg text-sm transition-colors w-full"
                          >
                            {actionLoading === phase.id ? '完成中...' : '✅ 完成此階段'}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
