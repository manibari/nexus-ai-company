import React, { useState } from 'react'

interface MEDDICScore {
  pain: {
    identified: boolean
    description: string | null
    intensity: number
    score: number
  }
  champion: {
    identified: boolean
    name: string | null
    title: string | null
    strength: string
    score: number
  }
  economic_buyer: {
    identified: boolean
    name: string | null
    title: string | null
    access_level: string
    score: number
  }
  total_score: number
  deal_health: string
  gaps: string[]
  next_actions: string[]
}

interface AnalysisResult {
  id: string
  intent: string
  confidence: number
  summary: string
  meddic: MEDDICScore | null
  suggested_actions: string[]
  requires_confirmation: boolean
}

interface CEOInboxProps {
  apiUrl: string
}

export default function CEOInbox({ apiUrl }: CEOInboxProps) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState(false)

  const handleSubmit = async () => {
    if (!input.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)
    setConfirmed(false)

    try {
      // Call intake API
      const response = await fetch(`${apiUrl}/api/v1/intake/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: input,
          input_type: 'text',
          source: 'web',
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to process input')
      }

      const data = await response.json()

      // Also get MEDDIC analysis
      const meddic = await getMEDDICAnalysis(input)

      setResult({
        id: data.id,
        intent: data.intent,
        confidence: data.confidence,
        summary: data.summary,
        meddic: meddic,
        suggested_actions: data.suggested_actions,
        requires_confirmation: data.requires_confirmation,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const getMEDDICAnalysis = async (content: string): Promise<MEDDICScore | null> => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/intake/analyze-meddic`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })

      if (response.ok) {
        return await response.json()
      }
    } catch {
      // MEDDIC analysis is optional
    }
    return null
  }

  const handleConfirm = async () => {
    if (!result) return

    try {
      await fetch(`${apiUrl}/api/v1/intake/inputs/${result.id}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: true }),
      })
      setConfirmed(true)
    } catch (err) {
      setError('Failed to confirm')
    }
  }

  const handleReject = async () => {
    if (!result) return

    try {
      await fetch(`${apiUrl}/api/v1/intake/inputs/${result.id}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: false }),
      })
      setResult(null)
      setInput('')
    } catch (err) {
      setError('Failed to reject')
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

  const getHealthLabel = (health: string) => {
    switch (health) {
      case 'healthy': return '健康'
      case 'at_risk': return '有風險'
      case 'needs_attention': return '需關注'
      case 'weak': return '較弱'
      default: return health
    }
  }

  const renderScoreBar = (score: number, max: number, label: string) => {
    const percentage = (score / max) * 100
    const getBarColor = () => {
      if (percentage >= 70) return 'bg-green-500'
      if (percentage >= 40) return 'bg-yellow-500'
      return 'bg-red-500'
    }

    return (
      <div className="flex items-center gap-3 mb-2">
        <span className="w-24 text-sm text-gray-400">{label}</span>
        <div className="flex-1 h-3 bg-slate-600 rounded-full overflow-hidden">
          <div
            className={`h-full ${getBarColor()} transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="w-12 text-sm text-right">{score}/{max}</span>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4 text-cyan-300 flex items-center gap-2">
        📥 CEO Inbox
      </h2>

      {/* Input Area */}
      <div className="mb-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="輸入商機、任務或問題...&#10;&#10;例如：今天跟老王吃飯，他介紹了 ABC 公司的 CTO，他們系統效能有問題，想下週約個會議聊聊。"
          className="w-full h-32 bg-slate-700 border border-slate-600 rounded-lg p-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-cyan-500"
          disabled={loading}
        />
        <div className="flex justify-end mt-2">
          <button
            onClick={handleSubmit}
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
          >
            {loading ? '分析中...' : '送出分析'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-300">
          ⚠️ {error}
        </div>
      )}

      {/* Analysis Result */}
      {result && (
        <div className="border border-slate-600 rounded-lg overflow-hidden">
          {/* Header */}
          <div className="bg-slate-700 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-lg">📊</span>
              <span className="font-medium">分析結果</span>
              <span className={`px-2 py-0.5 rounded text-sm ${
                result.intent === 'opportunity' ? 'bg-green-600' :
                result.intent === 'project' ? 'bg-blue-600' :
                result.intent === 'question' ? 'bg-purple-600' :
                'bg-gray-600'
              }`}>
                {result.intent === 'opportunity' ? '商機' :
                 result.intent === 'project' ? '專案' :
                 result.intent === 'question' ? '問題' :
                 result.intent}
              </span>
              <span className="text-sm text-gray-400">
                信心度: {(result.confidence * 100).toFixed(0)}%
              </span>
            </div>
            {confirmed && (
              <span className="px-3 py-1 bg-green-600 rounded text-sm">
                ✓ 已確認
              </span>
            )}
          </div>

          {/* Content */}
          <div className="p-4">
            {/* Summary */}
            <div className="mb-4 p-3 bg-slate-700/50 rounded-lg">
              <pre className="text-sm whitespace-pre-wrap text-gray-300">
                {result.summary}
              </pre>
            </div>

            {/* MEDDIC Analysis */}
            {result.meddic && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  📈 MEDDIC 分析
                  <span className={`ml-2 ${getHealthColor(result.meddic.deal_health)}`}>
                    ({getHealthLabel(result.meddic.deal_health)} - {result.meddic.total_score}/100)
                  </span>
                </h3>

                <div className="bg-slate-700/50 rounded-lg p-4">
                  {renderScoreBar(result.meddic.pain.score, 10, 'Pain 痛點')}
                  {renderScoreBar(result.meddic.champion.score, 9, 'Champion')}
                  {renderScoreBar(result.meddic.economic_buyer.score, 10, 'EB 決策者')}
                </div>

                {/* Gaps */}
                {result.meddic.gaps.length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-sm text-yellow-400 mb-2">⚠️ 缺口：</h4>
                    <ul className="text-sm text-gray-400 space-y-1">
                      {result.meddic.gaps.map((gap, i) => (
                        <li key={i}>• {gap}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Next Actions */}
                {result.meddic.next_actions.length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-sm text-cyan-400 mb-2">💡 建議動作：</h4>
                    <ul className="text-sm text-gray-300 space-y-1">
                      {result.meddic.next_actions.map((action, i) => (
                        <li key={i}>{i + 1}. {action}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Suggested Actions (from intake) */}
            {!result.meddic && result.suggested_actions.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-400 mb-2">💡 建議動作：</h3>
                <ul className="text-sm text-gray-300 space-y-1">
                  {result.suggested_actions.map((action, i) => (
                    <li key={i}>• {action}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actions */}
            {result.requires_confirmation && !confirmed && (
              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-slate-600">
                <button
                  onClick={handleReject}
                  className="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg transition-colors"
                >
                  ✗ 取消
                </button>
                <button
                  onClick={handleConfirm}
                  className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg transition-colors"
                >
                  ✓ 確認執行
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <div className="text-center text-gray-500 py-8">
          <div className="text-4xl mb-2">💬</div>
          <div>輸入商機、任務或問題，系統會自動分析並建議下一步</div>
        </div>
      )}
    </div>
  )
}
