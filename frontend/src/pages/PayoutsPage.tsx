import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { generatePayout, listFarmers, listPayouts } from '../api/endpoints'
import type { PayoutStatus } from '../api/types'
import { ErrorMessage, Field, Loading, PageHeader, StatusBadge } from '../components/common'
import { useAsync } from '../hooks/useAsync'
import { formatDate, mondayOf, todayIso } from '../lib/dates'
import { formatRupees } from '../lib/money'

export function PayoutsPage() {
  const navigate = useNavigate()
  const farmers = useAsync(() => listFarmers(), [])
  const [filterFarmer, setFilterFarmer] = useState('')
  const [filterStatus, setFilterStatus] = useState<PayoutStatus | ''>('')
  const payouts = useAsync(
    () =>
      listPayouts({
        farmerId: filterFarmer ? Number(filterFarmer) : undefined,
        status: filterStatus || undefined,
      }),
    [filterFarmer, filterStatus],
  )

  const [farmerId, setFarmerId] = useState('')
  // Convenience default only: the backend decides whether a week is valid.
  const [weekStart, setWeekStart] = useState(mondayOf(todayIso()))
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  async function generate() {
    setGenerating(true)
    setError(null)
    try {
      const payout = await generatePayout(Number(farmerId), weekStart)
      navigate(`/payouts/${payout.id}`)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'Could not generate the payout.'))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <>
      <PageHeader title="Weekly payouts" />

      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault()
          void generate()
        }}
      >
        <h2 style={{ marginTop: 0 }}>Generate a payout</h2>
        <p className="muted">
          Collects the farmer's unpaid deliveries for a Monday–Sunday week. Running it again on a Draft
          refreshes it.
        </p>
        <div className="form-grid">
          <Field label="Farmer">
            <select value={farmerId} onChange={(e) => setFarmerId(e.target.value)} required>
              <option value="">Select farmer…</option>
              {farmers.data?.items.map((farmer) => (
                <option key={farmer.id} value={farmer.id}>
                  {farmer.name} · {farmer.village}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Week starting (Monday)">
            <input type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} required />
          </Field>
          <button type="submit" className="primary" disabled={generating || !farmerId}>
            {generating ? 'Generating…' : 'Generate / refresh draft'}
          </button>
        </div>
        <ErrorMessage error={error} />
      </form>

      <div className="form-grid" style={{ marginBottom: 12 }}>
        <Field label="Filter by farmer">
          <select value={filterFarmer} onChange={(e) => setFilterFarmer(e.target.value)}>
            <option value="">All farmers</option>
            {farmers.data?.items.map((farmer) => (
              <option key={farmer.id} value={farmer.id}>
                {farmer.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Filter by status">
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as PayoutStatus | '')}>
            <option value="">All statuses</option>
            <option value="Draft">Draft</option>
            <option value="Finalised">Finalised</option>
            <option value="Paid">Paid</option>
          </select>
        </Field>
      </div>

      {payouts.loading && <Loading />}
      <ErrorMessage error={payouts.error} onRetry={payouts.reload} />
      {payouts.data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Week</th>
                <th>Farmer</th>
                <th>Status</th>
                <th className="num">Gross</th>
                <th className="num">Advance recovered</th>
                <th className="num">Net</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {payouts.data.items.map((payout) => (
                <tr key={payout.id}>
                  <td>
                    {formatDate(payout.week_start)} – {formatDate(payout.week_end)}
                  </td>
                  <td>{payout.farmer_name}</td>
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
              {payouts.data.items.length === 0 && (
                <tr>
                  <td colSpan={7} className="muted">
                    No payouts yet. Generate one above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
