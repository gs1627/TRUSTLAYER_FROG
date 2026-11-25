
import { useState } from 'react'
import {
  Radio,
  Phone,
  PhoneOff,
  ShieldCheck,
  ShieldAlert,
  Fingerprint,
  Mic,
  Activity,
  Clock,
  AlertTriangle,
  Languages,
  MessageSquare,
} from 'lucide-react'

function LiveMonitoring() {
  const [active, setActive] = useState(false)
  const [callId, setCallId] = useState('')

  function startDemoCall() {
    setCallId(`DEMO-${Date.now().toString().slice(-6)}`)
    setActive(true)
  }

  function endDemoCall() {
    setActive(false)
  }

  const evidence = [
    {
      name: 'Voice Authenticity',
      provider: 'DetectifAI Aletheia',
      icon: ShieldCheck,
      status: 'Awaiting provider',
      color: 'text-amber-400',
    },
    {
      name: 'Speaker Identity',
      provider: 'DetectifAI Eidos',
      icon: Fingerprint,
      status: 'Awaiting provider',
      color: 'text-amber-400',
    },
    {
      name: 'Speech Transcription',
      provider: 'Sarvam Saaras',
      icon: Languages,
      status: 'Awaiting provider',
      color: 'text-amber-400',
    },
  ]

  return (
    <div className="space-y-7">

      {/* Header */}
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-cyan-500/10 p-3">
            <Radio className="h-7 w-7 text-cyan-400" />
          </div>

          <div>
            <h1 className="text-2xl font-bold text-white">
              Live Call Monitoring
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Monitor voice authenticity, identity and conversation activity.
            </p>
          </div>
        </div>

        <span className="self-start rounded-lg border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
          Frontend Demo Mode
        </span>
      </section>

      {/* Demo notice */}
      <div className="flex gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-400" />
        <div>
          <p className="text-sm font-semibold text-amber-300">
            Simulated monitoring
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-400">
            This page demonstrates the monitoring interface. It does not
            connect to a real telephone call, microphone stream or AI provider.
            Provider verdicts are not being generated.
          </p>
        </div>
      </div>

      {/* Call controls */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">

          <div>
            <p className="text-sm text-slate-400">
              Current call session
            </p>

            <h2 className="mt-2 text-xl font-bold text-white">
              {active ? 'Demo session active' : 'No active session'}
            </h2>

            <p className="mt-2 text-xs text-slate-500">
              {active ? `Session ID: ${callId}` : 'Start a demo session to preview the interface.'}
            </p>
          </div>

          {active ? (
            <button
              type="button"
              onClick={endDemoCall}
              className="flex items-center justify-center gap-2 rounded-lg bg-rose-500 px-5 py-3 font-semibold text-white hover:bg-rose-400"
            >
              <PhoneOff size={18} />
              End Demo Call
            </button>
          ) : (
            <button
              type="button"
              onClick={startDemoCall}
              className="flex items-center justify-center gap-2 rounded-lg bg-cyan-500 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-400"
            >
              <Phone size={18} />
              Start Demo Call
            </button>
          )}
        </div>

        <div className="mt-6 grid gap-4 border-t border-slate-800 pt-5 sm:grid-cols-3">
          <div>
            <p className="text-xs text-slate-500">Session status</p>
            <p className={`mt-2 text-sm font-semibold ${active ? 'text-cyan-400' : 'text-slate-400'}`}>
              {active ? 'Demo active' : 'Inactive'}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-500">Audio stream</p>
            <p className="mt-2 text-sm font-semibold text-amber-400">
              {active ? 'Not connected' : 'Not started'}
            </p>
          </div>

          <div>
            <p className="text-xs text-slate-500">AI analysis</p>
            <p className="mt-2 text-sm font-semibold text-amber-400">
              Pending integration
            </p>
          </div>
        </div>
      </section>

      {/* Evidence cards */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-white">
          AI Security Analysis
        </h2>

        <div className="grid gap-4 md:grid-cols-3">
          {evidence.map((item) => {
            const Icon = item.icon

            return (
              <div
                key={item.name}
                className="rounded-xl border border-slate-800 bg-slate-900 p-5"
              >
                <div className="flex items-center justify-between">
                  <div className="rounded-lg bg-slate-800 p-3">
                    <Icon className="h-6 w-6 text-cyan-400" />
                  </div>

                  <Activity className="h-5 w-5 text-slate-500" />
                </div>

                <h3 className="mt-5 font-semibold text-white">
                  {item.name}
                </h3>

                <p className="mt-1 text-xs text-slate-500">
                  {item.provider}
                </p>

                <p className={`mt-4 text-sm font-medium ${item.color}`}>
                  {item.status}
                </p>
              </div>
            )
          })}
        </div>
      </section>

      {/* Trust decision */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">
            Trust Engine Decision
          </h2>
        </div>

        <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950 p-6 text-center">
          <ShieldAlert className="mx-auto h-10 w-10 text-amber-400" />

          <h3 className="mt-3 text-lg font-semibold text-white">
            Insufficient Evidence
          </h3>

          <p className="mx-auto mt-2 max-w-lg text-sm leading-6 text-slate-400">
            Authenticity and identity evidence have not yet been received.
            No trust or transaction authorization decision can be made.
          </p>

          <span className="mt-4 inline-block rounded-full bg-amber-500/10 px-4 py-2 text-xs font-medium text-amber-300">
            Awaiting real provider integration
          </span>
        </div>
      </section>

      {/* Transcript */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-white">
            Live Conversation Transcript
          </h2>
        </div>

        <div className="mt-5 rounded-lg border border-slate-800 bg-slate-950 p-5">
          {active ? (
            <div className="text-center">
              <Mic className="mx-auto h-8 w-8 text-slate-500" />
              <p className="mt-3 text-sm text-slate-400">
                Waiting for a real audio stream and transcription service.
              </p>
            </div>
          ) : (
            <p className="text-center text-sm text-slate-500">
              No active call transcript.
            </p>
          )}
        </div>
      </section>

      {/* Event timeline */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-white">
            Call Event Timeline
          </h2>
        </div>

        <div className="mt-5 space-y-4">
          <div className="flex items-start gap-3">
            <span className="mt-1 h-2.5 w-2.5 rounded-full bg-cyan-400" />
            <div>
              <p className="text-sm text-white">Monitoring interface initialized</p>
              <p className="mt-1 text-xs text-slate-500">Frontend ready</p>
            </div>
          </div>

          {active && (
            <div className="flex items-start gap-3">
              <span className="mt-1 h-2.5 w-2.5 rounded-full bg-cyan-400" />
              <div>
                <p className="text-sm text-white">Demo session created</p>
                <p className="mt-1 text-xs text-slate-500">{callId}</p>
              </div>
            </div>
          )}

          {!active && (
            <p className="text-xs text-slate-500">
              Start a demo session to see its event here.
            </p>
          )}
        </div>
      </section>

    </div>
  )
}

export default LiveMonitoring
