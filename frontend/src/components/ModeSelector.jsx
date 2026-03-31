const MODES = [
  { value: 'rag', label: 'Clinical textbooks' },
  { value: 'graph', label: 'Medical knowledge graph' },
  { value: 'hybrid', label: 'Textbooks + Knowledge graph' },
  { value: 'deep_search', label: 'PubMed articles' },
]

export default function ModeSelector({ value, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700">Mode:</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {MODES.map((m) => (
          <option key={m.value} value={m.value}>{m.label}</option>
        ))}
      </select>
    </div>
  )
}
