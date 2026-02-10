import React, { useCallback, useEffect, useState } from 'react'
import { useAgentWebSocket } from '../hooks/useAgentWebSocket'

interface ActivityEntry {
  id: string
  agent_id: string
  agent_name: string
  activity_type: string
  message: string
  timestamp: string
  project_id: string | null
  project_name: string | null
  duration_seconds: number | null
  metadata: Record<string, any>
}

interface AgentActivityLogProps {
  apiUrl: string
  agentId?: string  // Optional: filter by agent
  limit?: number
}

const ACTIVITY_ICONS: Record<string, string> = {
  task_start: '▶️',
  task_end: '✅',
  status_change: '🔄',
  blocked: '🚫',
  unblocked: '✅',
  message: '💬',
  error: '❌',
  milestone: '🎯',
}

const ACTIVITY_COLORS: Record<string, string> = {
  task_start: 'border-green-500 bg-green-900/20',
  task_end: 'border-blue-500 bg-blue-900/20',
  status_change: 'border-yellow-500 bg-yellow-900/20',
  blocked: 'border-red-500 bg-red-900/20',
  unblocked: 'border-green-500 bg-green-900/20',
  message: 'border-gray-500 bg-gray-900/20',
  error: 'border-red-500 bg-red-900/20',
  milestone: 'border-purple-500 bg-purple-900/20',
}

export default function AgentActivityLog({ apiUrl, agentId, limit = 30 }: AgentActivityLogProps) {
  const [activities, setActivities] = useState<ActivityEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchActivities = useCallback(async () => {
    try {
      let url = `${apiUrl}/api/v1/activity/?limit=${limit}`
      if (agentId) {
        url += `&agent_id=${agentId}`
      }

      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setActivities(data)
        setError(null)
      } else {
        setError('Failed to fetch activities')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setLoading(false)
    }
  }, [apiUrl, limit, agentId])

  // Initial fetch
  useEffect(() => { fetchActivities() }, [fetchActivities])

  // WebSocket: real-time activity updates
  const handleWsMessage = useCallback((data: any) => {
    if (data.type === 'activity') {
      // If filtering by agentId, only accept matching activities
      if (agentId && data.agent_id !== agentId) return

      const newEntry: ActivityEntry = {
        id: `ws-${Date.now()}`,
        agent_id: data.agent_id,
        agent_name: data.agent_name,
        activity_type: data.activity_type,
        message: data.message,
        timestamp: data.timestamp,
        project_id: data.project_id ?? null,
        project_name: data.project_name ?? null,
        duration_seconds: data.duration_seconds ?? null,
        metadata: {},
      }
      setActivities(prev => [newEntry, ...prev].slice(0, limit))
    }
  }, [agentId, limit])

  const { connected } = useAgentWebSocket({
    apiUrl,
    onMessage: handleWsMessage,
    enabled: autoRefresh,
    onReconnect: fetchActivities,
  })

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return null
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-4">
        <div className="text-center text-gray-400 py-4">載入活動日誌...</div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-cyan-300 flex items-center gap-2">
          📜 Agent Activity Log
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} title={connected ? 'Live' : 'Reconnecting...'} />
        </h3>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-sm text-gray-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            Auto-refresh
          </label>
          <button
            onClick={fetchActivities}
            className="px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm"
          >
            🔄
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-2 bg-red-900/30 border border-red-500 rounded text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Activity List */}
      {activities.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <div className="text-3xl mb-2">📝</div>
          <div>尚無活動記錄</div>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className={`border-l-2 pl-3 py-2 ${ACTIVITY_COLORS[activity.activity_type] || 'border-gray-500'}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 text-sm">
                    <span>{ACTIVITY_ICONS[activity.activity_type] || '•'}</span>
                    <span className="font-medium text-white">{activity.agent_name}</span>
                    {activity.project_name && (
                      <span className="px-1.5 py-0.5 bg-slate-600 rounded text-xs text-gray-300">
                        {activity.project_name}
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-300 mt-1">{activity.message}</div>
                </div>
                <div className="text-right text-xs text-gray-500 ml-2">
                  <div>{formatTime(activity.timestamp)}</div>
                  {activity.duration_seconds && (
                    <div className="text-green-400">
                      ⏱️ {formatDuration(activity.duration_seconds)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
