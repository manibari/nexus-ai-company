import React, { useEffect, useState } from 'react'
import CEOInbox from './components/CEOInbox'
import GoalDashboard from './components/GoalDashboard'

interface Agent {
  id: string
  name: string
  role: string
  status: string
}

interface KPI {
  burn_rate_daily_usd: number
  total_cost_usd: number
  agents_status: Record<string, number>
}

function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [kpi, setKPI] = useState<KPI | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'dashboard' | 'inbox' | 'goals'>('goals')

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
          <nav className="flex gap-2">
            <button
              onClick={() => setActiveTab('inbox')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'inbox'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              📥 CEO Inbox
            </button>
            <button
              onClick={() => setActiveTab('goals')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'goals'
                  ? 'bg-cyan-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              🎯 Goals
            </button>
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
            ) : (
              <>
                {/* Agent Grid */}
                <div className="bg-slate-800 rounded-lg p-6 mb-8">
                  <h2 className="text-xl font-bold mb-4 text-cyan-300">
                    👥 Agent Status
                  </h2>
                  <div className="grid grid-cols-3 gap-4">
                    {agents.map(agent => (
                      <div
                        key={agent.id}
                        className="bg-slate-700 rounded-lg p-4 flex items-center gap-4"
                      >
                        <div className={`w-4 h-4 rounded-full ${getStatusColor(agent.status)}`} />
                        <div>
                          <div className="font-bold">{agent.name}</div>
                          <div className="text-sm text-gray-400">{agent.role}</div>
                          <div className="text-xs text-gray-500">{agent.status}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Office Map Placeholder */}
                <div className="bg-slate-800 rounded-lg p-6">
                  <h2 className="text-xl font-bold mb-4 text-cyan-300">
                    🗺️ Office Map
                  </h2>
                  <div className="h-64 bg-slate-700 rounded-lg flex items-center justify-center text-gray-500">
                    <div className="text-center">
                      <div className="text-4xl mb-2">🏗️</div>
                      <div>RPG 2.5D Office Map</div>
                      <div className="text-sm mt-1">Coming Soon</div>
                    </div>
                  </div>
                </div>
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
                <button className="w-full px-4 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg text-left transition-colors">
                  📚 查詢知識庫
                </button>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-slate-800 rounded-lg p-6">
              <h2 className="text-lg font-bold mb-4 text-cyan-300">
                📜 Recent Activity
              </h2>
              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-3 text-gray-400">
                  <span className="text-green-400">●</span>
                  <div>
                    <div>HUNTER 完成 Lead 分析</div>
                    <div className="text-xs text-gray-500">2 分鐘前</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 text-gray-400">
                  <span className="text-cyan-400">●</span>
                  <div>
                    <div>新商機已建立: ABC Corp</div>
                    <div className="text-xs text-gray-500">5 分鐘前</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 text-gray-400">
                  <span className="text-yellow-400">●</span>
                  <div>
                    <div>ORCHESTRATOR 等待確認</div>
                    <div className="text-xs text-gray-500">10 分鐘前</div>
                  </div>
                </div>
              </div>
            </div>
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
