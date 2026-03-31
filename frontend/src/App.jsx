import { useState, useEffect, useRef } from 'react'
import ChatWindow from './components/ChatWindow'
import ModelSelector from './components/ModelSelector'
import SearchModeSelector from './components/SearchModeSelector'
import DarkModeToggle from './components/DarkModeToggle'
import AuthPage from './components/AuthPage'
import { createChatSocket } from './api/client'

function createInitialTrace(searchMode) {
  return {
    searchMode,
    steps: {
      planning: 'pending',
      retrieval: 'pending',
      drilldown: 'pending',
      assessment: 'pending',
      generation: 'pending',
    },
    queries: [],
    followUpQueries: [],
    evidenceCount: 0,
    topSources: [],
    confidence: null,
  }
}

function mergeTrace(prevTrace, event) {
  const trace = prevTrace || createInitialTrace(event.search_mode || 'deep')
  const next = {
    ...trace,
    steps: {
      ...trace.steps,
      [event.step]: event.status,
    },
  }

  if (event.queries) next.queries = event.queries
  if (event.follow_up_queries) next.followUpQueries = event.follow_up_queries
  if (event.evidence_count !== undefined) next.evidenceCount = event.evidence_count
  if (event.top_sources) next.topSources = event.top_sources
  if (event.is_confident !== undefined) next.confidence = event.is_confident
  return next
}

export default function App() {
  const [user, setUser] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [model, setModel] = useState('gemini')
  const [searchMode, setSearchMode] = useState('standard')
  const [loading, setLoading] = useState(false)
  const [connected, setConnected] = useState(false)
  const [activeTrace, setActiveTrace] = useState(null)
  const [streamingAnswer, setStreamingAnswer] = useState('')
  const wsRef = useRef(null)
  const activeTraceRef = useRef(null)

  const role = user?.role

  const updateTrace = (updater) => {
    setActiveTrace((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      activeTraceRef.current = next
      return next
    })
  }

  useEffect(() => {
    if (!user) return
    const ws = createChatSocket(
      (data) => {
        if (data.type === 'start') {
          setLoading(true)
          setStreamingAnswer('')
          updateTrace(createInitialTrace(data.search_mode || searchMode))
        } else if (data.type === 'trace') {
          updateTrace((prev) => mergeTrace(prev, data))
        } else if (data.type === 'delta') {
          setStreamingAnswer((prev) => `${prev}${data.text || ''}`)
        } else if (data.type === 'answer') {
          const finalTrace = activeTraceRef.current
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: data.answer,
              sources: data.sources,
              model: data.model,
              searchMode: data.search_mode,
              isConfident: data.is_confident,
              trace: finalTrace,
            },
          ])
          updateTrace(null)
          setStreamingAnswer('')
          setLoading(false)
        } else if (data.type === 'error') {
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: `Error: ${data.detail}`,
              sources: [],
              trace: activeTraceRef.current,
            },
          ])
          updateTrace(null)
          setStreamingAnswer('')
          setLoading(false)
        }
      },
      () => setConnected(false)
    )
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    wsRef.current = ws
    return () => ws.close()
  }, [user])

  const sendMessage = () => {
    const q = input.trim()
    if (!q || !connected || loading) return
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setInput('')
    setLoading(true)
    wsRef.current.send(JSON.stringify({ question: q, model, search_mode: searchMode, role }))
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleLogout = () => {
    if (wsRef.current) wsRef.current.close()
    setUser(null)
    setMessages([])
    setConnected(false)
    setLoading(false)
    setStreamingAnswer('')
    updateTrace(null)
  }

  if (!user) {
    return <AuthPage onAuth={setUser} />
  }

  const roleLabel = role === 'patient' ? 'Patient' : 'Doctor'
  const roleColor = role === 'patient' ? 'green' : 'indigo'

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">Medical RAG</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">Welcome, <span className="font-medium text-gray-700 dark:text-gray-300">{user.username}</span></p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-${roleColor}-100 text-${roleColor}-700 dark:bg-${roleColor}-900/40 dark:text-${roleColor}-300`}>
            {roleLabel}
          </span>
          <SearchModeSelector value={searchMode} onChange={setSearchMode} />
          <ModelSelector value={model} onChange={setModel} />
          <DarkModeToggle />
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-400'}`} title={connected ? 'Connected' : 'Disconnected'} />
          <button onClick={handleLogout} className="rounded-lg px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors" title="Log out">
            Logout
          </button>
        </div>
      </header>

      <ChatWindow
        messages={messages}
        loading={loading}
        activeTrace={activeTrace}
        streamingAnswer={streamingAnswer}
      />

      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-3">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <textarea
            className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-400 dark:placeholder-gray-500"
            rows={2}
            placeholder={role === 'patient' ? 'Ask a health question in plain language...' : 'Ask a clinical question...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || !connected || loading}
            className="rounded-xl bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40 transition-colors"
          >
            Send
          </button>
        </div>
        <p className="text-center text-xs text-gray-400 dark:text-gray-500 mt-1">Enter to send · Shift+Enter for newline</p>
      </div>
    </div>
  )
}
