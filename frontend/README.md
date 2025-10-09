# Frontend - Inova Docs

Interfaz React + Vite para acompañar el backend FastAPI de la PoC. Incluye una pantalla de inicio de
sesión (por ahora abierta) y un panel operativo dividido en cuatro pasos: subir, verificar, editar y
resumir documentos de importación/exportación.

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
- Configura la variable `VITE_API_BASE_URL` si el backend corre en una URL distinta a
  `http://localhost:8000`.
- El panel consulta al backend para obtener metadatos (`GET /documents/{id}`), entidades, keywords y
  texto OCR; asegúrate de tener el API activo antes de probar la carga de archivos.
- La etapa de subida admite PDF, imágenes o capturas tomadas con la cámara del dispositivo.
- Puedes ajustar los textos y estilos modificando los archivos dentro de cada carpeta de componente.
