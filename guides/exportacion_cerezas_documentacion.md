
# 📦 Exportación de Cerezas en Chile — Documentos, Validaciones y Errores Frecuentes

Guía para modelos de IA o copilots encargados de **leer, interpretar y validar documentos de exportación frutícola (cerezas)**.  
Enfocado en **Chile**, con prioridad en detectar **errores de ortografía, inconsistencias de datos y fallos operativos**.

---

## 1. 📁 Lista de Documentos Utilizados en la Exportación de Cerezas

### 1.1 Certificado Fitosanitario — *SAG*

**Qué es**  
Documento oficial que certifica que las cerezas cumplen requisitos fitosanitarios y están libres de plagas.

**Emitido por**: SAG (Servicio Agrícola y Ganadero)  
**Momento**: se emite después de la inspección fitosanitaria en puerto y suele estar disponible ~48 h después del zarpe.  
**Formato**: PDF oficial o físico firmado.

**Datos críticos a validar**

- Variedad correcta
- Cantidad / peso
- Código **CSG** (productor) y **CSP** (packing)
- Lote
- País de destino
- Tratamientos cuarentenarios (si aplica)

**Errores comunes**

- Códigos SAG mal digitados
- Nº de lote incorrecto
- Variedad mal escrita
- Datos inconsistentes con Packing List o Guía de Despacho

**Debe ser consistente con**

- Lista de empaque
- Guías de despacho
- DUS
- Factura comercial

---

### 1.2 Factura Comercial de Exportación

**Qué es**  
Documento de venta internacional con valor, cantidades y condiciones comerciales.

**Emitido por**: Exportadora  
**Formato**: PDF (a menudo bilingüe ES/EN)  
**Momento**: tras confirmar la venta; idealmente post-zarpe para tramitar Certificado de Origen.

**Datos críticos a validar**

- Descripción exacta del producto (cerezas frescas, variedad, calibre)
- Cantidades (cajas, pallets)
- Peso neto / bruto
- Código arancelario HS (ej. 0809.29)
- Incoterm (FOB, CIF, etc.)
- Valor total vs cantidades
- Moneda

**Errores comunes**

- HS Code equivocado
- Descripción no estandarizada (no sigue nomenclatura de ASOEX)
- Diferencias de cantidades respecto al Packing List
- Precios mal digitados

**Debe ser consistente con**

- Packing List
- DUS
- Certificado de Origen

---

### 1.3 Packing List (Lista de Empaque)

**Qué es**  
Documento logístico que describe el contenido físico del envío.

**Emitido por**: Packing / área de despacho  
**Formato**: PDF o Excel  
**Momento**: cuando la carga sale desde el packing hacia el puerto.

**Datos críticos a validar**

- Nº de pallets
- Nº de cajas por pallet
- Peso neto y bruto total
- Variedades y calibres
- Lotes y códigos de pallets
- IDs de contenedor y sello (si corresponde)

**Errores comunes**

- Lote incorrecto (motivo típico de retención en destino)
- Cajas o peso no coinciden con factura
- Variedad escrita de forma distinta a la factura o a la guía de calidad

**Debe ser consistente con**

- Factura comercial
- Certificado Fitosanitario
- BL
- DUS

---

### 1.4 Instrucciones de Embarque

**Qué es**  
Documento/correo que indica al agente cómo debe embarcarse la carga.

**Emitido por**: Exportadora  
**Formato**: formulario interno, carta o correo formal  
**Momento**: idealmente 48 h antes del cutoff documental de la naviera.

**Datos críticos a validar**

- Puerto de destino
- Datos del consignatario
- Nº de contenedor (si ya está asignado)
- Temperatura objetivo del reefer
- Lista de documentos a incluir

**Errores comunes**

- Puerto de destino incorrecto
- Datos incompletos → BL mal emitido
- Temperatura reefer no coincide con lo solicitado

**Impacto**: errores aquí se reflejan en un BL incorrecto.

---

### 1.5 Conocimiento de Embarque (B/L — Bill of Lading)

**Qué es**  
Documento del transportista que funciona como contrato de transporte, recibo de carga y documento de propiedad.

**Emitido por**: Naviera (transporte marítimo)  
**Formato**: draft digital + originales físicos  
**Momento**: draft 0–1 día post-zarpe; originales ~2 días post-zarpe.

**Datos críticos a validar**

- Nº de contenedor(es) y sello(s)
- Peso total
- Shipper / Consignee
- Puertos de origen y destino
- Descripción de mercancía (coherente con el resto)

**Errores comunes**

- Nº de contenedor mal digitado
- Consignatario incorrecto
- Fechas mal registradas
- Diferencias con factura/packing list

**Consecuencia**: retención de carga en destino hasta corregir.

---

### 1.6 Certificado de Origen (C.O.)

**Qué es**  
Certifica el origen chileno de las cerezas para obtener beneficios arancelarios.

**Emitido por**: ProChile / Cámaras de Comercio autorizadas  
**Formato**: formularios oficiales (en algunos casos electrónicos)  
**Momento**: posterior al zarpe, cuando ya existe factura y BL definitivo.

**Datos críticos a validar**

- HS Code coherente con factura y DUS
- Nº de factura correcto
- Shipper / Consignee exactos
- Descripción alineada con el acuerdo comercial
- Criterio de origen correctamente declarado

**Errores comunes**

- Descripción distinta a la de la factura
- HS Code incorrecto → pérdida del arancel preferencial
- Cambios manuales no permitidos (enmendaduras)
- Necesidad de reemisión por errores de digitación

---

### 1.7 Declaración Aduanera de Exportación — DUS

**Qué es**  
Declaración oficial ante Aduanas (Documento Único de Salida).

**Emitido por**: Agente de Aduanas  
**Formato**: digital (SICEX u otros sistemas)  

**Datos críticos a validar**

- Peso total
- Descripción de la mercancía
- Valor FOB
- HS Code
- País de destino
- Régimen y tratados aplicables

**Errores comunes**

- Inconsistencias con factura, packing list o BL → rechazo por Aduanas
- Cantidades o pesos distintos a guías de despacho
- Mal uso de regímenes o códigos

---

### 1.8 Guía de Despacho (SII)

**Qué es**  
Documento tributario que ampara el traslado interno hasta el puerto.

**Emitido por**: Exportadora / Packing  
**Formato**: electrónico (SII)  

**Datos críticos a validar**

- Código CSG del productor
- Especie y variedad
- Cantidad transportada
- Origen y destino del traslado
- RUT emisor y receptor

**Errores comunes**

- CSG incorrecto → ruptura de trazabilidad
- Variedad mal escrita
- Cantidad distinta a inspección SAG o a packing list

---

## 2. 🔎 Validaciones Automáticas Recomendadas

### 2.1 Coincidencias obligatorias entre documentos

| Campo            | Debe coincidir en                                       |
|------------------|---------------------------------------------------------|
| Peso total       | Packing List – Factura – BL – DUS                       |
| Variedad         | Packing List – Factura – Cert. Fitosanitario           |
| CSG/CSP          | Guía – Cert. Fitosanitario – DUS                        |
| HS Code          | Factura – Cert. de Origen – DUS                         |
| Nº de contenedor | Packing List – BL – DUS                                 |
| Consignatario    | Instrucciones – BL – Cert. de Origen – Factura         |

### 2.2 Validación de formato y ortografía

La IA debe revisar:

- Nombres de empresas y personas (sin errores tipográficos)
- Nombres de variedades (Santina, Regina, Lapins, etc.)
- Códigos SAG (CSG, CSP, CSE)
- Formato y coherencia de fechas
- Unidades (kg, pallets, cajas)
- Coherencia entre números en letra y número (si existen)

---

## 3. 🔄 Flujo Estándar del Proceso Documental

1. Guía de Despacho  
2. Packing List  
3. Instrucciones de Embarque  
4. Embarque (zarpe)  
5. BL – Draft  
6. Factura Comercial  
7. Certificado Fitosanitario  
8. Certificado de Origen  
9. BL – Originales  
10. DUS (legalización, si aplica)  

La IA puede usar este flujo para detectar documentos faltantes o fuera de secuencia.

---

## 4. 📚 Terminología Crítica

- **CSG**: Código de productor (huerto)
- **CSP**: Código de packing
- **CSE**: Código de exportadora
- **HS Code**: Clasificación arancelaria
- **FOB / CIF / CFR**: Incoterms
- **BL/BOL**: Bill of Lading (Conocimiento de embarque)
- **Cutoff documental**: Fecha límite de entrega de documentos a la naviera
- **Reefer**: Contenedor refrigerado
- **SAG**: Servicio Agrícola y Ganadero
- **SICEX**: Sistema Integrado de Comercio Exterior
- **DUS**: Documento Único de Salida

---

## 5. 🧠 Rol de la IA/Copilot

- Leer documentos PDF/escaneados relacionados a exportación de cerezas desde Chile.
- Extraer campos clave según el tipo de documento.
- Verificar consistencia cruzada de datos entre documentos.
- Identificar errores típicos (digitación, ortografía, cruces de datos).
- Alertar y sugerir correcciones concretas al usuario.
