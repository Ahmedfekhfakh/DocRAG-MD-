import { useState } from 'react'

export default function SourcePanel({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-2 border-t border-gray-100 dark:border-gray-700 pt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
      >
        {open ? '▾' : '▸'} {sources.length} source{sources.length !== 1 ? 's' : ''}
      </button>
      {open && (
        <ul className="mt-2 space-y-2">
          {sources.map((src, i) => (
            <li key={i} className="rounded-lg bg-gray-50 dark:bg-gray-800 p-3 text-xs">
              <p className="font-semibold text-gray-700 dark:text-gray-300">[{i + 1}] {src.title || 'Untitled'}</p>
              <p className="text-gray-500 dark:text-gray-400 mt-1 line-clamp-3">{src.content}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
