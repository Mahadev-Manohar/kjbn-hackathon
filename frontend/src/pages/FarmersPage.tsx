import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { createFarmer, listFarmers } from '../api/endpoints'
import { ErrorMessage, Field, Loading, Notice, PageHeader } from '../components/common'
import { useAsync } from '../hooks/useAsync'
import { formatRupees } from '../lib/money'

export function FarmersPage() {
  const [search, setSearch] = useState('')
  const farmers = useAsync(() => listFarmers(search.trim() || undefined), [search])

  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [village, setVillage] = useState('')
  const [bank, setBank] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [added, setAdded] = useState<string | null>(null)

  async function submit() {
    setSaving(true)
    setError(null)
    setAdded(null)
    try {
      const farmer = await createFarmer({
        name,
        phone,
        village,
        bank_reference: bank.trim() || null,
      })
      setAdded(`Added ${farmer.name}.`)
      setName('')
      setPhone('')
      setVillage('')
      setBank('')
      farmers.reload()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'Could not add the farmer.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader title="Farmers">
        <Field label="Search name or village">
          <input value={search} onChange={(e) => setSearch(e.target.value)} />
        </Field>
      </PageHeader>

      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <h2 style={{ marginTop: 0 }}>Add a farmer</h2>
        <div className="form-grid">
          <Field label="Name">
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={150} />
          </Field>
          <Field label="Phone" hint="10–15 digits, optional leading +">
            <input inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} required />
          </Field>
          <Field label="Village">
            <input value={village} onChange={(e) => setVillage(e.target.value)} required maxLength={150} />
          </Field>
          <Field label="Bank reference" hint="Free text, optional">
            <input value={bank} onChange={(e) => setBank(e.target.value)} maxLength={500} />
          </Field>
          <button type="submit" className="primary" disabled={saving}>
            {saving ? 'Adding…' : 'Add farmer'}
          </button>
        </div>
        <ErrorMessage error={error} />
        {added && <Notice>{added}</Notice>}
      </form>

      {farmers.loading && <Loading />}
      <ErrorMessage error={farmers.error} onRetry={farmers.reload} />
      {farmers.data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Village</th>
                <th>Phone</th>
                <th>Bank reference</th>
                <th className="num">Advance outstanding</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {farmers.data.items.map((farmer) => (
                <tr key={farmer.id}>
                  <td>{farmer.name}</td>
                  <td>{farmer.village}</td>
                  <td>{farmer.phone}</td>
                  <td>{farmer.bank_reference ?? '-'}</td>
                  <td className="num">{formatRupees(farmer.outstanding_advance)}</td>
                  <td>
                    <Link to={`/farmers/${farmer.id}`}>Ledger</Link>
                  </td>
                </tr>
              ))}
              {farmers.data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">
                    No farmers found.
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
