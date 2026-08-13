import { useMemo, useState } from 'react'
import type { DocumentInfo, FundConfig, ParseResult } from '../types'

interface Props {
  configs: FundConfig[]
  selectedFundId: string
  document: DocumentInfo | null
  result: ParseResult | null
  busy: boolean
  onSelectConfig: (fundId: string) => void
  onUpload: (file: File) => Promise<void>
  onSaveConfig: (config: FundConfig) => Promise<void>
}

export function SetupPage(props: Props) {
  const config = useMemo(
    () => props.configs.find((item) => item.fund_id === props.selectedFundId),
    [props.configs, props.selectedFundId],
  )
  const [editor, setEditor] = useState('')
  const [editorOpen, setEditorOpen] = useState(false)

  function openEditor() {
    if (config) setEditor(JSON.stringify(config, null, 2))
    setEditorOpen(true)
  }

  async function save() {
    const parsed = JSON.parse(editor) as FundConfig
    await props.onSaveConfig(parsed)
    setEditorOpen(false)
  }

  return (
    <section className="page-grid">
      <div className="panel panel-primary">
        <p className="eyebrow">1 / Document</p>
        <h2>Set up an import</h2>
        <label className="drop-zone">
          <input
            type="file"
            accept="application/pdf,.pdf"
            disabled={props.busy}
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void props.onUpload(file)
            }}
          />
          <span>{props.busy ? 'Uploading…' : 'Choose a mutual fund PDF'}</span>
          <small>PDF only. Files stay in the configured local data directory.</small>
        </label>
        {props.document && (
          <dl className="facts">
            <div><dt>File</dt><dd>{props.document.original_filename}</dd></div>
            <div><dt>Size</dt><dd>{(props.document.size_bytes / 1_000_000).toFixed(2)} MB</dd></div>
          </dl>
        )}
      </div>

      <div className="panel">
        <p className="eyebrow">2 / Configuration</p>
        <h2>Choose the fund layout</h2>
        <label>
          Saved configuration
          <select value={props.selectedFundId} onChange={(event) => props.onSelectConfig(event.target.value)}>
            <option value="">Auto-detect from the document</option>
            {props.configs.map((item) => (
              <option key={item.fund_id} value={item.fund_id}>{item.display_name} · v{item.version}</option>
            ))}
          </select>
        </label>
        {config && (
          <>
            <dl className="facts compact">
              <div><dt>Hierarchy</dt><dd>Security type → {config.hierarchy.second_level}</dd></div>
              <div><dt>Columns</dt><dd>{String(config.layout_hints.columns)}</dd></div>
              <div><dt>Remote fallback</dt><dd>{config.fallback.enabled ? 'Enabled when available' : 'Disabled'}</dd></div>
            </dl>
            <button className="button secondary" onClick={openEditor}>Edit mappings</button>
          </>
        )}
      </div>

      <div className="panel panel-wide">
        <p className="eyebrow">Detection preview</p>
        <div className="preview-row">
          <div><span>Fund name</span><strong>{props.result?.fund_name ?? config?.display_name ?? 'Detected during parse'}</strong></div>
          <div><span>Report date</span><strong>{props.result?.report_date ?? 'Detected during parse'}</strong></div>
          <div><span>Schedule pages</span><strong>{props.result ? `${Math.min(...props.result.holdings.map((r) => r.source_page))}–${Math.max(...props.result.holdings.map((r) => r.source_page))}` : 'Detected during parse'}</strong></div>
        </div>
      </div>

      {editorOpen && (
        <div className="modal-backdrop" role="presentation">
          <div className="modal" role="dialog" aria-modal="true" aria-label="Edit configuration">
            <div className="modal-heading"><h2>Edit fund configuration</h2><button className="icon-button" onClick={() => setEditorOpen(false)}>×</button></div>
            <p>Version the reusable aliases and hierarchy here. Invalid configurations are rejected before parsing.</p>
            <textarea className="config-editor" value={editor} onChange={(event) => setEditor(event.target.value)} spellCheck={false} />
            <div className="button-row"><button className="button secondary" onClick={() => setEditorOpen(false)}>Cancel</button><button className="button" onClick={() => void save()}>Save configuration</button></div>
          </div>
        </div>
      )}
    </section>
  )
}
