import { StatusBadge } from '../components/StatusBadge'
import type { DocumentInfo, Job } from '../types'

interface Props {
  document: DocumentInfo | null
  job: Job | null
  onStart: () => Promise<void>
  onBack: () => void
  onContinue: () => void
}

export function ParsePage({ document, job, onStart, onBack, onContinue }: Props) {
  const canStart = document && (!job || job.status === 'complete' || job.status === 'failed')
  return (
    <section className="page-stack">
      <div className="panel panel-primary parse-hero">
        <div>
          <p className="eyebrow">Local-first pipeline</p>
          <h2>{job?.current_stage ?? 'Ready to parse'}</h2>
          <p className="muted">LiteParse scan → schedule location → Docling structure → deterministic parser → validation → optional page-level OCR.</p>
        </div>
        <button className="button button-light" disabled={!canStart} onClick={() => void onStart()}>
          {document ? 'Start parsing' : 'Upload a PDF first'}
        </button>
      </div>
      <div className="metrics">
        <article><span>Status</span><strong>{job ? <StatusBadge value={job.status} /> : '—'}</strong></article>
        <article><span>Pages processed</span><strong>{job?.pages_processed ?? 0}</strong></article>
        <article><span>Local pages</span><strong>{job?.local_page_count ?? 0}</strong></article>
        <article><span>Remote pages</span><strong>{job?.remote_page_count ?? 0}</strong></article>
        <article><span>Holdings</span><strong>{job?.holding_count ?? 0}</strong></article>
      </div>
      {job?.error_message && <div className="alert error">{job.error_message}</div>}
      {job && ['queued', 'processing'].includes(job.status) && <div className="progress"><span /></div>}
      <div className="workflow-actions">
        <button className="button secondary" onClick={onBack}>Back to Setup</button>
        <div className="workflow-actions-copy">
          {job?.status === 'complete' && <span>Parsing is complete. Continue to inspect validation results.</span>}
          {job?.status === 'failed' && <span>Review the error above or return to Setup before retrying.</span>}
        </div>
        {job?.status === 'complete' && <button className="button" onClick={onContinue}>Continue to Validation <span aria-hidden="true">→</span></button>}
      </div>
    </section>
  )
}
