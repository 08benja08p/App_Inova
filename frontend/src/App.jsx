import { useState } from 'react';
import LoginScreen from './components/LoginScreen';
import Workspace from './components/Workspace';
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
          <div className="brand__mark">ID</div>
          <div className="brand__copy">
            <p className="brand__title">Inova Docs</p>
            <p className="brand__subtitle">Workflow Studio</p>
          </div>
        </div>
        {session.authenticated ? (
          <div className="session-badge">
            Sesión iniciada como <span>{session.user}</span>
          </div>
        ) : (
          <div className="session-badge session-badge--muted">Demo UI · React + Vite</div>
        )}
      </nav>

      <main className="app-shell__main">
        {session.authenticated ? (
          <Workspace onReset={handleLogout} />
        ) : (
          <LoginScreen onContinue={handleLogin} />
        )}
      </main>

      <footer className="app-shell__footer">
        UI inspirada en tu storyboard para la PoC OCR · Lista para conectar con FastAPI.
      </footer>
    </div>
  );
}
