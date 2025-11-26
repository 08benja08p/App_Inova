import { useEffect, useRef } from 'react';
import template from './LoginScreen.html?raw';
import './LoginScreen.css';
import cloudDiagram from '../../assets/cloud_diagram_v4_es_2.png';

export default function LoginScreen({ onContinue }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return undefined;
    }

    container.innerHTML = template;

    const img = container.querySelector('[data-diagram-img]');
    if (img) {
      img.src = cloudDiagram;
    }

    const form = container.querySelector('[data-login-form]');
    if (!form) {
      return undefined;
    }

    const handleSubmit = (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const email = formData.get('email')?.toString() ?? '';
      const password = formData.get('password')?.toString() ?? '';
      onContinue({ email, password });
    };

    form.addEventListener('submit', handleSubmit);

    return () => {
      form.removeEventListener('submit', handleSubmit);
    };
  }, [onContinue]);

  return <section className="login-screen-wrapper" ref={containerRef} />;
}
