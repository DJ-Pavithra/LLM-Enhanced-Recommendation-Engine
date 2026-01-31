import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = "http://localhost:8000/api/v1"
const MOCK_USER_ID = "12347" // Changing ID to test new profile

function App() {
  const [recommendations, setRecommendations] = useState([])
  const [userStats, setUserStats] = useState(null)
  const [searchResults, setSearchResults] = useState([])
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [intent, setIntent] = useState(null)
  const [training, setTraining] = useState(false)

  useEffect(() => {
    fetchUserData()
  }, [])

  const fetchUserData = async () => {
    try {
      // Parallel Fetch
      const [recRes, statRes] = await Promise.all([
        fetch(`${API_BASE}/users/${MOCK_USER_ID}/recommendations`),
        fetch(`${API_BASE}/users/${MOCK_USER_ID}/stats`)
      ])

      const recData = await recRes.json()
      const statData = await statRes.json()

      setRecommendations(recData)
      setUserStats(statData)
    } catch (err) {
      console.error("Failed to fetch data", err)
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      })
      const data = await res.json()
      setSearchResults(data.results)
      setIntent(data.intent)
    } catch (err) {
      console.error("Search failed", err)
    } finally {
      setLoading(false)
    }
  }

  const triggerTraining = async () => {
    setTraining(true)
    await fetch(`${API_BASE}/train`, { method: "POST" })
    setTimeout(() => setTraining(false), 3000) // Mock feedback duration
    alert("Training started! (Check backend logs)")
  }

  return (
    <div className="container">
      <header>
        <div>
          <h1>🛍️ AutoRec AI</h1>
          <p style={{ color: '#94a3b8' }}>Intelligent Context-Aware Recommendations</p>
        </div>
        <button onClick={triggerTraining} className="btn secondary-btn">
          {training ? "Training..." : "Train Model"}
        </button>
      </header>

      {/* User Profile Section */}
      {userStats && (
        <section className="profile-section">
          <div className="stats-card">
            <h2 style={{ marginTop: 0 }}>User #{MOCK_USER_ID}</h2>
            <div className="stat-item">
              <span>Orders Placed</span>
              <span className="stat-value">{userStats.order_count}</span>
            </div>
            <div className="stat-item">
              <span>Total Spent</span>
              <span className="stat-value">£{userStats.total_spent?.toFixed(2)}</span>
            </div>
            <div className="stat-item">
              <span>Top Categories</span>
              <span className="stat-value">{userStats.top_categories.join(", ")}</span>
            </div>
          </div>

          <div className="stats-card" style={{ borderLeft: '4px solid var(--primary)' }}>
            <h3 style={{ marginTop: 0, color: 'var(--primary)' }}>🧠 LLM Profile Analysis</h3>
            {userStats.llm_profile ? (
              <div>
                <p style={{ fontSize: '1.1rem', fontWeight: 500 }}>"{userStats.llm_profile.persona}"</p>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                  <div className="factor-tag">Price Sensitivity: {userStats.llm_profile.price_sensitivity}</div>
                  <div className="factor-tag">Best Time: {userStats.llm_profile.best_time}</div>
                </div>
              </div>
            ) : (
              <p>Generating detailed profile...</p>
            )}
          </div>
        </section>
      )}

      {/* Search Section */}
      <section className="search-section">
        <form onSubmit={handleSearch}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything... 'Show me gifts for a gamer under £50'"
          />
          <button type="submit" className="btn primary-btn" disabled={loading}>
            {loading ? "Analyzing..." : "AI Search"}
          </button>
        </form>

        {intent && intent.category !== 'general' && (
          <div className="intent-box">
            <h4 style={{ margin: '0 0 0.5rem 0' }}>System Interpretation</h4>
            <div className="intent-tags">
              <span>🎯 Intent: <strong>{intent.intent}</strong></span>
              <span>📂 Category: <strong>{intent.category}</strong></span>
              {intent.use_case && <span>💡 Context: <strong>{intent.use_case}</strong></span>}
              {intent.budget && <span>💰 Budget: <strong>{intent.budget}</strong></span>}
            </div>
          </div>
        )}
      </section>

      {searchResults.length > 0 && (
        <section style={{ marginBottom: '3rem' }}>
          <h2>🔍 Search Results</h2>
          <div className="grid">
            {searchResults.map((item, idx) => (
              <div key={idx} className="card">
                <span className="score-badge">Match: {(item.score * 100).toFixed(0)}%</span>
                <h3>{item.description}</h3>
                <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>{item.stock_code}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2>✨ Recommended For You</h2>
        <div className="grid">
          {recommendations.length === 0 ? (
            <p>No recommendations yet. Try training the model!</p>
          ) : (
            recommendations.map((item, idx) => (
              <div key={idx} className="card">
                <span className="score-badge">Sc: {item.score.toFixed(2)}</span>
                <h3>{item.description}</h3>

                {/* Structured Explanation */}
                {item.explanation ? (
                  <div className="explanation">
                    <p><strong>Example Reason:</strong> {item.explanation.reason}</p>
                    <div className="match-factors">
                      {item.explanation.match_factors?.map((f, i) => (
                        <span key={i} className="factor-tag">{f}</span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="explanation">
                    <p>Based on your purchase history.</p>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

export default App
