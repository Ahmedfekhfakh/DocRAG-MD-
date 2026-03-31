export default function LandingPage({ onSelectRole }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 transition-colors">
      {/* Logo / Title */}
      <div className="text-center mb-12">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-blue-600 dark:bg-blue-500 flex items-center justify-center mb-6 shadow-lg">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-3">Medical RAG</h1>
        <p className="text-gray-500 dark:text-gray-400 text-lg max-w-md mx-auto">
          AI-powered clinical assistant backed by StatPearls evidence.
        </p>
      </div>

      {/* Role Selection */}
      <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-6">I am a...</p>
      <div className="flex gap-6">
        {/* Patient Card */}
        <button
          onClick={() => onSelectRole('patient')}
          className="group w-64 rounded-2xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center shadow-sm hover:border-blue-500 dark:hover:border-blue-400 hover:shadow-lg transition-all"
        >
          <div className="mx-auto w-14 h-14 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <svg className="w-7 h-7 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.5 20.25a8.25 8.25 0 0115 0" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Patient</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Get clear, simple explanations about your health questions.
          </p>
        </button>

        {/* Doctor Card */}
        <button
          onClick={() => onSelectRole('doctor')}
          className="group w-64 rounded-2xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-8 text-center shadow-sm hover:border-indigo-500 dark:hover:border-indigo-400 hover:shadow-lg transition-all"
        >
          <div className="mx-auto w-14 h-14 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
            <svg className="w-7 h-7 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.438 60.438 0 00-.491 6.347A48.62 48.62 0 0112 20.904a48.62 48.62 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.636 50.636 0 00-2.658-.813A59.906 59.906 0 0112 3.493a59.903 59.903 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0112 13.489a50.702 50.702 0 017.74-3.342" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Doctor</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Get detailed clinical answers with full medical terminology.
          </p>
        </button>
      </div>

      <p className="mt-10 text-xs text-gray-400 dark:text-gray-600">
        Powered by Gemini 2.5 Flash · StatPearls · 70k+ clinical chunks
      </p>
    </div>
  )
}
