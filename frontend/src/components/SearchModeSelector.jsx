const SEARCH_MODES = [
  { value: 'standard', label: 'Standard' },
  { value: 'deep', label: 'Deep Search' },
]

export default function SearchModeSelector({ value, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Search:</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {SEARCH_MODES.map((mode) => (
          <option key={mode.value} value={mode.value}>{mode.label}</option>
        ))}
      </select>
    </div>
  )
}
