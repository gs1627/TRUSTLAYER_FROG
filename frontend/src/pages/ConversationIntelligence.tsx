
import { useState } from 'react'
import {
  BrainCircuit,
  Search,
  AlertTriangle,
  ShieldCheck,
  Loader2,
  MessageSquare,
  Sparkles,
} from 'lucide-react'

interface AIAnalysis {
  intent: string
  urgency: string
  suspiciousIndicators: string[]
  explanation: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function ConversationIntelligence() {
  const [transcript, setTranscript] = useState('')
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const analyzeConversation = async () => {
    if (!transcript.trim()) {
      setError('Please enter a conversation transcript first.')
      return
    }

    setLoading(true)
    setError('')
    setAnalysis(null)

    try {
      const response = await fetch(`${API_BASE}/api/intelligence/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript }),
      })

      if (!response.ok) {
        throw new Error(`Analysis request failed (${response.status}).`)
      }

      const result: AIAnalysis = await response.json()
      setAnalysis(result)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not connect to the intelligence service.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium">
          <BrainCircuit size={17} />
          AI-POWERED ANALYSIS
        </div>
        <h1 className="text-2xl font-bold text-white mt-2">
          Conversation Intelligence
        </h1>
        <p className="text-slate-400 mt-1">
          Identify suspicious language, manipulation tactics and risky requests.
        </p>
      </div>

      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
        <div className="flex gap-3">
          <AlertTriangle className="text-amber-400 shrink-0" size={20} />
          <div>
            <p className="text-amber-300 font-medium text-sm">Integration status</p>
            <p className="text-slate-400 text-sm mt-1">
              This page expects the backend endpoint
              {' '}POST /api/intelligence/analyze. It will work once the backend
              team implements that endpoint. Do not enter real customer data here.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <MessageSquare className="text-cyan-400" size={20} />
            <h2 className="text-white font-semibold">Conversation Transcript</h2>
          </div>

          <p className="text-slate-400 text-sm">
            Paste a test conversation to inspect its language and intent.
          </p>

          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Example: Hello, I am calling from your bank. Your account will be blocked unless you share your OTP immediately..."
            rows={10}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 p-4 text-sm text-slate-200 placeholder:text-slate-600 outline-none focus:border-cyan-500 resize-y"
          />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-slate-500">
              {transcript.length} characters
            </span>

            <button
              onClick={analyzeConversation}
              disabled={loading || !transcript.trim()}
              className="flex items-center gap-2 rounded-lg bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 size={17} className="animate-spin" />
              ) : (
                <Search size={17} />
              )}
              {loading ? 'Analyzing...' : 'Analyze Conversation'}
            </button>
          </div>

          {error && (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
              {error}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="text-cyan-400" size={20} />
            <h2 className="text-white font-semibold">Analysis Overview</h2>
          </div>

          {!analysis ? (
            <div className="py-12 text-center">
              <BrainCircuit size={36} className="mx-auto text-slate-700" />
              <p className="text-slate-400 text-sm mt-3">
                No analysis available
              </p>
              <p className="text-slate-600 text-xs mt-1">
                Submit a transcript to begin.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg bg-slate-950 p-3">
                <p className="text-xs text-slate-500">Detected intent</p>
                <p className="text-white font-medium mt-1">{analysis.intent}</p>
              </div>

              <div className="rounded-lg bg-slate-950 p-3">
                <p className="text-xs text-slate-500">Urgency level</p>
                <p className="text-white font-medium mt-1">{analysis.urgency}</p>
              </div>

              <div>
                <p className="text-xs text-slate-500 mb-2">
                  Suspicious indicators
                </p>
                {analysis.suspiciousIndicators.length === 0 ? (
                  <p className="text-sm text-slate-400">No indicators returned.</p>
                ) : (
                  analysis.suspiciousIndicators.map((item, index) => (
                    <div key={index} className="mb-2 rounded-lg bg-red-500/10 p-2 text-sm text-red-300">
                      <AlertTriangle size={14} className="inline mr-2" />
                      {item}
                    </div>
                  ))
                )}
              </div>

              <div className="rounded-lg border border-slate-700 p-3">
                <p className="text-xs text-slate-500">Explanation</p>
                <p className="text-sm text-slate-300 mt-1">
                  {analysis.explanation}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck className="text-cyan-400" size={20} />
          <h2 className="text-white font-semibold">Security principle</h2>
        </div>
        <p className="text-slate-400 text-sm leading-6">
          Conversation intelligence identifies possible social-engineering
          indicators. It does not establish whether a voice is genuine, verify
          the speaker's identity, or authorize a transaction. Those decisions
          require separate evidence and the Trust Engine's security policy.
        </p>
      </div>
    </div>
  )
}

export default ConversationIntelligence
