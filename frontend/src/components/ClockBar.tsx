import { useState } from 'react'
import { getTestClock, setTestClock } from '../lib/clock'

/** Reviewer aid: override "today" for every API call (sent as X-Test-Clock). */
export function ClockBar() {
  const active = getTestClock()
  const [value, setValue] = useState(active ?? '')

  function apply(next: string | null) {
    setTestClock(next)
    window.location.reload() // every screen re-reads its data under the new clock
  }

  return (
    <form
      className="clock-bar"
      onSubmit={(event) => {
        event.preventDefault()
        apply(value.trim() || null)
      }}
    >
      <label htmlFor="test-clock">Reviewer clock</label>
      <input
        id="test-clock"
        type="text"
        value={value}
        placeholder="2026-10-20 or 2026-10-20T10:00:00+05:30"
        onChange={(event) => setValue(event.target.value)}
      />
      <button type="submit">Set</button>
      {active && (
        <button type="button" onClick={() => apply(null)}>
          Use real time
        </button>
      )}
      {active && <span className="badge badge-draft">clock: {active}</span>}
    </form>
  )
}
