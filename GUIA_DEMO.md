# Guía de Demostración - Revisa Docs (Control Documental)

Este documento detalla los escenarios preparados para la demostración de la plataforma. Los casos están basados en **documentos reales** de exportación de cerezas chilenas.

---

## 🏢 Datos de la Empresa Demo

| Campo | Valor |
|-------|-------|
| **Empresa** | Exportadora San Andrés SpA |
| **RUT** | 76.981.890-1 |
| **Ubicación** | Sagrada Familia, VII Región, Chile |
| **Producto** | Cerezas frescas (PRUNUS AVIUM) |
| **HS Code** | 0809.29.00 |

---

## 📂 Archivos para la Demo

Los archivos HTML de demostración están en la raíz del proyecto. Cada uno replica visualmente un documento real de exportación.

### Embarques Disponibles

| Embarque | Destino | Vía | Cantidad | Valor FOB |
|----------|---------|-----|----------|-----------|
| **SA1690CZ** | Hong Kong | Marítimo | 7,080 cajas | USD 76,320 |
| **SA1704CZ** | Curazao | Aéreo | 120 cajas | USD 1,800 |

---

## 🎬 Escenarios de Demostración

### 1. ✅ Happy Path: Factura Comercial Válida

**Archivo:** `demo_factura_5873_real.html`

**Lo que ocurrirá:**
- Estado: **✓ Documento válido** (verde)
- Sin errores ni advertencias
- Extracción automática de:
  - Exportador: EXPORTADORA SAN ANDRÉS SPA
  - Consignatario: SUNKFA HONG KONG LIMITED
  - Contenedor: ONEU9254131
  - Valor: USD 76,320.00 FOB

**Puntos a destacar:**
- Vista previa HTML limpia y profesional
- Extracción precisa de entidades comerciales
- Detección automática de tipo de documento

---

### 2. ✅ Happy Path: Bill of Lading

**Archivo:** `demo_bl_sa1690_real.html`

**Lo que ocurrirá:**
- Documento válido sin errores
- Cruce correcto con factura (mismo contenedor ONEU9254131)
- Peso bruto: 22,132.80 KGS

**Pregunta sugerida para el Chat:**
> "¿El contenedor coincide con la factura?"

---

### 3. ✅ Happy Path: DUS (Declaración Única de Salida)

**Archivo:** `demo_dus_sa1690_real.html`

**Lo que ocurrirá:**
- Validación aduanera exitosa
- Datos consistentes con factura y BL
- Puerto de embarque: VALPARAISO

---

### 4. ✅ Happy Path: Certificado Fitosanitario

**Archivo:** `demo_fito_2630187_real.html`

**Lo que ocurrirá:**
- Certificado SAG válido
- Especie correcta: PRUNUS AVIUM
- Destino: CURACAO (vía aérea)

---

### 5. ❌ Error Path: Factura con Discrepancias

**Archivo:** `demo_factura_5873_error.html`

**Errores detectados:**

| Severidad | Error | Detalle |
|-----------|-------|---------|
| 🔴 Crítico | Cantidad inconsistente | Factura: 7,000 cajas vs BL: 7,080 cajas |
| 🔴 Crítico | Peso discrepante | Factura: 21,500 KG vs BL/DUS: 22,132.80 KG |
| 🟡 Alerta | Valor FOB no coincide | Declarado: USD 75,600 vs Calculado: USD 76,320 |

**Visualización de errores:**
- Panel lateral derecho con lista de discrepancias
- Marcadores inline en el documento (números en círculos rojos)
- Click en error → scroll al campo afectado
- Hover sobre marcador → tooltip con detalle

**Puntos a destacar:**
- Sistema de anotaciones estilo Google Docs
- Navegación bidireccional panel ↔ documento
- Colores diferenciados: rojo = crítico, amarillo = alerta

---

### 6. ❌ Error Path: FITO con Especie Incorrecta

**Archivo:** `demo_fito_2630187_error.html`

**Errores detectados:**

| Severidad | Error | Detalle |
|-----------|-------|---------|
| 🔴 **CRÍTICO** | Especie incorrecta | PRUNUS DOMESTICA (ciruelas) vs PRUNUS AVIUM (cerezas) |
| 🔴 Crítico | Peso no coincide | FITO: 500 KG vs Factura: 600 KG |

**Impacto del error:**
- Rechazo fitosanitario garantizado en destino
- Requiere nuevo certificado SAG antes del embarque
- Demora mínima de 24-48 horas

**Puntos a destacar:**
- Validación de reglas de negocio específicas (SAG)
- Prevención de errores costosos (multas, re-embarques)

---

## 🤖 Uso del Asistente IA (Chat)

El paso 3 ("Asistente IA") permite consultas en lenguaje natural sobre el documento.

### Preguntas Sugeridas

**Para documentos válidos:**
1. "¿Quién es el exportador?"
2. "¿Cuál es el número de contenedor?"
3. "¿El incoterm es correcto para esta operación?"
4. "Resume los datos principales del documento"

**Para documentos con errores:**
1. "¿Hay errores en este documento?"
2. "¿Qué debo corregir antes de enviar?"
3. "¿El peso coincide con otros documentos?"

---

## 📋 Flujo Recomendado para Video

### Opción A: Demo Rápida (3 minutos)

1. **Login** → `demo@inova.cl`
2. **Cargar** → `demo_factura_5873_real.html`
3. **Verificar** → Mostrar validación exitosa
4. **Chat** → "¿Quién es el consignatario?"
5. **Cargar** → `demo_fito_2630187_error.html`
6. **Verificar** → Mostrar errores detectados
7. **Destacar** → Sistema de anotaciones inline

### Opción B: Demo Completa (8 minutos)

1. **Contexto** → Explicar exportación de cerezas chilenas
2. **Happy Path** → Subir factura, BL y DUS del embarque SA1690CZ
3. **Validación cruzada** → Mostrar consistencia entre documentos
4. **Error Path** → Subir versiones con error
5. **Anotaciones** → Demostrar navegación panel ↔ documento
6. **Chat IA** → Preguntas sobre correcciones
7. **Resumen** → Descargar informe

---

## ⚙️ Notas Técnicas

### Sistema de Anotaciones (Nuevo)

Los archivos `*_error.html` incluyen un sistema de visualización de errores inspirado en Google Docs:

```html
<!-- Marcador en el documento -->
<span class="annotation-marker error-critical" data-annotation-id="1">
    7,000 CASES
    <span class="error-tooltip">❌ BL indica 7,080 CASES</span>
</span>

<!-- Panel lateral sincronizado -->
<div class="errors-panel">
    <div class="error-item" onclick="...scrollIntoView()">
        Cantidad inconsistente
    </div>
</div>
```

### Mapeo de Archivos (Backend)

En `backend/app/services/processing.py`:

```python
DEMO_HTML_MAPPING = {
    "FACTURA TRIBUTARIA N°5873 SA1690CZ.pdf": "demo_factura_5873_real.html",
    "demo_factura_error.pdf": "demo_factura_5873_error.html",
    # ...
}
```

### Validaciones Hardcodeadas

Los escenarios de demo tienen validaciones pre-programadas en `DEMO_SCENARIOS` para garantizar resultados consistentes durante las presentaciones.

---

## 📁 Archivos Disponibles

| Archivo | Tipo | Embarque | Estado |
|---------|------|----------|--------|
| `demo_factura_5873_real.html` | Factura | SA1690CZ | ✅ Válido |
| `demo_factura_5873_error.html` | Factura | SA1690CZ | ❌ Errores |
| `demo_bl_sa1690_real.html` | Bill of Lading | SA1690CZ | ✅ Válido |
| `demo_dus_sa1690_real.html` | DUS | SA1690CZ | ✅ Válido |
| `demo_fito_2630187_real.html` | Fitosanitario | SA1704CZ | ✅ Válido |
| `demo_fito_2630187_error.html` | Fitosanitario | SA1704CZ | ❌ Errores |
| `demo_invoice_reconstructed.html` | Factura (Legacy) | SA1704CZ | ✅ Válido |
| `demo_packing_list_reconstructed.html` | Packing List | - | ✅ Válido |

---

## ✨ Mejoras Implementadas

1. **Datos reales** → Basado en Exportadora San Andrés SpA
2. **Consistencia** → Mismo embarque (SA1690CZ) en factura, BL y DUS
3. **Anotaciones visuales** → Sistema estilo Google Docs para errores
4. **Errores realistas** → Basados en discrepancias comunes en exportación
5. **Panel sincronizado** → Click en error navega al campo en el documento
