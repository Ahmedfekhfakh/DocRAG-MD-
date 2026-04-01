const STEP_LABELS = {
  planning: 'Query planning',
  retrieval: 'Retrieval',
  drilldown: 'Source drilldown',
  assessment: 'Evidence assessment',
  generation: 'Final generation',
}

function statusPill(status) {
  if (status === 'done') {
    return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
  }
  if (status === 'running') {
    return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
  }
  return 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300'
}

export default function DeepSearchTracePanel({ trace, compact = false }) {
  if (!trace || trace.searchMode !== 'deep') return null

  const steps = trace.steps || {}
  const queries = trace.queries || []
  const followUpQueries = trace.followUpQueries || []
  const topSources = trace.topSources || []

  return (
    <div className={`rounded-xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/60 dark:bg-gray-900/60 ${compact ? 'p-3 mt-3' : 'p-4 mt-4'}`}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300">
            Deep Search Trace
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Multi-step retrieval, drilldown, assessment, and final generation.
          </p>
        </div>
        {trace.confidence !== null && trace.confidence !== undefined && (
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${trace.confidence ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'}`}>
            {trace.confidence ? 'Confident' : 'Low confidence'}
          </span>
        )}
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
        {Object.entries(STEP_LABELS).map(([key, label]) => (
          <div key={key} className="rounded-lg bg-white/80 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 px-3 py-2">
            <div className="text-xs font-medium text-gray-700 dark:text-gray-200">{label}</div>
            <div className={`mt-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${statusPill(steps[key])}`}>
              {steps[key] || 'pending'}
            </div>
          </div>
        ))}
      </div>

      {(queries.length > 0 || followUpQueries.length > 0 || topSources.length > 0 || trace.evidenceCount) && (
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          <div className="rounded-lg bg-white/80 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-3">
            <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">Queries</p>
            {queries.length > 0 ? (
              <ul className="mt-2 space-y-1 text-xs text-gray-600 dark:text-gray-300">
                {queries.map((query, idx) => (
                  <li key={`${query}-${idx}`} className="line-clamp-2">{query}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">Waiting for query planning.</p>
            )}
          </div>

          <div className="rounded-lg bg-white/80 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-3">
            <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">Evidence</p>
            <p className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
              {trace.evidenceCount || 0} chunks
            </p>
            {followUpQueries.length > 0 && (
              <div className="mt-3">
                <p className="text-[11px] font-medium text-gray-500 dark:text-gray-400">Follow-up queries</p>
                <ul className="mt-1 space-y-1 text-xs text-gray-600 dark:text-gray-300">
                  {followUpQueries.map((query, idx) => (
                    <li key={`${query}-${idx}`} className="line-clamp-2">{query}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="rounded-lg bg-white/80 dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-3">
            <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">Top sources</p>
            {topSources.length > 0 ? (
              <ul className="mt-2 space-y-1 text-xs text-gray-600 dark:text-gray-300">
                {topSources.map((source, idx) => (
                  <li key={`${source}-${idx}`} className="line-clamp-2">{source}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">No source drilldown yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
