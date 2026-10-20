import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { finalisePayout, generatePayout, getPayout, markPayoutPaid } from '../api/endpoints'
import type { PayoutStatement } from '../api/types'
import { ErrorMessage, Loading, Notice, PageHeader, StatusBadge } from '../components/common'
import { useAsync } from '../hooks/useAsync'
import { formatDate, formatDateTimeIST } from '../lib/dates'
import { formatKg, formatPercent, formatRupees } from '../lib/money'

const KIND_LABEL = { DELIVERY: 'Delivery', CREDIT_NOTE: 'Credit note', DEBIT_NOTE: 'Debit note' } as const

export function PayoutStatementPage() {
  const { payoutId } = useParams()
  const id = Number(payoutId)
  const payout = useAsync(() => getPayout(id), [id])
  const [override, setOverride] = useState<PayoutStatement | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const current = override ?? payout.data

  async function run(action: () => Promise<PayoutStatement>, done: string) {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      setOverride(await action())
      setMessage(done)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'The action failed.'))
    } finally {
      setBusy(false)
    }
  }

  if (!Number.isInteger(id)) return <p>Invalid payout id.</p>
  if (payout.loading && !current) return <Loading />
  if (payout.error && !current) return <ErrorMessage error={payout.error} onRetry={payout.reload} />
  if (!current) return null

  const lines = current.deliveries
  return (
    <>
      <PageHeader title={`Payout statement · ${current.farmer_name}`}>
        <StatusBadge status={current.status} />
      </PageHeader>
      <p>
        Week {formatDate(current.week_start)} – {formatDate(current.week_end)} ·{' '}
        <Link to={`/farmers/${current.farmer_id}`}>Farmer ledger</Link> · <Link to="/payouts">All payouts</Link>
      </p>

      <ErrorMessage error={error} />
      {message && <Notice>{message}</Notice>}

      <div className="actions" style={{ marginBottom: 16 }}>
        {current.status === 'Draft' && (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void run(() => generatePayout(current.farmer_id, current.week_start), 'Draft refreshed.')
              }
            >
              Refresh draft
            </button>
            <button
              type="button"
              className="primary"
              disabled={busy}
              onClick={() => {
                if (
                  window.confirm(
                    'Finalise this payout? It becomes immutable and the advance deduction is applied to the farmer.',
                  )
                ) {
                  void run(() => finalisePayout(current.id), 'Payout finalised.')
                }
              }}
            >
              Finalise payout
            </button>
          </>
        )}
        {current.status === 'Finalised' && (
          <button
            type="button"
            className="primary"
            disabled={busy}
            onClick={() => void run(() => markPayoutPaid(current.id), 'Marked as paid.')}
          >
            Mark as paid
          </button>
        )}
        {current.status === 'Paid' && <span className="muted">Paid {formatDateTimeIST(current.paid_at)}</span>}
        {current.finalised_at && (
          <span className="muted">Finalised {formatDateTimeIST(current.finalised_at)}</span>
        )}
      </div>

      <h2>Lines</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Item</th>
              <th className="num">Gross</th>
              <th className="num">Moisture</th>
              <th className="num">Deduction</th>
              <th className="num">Net</th>
              <th className="num">Price</th>
              <th className="num">Amount</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.id}>
                <td>{formatDate(line.delivered_on)}</td>
                <td>
                  {KIND_LABEL[line.kind]} #{line.id} · {line.crop_name} {line.grade}
                  {line.reason && <div className="muted">{line.reason}</div>}
                  {line.references_delivery_id && (
                    <div className="muted">Corrects delivery #{line.references_delivery_id}</div>
                  )}
                </td>
                <td className="num">{formatKg(line.gross_kg)}</td>
                <td className="num">{formatPercent(line.moisture)}</td>
                <td className="num">
                  {line.deduction_pct === null ? '-' : `${formatPercent(line.deduction_pct)} = ${formatKg(line.deduction_kg)}`}
                </td>
                <td className="num">{formatKg(line.net_kg)}</td>
                <td className="num">{line.applied_price === null ? '-' : `${formatRupees(line.applied_price)}/kg`}</td>
                <td className="num">{formatRupees(line.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>How the net amount is reached</h2>
      <section className="card">
        <dl className="sum-list">
          <dt>Gross amount (sum of the {lines.length} line{lines.length === 1 ? '' : 's'} above)</dt>
          <dd>{formatRupees(current.gross_amount)}</dd>
          <dt>Recovery cap (30% of gross)</dt>
          <dd>{formatRupees(current.recovery_cap)}</dd>
          <dt>Advance outstanding {current.status === 'Draft' ? 'now' : 'when finalised'}</dt>
          <dd>{formatRupees(current.outstanding_before)}</dd>
          <dt>Advance deduction (the lesser of the two)</dt>
          <dd>− {formatRupees(current.advance_deduction)}</dd>
          <dt className="total">Net payable</dt>
          <dd className="total">{formatRupees(current.net_amount)}</dd>
          <dt>Advance outstanding after this payout</dt>
          <dd>{formatRupees(current.outstanding_after)}</dd>
          {current.status === 'Draft' && (
            <dd className="rule">
              Draft figures are a preview. The advance is only reduced once the payout is finalised, and
              the deduction is recalculated then against the advance still outstanding.
            </dd>
          )}
        </dl>
      </section>
    </>
  )
}
