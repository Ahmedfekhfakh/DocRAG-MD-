import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import SourcePanel from './SourcePanel'

export default function ChatWindow({ messages, loading }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-2">
      {messages.length === 0 && (
        <div className="text-center text-gray-400 dark:text-gray-500 mt-20 text-sm">
          Ask a medical question to get started.
        </div>
      )}
      {messages.map((msg, i) => (
        <div key={i}>
          <MessageBubble message={msg} />
          {msg.role === 'assistant' && msg.sources && (
            <div className="ml-4">
              <SourcePanel sources={msg.sources} />
            </div>
          )}
        </div>
      ))}
      {loading && (
        <div className="flex justify-start mb-4">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 text-sm text-gray-400 dark:text-gray-500 shadow-sm animate-pulse">
            Retrieving and generating...
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
