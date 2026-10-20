import { useState } from 'react'
import { ApiError } from '../api/client'
import { addPrice, listCrops, listPrices } from '../api/endpoints'
import type { Crop, PriceEntry } from '../api/types'
import { ErrorMessage, Field, Loading, Notice, PageHeader } from '../components/common'
import { useAsync } from '../hooks/useAsync'
import { formatDate, todayIso } from '../lib/dates'
import { formatRupees } from '../lib/money'

interface Group {
  key: string
  crop: string
  grade: string
  entries: PriceEntry[]
}

function groupHistory(entries: PriceEntry[], crops: Crop[]): Group[] {
  const names = new Map(crops.map((crop) => [crop.id, crop.name]))
  const groups = new Map<string, Group>()
  for (const entry of entries) {
    const key = `${entry.crop_id}:${entry.grade}`
    const group = groups.get(key) ?? {
      key,
      crop: names.get(entry.crop_id) ?? `Crop ${entry.crop_id}`,
      grade: entry.grade,
      entries: [],
    }
    group.entries.push(entry) // the API returns newest effective date first
    groups.set(key, group)
  }
  return [...groups.values()].sort((a, b) => a.crop.localeCompare(b.crop) || a.grade.localeCompare(b.grade))
}

export function PriceListPage() {
  const crops = useAsync(() => listCrops(), [])
  const [filterCrop, setFilterCrop] = useState('')
  const prices = useAsync(
    () => listPrices(filterCrop ? Number(filterCrop) : undefined),
    [filterCrop],
  )

  const [cropId, setCropId] = useState('')
  const [grade, setGrade] = useState('')
  const [price, setPrice] = useState('')
  const [effectiveFrom, setEffectiveFrom] = useState(todayIso())
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [added, setAdded] = useState<string | null>(null)

  const formCrop = crops.data?.find((crop) => String(crop.id) === cropId) ?? null

  async function submit() {
    setSaving(true)
    setError(null)
    setAdded(null)
    try {
      const entry = await addPrice({
        crop_id: Number(cropId),
        grade,
        price_per_kg: price.trim(),
        effective_from: effectiveFrom,
      })
      setAdded(`Added ${formatRupees(entry.price_per_kg)}/kg effective ${formatDate(entry.effective_from)}.`)
      setPrice('')
      prices.reload()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'Could not add the price.'))
    } finally {
      setSaving(false)
    }
  }

  if (crops.loading) return <Loading />
  if (crops.error) return <ErrorMessage error={crops.error} onRetry={crops.reload} />

  const groups = groupHistory(prices.data?.items ?? [], crops.data ?? [])

  return (
    <>
      <PageHeader title="Price list">
        <Field label="Show crop">
          <select value={filterCrop} onChange={(e) => setFilterCrop(e.target.value)}>
            <option value="">All crops</option>
            {crops.data?.map((crop) => (
              <option key={crop.id} value={crop.id}>
                {crop.name}
              </option>
            ))}
          </select>
        </Field>
      </PageHeader>

      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault()
          void submit()
        }}
      >
        <h2 style={{ marginTop: 0 }}>Add a price</h2>
        <p className="muted">
          Prices are never overwritten: a new entry applies to deliveries on or after its effective date.
          Back-dated entries are allowed; deliveries already saved keep the price they used.
        </p>
        <div className="form-grid">
          <Field label="Crop">
            <select
              value={cropId}
              onChange={(e) => {
                setCropId(e.target.value)
                setGrade(crops.data?.find((c) => String(c.id) === e.target.value)?.grades[0] ?? '')
              }}
              required
            >
              <option value="">Select crop…</option>
              {crops.data?.map((crop) => (
                <option key={crop.id} value={crop.id}>
                  {crop.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Grade">
            <select value={grade} onChange={(e) => setGrade(e.target.value)} required disabled={!formCrop}>
              {!formCrop && <option value="">Choose a crop first</option>}
              {formCrop?.grades.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Price per kg (₹)" hint="Up to 2 decimals">
            <input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} required />
          </Field>
          <Field label="Effective from">
            <input type="date" value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.target.value)} required />
          </Field>
          <button type="submit" className="primary" disabled={saving}>
            {saving ? 'Adding…' : 'Add price'}
          </button>
        </div>
        <ErrorMessage error={error} />
        {added && <Notice>{added}</Notice>}
      </form>

      {prices.loading && <Loading />}
      <ErrorMessage error={prices.error} onRetry={prices.reload} />
      {!prices.loading && !prices.error && groups.length === 0 && <p className="muted">No prices yet.</p>}
      {groups.map((group) => (
        <section key={group.key}>
          <h2>
            {group.crop} · grade {group.grade}
          </h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Effective from</th>
                  <th className="num">Price per kg</th>
                  <th>Entry</th>
                </tr>
              </thead>
              <tbody>
                {group.entries.map((entry) => (
                  <tr key={entry.id}>
                    <td>{formatDate(entry.effective_from)}</td>
                    <td className="num">{formatRupees(entry.price_per_kg)}</td>
                    <td>#{entry.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </>
  )
}
