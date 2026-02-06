import React, { useEffect, useState } from 'react'

// === Types ===

interface TodoAction {
  id: string
  label: string
  style: string
  requires_input: boolean
  input_placeholder?: string
}

interface QuestionItem {
  id: string
  question: string
  options?: string[]
  type?: string
  placeholder?: string
  multi?: boolean
}

interface TodoItem {
  id: string
  project_name: string
  subject: string
  description: string | null
  from_agent: string
  from_agent_name: string
  type: string
  priority: string
  created_at: string
  deadline: string | null
  completed_at: string | null
  status: string
  actions: TodoAction[]
  response: any
  related_entity_type: string | null
  related_entity_id: string | null
  payload: {
    questions?: QuestionItem[]
    [key: string]: any
  }
  is_overdue: boolean
}

interface TodoStats {
  total: number
  pending: number
  overdue: number
  completed: number
  by_priority: Record<string, number>
  by_type: Record<string, number>
}

interface CEOInboxProps {
  apiUrl: string
}

// === Main Component ===

export default function CEOInbox({ apiUrl }: CEOInboxProps) {
  const [activeView, setActiveView] = useState<'todo' | 'input'>('todo')
  const [todos, setTodos] = useState<TodoItem[]>([])
  const [stats, setStats] = useState<TodoStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Input form state (existing functionality)
  const [input, setInput] = useState('')
  const [inputLoading, setInputLoading] = useState(false)

  // Selected todo for detail view
  const [selectedTodo, setSelectedTodo] = useState<TodoItem | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})

  // Fetch todos
  const fetchTodos = async () => {
    try {
      const [todosRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/ceo/todos/pending`),
        fetch(`${apiUrl}/api/v1/ceo/todos/stats`),
      ])

      if (todosRes.ok) setTodos(await todosRes.json())
      if (statsRes.ok) setStats(await statsRes.json())
    } catch (err) {
      setError('Failed to fetch todos')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTodos()
    const interval = setInterval(fetchTodos, 30000)
    return () => clearInterval(interval)
  }, [])

  // Handle todo response
  const handleRespond = async (todoId: string, actionId: string, data?: any) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/ceo/todos/${todoId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, data }),
      })

      if (response.ok) {
        setSelectedTodo(null)
        setAnswers({})
        await fetchTodos()
      } else {
        setError('Failed to respond')
      }
    } catch (err) {
      setError('Failed to respond')
    }
  }

  // Handle questionnaire submit
  const handleQuestionnaireSubmit = async (todo: TodoItem) => {
    await handleRespond(todo.id, 'respond', { answers })
  }

  // Handle input submit (existing functionality)
  const handleInputSubmit = async () => {
    if (!input.trim()) return

    setInputLoading(true)
    setError(null)

    try {
      const response = await fetch(`${apiUrl}/api/v1/intake/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: input,
          input_type: 'text',
          source: 'web',
        }),
      })

      if (response.ok) {
        setInput('')
        // Could show success message or result
      }
    } catch (err) {
      setError('Failed to submit')
    } finally {
      setInputLoading(false)
    }
  }

  // Helpers
  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'border-red-500 bg-red-900/20'
      case 'high': return 'border-orange-500 bg-orange-900/20'
      case 'normal': return 'border-yellow-500 bg-yellow-900/20'
      case 'low': return 'border-green-500 bg-green-900/20'
      default: return 'border-slate-600'
    }
  }

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'urgent': return '🔴'
      case 'high': return '🟠'
      case 'normal': return '🟡'
      case 'low': return '🟢'
      default: return '⚪'
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'questionnaire': return '📝 問卷'
      case 'approval': return '✅ 審批'
      case 'review': return '🔍 審查'
      case 'decision': return '🎯 決策'
      case 'notification': return '📢 通知'
      default: return type
    }
  }

  const formatDeadline = (deadline: string | null) => {
    if (!deadline) return '無期限'
    const d = new Date(deadline)
    const now = new Date()
    const diff = d.getTime() - now.getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))

    if (hours < 0) return '已過期'
    if (hours < 24) return `${hours} 小時內`
    const days = Math.floor(hours / 24)
    return `${days} 天內`
  }

  // Render
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="text-center text-gray-400 py-8">載入中...</div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-cyan-300 flex items-center gap-2">
          📥 CEO Inbox
        </h2>
        <button
          onClick={fetchTodos}
          className="px-3 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors"
        >
          🔄 重新整理
        </button>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveView('todo')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
            activeView === 'todo'
              ? 'bg-cyan-600 text-white'
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          📋 To-Do
          {stats && stats.pending > 0 && (
            <span className="px-2 py-0.5 bg-red-500 rounded-full text-xs">
              {stats.pending}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveView('input')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeView === 'input'
              ? 'bg-cyan-600 text-white'
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          ✏️ Input
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-500 rounded-lg text-red-300 text-sm">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-400 hover:text-red-300">✕</button>
        </div>
      )}

      {/* === TO-DO VIEW === */}
      {activeView === 'todo' && (
        <>
          {/* Stats Bar */}
          {stats && (
            <div className="grid grid-cols-4 gap-2 mb-6">
              <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-white">{stats.pending}</div>
                <div className="text-xs text-gray-400">待處理</div>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-red-400">{stats.overdue}</div>
                <div className="text-xs text-gray-400">已過期</div>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-orange-400">{stats.by_priority?.urgent || 0}</div>
                <div className="text-xs text-gray-400">緊急</div>
              </div>
              <div className="bg-slate-700/50 rounded-lg p-3 text-center">
                <div className="text-2xl font-bold text-green-400">{stats.completed}</div>
                <div className="text-xs text-gray-400">已完成</div>
              </div>
            </div>
          )}

          {/* Todo List */}
          {todos.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <div className="text-4xl mb-2">✅</div>
              <div>目前沒有待處理事項</div>
            </div>
          ) : (
            <div className="space-y-4">
              {todos.map((todo) => (
                <div
                  key={todo.id}
                  className={`border rounded-lg p-4 ${getPriorityStyle(todo.priority)} ${
                    selectedTodo?.id === todo.id ? 'ring-2 ring-cyan-500' : ''
                  }`}
                >
                  {/* Todo Header */}
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span>{getPriorityIcon(todo.priority)}</span>
                        <span className="font-medium text-white">{todo.project_name}</span>
                        <span className="px-2 py-0.5 bg-slate-600 rounded text-xs">
                          {getTypeLabel(todo.type)}
                        </span>
                      </div>
                      <div className="text-cyan-400 font-medium">{todo.subject}</div>
                      {todo.description && (
                        <div className="text-sm text-gray-400 mt-1">{todo.description}</div>
                      )}
                    </div>
                    <div className="text-right text-sm">
                      <div className="text-gray-400">來源: {todo.from_agent_name}</div>
                      <div className={todo.is_overdue ? 'text-red-400 font-medium' : 'text-gray-400'}>
                        DDL: {formatDeadline(todo.deadline)}
                      </div>
                    </div>
                  </div>

                  {/* Expand Button */}
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-600/50">
                    <button
                      onClick={() => setSelectedTodo(selectedTodo?.id === todo.id ? null : todo)}
                      className="text-sm text-gray-400 hover:text-white transition-colors"
                    >
                      {selectedTodo?.id === todo.id ? '收起 ▲' : '展開詳情 ▼'}
                    </button>

                    {/* Quick Actions */}
                    {selectedTodo?.id !== todo.id && (
                      <div className="flex gap-2">
                        {todo.actions.slice(0, 2).map((action) => (
                          <button
                            key={action.id}
                            onClick={() => {
                              if (todo.type === 'questionnaire') {
                                setSelectedTodo(todo)
                              } else {
                                handleRespond(todo.id, action.id)
                              }
                            }}
                            className={`px-3 py-1 rounded text-sm transition-colors ${
                              action.style === 'primary'
                                ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                                : action.style === 'danger'
                                ? 'bg-red-600 hover:bg-red-500 text-white'
                                : 'bg-slate-600 hover:bg-slate-500 text-gray-200'
                            }`}
                          >
                            {action.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Expanded Content */}
                  {selectedTodo?.id === todo.id && (
                    <div className="mt-4 p-4 bg-slate-700/50 rounded-lg">
                      {/* Questionnaire Form */}
                      {todo.type === 'questionnaire' && todo.payload.questions && (
                        <div className="space-y-4">
                          <h4 className="font-medium text-white mb-3">請回覆以下問題：</h4>
                          {todo.payload.questions.map((q, idx) => (
                            <div key={q.id} className="space-y-2">
                              <label className="block text-sm text-gray-300">
                                {idx + 1}. {q.question}
                              </label>
                              {q.options ? (
                                <div className="flex flex-wrap gap-2">
                                  {q.options.map((opt) => (
                                    <button
                                      key={opt}
                                      onClick={() => {
                                        if (q.multi) {
                                          const current = answers[q.id] || ''
                                          const selected = current.split(',').filter(Boolean)
                                          const newSelected = selected.includes(opt)
                                            ? selected.filter(s => s !== opt)
                                            : [...selected, opt]
                                          setAnswers({ ...answers, [q.id]: newSelected.join(',') })
                                        } else {
                                          setAnswers({ ...answers, [q.id]: opt })
                                        }
                                      }}
                                      className={`px-3 py-1 rounded text-sm transition-colors ${
                                        (answers[q.id] || '').split(',').includes(opt)
                                          ? 'bg-cyan-600 text-white'
                                          : 'bg-slate-600 text-gray-300 hover:bg-slate-500'
                                      }`}
                                    >
                                      {opt}
                                    </button>
                                  ))}
                                </div>
                              ) : (
                                <input
                                  type="text"
                                  value={answers[q.id] || ''}
                                  onChange={(e) => setAnswers({ ...answers, [q.id]: e.target.value })}
                                  placeholder={q.placeholder || '請輸入'}
                                  className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-white text-sm"
                                />
                              )}
                            </div>
                          ))}

                          {/* Submit */}
                          <div className="flex justify-end gap-2 mt-4 pt-4 border-t border-slate-600">
                            <button
                              onClick={() => {
                                setSelectedTodo(null)
                                setAnswers({})
                              }}
                              className="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded text-sm"
                            >
                              取消
                            </button>
                            <button
                              onClick={() => handleQuestionnaireSubmit(todo)}
                              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded text-sm"
                            >
                              提交回覆
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Other types - show payload info */}
                      {todo.type !== 'questionnaire' && (
                        <div>
                          <pre className="text-sm text-gray-400 whitespace-pre-wrap">
                            {JSON.stringify(todo.payload, null, 2)}
                          </pre>
                          <div className="flex justify-end gap-2 mt-4">
                            {todo.actions.map((action) => (
                              <button
                                key={action.id}
                                onClick={() => handleRespond(todo.id, action.id)}
                                className={`px-4 py-2 rounded text-sm transition-colors ${
                                  action.style === 'primary'
                                    ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                                    : action.style === 'danger'
                                    ? 'bg-red-600 hover:bg-red-500 text-white'
                                    : 'bg-slate-600 hover:bg-slate-500 text-gray-200'
                                }`}
                              >
                                {action.label}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* === INPUT VIEW === */}
      {activeView === 'input' && (
        <div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="輸入商機、任務或問題...&#10;&#10;例如：今天跟老王吃飯，他介紹了 ABC 公司的 CTO，他們系統效能有問題，想下週約個會議聊聊。"
            className="w-full h-32 bg-slate-700 border border-slate-600 rounded-lg p-4 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-cyan-500"
            disabled={inputLoading}
          />
          <div className="flex justify-end mt-2">
            <button
              onClick={handleInputSubmit}
              disabled={inputLoading || !input.trim()}
              className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
            >
              {inputLoading ? '處理中...' : '送出'}
            </button>
          </div>

          {/* Empty State */}
          <div className="text-center text-gray-500 py-8 mt-4">
            <div className="text-4xl mb-2">💬</div>
            <div>輸入商機、任務或問題，系統會自動分析並建議下一步</div>
          </div>
        </div>
      )}
    </div>
  )
}
