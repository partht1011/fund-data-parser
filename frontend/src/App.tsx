import { useEffect, useState } from 'react'
import { correctHolding, getJob, getResults, listConfigs, saveConfig, startParse, uploadDocument } from './api/client'
import { OutputPage } from './pages/OutputPage'
import { ParsePage } from './pages/ParsePage'
import { SetupPage } from './pages/SetupPage'
import { ValidationPage } from './pages/ValidationPage'
import type { DocumentInfo, FundConfig, Holding, Job, ParseResult } from './types'

type Tab = 'setup' | 'parse' | 'validation' | 'output'
const tabs: { id: Tab; label: string }[] = [{ id: 'setup', label: 'Setup' }, { id: 'parse', label: 'Parse' }, { id: 'validation', label: 'Validation' }, { id: 'output', label: 'Output' }]

export default function App() {
  const [tab, setTab] = useState<Tab>('setup')
  const [configs, setConfigs] = useState<FundConfig[]>([])
  const [selectedFundId, setSelectedFundId] = useState('')
  const [document, setDocument] = useState<DocumentInfo | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [result, setResult] = useState<ParseResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { void listConfigs().then(setConfigs).catch((reason: Error) => setError(reason.message)) }, [])
  useEffect(() => {
    if (!job || !['queued', 'processing'].includes(job.status)) return
    const timer = window.setInterval(() => {
      void getJob(job.id).then(async (next) => {
        setJob(next)
        if (next.status === 'complete') { setResult(await getResults(next.id)); setTab('validation') }
      }).catch((reason: Error) => setError(reason.message))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [job])

  async function upload(file: File) { setBusy(true); setError(''); try { setDocument(await uploadDocument(file)); setJob(null); setResult(null) } catch (reason) { setError((reason as Error).message) } finally { setBusy(false) } }
  async function parse() { if (!document) return; setError(''); const next = await startParse(document.id, selectedFundId || null); setJob(next); setResult(null) }
  async function save(config: FundConfig) { const saved = await saveConfig(config); setConfigs((items) => items.map((item) => item.fund_id === saved.fund_id ? saved : item)) }
  async function correct(record: Holding, field: string, value: string, updateConfig: boolean) { if (!job || !record.id || !result) return; const changed = await correctHolding(job.id, record.id, field, value || null, updateConfig); setResult({ ...result, holdings: result.holdings.map((item) => item.id === changed.id ? changed : item) }) }

  return (
    <div className="app-shell">
      <header className="topbar"><div className="brand-mark">VA</div><div><strong>Visual Alpha</strong><span>Data Parser Prototype</span></div></header>
      <nav className="tabs" aria-label="Workflow stages">{tabs.map((item, index) => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)}><span>{index + 1}</span>{item.label}</button>)}</nav>
      {error && <div className="alert error global-alert">{error}<button onClick={() => setError('')}>×</button></div>}
      <main>
        {tab === 'setup' && <SetupPage configs={configs} selectedFundId={selectedFundId} document={document} result={result} busy={busy} onSelectConfig={setSelectedFundId} onUpload={upload} onSaveConfig={save} />}
        {tab === 'parse' && <ParsePage document={document} job={job} onStart={parse} />}
        {tab === 'validation' && <ValidationPage result={result} onCorrect={correct} />}
        {tab === 'output' && <OutputPage result={result} job={job} />}
      </main>
      <footer><span>Prototype v0.1</span><span>Data Parser</span></footer>
    </div>
  )
}
