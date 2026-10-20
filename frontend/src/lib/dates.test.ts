import { describe, expect, it } from 'vitest'
import { formatDate, formatDateTimeIST, mondayOf } from './dates'

describe('formatDate', () => {
  it('formats an ISO date without any timezone shift', () => {
    expect(formatDate('2026-10-19')).toBe('19 Oct 2026')
    expect(formatDate('2026-01-01')).toBe('1 Jan 2026')
  })

  it('returns malformed input unchanged', () => {
    expect(formatDate('nonsense')).toBe('nonsense')
  })
})

describe('formatDateTimeIST', () => {
  it('shows stored UTC timestamps in IST', () => {
    // 10:00 UTC is 15:30 IST
    expect(formatDateTimeIST('2026-10-20T10:00:00+00:00')).toMatch(/20 Oct 2026.*3:30 pm IST/i)
  })

  it('handles missing values', () => {
    expect(formatDateTimeIST(null)).toBe('-')
  })
})

describe('mondayOf', () => {
  it('snaps any day to the Monday of its Monday-Sunday week', () => {
    expect(mondayOf('2026-10-19')).toBe('2026-10-19')
    expect(mondayOf('2026-10-25')).toBe('2026-10-19')
    expect(mondayOf('2026-10-26')).toBe('2026-10-26')
    expect(mondayOf('2026-11-01')).toBe('2026-10-26')
  })
})
