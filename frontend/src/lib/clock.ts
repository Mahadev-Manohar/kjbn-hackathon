// Reviewer clock override. Stored in the browser and sent to the API as X-Test-Clock.

const STORAGE_KEY = 'kjbn.testClock'

export function getTestClock(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function setTestClock(value: string | null): void {
  try {
    if (value) localStorage.setItem(STORAGE_KEY, value)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage can be unavailable (private mode); the override then simply does not persist.
  }
}
