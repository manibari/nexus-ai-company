import React, { useEffect, useState } from 'react'
import CEOInbox from './components/CEOInbox'
import GoalDashboard from './components/GoalDashboard'
import SalesPipeline from './components/SalesPipeline'
import ProductBoard from './components/ProductBoard'
import KnowledgeBase from './components/KnowledgeBase'
import OfficeMap from './components/OfficeMap'
import AgentActivityLog from './components/AgentActivityLog'

interface Agent {
  id: string
  name: string
  role: string
  status: string
  current_task?: string
}

interface KPI {
  burn_rate_daily_usd: number
  total_cost_usd: number
  agents_status: Record<string, number>
}

interface AgentDailySummary {
  agent_id: string
  agent_name: string
  date: string
  total_work_seconds: number
  total_work_formatted: string
  task_count: number
  tasks: Array<{
    start_time: string | null
    end_time: string | null
    duration_seconds: number
    duration_formatted: string
    message: string
    status: string
  }>
}

function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [kpi, setKPI] = useState<KPI | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'pipeline' | 'goals' | 'product' | 'knowledge' | 'inbox'>('dashboard')
  const [agentSummaries, setAgentSummaries] = useState<Record<string, AgentDailySummary>>({})
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const fetchAgentSummaries = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/activity/daily-summary`)
      if (res.ok) {
        const data: AgentDailySummary[] = await res.json()
        const summaryMap: Record<string, AgentDailySummary> = {}
        data.forEach(s => { summaryMap[s.agent_id] = s })
        setAgentSummaries(summaryMap)
      }
    } catch (err) {
      console.error('Failed to fetch agent summaries:', err)
    }
  }

  useEffect(() => {
    // Fetch agents
    fetch(`${API_URL}/api/v1/agents`)
      .then(res => res.json())
      .then(data => setAgents(data))
      .catch(err => console.error('Failed to fetch agents:', err))

    // Fetch KPI
    fetch(`${API_URL}/api/v1/dashboard/kpi`)
      .then(res => res.json())
      .then(data => setKPI(data))
      .catch(err => console.error('Failed to fetch KPI:', err))
      .finally(() => setLoading(false))

    // Fetch agent daily summaries
    fetchAgentSummaries()

    // Auto-refresh summaries every 30 seconds
    const interval = setInterval(fetchAgentSummaries, 30000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'idle': return 'bg-gray-500'
      case 'working': return 'bg-green-500'
      case 'blocked_internal': return 'bg-yellow-500'
      case 'blocked_user': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center">
        <div className="text-2xl">Loading Nexus AI Company...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-8 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-cyan-400">
              🏢 Nexus AI Company
            </h1>
            <p className="text-gray-400 text-sm">War Room - CEO Dashboard</p>
          </div>
          <nav className="flex gap-2 flex-wrap">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              📊 Dashboard
            </button>
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'pipeline'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              💰 Sales Board
            </button>
            <button
              onClick={() => setActiveTab('goals')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'goals'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              🎯 Project Board
            </button>
            <button
              onClick={() => setActiveTab('product')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'product'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              🏭 Product Board
            </button>
            <button
              onClick={() => setActiveTab('knowledge')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'knowledge'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              📚 Knowledge Base
            </button>
            <button
              onClick={() => setActiveTab('inbox')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'inbox'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              📥 Inbox
            </button>
          </nav>
        </div>
      </header>

      <main className="p-8">
        {/* KPI Bar */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Daily Burn Rate</div>
            <div className="text-2xl font-bold text-red-400">
              ${kpi?.burn_rate_daily_usd.toFixed(2) || '0.00'}
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Total Cost</div>
            <div className="text-2xl font-bold text-orange-400">
              ${kpi?.total_cost_usd.toFixed(2) || '0.00'}
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Active Agents</div>
            <div className="text-2xl font-bold text-green-400">
              {kpi?.agents_status.working || 0}
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Blocked Agents</div>
            <div className="text-2xl font-bold text-yellow-400">
              {(kpi?.agents_status.blocked_internal || 0) + (kpi?.agents_status.blocked_user || 0)}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-3 gap-8">
          {/* Left: Main Panel */}
          <div className="col-span-2">
            {activeTab === 'inbox' ? (
              <CEOInbox apiUrl={API_URL} />
            ) : activeTab === 'goals' ? (
              <GoalDashboard apiUrl={API_URL} />
            ) : activeTab === 'pipeline' ? (
              <SalesPipeline apiUrl={API_URL} />
            ) : activeTab === 'product' ? (
              <ProductBoard apiUrl={API_URL} />
            ) : activeTab === 'knowledge' ? (
              <KnowledgeBase apiUrl={API_URL} />
            ) : (
              <>
                {/* Agent Grid */}
                <div className="bg-slate-800 rounded-lg p-6 mb-8">
                  <h2 className="text-xl font-bold mb-4 text-cyan-300">
                    👥 Agent Status
                  </h2>
                  <div className="grid grid-cols-2 gap-4">
                    {agents.map(agent => {
                      const summary = agentSummaries[agent.id]
                      const isExpanded = expandedAgent === agent.id
                      return (
                        <div
                          key={agent.id}
                          className="bg-slate-700 rounded-lg p-4"
                        >
                          <div className="flex items-start gap-4">
                            <div className={`w-4 h-4 rounded-full mt-1 ${getStatusColor(agent.status)}`} />
                            <div className="flex-1">
                              <div className="flex justify-between items-start">
                                <div>
                                  <div className="font-bold">{agent.name}</div>
                                  <div className="text-sm text-gray-400">{agent.role}</div>
                                </div>
                                <div className="text-right">
                                  <div className="text-xs text-gray-500">{agent.status}</div>
                                  {summary && (
                                    <div className="text-sm text-cyan-400 font-medium">
                                      今日: {summary.total_work_formatted || '0s'}
                                    </div>
                                  )}
                                </div>
                              </div>
                              {agent.current_task && (
                                <div className="mt-2 text-xs text-green-400 bg-green-900/30 px-2 py-1 rounded">
                                  ▶️ {agent.current_task}
                                </div>
                              )}
                              {summary && summary.task_count > 0 && (
                                <div className="mt-2">
                                  <button
                                    onClick={() => setExpandedAgent(isExpanded ? null : agent.id)}
                                    className="text-xs text-gray-400 hover:text-cyan-400 transition-colors"
                                  >
                                    {isExpanded ? '▼' : '▶'} 任務: {summary.task_count} 項
                                  </button>
                                  {isExpanded && (
                                    <div className="mt-2 space-y-1 text-xs bg-slate-800 rounded p-2 max-h-40 overflow-y-auto">
                                      {summary.tasks.map((task, idx) => (
                                        <div key={idx} className="flex justify-between text-gray-300">
                                          <span className={task.status === 'completed' ? '' : 'text-green-400'}>
                                            {task.status === 'completed' ? '✅' : '▶️'} {task.message}
                                          </span>
                                          <span className="text-gray-500 ml-2">{task.duration_formatted}</span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Office Map */}
                <OfficeMap apiUrl={API_URL} />
              </>
            )}
          </div>

          {/* Right: Side Panel */}
          <div className="col-span-1">
            {/* Quick Actions */}
            <div className="bg-slate-800 rounded-lg p-6 mb-6">
              <h2 className="text-lg font-bold mb-4 text-cyan-300">
                ⚡ Quick Actions
              </h2>
              <div className="space-y-2">
                <button
                  onClick={() => setActiveTab('inbox')}
                  className="w-full px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-left transition-colors"
                >
                  📥 新增商機
                </button>
                <button className="w-full px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-left transition-colors">
                  📋 新增任務
                </button>
                <button
                  onClick={() => setActiveTab('knowledge')}
                  className="w-full px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-left transition-colors"
                >
                  📚 Knowledge Base
                </button>
              </div>
            </div>

            {/* Agent Activity Log */}
            <AgentActivityLog apiUrl={API_URL} limit={20} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700 px-8 py-3">
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>Nexus AI Company v0.1.0</span>
          <span>Backend: {API_URL}</span>
          <span>Status: 🟢 Operational</span>
        </div>
      </footer>
    </div>
  )
}

export default App
