# Guía de Demostración - App Inova (Control Documental)

Este documento detalla los escenarios preparados para la grabación del video de demostración. El objetivo es mostrar la capacidad de la plataforma para procesar documentos, detectar errores normativos y asistir al usuario mediante IA.

## 📂 Archivos para la Demo

Los archivos se encuentran en la carpeta raíz o en `docs/`. Para la demo, recomendamos usar los siguientes archivos específicos que tienen comportamientos pre-programados.

### 1. Escenario "Happy Path" (Documento Limpio)
**Objetivo:** Mostrar la velocidad de procesamiento, la extracción correcta de datos y una validación exitosa sin errores.

*   **Archivo a usar:** `demo_invoice_reconstructed.html` (o `FACTURA TRIBUTARIA N°5861 SA1704CZ.pdf`)
*   **Lo que ocurrirá:**
    *   El sistema procesará el documento rápidamente.
    *   **Estado:** "✓ Cumple" (Verde).
    *   **Validaciones:** No aparecerán alertas rojas ni amarillas.
    *   **Extracción:** Se verán entidades como el Número de Factura, Fecha, Monto Total y Pallets.
*   **En qué fijarse:**
    *   Destacar la interfaz limpia.
    *   Mostrar la vista previa del documento (que ahora se alinea correctamente arriba).
    *   Mostrar que el sistema detectó automáticamente el tipo de documento ("Factura Comercial").


*   usar 'demo_packing_list_reconstructed.html' para mostrar corroboración por Packing List.

### 2. Escenario "Error Fitosanitario" (Producto Incorrecto)
**Objetivo:** Demostrar la capacidad de detectar inconsistencias en el contenido del documento (reglas de negocio).

*   **Archivo a usar:** `demo_error_fito.pdf`
*   **Lo que ocurrirá:**
    *   **Estado:** Alertas de error.
    *   **Error Crítico (Rojo):** "Producto incorrecto". El sistema detectará "Manzanas" en lugar de "Cerezas".
    *   **Advertencia (Amarillo):** "Referencia SAG ausente". Falta el número de resolución.
*   **En qué fijarse:**
    *   Hacer clic en el paso 2 ("Verificar").
    *   Mostrar claramente la tarjeta de "Validaciones" con el error en rojo.
    *   Explicar que esto previene multas en destino al asegurar que el producto declarado sea el correcto.

### 3. Escenario "Error Logístico" (BL vs Packing List)
**Objetivo:** Simular una validación cruzada donde los datos logísticos no coinciden.

*   **Archivo a usar:** `demo_error_bl.pdf`
*   **Lo que ocurrirá:**
    *   **Error Crítico (Rojo):** "Contenedor no coincide". El número de contenedor en el BL es diferente al esperado.
    *   **Advertencia (Amarillo):** "Puerto de descarga ambiguo". Duda entre Shanghai y Hong Kong.
*   **En qué fijarse:**
    *   Este es un error común y costoso en logística.
    *   Destacar cómo la herramienta alerta proactivamente antes de que el documento se envíe al cliente.

### 4. Escenario "Error Aduanero" (DUS)
**Objetivo:** Mostrar validaciones financieras y de términos de comercio internacional.

*   **Archivo a usar:** `demo_error_dus.pdf`
*   **Lo que ocurrirá:**
    *   **Error Crítico:** "Incoterm incorrecto". El DUS dice CIF pero la factura es FOB.
    *   **Advertencia:** "Peso bruto discrepante". Diferencia de peso con la guía de despacho.
*   **En qué fijarse:**
    *   La importancia de la consistencia entre documentos financieros y aduaneros.

---

## 🤖 Uso del Asistente IA (Chat)

El paso 3 del flujo ("Asistente IA") permite interactuar con el documento. Úsalo para demostrar que el sistema "entiende" el contenido más allá de simples reglas.

**Preguntas sugeridas para el video:**

1.  **"¿Quién es el exportador?"**
    *   *Respuesta esperada:* Identificará a "FRUTAS DEL SUR LTDA" (o el que corresponda al doc).
2.  **"¿Cuál es el peso neto?"**
    *   *Respuesta esperada:* Buscará valores en kg (ej. "8,500 kg").
3.  **"¿Hay algún error en el documento?"**
    *   *Respuesta esperada:*
        *   Si es el documento limpio: "El documento parece estar en orden."
        *   Si es un documento con error: Resumirá los errores encontrados (ej. "He encontrado problemas potenciales: Producto incorrecto...").

---

## 📝 Flujo Recomendado para el Video

1.  **Login:** Ingresar con cualquier correo (ej. `demo@inova.cl`). Mostrar el botón con el nuevo efecto de click.
2.  **Carga (Happy Path):** Arrastrar `demo_invoice_reconstructed.html`.
    *   Verificar que la vista previa se ve bien (alineada arriba).
    *   Mostrar los metadatos extraídos a la derecha.
    *   Ir al Chat y preguntar "¿Quién es el consignatario?".
3.  **Carga (Error Path):** Recargar (o botón "Reiniciar") y subir `demo_error_fito.pdf`.
    *   Mostrar inmediatamente las alertas rojas en el panel de validaciones.
    *   Comentar sobre la seguridad que esto brinda al operador.
4.  **Descarga:**
    *   Ir al paso "Resumen".
    *   Hacer clic en "Descargar informe (PDF)".
    *   Mostrar que se descarga el PDF original (`FACTURA TRIBUTARIA...`), simulando que el documento ya fue procesado/validado y está listo para envío.

## ⚠️ Notas Técnicas
*   Si usas los archivos `.html` (como `demo_invoice_reconstructed.html`), el sistema mostrará una vista previa web perfecta.
*   Si usas los archivos `.pdf` de error (`demo_error_...`), el sistema usará el visor de PDF nativo del navegador.
*   El botón de descarga ahora entrega el **PDF Real** asociado, no un JSON, para dar una sensación de producto finalizado.
