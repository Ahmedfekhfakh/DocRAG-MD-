const MODELS = [
  { value: 'gemini', label: 'Gemini 2.5 Flash' },
  { value: 'gemini-pro', label: 'Gemini 2.5 Pro' },
  { value: 'biomistral', label: 'BioMistral 7B (local)' },
  { value: 'gpt4o', label: 'GPT-4o' },
]

export default function ModelSelector({ value, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Model:</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {MODELS.map((m) => (
          <option key={m.value} value={m.value}>{m.label}</option>
        ))}
      </select>
    </div>
  )
}
