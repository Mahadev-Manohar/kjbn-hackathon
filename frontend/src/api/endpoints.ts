import { request } from './client'
import type {
  Advance,
  Crop,
  Delivery,
  DeliveryInput,
  DeliveryPreview,
  Farmer,
  Ledger,
  NoteInput,
  Page,
  Payout,
  PayoutStatement,
  PayoutStatus,
  PriceEntry,
} from './types'

export const listFarmers = (q?: string, limit = 200) =>
  request<Page<Farmer>>('GET', '/farmers', { params: { q, limit } })

export const createFarmer = (body: Omit<Farmer, 'id' | 'outstanding_advance'>) =>
  request<Farmer>('POST', '/farmers', { body })

export const listCrops = () => request<Crop[]>('GET', '/crops')

export const listPrices = (cropId?: number, grade?: string) =>
  request<Page<PriceEntry>>('GET', '/price-list', {
    params: { crop_id: cropId, grade, limit: 200 },
  })

export const addPrice = (body: {
  crop_id: number
  grade: string
  price_per_kg: string
  effective_from: string
}) => request<PriceEntry>('POST', '/price-list', { body })

export const previewDelivery = (body: DeliveryInput, signal?: AbortSignal) =>
  request<DeliveryPreview>('POST', '/deliveries/preview', { body, signal })

export const createDelivery = (body: DeliveryInput) =>
  request<Delivery>('POST', '/deliveries', { body })

export const createNote = (deliveryId: number, body: NoteInput) =>
  request<Delivery>('POST', `/deliveries/${deliveryId}/notes`, { body })

export const listPayouts = (filters: { farmerId?: number; status?: PayoutStatus } = {}) =>
  request<Page<Payout>>('GET', '/payouts', {
    params: { farmer_id: filters.farmerId, status: filters.status, limit: 100 },
  })

export const generatePayout = (farmerId: number, weekStart: string) =>
  request<PayoutStatement>('POST', '/payouts', {
    body: { farmer_id: farmerId, week_start: weekStart },
  })

export const getPayout = (id: number) => request<PayoutStatement>('GET', `/payouts/${id}`)

export const finalisePayout = (id: number) =>
  request<PayoutStatement>('POST', `/payouts/${id}/finalise`)

export const markPayoutPaid = (id: number) =>
  request<PayoutStatement>('POST', `/payouts/${id}/mark-paid`)

export const getLedger = (farmerId: number) =>
  request<Ledger>('GET', `/farmers/${farmerId}/ledger`, { params: { limit: 50 } })

export const recordAdvance = (farmerId: number, body: { amount: string; given_on: string }) =>
  request<Advance>('POST', `/farmers/${farmerId}/advances`, { body })
