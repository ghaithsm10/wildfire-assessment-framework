import { useState } from 'react'
import ShortTermAssessment from './pages/ShortTermAssessment'
import LongTermAssessment from './pages/LongTermAssessment'
import './index.css'

export default function App() {
  const [activeTab, setActiveTab] = useState('short')

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-logo">
          <span className="flame">🔥</span>
          <span>FireRisk Assessment</span>
        </div>

        <div className="app-tabs">
          <button
            className={`tab-btn ${activeTab === 'short' ? 'active' : ''}`}
            onClick={() => setActiveTab('short')}
          >
            📡 Short-Term
          </button>
          <button
            className={`tab-btn ${activeTab === 'long' ? 'active' : ''}`}
            onClick={() => setActiveTab('long')}
          >
            📈 Long-Term
          </button>
        </div>

        <div className="header-badge">
          <div className="status-dot" />
          API Connected
        </div>
      </header>

      <div className="app-body">
        {activeTab === 'short' ? <ShortTermAssessment /> : <LongTermAssessment />}
      </div>
    </div>
  )
}
