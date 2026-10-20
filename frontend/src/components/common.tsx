import type { ReactNode } from 'react'
import type { ApiError } from '../api/client'
import type { PayoutStatus } from '../api/types'

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <p className="muted" role="status">
      {label}
    </p>
  )
}

/** Shows what went wrong and what to do about it, plus the request id for support. */
export function ErrorMessage({ error, onRetry }: { error: ApiError | null; onRetry?: () => void }) {
  if (!error) return null
  return (
    <div className="alert alert-error" role="alert">
      <strong>{error.message}</strong>
      {error.fields.length > 0 && (
        <ul>
          {error.fields.map((problem) => (
            <li key={`${problem.field}:${problem.message}`}>
              {problem.field ? `${problem.field}: ` : ''}
              {problem.message}
            </li>
          ))}
        </ul>
      )}
      {(onRetry || error.requestId) && (
        <p className="alert-meta">
          {onRetry && (
            <button type="button" className="link" onClick={onRetry}>
              Try again
            </button>
          )}
          {error.requestId && <span> Reference: {error.requestId}</span>}
        </p>
      )}
    </div>
  )
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="alert alert-ok" role="status">
      {children}
    </div>
  )
}

export function StatusBadge({ status }: { status: PayoutStatus }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{status}</span>
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="page-header">
      <h1>{title}</h1>
      {children}
    </div>
  )
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: ReactNode
}) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}
