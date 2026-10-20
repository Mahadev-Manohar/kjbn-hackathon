import { getTestClock } from './clock'

const IST = 'Asia/Kolkata'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "2026-10-19" -> "19 Oct 2026". Pure string handling, so no timezone can shift the day. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-')
  const monthName = MONTHS[Number(month) - 1]
  if (!year || !monthName || !day) return isoDate
  return `${Number(day)} ${monthName} ${year}`
}

/** A stored UTC timestamp shown in IST, e.g. "20 Oct 2026, 03:30 pm IST". */
export function formatDateTimeIST(isoTimestamp: string | null): string {
  if (!isoTimestamp) return '-'
  const moment = new Date(isoTimestamp)
  if (Number.isNaN(moment.getTime())) return isoTimestamp
  const text = new Intl.DateTimeFormat('en-IN', {
    timeZone: IST,
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  }).format(moment)
  return `${text} IST`
}

/** Calendar date in IST for an instant, as YYYY-MM-DD. */
function istDate(moment: Date): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: IST,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(moment)
}

/**
 * Today's date for form defaults. It follows the reviewer clock when one is set; the API still
 * decides what is valid.
 */
export function todayIso(): string {
  const override = getTestClock()
  if (override) {
    if (/^\d{4}-\d{2}-\d{2}$/.test(override)) return override
    const moment = new Date(override)
    // A datetime without an offset is read as IST by the API; its date part is already IST.
    if (!Number.isNaN(moment.getTime())) {
      return /(Z|[+-]\d{2}:?\d{2})$/.test(override) ? istDate(moment) : override.slice(0, 10)
    }
  }
  return istDate(new Date())
}

/** Monday of the week containing an ISO date (display helper for the week picker). */
export function mondayOf(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  const offset = (date.getUTCDay() + 6) % 7
  date.setUTCDate(date.getUTCDate() - offset)
  return date.toISOString().slice(0, 10)
}
