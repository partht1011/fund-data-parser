import { useMemo, useRef, useState } from 'react'
import { Pagination } from '../components/Pagination'
import { StatusBadge } from '../components/StatusBadge'
import type { Holding, ParseResult } from '../types'

const CHECKS_PER_PAGE = 8
const REVIEW_RECORDS_PER_PAGE = 8

interface Props {
  result: ParseResult | null
  onCorrect: (record: Holding, field: string, value: string, updateConfig: boolean) => Promise<void>
  onBack: () => void
  onContinue: () => void
}

export function ValidationPage({ result, onCorrect, onBack, onContinue }: Props) {
  const review = useMemo(() => result?.holdings.filter((item) => item.validation_status === 'review') ?? [], [result])
  const [selected, setSelected] = useState<Holding | null>(null)
  const [field, setField] = useState('security_name')
  const [value, setValue] = useState('')
  const [updateConfig, setUpdateConfig] = useState(false)
  const [checksPage, setChecksPage] = useState(1)
  const [reviewPage, setReviewPage] = useState(1)
  const checksPanel = useRef<HTMLDivElement>(null)
  const reviewPanel = useRef<HTMLDivElement>(null)
  const visibleChecks = useMemo(
    () => pageItems(result?.validations ?? [], checksPage, CHECKS_PER_PAGE),
    [result?.validations, checksPage],
  )
  const visibleReview = useMemo(
    () => pageItems(review, reviewPage, REVIEW_RECORDS_PER_PAGE),
    [review, reviewPage],
  )

  if (!result) return <Empty message="Complete a parse to inspect validation results." />
  const errors = result.validations.filter((item) => item.severity === 'error').length
  const warnings = result.validations.filter((item) => item.severity === 'warning').length
  return (
    <section className="page-grid validation-layout">
      <div className="metrics panel-wide">
        <article><span>Validation errors</span><strong>{errors}</strong></article>
        <article><span>Warnings</span><strong>{warnings}</strong></article>
        <article><span>Review records</span><strong>{review.length}</strong></article>
        <article><span>Config version</span><strong>v{result.config_version}</strong></article>
      </div>
      <div className="panel" ref={checksPanel}>
        <p className="eyebrow">Checks</p>
        <h2>Validation & reconciliation</h2>
        <div className="check-list">
          {visibleChecks.map(({ item, index }) => (
            <div className="check" key={`${item.id ?? item.code}-${index}`}>
              <StatusBadge value={item.severity} />
              <div><strong>{item.code.replaceAll('_', ' ')}</strong><p>{item.message}</p></div>
              <span>{item.page_number ? `p. ${item.page_number}` : ''}</span>
            </div>
          ))}
        </div>
        <Pagination currentPage={checksPage} totalItems={result.validations.length} pageSize={CHECKS_PER_PAGE} onPageChange={(page) => changePage(page, setChecksPage, checksPanel)} itemLabel="checks" />
      </div>
      <div className="panel" ref={reviewPanel}>
        <p className="eyebrow">Review queue</p>
        <h2>Records needing attention</h2>
        {review.length === 0 ? <p className="empty-copy">No records are currently marked for review.</p> : (
          <div className="review-list">{visibleReview.map(({ item, index }) => <button key={item.id ?? `${item.security_name}-${index}`} onClick={() => { setSelected(item); setValue(item.security_name) }}><span>{item.security_name}</span><small>Page {item.source_page}</small></button>)}</div>
        )}
        <Pagination currentPage={reviewPage} totalItems={review.length} pageSize={REVIEW_RECORDS_PER_PAGE} onPageChange={(page) => changePage(page, setReviewPage, reviewPanel)} itemLabel="records" />
      </div>
      {selected && selected.id && (
        <div className="panel panel-wide correction">
          <div><p className="eyebrow">Source provenance</p><h2>{selected.security_name}</h2><p>Page {selected.source_page} · parsed {selected.parser_source}</p></div>
          <div className="correction-form">
            <label>Field<select value={field} onChange={(event) => { const next = event.target.value; setField(next); setValue(String(selected[next as keyof Holding] ?? '')) }}><option>security_name</option><option>security_type</option><option>country_iso3</option><option>sector</option><option>number_of_shares</option><option>principal_amount</option><option>market_value</option></select></label>
            <label>Corrected value<input value={value} onChange={(event) => setValue(event.target.value)} /></label>
            <label className="checkbox"><input type="checkbox" checked={updateConfig} onChange={(event) => setUpdateConfig(event.target.checked)} />Offer this mapping as a reusable config update</label>
            <button className="button" onClick={() => void onCorrect(selected, field, value, updateConfig)}>Apply correction</button>
          </div>
        </div>
      )}
      <div className="workflow-actions panel-wide">
        <button className="button secondary" onClick={onBack}>Back to Parse</button>
        <div className="workflow-actions-copy"><span>Review items can be corrected now or exported with their current status.</span></div>
        <button className="button" onClick={onContinue}>Continue to Output <span aria-hidden="true">→</span></button>
      </div>
    </section>
  )
}

function Empty({ message }: { message: string }) { return <div className="panel empty-state"><h2>Nothing to validate yet</h2><p>{message}</p></div> }

function pageItems<T>(items: T[], currentPage: number, pageSize: number) {
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize))
  const safePage = Math.min(Math.max(currentPage, 1), totalPages)
  const start = (safePage - 1) * pageSize
  return items.slice(start, start + pageSize).map((item, offset) => ({ item, index: start + offset }))
}

function changePage(
  page: number,
  setPage: (page: number) => void,
  section: React.RefObject<HTMLElement | null>,
) {
  setPage(page)
  window.requestAnimationFrame(() => section.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}
