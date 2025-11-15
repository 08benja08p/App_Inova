
# Reglas de Validación para Documentos de Exportación de Cerezas (Chile)

Este documento define reglas de negocio para validar consistencia entre documentos.

## 1. Reglas de Consistencia Entre Documentos

### 1.1 Peso Total

- `factura.peso_neto` ≈ `packing_list.peso_neto`
- `factura.peso_bruto` ≈ `packing_list.peso_bruto`
- `bl.peso_bruto` ≈ `packing_list.peso_bruto`
- `dus.peso_neto` ≈ `factura.peso_neto`
- `dus.peso_bruto` ≈ `packing_list.peso_bruto`

Tolerancias recomendadas (configurable):
- ±1–2% para pesos totales
- ±1 unidad para número de cajas/pallets

### 1.2 Variedad y Especie

- `factura.variedad` == `packing_list.variedad` == `certificado_fitosanitario.variedad`
- `guia_despacho.variedad` debe coincidir con `certificado_fitosanitario.variedad` para el mismo CSG.

### 1.3 Códigos SAG (CSG, CSP)

- `certificado_fitosanitario.codigo_csg` == `guia_despacho.codigo_csg`
- `certificado_fitosanitario.codigo_csp` debe asociarse al packing que emite el `packing_list`.

### 1.4 Código Arancelario (HS Code)

- `factura.hs_code` == `certificado_origen.hs_code` == `dus.hs_code`

### 1.5 Número de Contenedor

- `packing_list.numero_contenedor` == `bl.numero_contenedor`
- Si el DUS incluye contenedor, debe coincidir también con BL/packing_list.

### 1.6 Consignatario

- `instrucciones_embarque.consignatario` == `bl.consignee`
- `certificado_origen.importador` debe ser compatible con `factura.importador` y `bl.consignee`.

## 2. Reglas de Formato y Ortografía

### 2.1 Fechas

- Todas las fechas deben tener un formato consistente (ej: `YYYY-MM-DD` interno).
- No se permiten fechas futuras en documentos que ya debieron ocurrir (ej: fecha de zarpe > fecha actual).

### 2.2 Nombres y Variedades

- Verificar nombres de variedades contra catálogo interno (ej: [`Santina`, `Regina`, `Lapins`, ...]).
- Marcar palabras con alta distancia de Levenshtein respecto a variedades válidas como posibles errores.

### 2.3 Códigos

- `codigo_csg`, `codigo_csp`: validar por longitud, prefijos, solo caracteres permitidos (ej: alfanumérico sin espacios).
- `hs_code`: validar patrón `NNNN.NN` o `NNNN.NN.NN` según criterio configurado.

## 3. Reglas de Secuencia Temporal

- `guia_despacho.fecha_emision` <= fecha de inspección SAG y fecha de embarque.
- `packing_list.fecha_emision` <= fecha BL.fecha_zarpe.
- `factura.fecha_emision` >= fecha BL.fecha_zarpe (cuando se emite post-zarpe).
- `certificado_fitosanitario.fecha_emision` >= fecha BL.fecha_zarpe.
- `certificado_origen.fecha_emision` >= factura.fecha_emision.

Cualquier violación debe generar una alerta de flujo.

## 4. Severidad de Errores (Sugerida)

- **Críticos**: diferencias de contenedor, CSG, HS Code, consignatario, país destino.
- **Altos**: diferencias importantes de peso, lote, variedad.
- **Medios**: diferencias leves de cantidades o pesos dentro de tolerancia ampliada.
- **Bajos**: errores ortográficos que no cambian el significado.

