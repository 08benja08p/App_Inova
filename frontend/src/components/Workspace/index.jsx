import { useEffect, useRef } from 'react';
import template from './Workspace.html?raw';
import './Workspace.css';

export default function Workspace({ onReset }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    container.innerHTML = template;

    const logoutButton = container.querySelector('[data-action="logout"]');
    if (!logoutButton) {
      return undefined;
    }

    const handleLogout = (event) => {
      event.preventDefault();
      onReset();
    };

    logoutButton.addEventListener('click', handleLogout);

    return () => {
      logoutButton.removeEventListener('click', handleLogout);
    };
  }, [onReset]);

  return <section className="workspace-wrapper" ref={containerRef} />;
}
