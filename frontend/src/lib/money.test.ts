import { describe, expect, it } from 'vitest'
import { formatPercent, formatRupees } from './money'

describe('formatRupees', () => {
  it('keeps paise exactly and uses Indian grouping', () => {
    expect(formatRupees('2328.00')).toBe('₹2,328.00')
    expect(formatRupees('1234567.50')).toBe('₹12,34,567.50')
    expect(formatRupees('0.02')).toBe('₹0.02')
    expect(formatRupees('100000')).toBe('₹1,00,000')
  })

  it('does not lose precision on values a JS number cannot hold', () => {
    expect(formatRupees('9007199254740993.01')).toBe('₹9,00,71,99,25,47,40,993.01')
  })

  it('formats negatives (debit notes) with the sign before the symbol', () => {
    expect(formatRupees('-100.00')).toBe('-₹100.00')
  })

  it('shows a dash for missing values and passes odd input through unchanged', () => {
    expect(formatRupees(null)).toBe('-')
    expect(formatRupees('abc')).toBe('abc')
  })
})

describe('formatPercent', () => {
  it('appends the percent sign', () => {
    expect(formatPercent('3.00')).toBe('3.00%')
    expect(formatPercent(null)).toBe('-')
  })
})
