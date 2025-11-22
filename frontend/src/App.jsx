import { useState } from 'react';
import LoginScreen from './components/LoginScreen';
import Workflow from './components/Workflow';
import './App.css';

export default function App() {
  const [session, setSession] = useState({ authenticated: false, user: null });

  const handleLogin = (credentials) => {
    setSession({ authenticated: true, user: credentials.email });
  };

  const handleLogout = () => {
    setSession({ authenticated: false, user: null });
  };

  return (
    <div className="app-shell">
      <nav className="app-shell__nav">
        <div className="brand">
          <div className="brand__mark">
            <svg viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2l5 5h-5V4zM6 20V4h5v7h7v9H6z"/>
              <path d="M8 12h8v2H8zm0 4h8v2H8z"/>
            </svg>
          </div>
          <div className="brand__copy">
            <p className="brand__title">Revisa Docs</p>
            <p className="brand__subtitle">Intelligent Control</p>
          </div>
        </div>
        {session.authenticated ? (
          <div className="session-badge">
            <div style={{width: '8px', height: '8px', borderRadius: '50%', background: '#10b981'}}></div>
            <span>{session.user}</span>
          </div>
        ) : (
          <div className="session-badge session-badge--muted">Demo Mode</div>
        )}
      </nav>

      <main className="app-shell__main">
        {session.authenticated ? (
          <Workflow onReset={handleLogout} />
        ) : (
          <LoginScreen onContinue={handleLogin} />
        )}
      </main>

      <footer className="app-shell__footer">
        &copy; 2025 Revisa Docs. Powered by Microsoft Azure.
      </footer>
    </div>
  );
}
