import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, isAbort } from '../api/client'
import { createDelivery, listCrops, listFarmers, previewDelivery } from '../api/endpoints'
import type { Delivery, DeliveryInput, DeliveryPreview } from '../api/types'
import { ErrorMessage, Field, Loading, Notice, PageHeader } from '../components/common'
import { useAsync } from '../hooks/useAsync'
import { formatDate, todayIso } from '../lib/dates'
import { formatKg, formatPercent, formatRupees } from '../lib/money'

const PREVIEW_DELAY_MS = 400

type PreviewState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; key: string; data: DeliveryPreview }
  | { status: 'error'; error: ApiError }

export function DeliveryEntryPage() {
  const farmers = useAsync(() => listFarmers(), [])
  const crops = useAsync(() => listCrops(), [])

  const [farmerId, setFarmerId] = useState('')
  const [cropId, setCropId] = useState('')
  const [grade, setGrade] = useState('')
  const [grossKg, setGrossKg] = useState('')
  const [moisture, setMoisture] = useState('')
  const [deliveredOn, setDeliveredOn] = useState(todayIso())
  const [preview, setPreview] = useState<PreviewState>({ status: 'idle' })
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<ApiError | null>(null)
  const [saved, setSaved] = useState<Delivery | null>(null)

  const selectedCrop = crops.data?.find((crop) => String(crop.id) === cropId) ?? null

  const input: DeliveryInput | null = useMemo(() => {
    if (!farmerId || !cropId || !grade || !grossKg.trim() || !moisture.trim() || !deliveredOn) {
      return null
    }
    return {
      farmer_id: Number(farmerId),
      crop_id: Number(cropId),
      grade,
      gross_kg: grossKg.trim(),
      moisture: moisture.trim(),
      delivered_on: deliveredOn,
    }
  }, [farmerId, cropId, grade, grossKg, moisture, deliveredOn])
  const inputKey = input ? JSON.stringify(input) : ''

  // Live preview: the backend calculates it, so what is shown is what will be saved.
  useEffect(() => {
    if (!input) {
      setPreview({ status: 'idle' })
      return
    }
    const controller = new AbortController()
    setPreview({ status: 'loading' })
    const timer = window.setTimeout(() => {
      previewDelivery(input, controller.signal)
        .then((data) => setPreview({ status: 'ok', key: inputKey, data }))
        .catch((caught: unknown) => {
          if (isAbort(caught)) return
          setPreview({
            status: 'error',
            error: caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'Preview failed.'),
          })
        })
    }, PREVIEW_DELAY_MS)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
    // `input` is derived from `inputKey`; depending on the key avoids refetching on identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inputKey])

  function chooseCrop(value: string) {
    setCropId(value)
    const crop = crops.data?.find((item) => String(item.id) === value)
    setGrade(crop?.grades[0] ?? '')
  }

  async function save() {
    if (!input) return
    setSaving(true)
    setSaveError(null)
    try {
      const delivery = await createDelivery(input)
      setSaved(delivery)
      setGrossKg('')
      setMoisture('')
    } catch (caught) {
      setSaveError(caught instanceof ApiError ? caught : new ApiError(0, 'unknown', 'Save failed.'))
    } finally {
      setSaving(false)
    }
  }

  if (farmers.loading || crops.loading) return <Loading />
  const loadError = farmers.error ?? crops.error
  if (loadError) {
    return <ErrorMessage error={loadError} onRetry={() => { farmers.reload(); crops.reload() }} />
  }

  const canSave = preview.status === 'ok' && preview.key === inputKey && !saving

  return (
    <>
      <PageHeader title="New delivery" />
      <div className="grid">
        <form
          className="card"
          onSubmit={(event) => {
            event.preventDefault()
            void save()
          }}
        >
          <div className="form-grid">
            <Field label="Farmer">
              <select value={farmerId} onChange={(e) => { setFarmerId(e.target.value); setSaved(null) }} required>
                <option value="">Select farmer…</option>
                {farmers.data?.items.map((farmer) => (
                  <option key={farmer.id} value={farmer.id}>
                    {farmer.name} · {farmer.village}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Crop">
              <select value={cropId} onChange={(e) => chooseCrop(e.target.value)} required>
                <option value="">Select crop…</option>
                {crops.data?.map((crop) => (
                  <option key={crop.id} value={crop.id}>
                    {crop.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Grade">
              <select value={grade} onChange={(e) => setGrade(e.target.value)} required disabled={!selectedCrop}>
                {!selectedCrop && <option value="">Choose a crop first</option>}
                {selectedCrop?.grades.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Gross weight (kg)" hint="Up to 3 decimals">
              <input inputMode="decimal" value={grossKg} onChange={(e) => setGrossKg(e.target.value)} required />
            </Field>
            <Field
              label="Moisture (%)"
              hint={
                selectedCrop
                  ? `Threshold ${selectedCrop.base_moisture_threshold}%, maximum ${selectedCrop.max_moisture_accepted}%`
                  : 'Up to 2 decimals'
              }
            >
              <input inputMode="decimal" value={moisture} onChange={(e) => setMoisture(e.target.value)} required />
            </Field>
            <Field label="Delivered on">
              <input type="date" value={deliveredOn} onChange={(e) => setDeliveredOn(e.target.value)} required />
            </Field>
          </div>
          <ErrorMessage error={saveError} />
          {saved && (
            <Notice>
              Saved delivery #{saved.id}: {formatRupees(saved.amount)} for {saved.crop_name} grade {saved.grade}.{' '}
              <Link to={`/farmers/${saved.farmer_id}`}>Open ledger</Link>
            </Notice>
          )}
          <div className="actions">
            <button type="submit" className="primary" disabled={!canSave}>
              {saving ? 'Saving…' : 'Save delivery'}
            </button>
            {!canSave && !saving && (
              <span className="muted">Save unlocks once the preview on the right is calculated.</span>
            )}
          </div>
        </form>

        <section className="card" aria-live="polite" aria-label="Calculated preview">
          <h2 style={{ marginTop: 0 }}>Preview</h2>
          <PreviewPanel state={preview} filled={input !== null} />
        </section>
      </div>
    </>
  )
}

function PreviewPanel({ state, filled }: { state: PreviewState; filled: boolean }) {
  if (!filled) return <p className="muted">Fill in every field to see the price, deduction and amount.</p>
  if (state.status === 'loading' || state.status === 'idle') return <Loading label="Calculating…" />
  if (state.status === 'error') return <ErrorMessage error={state.error} />
  const p = state.data
  return (
    <dl className="sum-list">
      <dt>Price found</dt>
      <dd>
        {formatRupees(p.applied_price)}/kg (entry #{p.price_list_entry_id})
      </dd>
      <dt>Delivery date</dt>
      <dd>{formatDate(p.delivered_on)}</dd>
      <dt>Gross weight</dt>
      <dd>{formatKg(p.gross_kg)}</dd>
      <dt>Moisture (threshold {p.moisture_threshold}%)</dt>
      <dd>{formatPercent(p.moisture)}</dd>
      <dt>Moisture deduction</dt>
      <dd>
        {formatPercent(p.deduction_pct)} = {formatKg(p.deduction_kg)}
      </dd>
      <dt>Net weight</dt>
      <dd>{formatKg(p.net_kg)}</dd>
      <dt className="total">Amount</dt>
      <dd className="total">{formatRupees(p.amount)}</dd>
    </dl>
  )
}
