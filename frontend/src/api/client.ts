import type { DocumentInfo, FundConfig, Holding, Job, ParseResult } from '../types'

const API = import.meta.env.VITE_API_URL ?? '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, init)
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`)
  }
  return (await response.json()) as T
}

export async function uploadDocument(file: File): Promise<DocumentInfo> {
  const body = new FormData()
  body.append('file', file)
  return request('/documents', { method: 'POST', body })
}

export function listConfigs(): Promise<FundConfig[]> {
  return request('/configs')
}

export function saveConfig(config: FundConfig): Promise<FundConfig> {
  return request(`/configs/${config.fund_id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
}

export function startParse(documentId: string, fundId: string | null): Promise<Job> {
  return request(`/documents/${documentId}/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fund_id: fundId }),
  })
}

export function getJob(jobId: string): Promise<Job> {
  return request(`/jobs/${jobId}`)
}

export function getResults(jobId: string): Promise<ParseResult> {
  return request(`/jobs/${jobId}/results`)
}

export function correctHolding(
  jobId: string,
  recordId: string,
  fieldName: string,
  value: string | null,
  updateConfig: boolean,
): Promise<Holding> {
  return request(`/jobs/${jobId}/records/${recordId}/correction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field_name: fieldName, value, update_config: updateConfig }),
  })
}

export function exportUrl(jobId: string, format: 'json' | 'csv'): string {
  return `${API}/jobs/${jobId}/export.${format}`
}
