import React, { useEffect, useState } from 'react'

// === Types ===

interface ProductSummary {
  id: string
  title: string
  type: string
  priority: string
  stage: string
  assignee: string | null
  days_in_stage: number
  qa_passed: boolean
  version: string | null
}

interface ProductDetail extends ProductSummary {
  description: string
  spec_doc: string | null
  acceptance_criteria: string[]
  qa_results: { test_name: string; passed: boolean; details: string | null; timestamp: string }[]
  qa_score: number
  uat_feedback: { feedback: string; approved: boolean | null; timestamp: string }[]
  uat_approved: boolean
  estimated_hours: number | null
  actual_hours: number | null
  blocked_reason: string | null
  notes: string | null
  tags: string[]
  created_at: string
  started_at: string | null
  completed_at: string | null
}

interface Dashboard {
  total: number
  by_stage: Record<string, number>
  by_type: Record<string, number>
  by_priority: Record<string, number>
  blocked_count: number
  stale_count: number
}

// Catalog types
interface CatalogProduct {
  id: string
  name: string
  description: string
  status: 'production' | 'beta' | 'mvp' | 'development' | 'deprecated'
  version: string
  release_date: string | null
  links: {
    demo?: string
    docs?: string
    api?: string
    source?: string
  }
  features: string[]
  tech_stack: {
    frontend?: string
    backend?: string
    database?: string
  }
  full_content?: string
}

interface ProductBoardProps {
  apiUrl: string
}

const STAGES = [
  { key: 'backlog', label: 'Backlog', icon: '📋', color: 'bg-slate-600' },
  { key: 'spec_ready', label: 'Spec Ready', icon: '📝', color: 'bg-blue-600' },
  { key: 'in_progress', label: 'In Progress', icon: '🔨', color: 'bg-yellow-600' },
  { key: 'qa_testing', label: 'QA Testing', icon: '🔍', color: 'bg-purple-600' },
  { key: 'uat', label: 'UAT', icon: '👤', color: 'bg-orange-600' },
  { key: 'done', label: 'Done', icon: '✅', color: 'bg-green-600' },
]

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-gray-500',
}

const TYPE_ICONS: Record<string, string> = {
  feature: '✨',
  enhancement: '📈',
  bug_fix: '🐛',
  tech_debt: '🔧',
  experiment: '🧪',
}

const STATUS_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  production: { icon: '🟢', label: 'Production', color: 'bg-green-600' },
  beta: { icon: '🟡', label: 'Beta', color: 'bg-yellow-600' },
  mvp: { icon: '🔵', label: 'MVP', color: 'bg-blue-600' },
  development: { icon: '🔧', label: 'Development', color: 'bg-slate-600' },
  deprecated: { icon: '⚪', label: 'Deprecated', color: 'bg-gray-600' },
}

export default function ProductBoard({ apiUrl }: ProductBoardProps) {
  // View state
  const [activeView, setActiveView] = useState<'catalog' | 'pipeline'>('catalog')

  // Pipeline state
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [selectedProduct, setSelectedProduct] = useState<ProductDetail | null>(null)
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Catalog state
  const [catalogProducts, setCatalogProducts] = useState<CatalogProduct[]>([])
  const [selectedCatalogProduct, setSelectedCatalogProduct] = useState<CatalogProduct | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(true)

  // Create form state
  const [newProduct, setNewProduct] = useState({
    title: '',
    description: '',
    type: 'feature',
    priority: 'medium',
    target_release: '',
    spec_doc: '',
    acceptance_criteria: '',
  })

  // Fetch catalog products
  const fetchCatalog = async () => {
    setCatalogLoading(true)
    try {
      const response = await fetch(`${apiUrl}/api/v1/catalog`)
      if (response.ok) {
        setCatalogProducts(await response.json())
      }
    } catch (err) {
      console.error('Failed to fetch catalog:', err)
    } finally {
      setCatalogLoading(false)
    }
  }

  const fetchCatalogDetail = async (id: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/catalog/${id}`)
      if (response.ok) {
        setSelectedCatalogProduct(await response.json())
      }
    } catch (err) {
      console.error('Failed to fetch catalog detail:', err)
    }
  }

  const fetchProducts = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/product`)
      if (response.ok) {
        setProducts(await response.json())
      }
    } catch (err) {
      setError('Failed to fetch products')
    }
  }

  const fetchDashboard = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/product/dashboard`)
      if (response.ok) {
        setDashboard(await response.json())
      }
    } catch (err) {
      console.error('Failed to fetch dashboard:', err)
    }
  }

  const fetchProductDetail = async (id: string) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/product/${id}`)
      if (response.ok) {
        setSelectedProduct(await response.json())
      }
    } catch (err) {
      setError('Failed to fetch product detail')
    }
  }

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true)
      await Promise.all([fetchProducts(), fetchDashboard(), fetchCatalog()])
      setLoading(false)
    }
    fetchAll()
    const interval = setInterval(fetchAll, 30000)
    return () => clearInterval(interval)
  }, [apiUrl])

  const handleCreate = async () => {
    setActionLoading('create')
    try {
      const response = await fetch(`${apiUrl}/api/v1/product`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newProduct,
          acceptance_criteria: newProduct.acceptance_criteria
            .split('\n')
            .filter(c => c.trim()),
        }),
      })
      if (response.ok) {
        setShowCreateForm(false)
        setNewProduct({
          title: '',
          description: '',
          type: 'feature',
          priority: 'medium',
          target_release: '',
          spec_doc: '',
          acceptance_criteria: '',
        })
        await fetchProducts()
        await fetchDashboard()
      }
    } catch (err) {
      setError('Failed to create product')
    } finally {
      setActionLoading(null)
    }
  }

  const handleAdvance = async (id: string) => {
    setActionLoading(id)
    try {
      const response = await fetch(`${apiUrl}/api/v1/product/${id}/advance`, {
        method: 'POST',
      })
      if (response.ok) {
        await fetchProducts()
        await fetchDashboard()
        if (selectedProduct?.id === id) {
          await fetchProductDetail(id)
        }
      } else {
        const data = await response.json()
        setError(data.detail?.message || 'Cannot advance')
      }
    } catch (err) {
      setError('Failed to advance stage')
    } finally {
      setActionLoading(null)
    }
  }

  const getProductsByStage = (stage: string) => {
    if (stage === 'blocked') {
      return products.filter(p => p.stage === 'blocked')
    }
    return products.filter(p => p.stage === stage)
  }

  const getProductsByStatus = (status: string) => {
    return catalogProducts.filter(p => p.status === status)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl text-gray-400">Loading Product Board...</div>
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
              <span>🏭</span> Product Board
            </h2>
            <p className="text-sm text-gray-400">
              {catalogProducts.length} products | {dashboard?.total || 0} in pipeline
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { fetchProducts(); fetchDashboard(); fetchCatalog() }}
              className="px-3 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm"
            >
              🔄 Refresh
            </button>
            {activeView === 'pipeline' && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm"
              >
                + New Item
              </button>
            )}
          </div>
        </div>

        {/* View Switcher */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveView('catalog')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              activeView === 'catalog'
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
            }`}
          >
            📦 Catalog
            <span className="px-2 py-0.5 bg-black/30 rounded text-xs">
              {catalogProducts.length}
            </span>
          </button>
          <button
            onClick={() => setActiveView('pipeline')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
              activeView === 'pipeline'
                ? 'bg-cyan-600 text-white'
                : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
            }`}
          >
            🔄 Pipeline
            <span className="px-2 py-0.5 bg-black/30 rounded text-xs">
              {dashboard?.total || 0}
            </span>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded-lg text-red-400 text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-300">×</button>
          </div>
        )}

        {/* Catalog View */}
        {activeView === 'catalog' && (
          <div className="space-y-6">
            {catalogLoading ? (
              <div className="text-center text-gray-400 py-8">Loading catalog...</div>
            ) : catalogProducts.length === 0 ? (
              <div className="text-center text-gray-400 py-8">
                No products yet. Add products to the <code>products/</code> directory.
              </div>
            ) : (
              Object.entries(STATUS_CONFIG).map(([status, config]) => {
                const statusProducts = getProductsByStatus(status)
                if (statusProducts.length === 0) return null

                return (
                  <div key={status} className="space-y-3">
                    <h3 className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-sm font-medium ${config.color}`}>
                      {config.icon} {config.label}
                      <span className="bg-black/30 px-2 py-0.5 rounded text-xs">
                        {statusProducts.length}
                      </span>
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {statusProducts.map(product => (
                        <div
                          key={product.id}
                          onClick={() => fetchCatalogDetail(product.id)}
                          className="bg-slate-900 rounded-lg p-4 cursor-pointer hover:bg-slate-800 transition-colors border border-slate-700 hover:border-cyan-500"
                        >
                          {/* Header */}
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="font-bold text-white">{product.name}</h4>
                            <span className="text-xs text-gray-400">{product.version}</span>
                          </div>

                          {/* Description */}
                          <p className="text-sm text-gray-400 mb-3 line-clamp-2">
                            {product.description}
                          </p>

                          {/* Features */}
                          {product.features.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-3">
                              {product.features.slice(0, 3).map((f, i) => (
                                <span key={i} className="text-xs bg-slate-700 text-gray-300 px-2 py-0.5 rounded">
                                  {f.length > 15 ? f.substring(0, 15) + '...' : f}
                                </span>
                              ))}
                              {product.features.length > 3 && (
                                <span className="text-xs text-gray-500">+{product.features.length - 3}</span>
                              )}
                            </div>
                          )}

                          {/* Links */}
                          <div className="flex gap-2 mt-3 pt-3 border-t border-slate-700">
                            {product.links.demo && (
                              <a
                                href={product.links.demo}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={e => e.stopPropagation()}
                                className="text-xs bg-cyan-600 hover:bg-cyan-500 px-2 py-1 rounded"
                              >
                                🌐 Demo
                              </a>
                            )}
                            {product.links.api && (
                              <a
                                href={product.links.api}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={e => e.stopPropagation()}
                                className="text-xs bg-purple-600 hover:bg-purple-500 px-2 py-1 rounded"
                              >
                                📡 API
                              </a>
                            )}
                            {product.links.source && (
                              <a
                                href={product.links.source}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={e => e.stopPropagation()}
                                className="text-xs bg-slate-600 hover:bg-slate-500 px-2 py-1 rounded"
                              >
                                💻 Code
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}

        {/* Pipeline View (Kanban) */}
        {activeView === 'pipeline' && (
          <div className="flex gap-4 overflow-x-auto pb-4">
            {STAGES.map(stage => {
              const stageProducts = getProductsByStage(stage.key)
              return (
                <div
                  key={stage.key}
                  className="flex-shrink-0 w-56 bg-slate-900 rounded-lg"
                >
                  {/* Column Header */}
                  <div className={`${stage.color} rounded-t-lg px-3 py-2 flex items-center justify-between`}>
                    <span className="font-medium text-sm">
                      {stage.icon} {stage.label}
                    </span>
                    <span className="bg-black/30 px-2 py-0.5 rounded text-xs">
                      {stageProducts.length}
                    </span>
                  </div>

                  {/* Cards */}
                  <div className="p-2 space-y-2 max-h-96 overflow-y-auto">
                    {stageProducts.length === 0 ? (
                      <div className="text-center text-gray-500 text-xs py-4">
                        No items
                      </div>
                    ) : (
                      stageProducts.map(product => (
                        <div
                          key={product.id}
                          onClick={() => fetchProductDetail(product.id)}
                          className={`bg-slate-800 rounded-lg p-3 cursor-pointer hover:bg-slate-700 transition-colors ${
                            selectedProduct?.id === product.id ? 'ring-2 ring-cyan-500' : ''
                          }`}
                        >
                          {/* Title & Type */}
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <span className="text-sm font-medium line-clamp-2">
                              {TYPE_ICONS[product.type]} {product.title}
                            </span>
                          </div>

                          {/* Priority & Assignee */}
                          <div className="flex items-center justify-between text-xs">
                            <span className={`px-1.5 py-0.5 rounded ${PRIORITY_COLORS[product.priority]}`}>
                              {product.priority}
                            </span>
                            {product.assignee && (
                              <span className="text-gray-400">{product.assignee}</span>
                            )}
                          </div>

                          {/* Days in stage & QA status */}
                          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                            <span>{product.days_in_stage}d</span>
                            {stage.key === 'qa_testing' && (
                              <span className={product.qa_passed ? 'text-green-400' : 'text-yellow-400'}>
                                {product.qa_passed ? '✓ QA Passed' : '⏳ Testing'}
                              </span>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )
            })}

            {/* Blocked Column */}
            {dashboard && dashboard.blocked_count > 0 && (
              <div className="flex-shrink-0 w-56 bg-slate-900 rounded-lg">
                <div className="bg-red-600 rounded-t-lg px-3 py-2 flex items-center justify-between">
                  <span className="font-medium text-sm">🚫 Blocked</span>
                  <span className="bg-black/30 px-2 py-0.5 rounded text-xs">
                    {dashboard.blocked_count}
                  </span>
                </div>
                <div className="p-2 space-y-2 max-h-96 overflow-y-auto">
                  {getProductsByStage('blocked').map(product => (
                    <div
                      key={product.id}
                      onClick={() => fetchProductDetail(product.id)}
                      className="bg-slate-800 rounded-lg p-3 cursor-pointer hover:bg-slate-700 border-l-2 border-red-500"
                    >
                      <div className="text-sm font-medium line-clamp-2">
                        {TYPE_ICONS[product.type]} {product.title}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Pipeline Detail Panel */}
      {activeView === 'pipeline' && selectedProduct && (
        <div className="bg-slate-800 rounded-lg p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-bold text-white">
                {TYPE_ICONS[selectedProduct.type]} {selectedProduct.title}
              </h3>
              <p className="text-sm text-gray-400">{selectedProduct.id}</p>
            </div>
            <button
              onClick={() => setSelectedProduct(null)}
              className="text-gray-400 hover:text-white text-xl"
            >
              ×
            </button>
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Left: Info */}
            <div className="space-y-4">
              <div className="flex items-center gap-4 text-sm">
                <span className={`px-2 py-1 rounded ${PRIORITY_COLORS[selectedProduct.priority]}`}>
                  {selectedProduct.priority}
                </span>
                <span className="text-gray-400">
                  Stage: <span className="text-white">{selectedProduct.stage}</span>
                </span>
                {selectedProduct.assignee && (
                  <span className="text-gray-400">
                    Assignee: <span className="text-cyan-400">{selectedProduct.assignee}</span>
                  </span>
                )}
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-1">Description</h4>
                <p className="text-sm text-white bg-slate-700 p-3 rounded">
                  {selectedProduct.description}
                </p>
              </div>

              {selectedProduct.acceptance_criteria.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-1">Acceptance Criteria</h4>
                  <ul className="space-y-1">
                    {selectedProduct.acceptance_criteria.map((c, i) => (
                      <li key={i} className="text-sm text-white flex items-start gap-2">
                        <span className="text-gray-500">•</span> {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Right: QA & Actions */}
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">
                  QA Results ({selectedProduct.qa_score.toFixed(0)}% pass rate)
                </h4>
                {selectedProduct.qa_results.length === 0 ? (
                  <p className="text-sm text-gray-500">No QA tests yet</p>
                ) : (
                  <div className="space-y-1">
                    {selectedProduct.qa_results.map((r, i) => (
                      <div
                        key={i}
                        className={`text-sm p-2 rounded flex items-center justify-between ${
                          r.passed ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}
                      >
                        <span>{r.passed ? '✓' : '✗'} {r.test_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-slate-700">
                <button
                  onClick={() => handleAdvance(selectedProduct.id)}
                  disabled={actionLoading === selectedProduct.id || selectedProduct.stage === 'done'}
                  className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-600 disabled:cursor-not-allowed rounded text-sm"
                >
                  {actionLoading === selectedProduct.id ? '...' : '⏭️ Advance Stage'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Catalog Detail Modal */}
      {selectedCatalogProduct && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 rounded-lg w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  {STATUS_CONFIG[selectedCatalogProduct.status]?.icon} {selectedCatalogProduct.name}
                </h3>
                <p className="text-sm text-gray-400">
                  {selectedCatalogProduct.version} • {STATUS_CONFIG[selectedCatalogProduct.status]?.label}
                </p>
              </div>
              <button
                onClick={() => setSelectedCatalogProduct(null)}
                className="text-gray-400 hover:text-white text-2xl"
              >
                ×
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Quick Links */}
              <div className="flex gap-2 flex-wrap">
                {selectedCatalogProduct.links.demo && (
                  <a
                    href={selectedCatalogProduct.links.demo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg text-sm flex items-center gap-2"
                  >
                    🌐 Open Demo
                  </a>
                )}
                {selectedCatalogProduct.links.api && (
                  <a
                    href={selectedCatalogProduct.links.api}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm flex items-center gap-2"
                  >
                    📡 API Docs
                  </a>
                )}
                {selectedCatalogProduct.links.source && (
                  <a
                    href={selectedCatalogProduct.links.source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-sm flex items-center gap-2"
                  >
                    💻 Source Code
                  </a>
                )}
              </div>

              {/* Description */}
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">Description</h4>
                <p className="text-white bg-slate-700 p-3 rounded">{selectedCatalogProduct.description}</p>
              </div>

              {/* Features */}
              {selectedCatalogProduct.features.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Features</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedCatalogProduct.features.map((f, i) => (
                      <span key={i} className="bg-green-500/20 text-green-400 px-3 py-1 rounded-lg text-sm">
                        ✓ {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Tech Stack */}
              {Object.keys(selectedCatalogProduct.tech_stack).length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Tech Stack</h4>
                  <div className="bg-slate-700 rounded-lg p-3 space-y-2">
                    {selectedCatalogProduct.tech_stack.frontend && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Frontend</span>
                        <span className="text-white">{selectedCatalogProduct.tech_stack.frontend}</span>
                      </div>
                    )}
                    {selectedCatalogProduct.tech_stack.backend && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Backend</span>
                        <span className="text-white">{selectedCatalogProduct.tech_stack.backend}</span>
                      </div>
                    )}
                    {selectedCatalogProduct.tech_stack.database && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Database</span>
                        <span className="text-white">{selectedCatalogProduct.tech_stack.database}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Full Content */}
              {selectedCatalogProduct.full_content && (
                <div>
                  <h4 className="text-sm font-medium text-gray-400 mb-2">Full Documentation</h4>
                  <pre className="bg-slate-900 p-4 rounded-lg text-sm text-gray-300 overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto">
                    {selectedCatalogProduct.full_content}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white mb-4">Create New Product Item</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Title *</label>
                <input
                  type="text"
                  value={newProduct.title}
                  onChange={e => setNewProduct({ ...newProduct, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                  placeholder="Feature title"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Description *</label>
                <textarea
                  value={newProduct.description}
                  onChange={e => setNewProduct({ ...newProduct, description: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 rounded text-white h-24"
                  placeholder="What is this feature about?"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Type</label>
                  <select
                    value={newProduct.type}
                    onChange={e => setNewProduct({ ...newProduct, type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                  >
                    <option value="feature">Feature</option>
                    <option value="enhancement">Enhancement</option>
                    <option value="bug_fix">Bug Fix</option>
                    <option value="tech_debt">Tech Debt</option>
                    <option value="experiment">Experiment</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">Priority</label>
                  <select
                    value={newProduct.priority}
                    onChange={e => setNewProduct({ ...newProduct, priority: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-700 rounded text-white"
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">Acceptance Criteria (one per line)</label>
                <textarea
                  value={newProduct.acceptance_criteria}
                  onChange={e => setNewProduct({ ...newProduct, acceptance_criteria: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 rounded text-white h-24"
                  placeholder="User can login with email&#10;System sends confirmation email&#10;..."
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
                disabled={!newProduct.title || !newProduct.description || actionLoading === 'create'}
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
