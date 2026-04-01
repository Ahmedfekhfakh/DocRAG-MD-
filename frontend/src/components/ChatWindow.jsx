import { useEffect, useRef } from 'react'
import DeepSearchTracePanel from './DeepSearchTracePanel'
import MessageBubble from './MessageBubble'
import SourcePanel from './SourcePanel'

export default function ChatWindow({ messages, loading, activeTrace, streamingAnswer }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, streamingAnswer, activeTrace])

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
          {msg.role === 'assistant' && msg.trace && (
            <div className="ml-4 max-w-[85%]">
              <DeepSearchTracePanel trace={msg.trace} compact />
            </div>
          )}
          {msg.role === 'assistant' && msg.sources && (
            <div className="ml-4">
              <SourcePanel sources={msg.sources} />
            </div>
          )}
        </div>
      ))}
      {loading && (
        <div className="flex justify-start mb-4">
          <div className="max-w-[85%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 text-sm text-gray-500 dark:text-gray-400 shadow-sm">
            <div className="animate-pulse">
              {streamingAnswer || 'Retrieving and generating...'} 
            </div>
            <DeepSearchTracePanel trace={activeTrace} />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
