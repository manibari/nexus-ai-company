import React, { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'

interface KnowledgeCard {
  id: string
  title: string
  content: string
  type: string
  summary: string | null
  category: string | null
  tags: string[]
  metadata: Record<string, unknown>
  status: string
  created_by: string | null
  created_at: string
  updated_at: string
  usage_count: number
}

interface Statistics {
  total: number
  published: number
  by_type: Record<string, number>
  by_status: Record<string, number>
  top_used: { id: string; title: string; usage_count: number }[]
  recent: { id: string; title: string; created_at: string }[]
}

interface KnowledgeBaseProps {
  apiUrl: string
}

const TYPE_ICONS: Record<string, string> = {
  case: '📁',
  project: '📊',
  document: '📄',
  template: '📋',
  procedure: '📝',
  insight: '💡',
  lesson: '🎓',
}

const TYPE_COLORS: Record<string, string> = {
  case: 'bg-blue-500',
  project: 'bg-purple-500',
  document: 'bg-gray-500',
  template: 'bg-green-500',
  procedure: 'bg-yellow-500',
  insight: 'bg-cyan-500',
  lesson: 'bg-orange-500',
}

export default function KnowledgeBase({ apiUrl }: KnowledgeBaseProps) {
  const [cards, setCards] = useState<KnowledgeCard[]>([])
  const [selectedCard, setSelectedCard] = useState<KnowledgeCard | null>(null)
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [tags, setTags] = useState<Record<string, number>>({})
  const [categories, setCategories] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('')
  const [filterCategory, setFilterCategory] = useState<string>('')
  const [filterTag, setFilterTag] = useState<string>('')

  // Create form
  const [newCard, setNewCard] = useState({
    title: '',
    content: '',
    type: 'document',
    summary: '',
    category: '',
    tags: '',
  })

  const fetchCards = async () => {
    try {
      let url = `${apiUrl}/api/v1/knowledge`
      const params = new URLSearchParams()

      if (searchQuery) {
        url = `${apiUrl}/api/v1/knowledge/search`
        params.append('q', searchQuery)
      }
      if (filterType) params.append('type', filterType)
      if (filterCategory) params.append('category', filterCategory)
      if (filterTag) params.append('tag', filterTag)

      const queryString = params.toString()
      if (queryString) url += `?${queryString}`

      const response = await fetch(url)
      if (response.ok) {
        setCards(await response.json())
      }
    } catch (err) {
      setError('Failed to fetch knowledge cards')
    }
  }

  const fetchMeta = async () => {
    try {
      const [tagsRes, catsRes, statsRes] = await Promise.all([
        fetch(`${apiUrl}/api/v1/knowledge/tags`),
        fetch(`${apiUrl}/api/v1/knowledge/categories`),
        fetch(`${apiUrl}/api/v1/knowledge/statistics`),
      ])

      if (tagsRes.ok) setTags(await tagsRes.json())
      if (catsRes.ok) setCategories(await catsRes.json())
      if (statsRes.ok) setStatistics(await statsRes.json())
    } catch (err) {
      console.error('Failed to fetch metadata:', err)
    }
  }

  const fetchCardDetail = async (id: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/knowledge/${id}`)
      if (response.ok) {
        setSelectedCard(await response.json())
      }
    } catch (err) {
      setError('Failed to fetch card detail')
    }
  }

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true)
      await Promise.all([fetchCards(), fetchMeta()])
      setLoading(false)
    }
    fetchAll()
  }, [apiUrl])

  useEffect(() => {
    fetchCards()
  }, [searchQuery, filterType, filterCategory, filterTag])

  const handleCreate = async () => {
    setActionLoading('create')
    try {
      const response = await fetch(`${apiUrl}/api/v1/knowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newCard,
          tags: newCard.tags.split(',').map(t => t.trim()).filter(t => t),
        }),
      })
      if (response.ok) {
        setShowCreateForm(false)
        setNewCard({
          title: '',
          content: '',
          type: 'document',
          summary: '',
          category: '',
          tags: '',
        })
        await fetchCards()
        await fetchMeta()
      }
    } catch (err) {
      setError('Failed to create knowledge card')
    } finally {
      setActionLoading(null)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Archive this knowledge card?')) return

    setActionLoading(id)
    try {
      const response = await fetch(`${apiUrl}/api/v1/knowledge/${id}`, {
        method: 'DELETE',
      })
      if (response.ok) {
        setSelectedCard(null)
        await fetchCards()
        await fetchMeta()
      }
    } catch (err) {
      setError('Failed to archive card')
    } finally {
      setActionLoading(null)
    }
  }

  const clearFilters = () => {
    setSearchQuery('')
    setFilterType('')
    setFilterCategory('')
    setFilterTag('')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl text-gray-400">Loading Knowledge Base...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-800 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-cyan-300 flex items-center gap-2">
              <span>📚</span> Knowledge Base
            </h2>
            <p className="text-sm text-gray-400">
              {statistics?.published || 0} published cards | {cards.length} shown
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { fetchCards(); fetchMeta() }}
              className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
            >
              🔄 Refresh
            </button>
            <button
              onClick={() => setShowCreateForm(true)}
              className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm"
            >
              + New Card
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-400 text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-300">×</button>
          </div>
        )}

        {/* Search & Filters */}
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-64">
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search knowledge..."
              className="w-full px-4 py-2 bg-slate-700 rounded-lg text-white placeholder-gray-400"
            />
          </div>

          <select
            value={filterType}
            onChange={e => setFilterType(e.target.value)}
            className="px-3 py-2 bg-slate-700 rounded-lg text-white"
          >
            <option value="">All Types</option>
            <option value="case">Case</option>
            <option value="project">Project</option>
            <option value="document">Document</option>
            <option value="template">Template</option>
            <option value="procedure">Procedure</option>
            <option value="insight">Insight</option>
            <option value="lesson">Lesson</option>
          </select>

          <select
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
            className="px-3 py-2 bg-slate-700 rounded-lg text-white"
          >
            <option value="">All Categories</option>
            {Object.keys(categories).map(cat => (
              <option key={cat} value={cat}>{cat} ({categories[cat]})</option>
            ))}
          </select>

          {(searchQuery || filterType || filterCategory || filterTag) && (
            <button
              onClick={clearFilters}
              className="px-3 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-sm"
            >
              Clear Filters
            </button>
          )}
        </div>

        {/* Tag Cloud */}
        {Object.keys(tags).length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(tags).slice(0, 15).map(([tag, count]) => (
              <button
                key={tag}
                onClick={() => setFilterTag(filterTag === tag ? '' : tag)}
                className={`px-2 py-1 rounded text-xs ${
                  filterTag === tag
                    ? 'bg-cyan-600 text-white'
                    : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                }`}
              >
                #{tag} <span className="text-gray-500">({count})</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Card List */}
        <div className="col-span-2 space-y-3">
          {cards.length === 0 ? (
            <div className="bg-slate-800 rounded-lg p-8 text-center text-gray-400">
              <p className="text-4xl mb-2">📭</p>
              <p>No knowledge cards found</p>
              {(searchQuery || filterType || filterCategory || filterTag) && (
                <button
                  onClick={clearFilters}
                  className="mt-2 text-cyan-400 hover:underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            cards.map(card => (
              <div
                key={card.id}
                onClick={() => fetchCardDetail(card.id)}
                className={`bg-slate-800 rounded-lg p-4 cursor-pointer hover:bg-slate-700 transition-colors ${
                  selectedCard?.id === card.id ? 'ring-2 ring-cyan-500' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs ${TYPE_COLORS[card.type]}`}>
                        {TYPE_ICONS[card.type]} {card.type}
                      </span>
                      {card.category && (
                        <span className="text-xs text-gray-400">{card.category}</span>
                      )}
                    </div>
                    <h3 className="font-medium text-white">{card.title}</h3>
                    {card.summary && (
                      <p className="text-sm text-gray-400 mt-1 line-clamp-2">{card.summary}</p>
                    )}
                    {card.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {card.tags.slice(0, 5).map(tag => (
                          <span key={tag} className="text-xs text-cyan-400">#{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="text-right text-xs text-gray-500">
                    <div>👁 {card.usage_count}</div>
                    <div>{new Date(card.created_at).toLocaleDateString()}</div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Detail Panel / Statistics */}
        <div className="col-span-1">
          {selectedCard ? (
            <div className="bg-slate-800 rounded-lg p-4 sticky top-4">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span className={`px-2 py-0.5 rounded text-xs ${TYPE_COLORS[selectedCard.type]}`}>
                    {TYPE_ICONS[selectedCard.type]} {selectedCard.type}
                  </span>
                  <h3 className="font-bold text-white mt-2">{selectedCard.title}</h3>
                </div>
                <button
                  onClick={() => setSelectedCard(null)}
                  className="text-gray-400 hover:text-white"
                >
                  ×
                </button>
              </div>

              {/* Metadata */}
              <div className="text-xs text-gray-400 mb-4 space-y-1">
                {selectedCard.category && <div>Category: {selectedCard.category}</div>}
                <div>Views: {selectedCard.usage_count}</div>
                <div>Created: {new Date(selectedCard.created_at).toLocaleDateString()}</div>
                {selectedCard.created_by && <div>By: {selectedCard.created_by}</div>}
              </div>

              {/* Tags */}
              {selectedCard.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-4">
                  {selectedCard.tags.map(tag => (
                    <span key={tag} className="px-2 py-0.5 bg-slate-700 rounded text-xs text-cyan-400">
                      #{tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Content */}
              <div className="prose prose-invert prose-sm max-w-none bg-slate-700 rounded p-3 max-h-96 overflow-y-auto">
                <ReactMarkdown>{selectedCard.content}</ReactMarkdown>
              </div>

              {/* Actions */}
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => handleDelete(selectedCard.id)}
                  disabled={actionLoading === selectedCard.id}
                  className="px-3 py-1.5 bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded text-sm"
                >
                  Archive
                </button>
              </div>
            </div>
          ) : (
            /* Statistics Panel */
            statistics && (
              <div className="bg-slate-800 rounded-lg p-4 sticky top-4">
                <h3 className="font-bold text-white mb-4">📊 Statistics</h3>

                <div className="space-y-4">
                  {/* By Type */}
                  <div>
                    <h4 className="text-sm text-gray-400 mb-2">By Type</h4>
                    <div className="space-y-1">
                      {Object.entries(statistics.by_type).map(([type, count]) => (
                        <div key={type} className="flex items-center justify-between text-sm">
                          <span className="text-gray-300">
                            {TYPE_ICONS[type]} {type}
                          </span>
                          <span className="text-white">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Top Used */}
                  {statistics.top_used.length > 0 && (
                    <div>
                      <h4 className="text-sm text-gray-400 mb-2">Most Viewed</h4>
                      <div className="space-y-1">
                        {statistics.top_used.map(card => (
                          <div
                            key={card.id}
                            onClick={() => fetchCardDetail(card.id)}
                            className="flex items-center justify-between text-sm cursor-pointer hover:text-cyan-400"
                          >
                            <span className="text-gray-300 truncate flex-1">{card.title}</span>
                            <span className="text-gray-500 ml-2">👁 {card.usage_count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recent */}
                  {statistics.recent.length > 0 && (
                    <div>
                      <h4 className="text-sm text-gray-400 mb-2">Recently Added</h4>
                      <div className="space-y-1">
                        {statistics.recent.map(card => (
                          <div
                            key={card.id}
                            onClick={() => fetchCardDetail(card.id)}
                            className="text-sm cursor-pointer hover:text-cyan-400"
                          >
                            <span className="text-gray-300 truncate block">{card.title}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white mb-4">Create Knowledge Card</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Title *</label>
                <input
                  type="text"
                  value={newCard.title}
                  onChange={e => setNewCard({ ...newCard, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                  placeholder="Knowledge card title"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Type</label>
                  <select
                    value={newCard.type}
                    onChange={e => setNewCard({ ...newCard, type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                  >
                    <option value="case">Case</option>
                    <option value="project">Project</option>
                    <option value="document">Document</option>
                    <option value="template">Template</option>
                    <option value="procedure">Procedure</option>
                    <option value="insight">Insight</option>
                    <option value="lesson">Lesson</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">Category</label>
                  <input
                    type="text"
                    value={newCard.category}
                    onChange={e => setNewCard({ ...newCard, category: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                    placeholder="e.g., Sales, Engineering"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Summary</label>
                <input
                  type="text"
                  value={newCard.summary}
                  onChange={e => setNewCard({ ...newCard, summary: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                  placeholder="Brief summary (shown in list)"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Content * (Markdown supported)</label>
                <textarea
                  value={newCard.content}
                  onChange={e => setNewCard({ ...newCard, content: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 rounded text-white h-48 font-mono text-sm"
                  placeholder="# Heading&#10;&#10;Your content here...&#10;&#10;- List item&#10;- Another item"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={newCard.tags}
                  onChange={e => setNewCard({ ...newCard, tags: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                  placeholder="sales, meddic, best-practice"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!newCard.title || !newCard.content || actionLoading === 'create'}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 rounded"
              >
                {actionLoading === 'create' ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
