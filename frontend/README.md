# Frontend - Inova Docs

Interfaz React + Vite para acompañar el backend FastAPI de la PoC. Incluye una pantalla de inicio de
sesión (por ahora abierta) y un panel que replica el storyboard proporcionado.

## Scripts disponibles

```bash
yarn install
yarn dev
yarn build
yarn preview
```

## Notas

- Cada componente en `src/components` incluye su propio archivo HTML y CSS para mantener el diseño
  modular.
- La autenticación todavía no está conectada; el formulario siempre permite acceder al panel.
- Puedes ajustar los textos y estilos modificando los archivos dentro de cada carpeta de componente.
