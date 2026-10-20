import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { createNote, getLedger, recordAdvance } from '../api/endpoints'
import type { Delivery, NoteInput } from '../api/types'
import { ErrorMessage, Field, Loading, Notice, PageHeader, StatusBadge } from '../components/common'
import { useAsync } from '../hooks/useAsync'
import { formatDate, todayIso } from '../lib/dates'
import { formatKg, formatRupees } from '../lib/money'

const KIND_LABEL = { DELIVERY: 'Delivery', CREDIT_NOTE: 'Credit note', DEBIT_NOTE: 'Debit note' } as const

export function FarmerLedgerPage() {
  const { farmerId } = useParams()
  const id = Number(farmerId)
  const ledger = useAsync(() => getLedger(id), [id])

  const [advanceAmount, setAdvanceAmount] = useState('')
  const [advanceDate, setAdvanceDate] = useState(todayIso())
  const [advanceError, setAdvanceError] = useState<ApiError | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [noteFor, setNoteFor] = useState<Delivery | null>(null)

  async function submitAdvance() {
    setAdvanceError(null)
    setMessage(null)
    try {
      await recordAdvance(id, { amount: advanceAmount.trim(), given_on: advanceDate })
      setAdvanceAmount('')
      setMessage('Advance recorded.')
      ledger.reload()
    } catch (caught) {
      setAdvanceError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'Could not record the advance.'))
    }
  }

  if (!Number.isInteger(id)) return <p>Invalid farmer id.</p>
  if (ledger.loading && !ledger.data) return <Loading />
  if (ledger.error && !ledger.data) return <ErrorMessage error={ledger.error} onRetry={ledger.reload} />
  const data = ledger.data
  if (!data) return null

  return (
    <>
      <PageHeader title={`Ledger · ${data.farmer.name}`} />
      <p className="muted">
        {data.farmer.village} · {data.farmer.phone}
        {data.farmer.bank_reference ? ` · ${data.farmer.bank_reference}` : ''}
      </p>
      <ErrorMessage error={ledger.error} onRetry={ledger.reload} />
      {message && <Notice>{message}</Notice>}

      <div className="grid">
        <section className="card">
          <h2 style={{ marginTop: 0 }}>Advance balance</h2>
          <dl className="sum-list">
            <dt>Advances given</dt>
            <dd>{formatRupees(data.total_advances)}</dd>
            <dt>Recovered (finalised payouts)</dt>
            <dd>− {formatRupees(data.total_recovered)}</dd>
            <dt className="total">Outstanding</dt>
            <dd className="total">{formatRupees(data.outstanding_advance)}</dd>
          </dl>
        </section>
        <form
          className="card"
          onSubmit={(event) => {
            event.preventDefault()
            void submitAdvance()
          }}
        >
          <h2 style={{ marginTop: 0 }}>Record an advance</h2>
          <div className="form-grid">
            <Field label="Amount (₹)">
              <input inputMode="decimal" value={advanceAmount} onChange={(e) => setAdvanceAmount(e.target.value)} required />
            </Field>
            <Field label="Given on">
              <input type="date" value={advanceDate} onChange={(e) => setAdvanceDate(e.target.value)} required />
            </Field>
            <button type="submit" className="primary">
              Record
            </button>
          </div>
          <ErrorMessage error={advanceError} />
        </form>
      </div>

      <h2>Deliveries and notes</h2>
      <Shown shown={data.deliveries.length} total={data.deliveries_total} limit={data.limit} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Item</th>
              <th className="num">Net weight</th>
              <th className="num">Amount</th>
              <th>Payout</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.deliveries.map((delivery) => (
              <tr key={delivery.id}>
                <td>{formatDate(delivery.delivered_on)}</td>
                <td>
                  {KIND_LABEL[delivery.kind]} #{delivery.id} · {delivery.crop_name} {delivery.grade}
                  {delivery.reason && <div className="muted">{delivery.reason}</div>}
                  {delivery.references_delivery_id && (
                    <div className="muted">Corrects delivery #{delivery.references_delivery_id}</div>
                  )}
                </td>
                <td className="num">{formatKg(delivery.net_kg)}</td>
                <td className="num">{formatRupees(delivery.amount)}</td>
                <td>
                  {delivery.payout_id && delivery.payout_status ? (
                    <Link to={`/payouts/${delivery.payout_id}`}>
                      <StatusBadge status={delivery.payout_status} />
                    </Link>
                  ) : (
                    <span className="muted">Not in a payout</span>
                  )}
                </td>
                <td>
                  {delivery.kind === 'DELIVERY' &&
                    (delivery.payout_status === 'Finalised' || delivery.payout_status === 'Paid') && (
                      <button type="button" onClick={() => setNoteFor(delivery)}>
                        Issue note
                      </button>
                    )}
                </td>
              </tr>
            ))}
            {data.deliveries.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No deliveries yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="muted">
        A delivery in a finalised payout cannot be edited; correct it with a credit or debit note.
      </p>

      {noteFor && (
        <NoteForm
          delivery={noteFor}
          onCancel={() => setNoteFor(null)}
          onDone={(text) => {
            setNoteFor(null)
            setMessage(text)
            ledger.reload()
          }}
        />
      )}

      <h2>Payouts</h2>
      <Shown shown={data.payouts.length} total={data.payouts_total} limit={data.limit} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Week</th>
              <th>Status</th>
              <th className="num">Gross</th>
              <th className="num">Advance recovered</th>
              <th className="num">Net</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.payouts.map((payout) => (
              <tr key={payout.id}>
                <td>
                  {formatDate(payout.week_start)} – {formatDate(payout.week_end)}
                </td>
                <td>
                  <StatusBadge status={payout.status} />
                </td>
                <td className="num">{formatRupees(payout.gross_amount)}</td>
                <td className="num">{formatRupees(payout.advance_deduction)}</td>
                <td className="num">{formatRupees(payout.net_amount)}</td>
                <td>
                  <Link to={`/payouts/${payout.id}`}>Statement</Link>
                </td>
              </tr>
            ))}
            {data.payouts.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No payouts yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h2>Advances</h2>
      <Shown shown={data.advances.length} total={data.advances_total} limit={data.limit} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Given on</th>
              <th className="num">Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.advances.map((advance) => (
              <tr key={advance.id}>
                <td>{formatDate(advance.given_on)}</td>
                <td className="num">{formatRupees(advance.amount)}</td>
              </tr>
            ))}
            {data.advances.length === 0 && (
              <tr>
                <td colSpan={2} className="muted">
                  No advances recorded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}

function Shown({ shown, total, limit }: { shown: number; total: number; limit: number }) {
  if (total <= shown) return null
  return (
    <p className="muted">
      Showing the newest {shown} of {total} (limit {limit}).
    </p>
  )
}

function NoteForm({
  delivery,
  onCancel,
  onDone,
}: {
  delivery: Delivery
  onCancel: () => void
  onDone: (message: string) => void
}) {
  const [kind, setKind] = useState<NoteInput['kind']>('CREDIT_NOTE')
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function submit() {
    setSaving(true)
    setError(null)
    try {
      const note = await createNote(delivery.id, { kind, amount: amount.trim(), reason: reason.trim() })
      onDone(
        `${KIND_LABEL[note.kind]} #${note.id} of ${formatRupees(note.amount)} created. It will be included in the payout for the week of ${formatDate(note.delivered_on)}.`,
      )
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'Could not create the note.'))
      setSaving(false)
    }
  }

  return (
    <form
      className="card"
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
    >
      <h2 style={{ marginTop: 0 }}>
        Note for delivery #{delivery.id} ({delivery.crop_name} {delivery.grade}, {formatRupees(delivery.amount)})
      </h2>
      <p className="muted">
        A credit note adds money for the farmer; a debit note deducts. It joins the next open payout.
      </p>
      <div className="form-grid">
        <Field label="Type">
          <select value={kind} onChange={(e) => setKind(e.target.value as NoteInput['kind'])}>
            <option value="CREDIT_NOTE">Credit note (pay more)</option>
            <option value="DEBIT_NOTE">Debit note (deduct)</option>
          </select>
        </Field>
        <Field label="Amount (₹)" hint="Positive, up to 2 decimals">
          <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} required />
        </Field>
        <Field label="Reason">
          <input value={reason} onChange={(e) => setReason(e.target.value)} required minLength={3} maxLength={500} />
        </Field>
      </div>
      <ErrorMessage error={error} />
      <div className="actions" style={{ marginTop: 12 }}>
        <button type="submit" className="primary" disabled={saving}>
          {saving ? 'Saving…' : 'Create note'}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
    </form>
  )
}
