import { getTestClock } from '../lib/clock'

// Set VITE_API_BASE_URL per environment. The localhost fallback only applies to `npm run dev`.
const configuredBase: string | undefined = import.meta.env.VITE_API_BASE_URL
export const API_BASE = (
  configuredBase ?? (import.meta.env.DEV ? 'http://localhost:8001' : '')
).replace(/\/$/, '')

export interface FieldProblem {
  field: string
  message: string
}

/** Mirrors the backend's single error shape: {error: {code, message, details, request_id}}. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: FieldProblem[]
  readonly requestId: string | null

  constructor(
    status: number,
    code: string,
    message: string,
    fields: FieldProblem[] = [],
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
    this.requestId = requestId
  }
}

type Params = Record<string, string | number | undefined | null>

interface RequestOptions {
  body?: unknown
  params?: Params
  signal?: AbortSignal
}

function buildUrl(path: string, params?: Params): string {
  const url = new URL(`${API_BASE}/api/v1${path}`, window.location.origin)
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
  }
  return url.toString()
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const payload = await response.json()
    const error = payload?.error
    if (error?.code && error?.message) {
      return new ApiError(
        response.status,
        error.code,
        error.message,
        error.details?.fields ?? [],
        error.request_id ?? null,
      )
    }
  } catch {
    // fall through to the generic message
  }
  return new ApiError(response.status, 'http_error', `The server returned an error (${response.status}).`)
}

export async function request<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH',
  path: string,
  { body, params, signal }: RequestOptions = {},
): Promise<T> {
  if (!API_BASE && !import.meta.env.DEV) {
    throw new ApiError(0, 'not_configured', 'VITE_API_BASE_URL is not set for this build.')
  }
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const clock = getTestClock()
  if (clock) headers['X-Test-Clock'] = clock

  let response: Response
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(
      0,
      'network_error',
      'Cannot reach the server. A free-tier server may be waking up; wait a few seconds and retry.',
    )
  }
  if (!response.ok) throw await parseError(response)
  return (await response.json()) as T
}

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}
