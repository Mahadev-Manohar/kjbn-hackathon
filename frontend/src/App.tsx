import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { ClockBar } from './components/ClockBar'
import { DeliveryEntryPage } from './pages/DeliveryEntryPage'
import { FarmerLedgerPage } from './pages/FarmerLedgerPage'
import { FarmersPage } from './pages/FarmersPage'
import { PayoutStatementPage } from './pages/PayoutStatementPage'
import { PayoutsPage } from './pages/PayoutsPage'
import { PriceListPage } from './pages/PriceListPage'

const NAV = [
  { to: '/deliveries/new', label: 'New delivery' },
  { to: '/prices', label: 'Price list' },
  { to: '/payouts', label: 'Payouts' },
  { to: '/farmers', label: 'Farmers' },
]

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">Produce Procurement &amp; Payout</span>
        <nav aria-label="Main">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <ClockBar />
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/deliveries/new" replace />} />
          <Route path="/deliveries/new" element={<DeliveryEntryPage />} />
          <Route path="/prices" element={<PriceListPage />} />
          <Route path="/payouts" element={<PayoutsPage />} />
          <Route path="/payouts/:payoutId" element={<PayoutStatementPage />} />
          <Route path="/farmers" element={<FarmersPage />} />
          <Route path="/farmers/:farmerId" element={<FarmerLedgerPage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </div>
  )
}
