import React, { useCallback, useEffect, useState } from 'react'
import { useAgentWebSocket } from '../hooks/useAgentWebSocket'

interface Agent {
  id: string
  name: string
  role: string
  status: string
  current_task?: string
}

interface Room {
  id: string
  name: string
  x: number
  y: number
  width: number
  height: number
  color: string
  icon: string
  agents: string[]
}

interface OfficeMapProps {
  apiUrl: string
}

const ROOMS: Room[] = [
  { id: 'ceo_office', name: 'CEO Office', x: 20, y: 20, width: 160, height: 110, color: '#1e3a5f', icon: '👔', agents: ['CEO'] },
  { id: 'reception', name: 'Reception', x: 200, y: 20, width: 140, height: 110, color: '#1e4d3a', icon: '🚪', agents: ['GATEKEEPER'] },
  { id: 'sales', name: 'Sales', x: 360, y: 20, width: 160, height: 110, color: '#4d1e3a', icon: '💼', agents: ['HUNTER'] },
  { id: 'war_room', name: 'War Room', x: 20, y: 150, width: 170, height: 120, color: '#3a1e4d', icon: '🎯', agents: ['ORCHESTRATOR'] },
  { id: 'dev_lab', name: 'Dev Lab', x: 210, y: 150, width: 150, height: 120, color: '#1e3a4d', icon: '💻', agents: ['DEVELOPER'] },
  { id: 'qa_station', name: 'QA Station', x: 380, y: 150, width: 140, height: 120, color: '#4d3a1e', icon: '🔍', agents: ['QA'] },
  { id: 'product', name: 'Product', x: 20, y: 290, width: 130, height: 100, color: '#2d4d1e', icon: '📋', agents: ['PM'] },
  { id: 'meeting', name: 'Meeting Room', x: 170, y: 290, width: 170, height: 100, color: '#1e2d4d', icon: '🤝', agents: [] },
  { id: 'break_room', name: 'Break Room', x: 360, y: 290, width: 160, height: 100, color: '#4d4d1e', icon: '☕', agents: [] },
]

// Agent character colors
const AGENT_COLORS: Record<string, { skin: string; shirt: string; hair: string }> = {
  CEO: { skin: '#fcd5b5', shirt: '#1e3a5f', hair: '#3a3a3a' },
  GATEKEEPER: { skin: '#fcd5b5', shirt: '#22c55e', hair: '#4a3728' },
  HUNTER: { skin: '#e8beac', shirt: '#f59e0b', hair: '#1a1a1a' },
  ORCHESTRATOR: { skin: '#fcd5b5', shirt: '#8b5cf6', hair: '#6b4423' },
  PM: { skin: '#e8beac', shirt: '#14b8a6', hair: '#2d2d2d' },
  DEVELOPER: { skin: '#d4a574', shirt: '#3b82f6', hair: '#1a1a1a' },
  QA: { skin: '#fcd5b5', shirt: '#ec4899', hair: '#8b4513' },
}

// 2.5D Character component
const Character = ({
  x, y, colors, status, isSelected, onClick, name, isWorking
}: {
  x: number
  y: number
  colors: { skin: string; shirt: string; hair: string }
  status: string
  isSelected: boolean
  onClick: () => void
  name: string
  isWorking: boolean
}) => {
  const statusColor = status === 'working' ? '#22c55e' :
                      status === 'idle' ? '#6b7280' :
                      status === 'blocked_internal' ? '#f59e0b' : '#ef4444'

  return (
    <g
      onClick={onClick}
      style={{ cursor: 'pointer' }}
      className={isWorking ? 'animate-bounce-subtle' : ''}
    >
      {/* Shadow */}
      <ellipse cx={x} cy={y + 38} rx="14" ry="5" fill="rgba(0,0,0,0.3)" />

      {/* Selection ring */}
      {isSelected && (
        <ellipse cx={x} cy={y + 38} rx="20" ry="7" fill="none" stroke="#22d3ee" strokeWidth="2" />
      )}

      {/* Legs */}
      <rect x={x - 6} y={y + 18} width="5" height="18" rx="2" fill="#1e293b" />
      <rect x={x + 1} y={y + 18} width="5" height="18" rx="2" fill="#1e293b" />

      {/* Body */}
      <rect x={x - 10} y={y} width="20" height="22" rx="4" fill={colors.shirt} />

      {/* Arms */}
      <rect x={x - 14} y={y + 2} width="5" height="14" rx="2" fill={colors.shirt} />
      <rect x={x + 9} y={y + 2} width="5" height="14" rx="2" fill={colors.shirt} />

      {/* Hands */}
      <circle cx={x - 12} cy={y + 18} r="3" fill={colors.skin} />
      <circle cx={x + 12} cy={y + 18} r="3" fill={colors.skin} />

      {/* Head */}
      <ellipse cx={x} cy={y - 8} rx="10" ry="12" fill={colors.skin} />

      {/* Hair */}
      <ellipse cx={x} cy={y - 16} rx="10" ry="6" fill={colors.hair} />
      <rect x={x - 10} y={y - 16} width="20" height="6" fill={colors.hair} />

      {/* Eyes */}
      <circle cx={x - 4} cy={y - 8} r="2" fill="#1a1a1a" />
      <circle cx={x + 4} cy={y - 8} r="2" fill="#1a1a1a" />
      <circle cx={x - 3} cy={y - 9} r="0.8" fill="white" />
      <circle cx={x + 5} cy={y - 9} r="0.8" fill="white" />

      {/* Mouth */}
      <path
        d={status === 'working' ? `M ${x-3} ${y-3} Q ${x} ${y-1} ${x+3} ${y-3}` : `M ${x-2} ${y-4} L ${x+2} ${y-4}`}
        stroke="#1a1a1a"
        strokeWidth="1"
        fill="none"
      />

      {/* Status indicator */}
      <circle cx={x + 12} cy={y - 18} r="5" fill={statusColor} stroke="#0f172a" strokeWidth="2" />

      {/* Working animation - floating icons */}
      {isWorking && (
        <>
          <text x={x - 18} y={y - 25} fontSize="10" className="animate-float">💭</text>
          <text x={x + 14} y={y - 28} fontSize="8" className="animate-float-delay">⚡</text>
        </>
      )}

      {/* Name tag */}
      <rect x={x - 22} y={y + 42} width="44" height="14" rx="3" fill="#0f172a" opacity="0.8" />
      <text x={x} y={y + 52} fill="#94a3b8" fontSize="8" textAnchor="middle" fontWeight="bold">
        {name}
      </text>
    </g>
  )
}

// Desk component
const Desk = ({ x, y, hasComputer = true }: { x: number; y: number; hasComputer?: boolean }) => (
  <g>
    {/* Desk surface */}
    <rect x={x} y={y} width="50" height="25" rx="3" fill="#5c4033" />
    <rect x={x + 2} y={y + 2} width="46" height="21" rx="2" fill="#8b6914" />

    {/* Desk legs */}
    <rect x={x + 5} y={y + 25} width="4" height="12" fill="#5c4033" />
    <rect x={x + 41} y={y + 25} width="4" height="12" fill="#5c4033" />

    {/* Computer */}
    {hasComputer && (
      <>
        <rect x={x + 15} y={y - 15} width="20" height="15" rx="2" fill="#1e293b" />
        <rect x={x + 17} y={y - 13} width="16" height="10" fill="#0ea5e9" opacity="0.8" />
        <rect x={x + 22} y={y} width="6" height="3" fill="#374151" />
      </>
    )}
  </g>
)

export default function OfficeMap({ apiUrl }: OfficeMapProps) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [hoveredRoom, setHoveredRoom] = useState<string | null>(null)

  const fetchAgents = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/agents`)
      if (response.ok) {
        setAgents(await response.json())
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err)
    }
  }, [apiUrl])

  // Initial fetch
  useEffect(() => { fetchAgents() }, [fetchAgents])

  // WebSocket: real-time agent status updates
  const handleWsMessage = useCallback((data: any) => {
    if (data.type === 'agent_status') {
      setAgents(prev => prev.map(a =>
        a.id === data.agent_id
          ? { ...a, status: data.status, current_task: data.current_task, name: data.name || a.name }
          : a
      ))
    }
  }, [])

  const { connected } = useAgentWebSocket({
    apiUrl,
    onMessage: handleWsMessage,
    onReconnect: fetchAgents,
  })

  const getAgentPosition = (agentId: string): { x: number; y: number } | null => {
    for (const room of ROOMS) {
      if (room.agents.includes(agentId)) {
        return { x: room.x + room.width / 2, y: room.y + 65 }
      }
    }
    return null
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <style>{`
        @keyframes bounce-subtle {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-3px); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0) rotate(-5deg); opacity: 1; }
          50% { transform: translateY(-8px) rotate(5deg); opacity: 0.7; }
        }
        .animate-bounce-subtle { animation: bounce-subtle 1s ease-in-out infinite; }
        .animate-float { animation: float 2s ease-in-out infinite; }
        .animate-float-delay { animation: float 2s ease-in-out 0.5s infinite; }
      `}</style>

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-cyan-300 flex items-center gap-2">
          🏢 Nexus AI Office
          <span className="text-sm font-normal text-gray-400">
            ({agents.filter(a => a.status === 'working').length}/{agents.length} working)
          </span>
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} title={connected ? 'Live' : 'Reconnecting...'} />
        </h2>
        <div className="flex gap-3 text-xs">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> Working</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-500" /> Idle</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500" /> Blocked</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> Waiting</span>
        </div>
      </div>

      <div className="relative bg-slate-900 rounded-lg overflow-hidden" style={{ height: '420px' }}>
        <svg width="100%" height="100%" viewBox="0 0 540 410" preserveAspectRatio="xMidYMid meet">
          {/* Floor */}
          <defs>
            <pattern id="floor-tiles" width="30" height="30" patternUnits="userSpaceOnUse">
              <rect width="30" height="30" fill="#1e293b" />
              <rect width="14" height="14" fill="#0f172a" />
              <rect x="15" y="15" width="14" height="14" fill="#0f172a" />
            </pattern>
          </defs>
          <rect width="540" height="410" fill="url(#floor-tiles)" />

          {/* Rooms */}
          {ROOMS.map((room) => (
            <g key={room.id} onMouseEnter={() => setHoveredRoom(room.id)} onMouseLeave={() => setHoveredRoom(null)}>
              <rect
                x={room.x} y={room.y} width={room.width} height={room.height} rx="6"
                fill={room.color} stroke={hoveredRoom === room.id ? '#22d3ee' : '#334155'}
                strokeWidth={hoveredRoom === room.id ? 2 : 1} opacity="0.85"
              />
              <text x={room.x + 12} y={room.y + 20} fontSize="16">{room.icon}</text>
              <text x={room.x + 32} y={room.y + 18} fill="#94a3b8" fontSize="10" fontWeight="bold">{room.name}</text>

              {/* Desks */}
              {room.agents.length > 0 && (
                <Desk x={room.x + room.width / 2 - 25} y={room.y + 30} />
              )}
            </g>
          ))}

          {/* Plants decoration */}
          <text x="175" y="145" fontSize="20">🪴</text>
          <text x="345" y="145" fontSize="20">🪴</text>
          <text x="155" y="285" fontSize="18">🌿</text>

          {/* Agents */}
          {agents.map((agent) => {
            const pos = getAgentPosition(agent.id)
            if (!pos) return null
            const colors = AGENT_COLORS[agent.id] || { skin: '#fcd5b5', shirt: '#6b7280', hair: '#4a3728' }

            return (
              <Character
                key={agent.id}
                x={pos.x}
                y={pos.y}
                colors={colors}
                status={agent.status}
                isSelected={selectedAgent?.id === agent.id}
                onClick={() => setSelectedAgent(selectedAgent?.id === agent.id ? null : agent)}
                name={agent.id}
                isWorking={agent.status === 'working'}
              />
            )
          })}
        </svg>

        {/* Agent detail panel */}
        {selectedAgent && (
          <div className="absolute top-4 right-4 bg-slate-800/95 border border-cyan-500 rounded-lg p-4 w-56 shadow-xl backdrop-blur">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="font-bold text-white">{selectedAgent.name}</div>
                <div className="text-xs text-cyan-400">{selectedAgent.id}</div>
              </div>
              <button onClick={() => setSelectedAgent(null)} className="text-gray-400 hover:text-white text-lg">×</button>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Role</span>
                <span className="text-white">{selectedAgent.role}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Status</span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  selectedAgent.status === 'working' ? 'bg-green-500/20 text-green-400' :
                  selectedAgent.status === 'idle' ? 'bg-gray-500/20 text-gray-400' :
                  'bg-yellow-500/20 text-yellow-400'
                }`}>{selectedAgent.status}</span>
              </div>
              {selectedAgent.current_task && (
                <div className="pt-2 border-t border-slate-700">
                  <div className="text-gray-400 text-xs">Current Task</div>
                  <div className="text-white text-xs mt-1">{selectedAgent.current_task}</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
