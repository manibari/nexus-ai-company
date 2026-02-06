import React, { useEffect, useState } from 'react'

interface MEDDICScore {
  pain: { score: number; identified: boolean; description: string | null }
  champion: { score: number; identified: boolean; name: string | null; title: string | null }
  economic_buyer: { score: number; identified: boolean; name: string | null; access_level: string }
  total_score: number
  health: string
  gaps: string[]
  next_actions: string[]
}

interface Contact {
  id: string
  name: string
  title: string | null
  role: string
  email: string | null
}

interface OpportunitySummary {
  id: string
  name: string
  company: string
  amount: number | null
  stage: string
  status: string
  meddic_score: number
  meddic_health: string
  win_probability: number
  weighted_amount: number
  days_in_stage: number
  is_stale: boolean
  champion: string | null
  expected_close: string | null
}

interface OpportunityDetail {
  id: string
  name: string
  company: string
  amount: number | null
  currency: string
  stage: string
  status: string
  days_in_stage: number
  is_stale: boolean
  meddic: MEDDICScore
  contacts: Contact[]
  champion: Contact | null
  economic_buyer: Contact | null
  created_at: string
  expected_close: string | null
  last_activity_at: string | null
  days_since_activity: number | null
  source: string
  source_detail: string | null
  owner: string
  win_probability: number
  weighted_amount: number
  notes: string | null
}

interface Activity {
  id: string
  type: string
  subject: string
  occurred_at: string
  summary: string | null
  next_action: string | null
}

interface PipelineDashboard {
  total_open: number
  total_amount: number
  total_weighted_amount: number
  by_stage: Record<string, { count: number; total_amount: number; weighted_amount: number }>
  alerts: {
    stale_count: number
    at_risk_count: number
  }
}

interface SalesPipelineProps {
  apiUrl: string
}

const STAGES = [
  { key: 'lead', label: 'Lead', prob: '10%' },
  { key: 'qualification', label: 'Qualification', prob: '20%' },
  { key: 'discovery', label: 'Discovery', prob: '40%' },
  { key: 'proposal', label: 'Proposal', prob: '70%' },
  { key: 'negotiation', label: 'Negotiation', prob: '85%' },
  { key: 'won', label: 'Won', prob: '100%' },
]

export default function SalesPipeline({ apiUrl }: SalesPipelineProps) {
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([])
  const [dashboard, setDashboard] = useState<PipelineDashboard | null>(null)
  const [selectedOpp, setSelectedOpp] = useState<OpportunityDetail | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Closed Deals state
  const [view, setView] = useState<'pipeline' | 'closed'>('pipeline')
  const [wonDeals, setWonDeals] = useState<OpportunitySummary[]>([])
  const [lostDeals, setLostDeals] = useState<OpportunitySummary[]>([])
  const [dormantDeals, setDormantDeals] = useState<OpportunitySummary[]>([])
  const [closedLoading, setClosedLoading] = useState(false)

  // Create form state
  const [newOpp, setNewOpp] = useState({
    name: '',
    company: '',
    amount: '',
    source: 'referral',
    source_detail: '',
    pain_description: '',
  })

  const fetchData = async () => {
    try {
      const [oppsRes, dashRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/pipeline/opportunities`),
        fetch(`${apiUrl}/api/v1/pipeline/dashboard`),
      ])

      if (oppsRes.ok) setOpportunities(await oppsRes.json())
      if (dashRes.ok) setDashboard(await dashRes.json())
    } catch (err) {
      setError('Failed to fetch pipeline data')
    } finally {
      setLoading(false)
    }
  }

  const fetchOppDetail = async (oppId: string) => {
    try {
      const [oppRes, actRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/pipeline/opportunities/${oppId}`),
        fetch(`${apiUrl}/api/v1/pipeline/opportunities/${oppId}/activities`),
      ])

      if (oppRes.ok) setSelectedOpp(await oppRes.json())
      if (actRes.ok) setActivities(await actRes.json())
    } catch (err) {
      setError('Failed to fetch opportunity details')
    }
  }

  const fetchClosedDeals = async () => {
    setClosedLoading(true)
    try {
      const [wonRes, lostRes, dormantRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/pipeline/closed/won`),
        fetch(`${apiUrl}/api/v1/pipeline/closed/lost`),
        fetch(`${apiUrl}/api/v1/pipeline/closed/dormant`),
      ])

      if (wonRes.ok) setWonDeals(await wonRes.json())
      if (lostRes.ok) setLostDeals(await lostRes.json())
      if (dormantRes.ok) setDormantDeals(await dormantRes.json())
    } catch (err) {
      setError('Failed to fetch closed deals')
    } finally {
      setClosedLoading(false)
    }
  }

  const reactivateOpportunity = async (oppId: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/pipeline/opportunities/${oppId}/reactivate`, {
        method: 'POST',
      })

      if (response.ok) {
        await fetchClosedDeals()
        await fetchData()
      } else {
        const error = await response.json()
        setError(error.detail || 'Failed to reactivate opportunity')
      }
    } catch (err) {
      setError('Failed to reactivate opportunity')
    }
  }

  const markDormant = async (oppId: string) => {
    const reason = prompt('休眠原因？')
    try {
      await fetch(`${apiUrl}/api/v1/pipeline/opportunities/${oppId}/dormant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      await fetchData()
      setSelectedOpp(null)
    } catch (err) {
      setError('Failed to mark as dormant')
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (view === 'closed') {
      fetchClosedDeals()
    }
  }, [view])

  const createOpportunity = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/pipeline/opportunities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newOpp.name,
          company: newOpp.company,
          amount: newOpp.amount ? parseFloat(newOpp.amount) : null,
          source: newOpp.source,
          source_detail: newOpp.source_detail || null,
          pain_description: newOpp.pain_description || null,
        }),
      })

      if (response.ok) {
        setShowCreateForm(false)
        setNewOpp({ name: '', company: '', amount: '', source: 'referral', source_detail: '', pain_description: '' })
        await fetchData()
      }
    } catch (err) {
      setError('Failed to create opportunity')
    }
  }

  const advanceStage = async (oppId: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/pipeline/opportunities/${oppId}/advance`, {
        method: 'POST',
      })

      if (response.ok) {
        await fetchData()
        if (selectedOpp?.id === oppId) {
          await fetchOppDetail(oppId)
        }
      } else {
        const error = await response.json()
        setError(error.detail?.message || 'Cannot advance stage')
      }
    } catch (err) {
      setError('Failed to advance stage')
    }
  }

  const markWon = async (oppId: string) => {
    try {
      await fetch(`${apiUrl}/api/v1/pipeline/opportunities/${oppId}/win`, { method: 'POST' })
      await fetchData()
      setSelectedOpp(null)
    } catch (err) {
      setError('Failed to mark as won')
    }
  }

  const markLost = async (oppId: string) => {
    const reason = prompt('失敗原因？')
    try {
      await fetch(`${apiUrl}/api/v1/pipeline/opportunities/${oppId}/lose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      })
      await fetchData()
      setSelectedOpp(null)
    } catch (err) {
      setError('Failed to mark as lost')
    }
  }

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy': return 'text-green-400'
      case 'at_risk': return 'text-yellow-400'
      case 'needs_attention': return 'text-orange-400'
      case 'weak': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'healthy': return '🟢'
      case 'at_risk': return '🟡'
      case 'needs_attention': return '🟠'
      case 'weak': return '🔴'
      default: return '⚪'
    }
  }

  const formatAmount = (amount: number | null) => {
    if (!amount) return '-'
    if (amount >= 10000) return `$${(amount / 10000).toFixed(1)}萬`
    return `$${amount.toLocaleString()}`
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('zh-TW')
  }

  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="text-center text-gray-400 py-8">載入中...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-cyan-300 flex items-center gap-2">
            💰 Sales Board
          </h2>
          <div className="flex gap-2">
            <button
              onClick={view === 'pipeline' ? fetchData : fetchClosedDeals}
              className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors"
            >
              🔄 重新整理
            </button>
            {view === 'pipeline' && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 rounded text-sm transition-colors"
              >
                + 新增商機
              </button>
            )}
          </div>
        </div>

        {/* View Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setView('pipeline')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              view === 'pipeline'
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
            }`}
          >
            📊 Active Pipeline
          </button>
          <button
            onClick={() => setView('closed')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              view === 'closed'
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
            }`}
          >
            📁 Closed Deals
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded-lg text-red-300 text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-400 hover:text-red-300">✕</button>
          </div>
        )}

        {/* === CLOSED DEALS VIEW === */}
        {view === 'closed' && (
          closedLoading ? (
            <div className="text-center text-gray-400 py-8">載入中...</div>
          ) : (
            <div className="space-y-6">
              {/* Won Deals */}
              <div>
                <h3 className="text-lg font-medium text-green-400 mb-3 flex items-center gap-2">
                  🏆 Won <span className="text-sm text-gray-400">({wonDeals.length})</span>
                </h3>
                {wonDeals.length === 0 ? (
                  <div className="text-center text-gray-500 py-4 bg-slate-700/50 rounded-lg">
                    目前沒有成交商機
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {wonDeals.map((deal) => (
                      <div key={deal.id} className="p-4 bg-green-900/20 border border-green-600/30 rounded-lg">
                        <div className="font-medium text-green-300">{deal.name}</div>
                        <div className="text-sm text-gray-400">{deal.company}</div>
                        <div className="text-lg font-bold text-green-400 mt-2">{formatAmount(deal.amount)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Lost Deals */}
              <div>
                <h3 className="text-lg font-medium text-red-400 mb-3 flex items-center gap-2">
                  ❌ Lost <span className="text-sm text-gray-400">({lostDeals.length})</span>
                </h3>
                {lostDeals.length === 0 ? (
                  <div className="text-center text-gray-500 py-4 bg-slate-700/50 rounded-lg">
                    目前沒有失敗商機
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {lostDeals.map((deal) => (
                      <div key={deal.id} className="p-4 bg-red-900/20 border border-red-600/30 rounded-lg">
                        <div className="font-medium text-red-300">{deal.name}</div>
                        <div className="text-sm text-gray-400">{deal.company}</div>
                        <div className="text-lg font-bold text-red-400 mt-2">{formatAmount(deal.amount)}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Dormant Deals */}
              <div>
                <h3 className="text-lg font-medium text-yellow-400 mb-3 flex items-center gap-2">
                  💤 Dormant <span className="text-sm text-gray-400">({dormantDeals.length})</span>
                </h3>
                {dormantDeals.length === 0 ? (
                  <div className="text-center text-gray-500 py-4 bg-slate-700/50 rounded-lg">
                    目前沒有休眠商機
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {dormantDeals.map((deal) => (
                      <div key={deal.id} className="p-4 bg-yellow-900/20 border border-yellow-600/30 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-medium text-yellow-300">{deal.name}</div>
                            <div className="text-sm text-gray-400">{deal.company}</div>
                            <div className="text-lg font-bold text-yellow-400 mt-2">{formatAmount(deal.amount)}</div>
                          </div>
                          <button
                            onClick={() => reactivateOpportunity(deal.id)}
                            className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 rounded text-sm transition-colors"
                            title="重新啟動"
                          >
                            ♻️ Reactivate
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        )}

        {/* === ACTIVE PIPELINE VIEW === */}
        {view === 'pipeline' && dashboard && (
          <div className="mb-6">
            <div className="grid grid-cols-6 gap-2 mb-4">
              {STAGES.map((stage) => {
                const stats = dashboard.by_stage[stage.key] || { count: 0, total_amount: 0 }
                return (
                  <div key={stage.key} className="text-center">
                    <div className="text-xs text-gray-500 mb-1">{stage.label}</div>
                    <div className="text-lg font-bold text-white">{stats.count}</div>
                    <div className="text-xs text-gray-400">{formatAmount(stats.total_amount)}</div>
                    <div className="text-xs text-gray-500">({stage.prob})</div>
                  </div>
                )
              })}
            </div>

            {/* Summary Stats */}
            <div className="flex items-center justify-between text-sm border-t border-slate-700 pt-4">
              <div className="flex gap-6">
                <span className="text-gray-400">
                  Open: <span className="text-white font-medium">{dashboard.total_open}</span>
                </span>
                <span className="text-gray-400">
                  Total: <span className="text-white font-medium">{formatAmount(dashboard.total_amount)}</span>
                </span>
                <span className="text-gray-400">
                  Weighted: <span className="text-cyan-400 font-medium">{formatAmount(dashboard.total_weighted_amount)}</span>
                </span>
              </div>
              <div className="flex gap-4">
                {dashboard.alerts.stale_count > 0 && (
                  <span className="text-yellow-400">⚠️ {dashboard.alerts.stale_count} stale</span>
                )}
                {dashboard.alerts.at_risk_count > 0 && (
                  <span className="text-orange-400">🔥 {dashboard.alerts.at_risk_count} at risk</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Opportunity List */}
        {view === 'pipeline' && (opportunities.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-4xl mb-2">💼</div>
            <div>目前沒有商機</div>
            <button
              onClick={() => setShowCreateForm(true)}
              className="mt-3 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm"
            >
              + 新增第一個商機
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {opportunities.map((opp) => (
              <div
                key={opp.id}
                onClick={() => fetchOppDetail(opp.id)}
                className={`p-4 rounded-lg cursor-pointer transition-all ${
                  selectedOpp?.id === opp.id
                    ? 'bg-cyan-900/30 border border-cyan-500'
                    : 'bg-slate-700 hover:bg-slate-600 border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span>{getHealthIcon(opp.meddic_health)}</span>
                    <span className="font-medium">{opp.name}</span>
                    <span className="text-sm text-gray-400">@{opp.company}</span>
                    <span className="px-2 py-0.5 bg-slate-600 rounded text-xs">{opp.stage}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-cyan-400 font-medium">{formatAmount(opp.amount)}</span>
                    <span className="text-xs text-gray-500">({(opp.win_probability * 100).toFixed(0)}%)</span>
                  </div>
                </div>

                {/* MEDDIC Bar */}
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-20">MEDDIC</span>
                  <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        opp.meddic_health === 'healthy' ? 'bg-green-500' :
                        opp.meddic_health === 'at_risk' ? 'bg-yellow-500' :
                        opp.meddic_health === 'needs_attention' ? 'bg-orange-500' :
                        'bg-red-500'
                      }`}
                      style={{ width: `${opp.meddic_score}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 w-12 text-right">{opp.meddic_score}/100</span>
                </div>

                {/* Quick Info */}
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                  {opp.champion && <span>Champion: {opp.champion}</span>}
                  <span>Stage: {opp.days_in_stage}d</span>
                  {opp.is_stale && <span className="text-yellow-400">⚠️ Stale</span>}
                  {opp.expected_close && <span>Close: {formatDate(opp.expected_close)}</span>}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Opportunity Detail */}
      {selectedOpp && (
        <div className="bg-slate-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-cyan-300">{selectedOpp.name}</h3>
              <p className="text-sm text-gray-400">{selectedOpp.company}</p>
            </div>
            <button
              onClick={() => setSelectedOpp(null)}
              className="text-gray-400 hover:text-white"
            >
              ✕
            </button>
          </div>

          {/* Key Info */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Amount</div>
              <div className="text-lg font-bold text-cyan-400">{formatAmount(selectedOpp.amount)}</div>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Stage</div>
              <div className="text-lg font-bold">{selectedOpp.stage}</div>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">MEDDIC</div>
              <div className={`text-lg font-bold ${getHealthColor(selectedOpp.meddic.health)}`}>
                {selectedOpp.meddic.total_score}/100
              </div>
            </div>
            <div className="bg-slate-700/50 rounded-lg p-3">
              <div className="text-xs text-gray-500">Win Prob</div>
              <div className="text-lg font-bold">{(selectedOpp.win_probability * 100).toFixed(0)}%</div>
            </div>
          </div>

          {/* MEDDIC Detail */}
          <div className="mb-6">
            <h4 className="text-sm font-medium text-gray-400 mb-3">📊 MEDDIC 分析</h4>
            <div className="space-y-2">
              {/* Pain */}
              <div className="flex items-center gap-3">
                <span className="w-24 text-sm text-gray-400">Pain 痛點</span>
                <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500" style={{ width: `${selectedOpp.meddic.pain.score * 10}%` }} />
                </div>
                <span className="w-12 text-sm text-right">{selectedOpp.meddic.pain.score}/10</span>
                <span className={selectedOpp.meddic.pain.identified ? 'text-green-400' : 'text-gray-500'}>
                  {selectedOpp.meddic.pain.identified ? '✓' : '✗'}
                </span>
              </div>
              {/* Champion */}
              <div className="flex items-center gap-3">
                <span className="w-24 text-sm text-gray-400">Champion</span>
                <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500" style={{ width: `${selectedOpp.meddic.champion.score * 11}%` }} />
                </div>
                <span className="w-12 text-sm text-right">{selectedOpp.meddic.champion.score}/9</span>
                <span className={selectedOpp.meddic.champion.identified ? 'text-green-400' : 'text-gray-500'}>
                  {selectedOpp.meddic.champion.identified ? '✓' : '✗'}
                </span>
              </div>
              {/* EB */}
              <div className="flex items-center gap-3">
                <span className="w-24 text-sm text-gray-400">EB 決策者</span>
                <div className="flex-1 h-2 bg-slate-600 rounded-full overflow-hidden">
                  <div className="h-full bg-purple-500" style={{ width: `${selectedOpp.meddic.economic_buyer.score * 10}%` }} />
                </div>
                <span className="w-12 text-sm text-right">{selectedOpp.meddic.economic_buyer.score}/10</span>
                <span className={selectedOpp.meddic.economic_buyer.identified ? 'text-green-400' : 'text-gray-500'}>
                  {selectedOpp.meddic.economic_buyer.identified ? '✓' : '✗'}
                </span>
              </div>
            </div>

            {/* Gaps */}
            {selectedOpp.meddic.gaps.length > 0 && (
              <div className="mt-3 p-3 bg-yellow-900/20 border border-yellow-600/30 rounded-lg">
                <div className="text-sm text-yellow-400 mb-1">⚠️ 缺口</div>
                <ul className="text-sm text-gray-400 space-y-1">
                  {selectedOpp.meddic.gaps.map((gap, i) => (
                    <li key={i}>• {gap}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Next Actions */}
            {selectedOpp.meddic.next_actions.length > 0 && (
              <div className="mt-3 p-3 bg-cyan-900/20 border border-cyan-600/30 rounded-lg">
                <div className="text-sm text-cyan-400 mb-1">💡 建議動作</div>
                <ul className="text-sm text-gray-300 space-y-1">
                  {selectedOpp.meddic.next_actions.map((action, i) => (
                    <li key={i}>{i + 1}. {action}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Contacts */}
          {selectedOpp.contacts.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-medium text-gray-400 mb-3">👥 聯絡人</h4>
              <div className="grid grid-cols-2 gap-2">
                {selectedOpp.contacts.map((contact) => (
                  <div key={contact.id} className="p-2 bg-slate-700/50 rounded-lg text-sm">
                    <div className="font-medium">{contact.name}</div>
                    <div className="text-xs text-gray-400">
                      {contact.title} • {contact.role}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Activities */}
          {activities.length > 0 && (
            <div className="mb-6">
              <h4 className="text-sm font-medium text-gray-400 mb-3">📝 活動記錄</h4>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {activities.map((activity) => (
                  <div key={activity.id} className="p-2 bg-slate-700/50 rounded-lg text-sm">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{activity.subject}</span>
                      <span className="text-xs text-gray-500">{formatDate(activity.occurred_at)}</span>
                    </div>
                    {activity.summary && (
                      <div className="text-xs text-gray-400 mt-1">{activity.summary}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          {selectedOpp.status === 'open' && (
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-700">
              <button
                onClick={() => markDormant(selectedOpp.id)}
                className="px-4 py-2 bg-yellow-600/20 border border-yellow-500 hover:bg-yellow-600/40 rounded-lg text-sm text-yellow-400"
              >
                💤 Dormant
              </button>
              <button
                onClick={() => markLost(selectedOpp.id)}
                className="px-4 py-2 bg-red-600/20 border border-red-500 hover:bg-red-600/40 rounded-lg text-sm text-red-400"
              >
                ✗ Lost
              </button>
              <button
                onClick={() => advanceStage(selectedOpp.id)}
                className="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-sm"
              >
                ⏩ Advance Stage
              </button>
              <button
                onClick={() => markWon(selectedOpp.id)}
                className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-sm"
              >
                ✓ Won
              </button>
            </div>
          )}
        </div>
      )}

      {/* Create Form Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold text-cyan-300 mb-4">新增商機</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">商機名稱 *</label>
                <input
                  type="text"
                  value={newOpp.name}
                  onChange={(e) => setNewOpp({ ...newOpp, name: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  placeholder="e.g., ABC Corp 系統整合案"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">公司 *</label>
                <input
                  type="text"
                  value={newOpp.company}
                  onChange={(e) => setNewOpp({ ...newOpp, company: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  placeholder="e.g., ABC Corporation"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">預估金額</label>
                <input
                  type="number"
                  value={newOpp.amount}
                  onChange={(e) => setNewOpp({ ...newOpp, amount: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  placeholder="e.g., 500000"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">來源</label>
                <select
                  value={newOpp.source}
                  onChange={(e) => setNewOpp({ ...newOpp, source: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                >
                  <option value="referral">Referral 轉介</option>
                  <option value="inbound">Inbound 主動詢問</option>
                  <option value="outbound">Outbound 主動開發</option>
                  <option value="event">Event 活動</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">來源說明</label>
                <input
                  type="text"
                  value={newOpp.source_detail}
                  onChange={(e) => setNewOpp({ ...newOpp, source_detail: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
                  placeholder="e.g., 老王介紹"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">客戶痛點</label>
                <textarea
                  value={newOpp.pain_description}
                  onChange={(e) => setNewOpp({ ...newOpp, pain_description: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white resize-none"
                  rows={2}
                  placeholder="e.g., 系統效能問題，每月損失 50 萬"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={createOpportunity}
                disabled={!newOpp.name || !newOpp.company}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg"
              >
                建立
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
