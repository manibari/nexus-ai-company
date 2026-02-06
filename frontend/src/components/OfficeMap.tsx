import React, { useEffect, useState } from 'react'

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
  agents: string[] // Agent IDs that belong here
}

interface OfficeMapProps {
  apiUrl: string
}

// Office layout configuration
const ROOMS: Room[] = [
  {
    id: 'ceo_office',
    name: 'CEO Office',
    x: 10,
    y: 10,
    width: 180,
    height: 120,
    color: '#1e3a5f',
    icon: '👔',
    agents: [],
  },
  {
    id: 'reception',
    name: 'Reception',
    x: 200,
    y: 10,
    width: 150,
    height: 120,
    color: '#1e4d3a',
    icon: '🚪',
    agents: ['GATEKEEPER'],
  },
  {
    id: 'sales',
    name: 'Sales',
    x: 360,
    y: 10,
    width: 180,
    height: 120,
    color: '#4d1e3a',
    icon: '💼',
    agents: ['HUNTER'],
  },
  {
    id: 'war_room',
    name: 'War Room',
    x: 10,
    y: 140,
    width: 200,
    height: 130,
    color: '#3a1e4d',
    icon: '🎯',
    agents: ['ORCHESTRATOR'],
  },
  {
    id: 'dev_lab',
    name: 'Dev Lab',
    x: 220,
    y: 140,
    width: 160,
    height: 130,
    color: '#1e3a4d',
    icon: '💻',
    agents: ['BUILDER'],
  },
  {
    id: 'qa_station',
    name: 'QA Station',
    x: 390,
    y: 140,
    width: 150,
    height: 130,
    color: '#4d3a1e',
    icon: '🔍',
    agents: ['INSPECTOR'],
  },
  {
    id: 'finance',
    name: 'Finance',
    x: 10,
    y: 280,
    width: 140,
    height: 100,
    color: '#2d4d1e',
    icon: '📊',
    agents: ['LEDGER'],
  },
  {
    id: 'meeting',
    name: 'Meeting Room',
    x: 160,
    y: 280,
    width: 180,
    height: 100,
    color: '#1e2d4d',
    icon: '🤝',
    agents: [],
  },
  {
    id: 'break_room',
    name: 'Break Room',
    x: 350,
    y: 280,
    width: 190,
    height: 100,
    color: '#4d4d1e',
    icon: '☕',
    agents: [],
  },
]

// Agent avatar configuration
const AGENT_AVATARS: Record<string, { emoji: string; color: string }> = {
  GATEKEEPER: { emoji: '🛡️', color: '#22c55e' },
  HUNTER: { emoji: '🎯', color: '#f59e0b' },
  ORCHESTRATOR: { emoji: '🎭', color: '#8b5cf6' },
  BUILDER: { emoji: '🔧', color: '#3b82f6' },
  INSPECTOR: { emoji: '🔬', color: '#ec4899' },
  LEDGER: { emoji: '📒', color: '#14b8a6' },
}

export default function OfficeMap({ apiUrl }: OfficeMapProps) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)
  const [hoveredRoom, setHoveredRoom] = useState<string | null>(null)

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/v1/agents`)
        if (response.ok) {
          const data = await response.json()
          setAgents(data)
        }
      } catch (err) {
        console.error('Failed to fetch agents:', err)
      }
    }

    fetchAgents()
    const interval = setInterval(fetchAgents, 5000)
    return () => clearInterval(interval)
  }, [apiUrl])

  const getAgentPosition = (agentId: string): { x: number; y: number } | null => {
    for (const room of ROOMS) {
      if (room.agents.includes(agentId)) {
        const index = room.agents.indexOf(agentId)
        return {
          x: room.x + 30 + (index % 2) * 50,
          y: room.y + 50 + Math.floor(index / 2) * 40,
        }
      }
    }
    return null
  }

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'working':
        return '#22c55e'
      case 'idle':
        return '#6b7280'
      case 'blocked_internal':
        return '#f59e0b'
      case 'blocked_user':
        return '#ef4444'
      default:
        return '#6b7280'
    }
  }

  const getStatusAnimation = (status: string): string => {
    if (status === 'working') {
      return 'animate-pulse'
    }
    return ''
  }

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4 text-cyan-300 flex items-center gap-2">
        🏢 Nexus AI Office
        <span className="text-sm font-normal text-gray-400 ml-2">
          ({agents.filter(a => a.status === 'working').length} working)
        </span>
      </h2>

      {/* Legend */}
      <div className="flex gap-4 mb-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-gray-400">Working</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-gray-500" />
          <span className="text-gray-400">Idle</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="text-gray-400">Blocked</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-gray-400">Waiting CEO</span>
        </div>
      </div>

      {/* Office Map SVG */}
      <div className="relative bg-slate-900 rounded-lg overflow-hidden" style={{ height: '400px' }}>
        <svg width="100%" height="100%" viewBox="0 0 560 400" preserveAspectRatio="xMidYMid meet">
          {/* Floor pattern */}
          <defs>
            <pattern id="floor" width="20" height="20" patternUnits="userSpaceOnUse">
              <rect width="20" height="20" fill="#1e293b" />
              <rect width="10" height="10" fill="#0f172a" />
              <rect x="10" y="10" width="10" height="10" fill="#0f172a" />
            </pattern>
          </defs>
          <rect width="560" height="400" fill="url(#floor)" />

          {/* Rooms */}
          {ROOMS.map((room) => (
            <g
              key={room.id}
              onMouseEnter={() => setHoveredRoom(room.id)}
              onMouseLeave={() => setHoveredRoom(null)}
              style={{ cursor: 'pointer' }}
            >
              {/* Room background */}
              <rect
                x={room.x}
                y={room.y}
                width={room.width}
                height={room.height}
                rx="8"
                fill={room.color}
                stroke={hoveredRoom === room.id ? '#22d3ee' : '#334155'}
                strokeWidth={hoveredRoom === room.id ? 2 : 1}
                opacity={0.8}
              />

              {/* Room icon */}
              <text
                x={room.x + 15}
                y={room.y + 25}
                fontSize="20"
              >
                {room.icon}
              </text>

              {/* Room name */}
              <text
                x={room.x + 40}
                y={room.y + 22}
                fill="#94a3b8"
                fontSize="11"
                fontWeight="bold"
              >
                {room.name}
              </text>

              {/* Desk lines */}
              {room.agents.length > 0 && (
                <rect
                  x={room.x + 20}
                  y={room.y + 40}
                  width={room.width - 40}
                  height={4}
                  fill="#475569"
                  rx="2"
                />
              )}
            </g>
          ))}

          {/* Agents */}
          {agents.map((agent) => {
            const pos = getAgentPosition(agent.id)
            if (!pos) return null

            const avatar = AGENT_AVATARS[agent.id] || { emoji: '🤖', color: '#6b7280' }
            const statusColor = getStatusColor(agent.status)

            return (
              <g
                key={agent.id}
                onClick={() => setSelectedAgent(selectedAgent?.id === agent.id ? null : agent)}
                style={{ cursor: 'pointer' }}
                className={getStatusAnimation(agent.status)}
              >
                {/* Agent shadow */}
                <ellipse
                  cx={pos.x}
                  cy={pos.y + 25}
                  rx="18"
                  ry="6"
                  fill="rgba(0,0,0,0.3)"
                />

                {/* Agent body */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r="20"
                  fill="#1e293b"
                  stroke={selectedAgent?.id === agent.id ? '#22d3ee' : statusColor}
                  strokeWidth={selectedAgent?.id === agent.id ? 3 : 2}
                />

                {/* Agent avatar */}
                <text
                  x={pos.x}
                  y={pos.y + 6}
                  fontSize="18"
                  textAnchor="middle"
                >
                  {avatar.emoji}
                </text>

                {/* Status indicator */}
                <circle
                  cx={pos.x + 14}
                  cy={pos.y - 14}
                  r="6"
                  fill={statusColor}
                  stroke="#1e293b"
                  strokeWidth="2"
                />

                {/* Agent name */}
                <text
                  x={pos.x}
                  y={pos.y + 38}
                  fill="#94a3b8"
                  fontSize="9"
                  textAnchor="middle"
                  fontWeight="bold"
                >
                  {agent.id}
                </text>
              </g>
            )
          })}

          {/* Connecting paths (hallways) */}
          <path
            d="M 190 70 L 200 70"
            stroke="#334155"
            strokeWidth="3"
            strokeDasharray="5,5"
          />
          <path
            d="M 350 70 L 360 70"
            stroke="#334155"
            strokeWidth="3"
            strokeDasharray="5,5"
          />
          <path
            d="M 100 130 L 100 140"
            stroke="#334155"
            strokeWidth="3"
            strokeDasharray="5,5"
          />
        </svg>

        {/* Agent Info Panel */}
        {selectedAgent && (
          <div className="absolute top-4 right-4 bg-slate-800 border border-cyan-500 rounded-lg p-4 w-64 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">
                  {AGENT_AVATARS[selectedAgent.id]?.emoji || '🤖'}
                </span>
                <div>
                  <div className="font-bold text-white">{selectedAgent.name}</div>
                  <div className="text-xs text-gray-400">{selectedAgent.id}</div>
                </div>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Role</span>
                <span className="text-white">{selectedAgent.role}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Status</span>
                <span
                  className="px-2 py-0.5 rounded text-xs"
                  style={{ backgroundColor: getStatusColor(selectedAgent.status) + '33', color: getStatusColor(selectedAgent.status) }}
                >
                  {selectedAgent.status}
                </span>
              </div>
              {selectedAgent.current_task && (
                <div className="mt-2 pt-2 border-t border-slate-700">
                  <div className="text-gray-400 text-xs mb-1">Current Task</div>
                  <div className="text-white text-xs">{selectedAgent.current_task}</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Room hover info */}
      {hoveredRoom && (
        <div className="mt-2 text-sm text-gray-400">
          {ROOMS.find(r => r.id === hoveredRoom)?.name} - {' '}
          {ROOMS.find(r => r.id === hoveredRoom)?.agents.length || 0} agents
        </div>
      )}
    </div>
  )
}
