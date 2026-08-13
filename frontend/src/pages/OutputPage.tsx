import { useMemo, useRef, useState } from 'react'
import { exportUrl } from '../api/client'
import { Pagination } from '../components/Pagination'
import { StatusBadge } from '../components/StatusBadge'
import type { Job, ParseResult } from '../types'

const HOLDINGS_PER_PAGE = 15

interface Props {
  result: ParseResult | null
  job: Job | null
  onBack: () => void
  onNewImport: () => void
}

export function OutputPage({ result, job, onBack, onNewImport }: Props) {
  const [currentPage, setCurrentPage] = useState(1)
  const tableSection = useRef<HTMLDivElement>(null)

  const visibleHoldings = useMemo(() => {
    const holdings = result?.holdings ?? []
    const totalPages = Math.max(1, Math.ceil(holdings.length / HOLDINGS_PER_PAGE))
    const safePage = Math.min(Math.max(currentPage, 1), totalPages)
    const start = (safePage - 1) * HOLDINGS_PER_PAGE
    return holdings.slice(start, start + HOLDINGS_PER_PAGE)
  }, [currentPage, result?.holdings])

  if (!result || !job) return <div className="panel empty-state"><h2>No output yet</h2><p>Run a document through the parser to preview and export normalized records.</p></div>
  return (
    <section className="page-stack">
      <div className="panel output-heading"><div><p className="eyebrow">Normalized result</p><h2>{result.fund_name}</h2><p>{result.report_date} · {result.holdings.length} holdings</p></div><div className="button-row"><a className="button secondary" href={exportUrl(job.id, 'csv')}>Export CSV</a><a className="button" href={exportUrl(job.id, 'json')}>Export JSON</a></div></div>
      <div className="table-section" ref={tableSection}>
        <div className="table-wrap"><table><thead><tr><th>Security</th><th>Type</th><th>Country / sector</th><th className="number">Shares</th><th className="number">Principal</th><th className="number">Market value</th><th>Source</th></tr></thead><tbody>{visibleHoldings.map((item, index) => <tr key={item.id ?? index}><td><strong>{item.security_name}</strong><small>Page {item.source_page}</small></td><td>{item.security_type ?? '—'}</td><td>{item.country_iso3 ?? item.sector ?? '—'}</td><td className="number">{formatNumber(item.number_of_shares)}</td><td className="number">{formatNumber(item.principal_amount)}</td><td className="number">{formatNumber(item.market_value)}</td><td><StatusBadge value={item.parser_source} /></td></tr>)}</tbody></table></div>
        <Pagination currentPage={currentPage} totalItems={result.holdings.length} pageSize={HOLDINGS_PER_PAGE} onPageChange={(page) => { setCurrentPage(page); window.requestAnimationFrame(() => tableSection.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })) }} itemLabel="holdings" />
      </div>
      <details className="panel json-preview"><summary>JSON preview</summary><pre>{JSON.stringify({ ...result, holdings: result.holdings.slice(0, 10) }, null, 2)}</pre></details>
      <div className="workflow-actions">
        <button className="button secondary" onClick={onBack}>Back to Validation</button>
        <div className="workflow-actions-copy"><span>Exports remain available above. Start another import when finished.</span></div>
        <button className="button" onClick={onNewImport}>Set up another import</button>
      </div>
    </section>
  )
}

function formatNumber(value: string | null) { return value === null ? '—' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 4 }).format(Number(value)) }
