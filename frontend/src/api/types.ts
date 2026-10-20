// Money, weights and percentages arrive as exact decimal strings (e.g. "2328.00").
// The UI only displays them; every calculation happens in the backend.

export type DeliveryKind = 'DELIVERY' | 'CREDIT_NOTE' | 'DEBIT_NOTE'
export type PayoutStatus = 'Draft' | 'Finalised' | 'Paid'

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface Farmer {
  id: number
  name: string
  phone: string
  village: string
  bank_reference: string | null
}

export interface Crop {
  id: number
  name: string
  base_moisture_threshold: string
  max_moisture_accepted: string
  grades: string[]
}

export interface PriceEntry {
  id: number
  crop_id: number
  grade: string
  price_per_kg: string
  effective_from: string
}

export interface DeliveryInput {
  farmer_id?: number
  crop_id: number
  grade: string
  gross_kg: string
  moisture: string
  delivered_on: string
}

export interface DeliveryPreview {
  crop_id: number
  crop_name: string
  grade: string
  delivered_on: string
  gross_kg: string
  moisture: string
  moisture_threshold: string
  deduction_pct: string
  deduction_kg: string
  net_kg: string
  applied_price: string
  price_list_entry_id: number
  amount: string
}

export interface DeliveryLine {
  id: number
  farmer_id: number
  crop_id: number
  crop_name: string
  grade: string
  kind: DeliveryKind
  delivered_on: string
  gross_kg: string | null
  moisture: string | null
  deduction_pct: string | null
  deduction_kg: string | null
  net_kg: string | null
  applied_price: string | null
  price_list_entry_id: number | null
  amount: string
  payout_id: number | null
  references_delivery_id: number | null
  reason: string | null
}

export interface Delivery extends DeliveryLine {
  payout_status: PayoutStatus | null
}

export interface Payout {
  id: number
  farmer_id: number
  farmer_name: string
  week_start: string
  week_end: string
  status: PayoutStatus
  gross_amount: string
  recovery_cap: string
  outstanding_before: string
  advance_deduction: string
  net_amount: string
  outstanding_after: string
  finalised_at: string | null
  paid_at: string | null
}

export interface PayoutStatement extends Payout {
  deliveries: DeliveryLine[]
}

export interface Advance {
  id: number
  farmer_id: number
  amount: string
  given_on: string
}

export interface Ledger {
  farmer: Farmer
  total_advances: string
  total_recovered: string
  outstanding_advance: string
  limit: number
  deliveries_total: number
  advances_total: number
  payouts_total: number
  deliveries: Delivery[]
  advances: Advance[]
  payouts: Payout[]
}

export interface NoteInput {
  kind: 'CREDIT_NOTE' | 'DEBIT_NOTE'
  amount: string
  reason: string
}
