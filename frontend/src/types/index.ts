export type ParserSource = 'local' | 'remote'
export type ValidationStatus = 'pass' | 'review'
export type Severity = 'info' | 'warning' | 'error'

export interface DocumentInfo {
  id: string
  original_filename: string
  content_type: string
  size_bytes: number
  created_at: string
}

export interface Job {
  id: string
  document_id: string
  fund_id: string | null
  config_version: string | null
  status: 'queued' | 'processing' | 'complete' | 'failed'
  current_stage: string
  pages_processed: number
  local_page_count: number
  remote_page_count: number
  holding_count: number
  error_message: string | null
}

export interface Holding {
  id: string | null
  fund_name: string
  report_date: string
  security_name: string
  security_type: string | null
  country_iso3: string | null
  sector: string | null
  number_of_shares: string | null
  principal_amount: string | null
  market_value: string | null
  source_page: number
  parser_source: ParserSource
  validation_status: ValidationStatus
}

export interface Validation {
  id: string | null
  code: string
  severity: Severity
  message: string
  page_number: number | null
  section_name: string | null
}

export interface ParseResult {
  fund_name: string
  report_date: string
  holdings: Holding[]
  validations: Validation[]
  pages_used_remote: number[]
  config_version: string
}

export interface FundConfig {
  fund_id: string
  version: string
  display_name: string
  fund_name_patterns: string[]
  schedule_headings: string[]
  stop_headings: string[]
  column_aliases: Record<string, string[]>
  hierarchy: {
    first_level: 'security_type'
    second_level: 'country' | 'sector'
    sector_source: 'description' | null
    carry_context_across_pages: boolean
  }
  security_types: Record<string, string[]>
  country_aliases: Record<string, string>
  rules: Record<string, string | boolean | number>
  fallback: { enabled: boolean }
  layout_hints: { columns: number | 'auto'; split_ratio: number }
}
