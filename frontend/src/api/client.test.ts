import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, request } from './client'

function respond(status: number, body: unknown) {
  vi.stubGlobal('window', { location: { origin: 'http://localhost' } })
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request', () => {
  it('turns the backend error shape into an ApiError', async () => {
    respond(422, {
      error: {
        code: 'price_not_found',
        message: 'No price list entry for Maize grade C',
        details: {},
        request_id: 'abc123',
      },
    })
    const failure = await request('GET', '/x').catch((caught: unknown) => caught)
    expect(failure).toBeInstanceOf(ApiError)
    expect(failure).toMatchObject({
      status: 422,
      code: 'price_not_found',
      message: 'No price list entry for Maize grade C',
      requestId: 'abc123',
    })
  })

  it('exposes per-field validation problems', async () => {
    respond(422, {
      error: {
        code: 'validation_error',
        message: 'Request validation failed',
        details: { fields: [{ field: 'gross_kg', message: 'Input should be a valid decimal' }] },
        request_id: 'r1',
      },
    })
    const failure = (await request('POST', '/x', { body: {} }).catch((c: unknown) => c)) as ApiError
    expect(failure.fields).toEqual([{ field: 'gross_kg', message: 'Input should be a valid decimal' }])
  })

  it('gives a readable message when the server is unreachable', async () => {
    vi.stubGlobal('window', { location: { origin: 'http://localhost' } })
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    const failure = (await request('GET', '/x').catch((c: unknown) => c)) as ApiError
    expect(failure.code).toBe('network_error')
    expect(failure.message).toMatch(/Cannot reach the server/)
  })

  it('falls back to a generic message for a non-JSON error page', async () => {
    vi.stubGlobal('window', { location: { origin: 'http://localhost' } })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>bad gateway</html>', { status: 502 })))
    const failure = (await request('GET', '/x').catch((c: unknown) => c)) as ApiError
    expect(failure.status).toBe(502)
    expect(failure.message).toMatch(/502/)
  })

  it('sends decimal strings untouched', async () => {
    respond(200, { ok: true })
    await request('POST', '/x', { body: { gross_kg: '33.333' } })
    const sent = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1] as RequestInit
    expect(sent.body).toBe('{"gross_kg":"33.333"}')
  })
})
