import React, { useEffect, useState } from 'react'

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
    <div className="min-h-screen bg-slate-900 text-white p-8">
      {/* Header */}
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-cyan-400">
          🏢 Nexus AI Company
        </h1>
        <p className="text-gray-400 mt-2">War Room - CEO Dashboard</p>
      </header>

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

      {/* Agent Grid (Placeholder for RPG Map) */}
      <div className="bg-slate-800 rounded-lg p-6">
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

      {/* Placeholder for RPG Canvas */}
      <div className="mt-8 bg-slate-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 text-cyan-300">
          🗺️ Office Map (Coming Soon)
        </h2>
        <div className="h-96 bg-slate-700 rounded-lg flex items-center justify-center text-gray-500">
          <div className="text-center">
            <div className="text-6xl mb-4">🏗️</div>
            <div>RPG 2.5D Office Map will be rendered here</div>
            <div className="text-sm mt-2">Phase 1c: Visualization</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-gray-500 text-sm">
        Nexus AI Company v0.1.0 | Phase 1: Infrastructure
      </footer>
    </div>
  )
}

export default App
