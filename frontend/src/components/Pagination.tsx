interface Props {
  currentPage: number
  totalItems: number
  pageSize: number
  onPageChange: (page: number) => void
  itemLabel: string
}

type PageItem = number | 'ellipsis-start' | 'ellipsis-end'

export function Pagination({ currentPage, totalItems, pageSize, onPageChange, itemLabel }: Props) {
  if (totalItems === 0) return null

  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize))
  const safePage = Math.min(Math.max(currentPage, 1), totalPages)
  const firstItem = (safePage - 1) * pageSize + 1
  const lastItem = Math.min(safePage * pageSize, totalItems)
  const pages = visiblePages(safePage, totalPages)

  return (
    <nav className="pagination" aria-label={`${itemLabel} pagination`}>
      <span className="pagination-summary">
        {firstItem}–{lastItem} of {totalItems} {itemLabel}
      </span>
      {totalPages > 1 && (
        <div className="pagination-controls">
          <button
            type="button"
            className="pagination-direction"
            disabled={safePage === 1}
            onClick={() => onPageChange(safePage - 1)}
          >
            Previous
          </button>
          <div className="pagination-pages" aria-label={`Page ${safePage} of ${totalPages}`}>
            {pages.map((page) =>
              typeof page === 'number' ? (
                <button
                  type="button"
                  key={page}
                  className={page === safePage ? 'active' : ''}
                  aria-current={page === safePage ? 'page' : undefined}
                  aria-label={`Page ${page}`}
                  onClick={() => onPageChange(page)}
                >
                  {page}
                </button>
              ) : (
                <span key={page} aria-hidden="true">…</span>
              ),
            )}
          </div>
          <button
            type="button"
            className="pagination-direction"
            disabled={safePage === totalPages}
            onClick={() => onPageChange(safePage + 1)}
          >
            Next
          </button>
        </div>
      )}
    </nav>
  )
}

function visiblePages(currentPage: number, totalPages: number): PageItem[] {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1)

  const pages: PageItem[] = [1]
  const start = Math.max(2, currentPage - 1)
  const end = Math.min(totalPages - 1, currentPage + 1)

  if (start > 2) pages.push('ellipsis-start')
  for (let page = start; page <= end; page += 1) pages.push(page)
  if (end < totalPages - 1) pages.push('ellipsis-end')
  pages.push(totalPages)
  return pages
}
