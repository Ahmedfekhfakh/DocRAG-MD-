import { useState, useEffect, useRef } from 'react'
import ChatWindow from './components/ChatWindow'
import ModelSelector from './components/ModelSelector'
import ModeSelector from './components/ModeSelector'
import { createChatSocket } from './api/client'

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [model, setModel] = useState('gemini')
  const [mode, setMode] = useState('rag')
  const [loading, setLoading] = useState(false)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    const ws = createChatSocket(
      (data) => {
        if (data.type === 'answer') {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: data.answer, sources: data.sources, model: data.model, intent: data.intent },
          ])
          setLoading(false)
        } else if (data.type === 'error') {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: `Error: ${data.detail}`, sources: [] },
          ])
          setLoading(false)
        }
      },
      () => setConnected(false)
    )
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    wsRef.current = ws
    return () => ws.close()
  }, [])

  const sendMessage = () => {
    const q = input.trim()
    if (!q || !connected || loading) return
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setInput('')
    setLoading(true)
    wsRef.current.send(JSON.stringify({ question: q, model, mode }))
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-gray-900">Medical RAG</h1>
          <p className="text-xs text-gray-500">StatPearls · 301k clinical chunks</p>
        </div>
        <div className="flex items-center gap-4">
          <ModeSelector value={mode} onChange={setMode} />
          <ModelSelector value={model} onChange={setModel} />
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-400'}`} title={connected ? 'Connected' : 'Disconnected'} />
        </div>
      </header>

      {/* Chat */}
      <ChatWindow messages={messages} loading={loading} />

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-4 py-3">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <textarea
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
            placeholder="Ask a clinical question..."
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
        <p className="text-center text-xs text-gray-400 mt-1">Enter to send · Shift+Enter for newline</p>
      </div>
    </div>
  )
}
