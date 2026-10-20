/**
 * Display helpers for exact decimal strings from the API. They never convert to a JS number,
 * so no rounding can creep in.
 */

/** Indian digit grouping: 1234567 -> "12,34,567". */
function groupIndian(digits: string): string {
  if (digits.length <= 3) return digits
  const head = digits.slice(0, -3)
  const tail = digits.slice(-3)
  return `${head.replace(/\B(?=(\d{2})+(?!\d))/g, ',')},${tail}`
}

/** "2328.00" -> "₹2,328.00"; "-100.00" -> "-₹100.00". */
export function formatRupees(amount: string | null): string {
  if (amount === null || amount === '') return '-'
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(amount)
  if (!match) return amount
  const [, sign, whole, fraction] = match
  return `${sign}₹${groupIndian(whole)}${fraction ? `.${fraction}` : ''}`
}

export function formatKg(value: string | null): string {
  return value === null ? '-' : `${value} kg`
}

export function formatPercent(value: string | null): string {
  return value === null ? '-' : `${value}%`
}
