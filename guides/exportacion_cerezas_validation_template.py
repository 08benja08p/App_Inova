
"""
Ejemplo de estructura en Python para validar documentos
de exportación de cerezas usando las reglas definidas.
Este archivo es solo una base para integrar en tu backend.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Factura:
    numero_factura: str
    peso_neto: float
    peso_bruto: Optional[float]
    hs_code: str
    valor_total: float
    variedad: Optional[str] = None


@dataclass
class PackingList:
    peso_neto: float
    peso_bruto: float
    numero_cajas: int
    numero_contenedor: Optional[str] = None
    variedad: Optional[str] = None


@dataclass
class BL:
    peso_bruto: float
    numero_contenedor: str
    consignee: str
    puerto_origen: str
    puerto_destino: str


def check_pesos(factura: Factura, packing: PackingList, bl: BL, tolerance_ratio: float = 0.02):
    """Valida coherencia de pesos entre factura, packing list y BL."""
    issues = []

    def diff_ratio(a: float, b: float) -> float:
        if max(abs(a), abs(b)) == 0:
            return 0.0
        return abs(a - b) / max(abs(a), abs(b))

    # Factura vs Packing
    if diff_ratio(factura.peso_neto, packing.peso_neto) > tolerance_ratio:
        issues.append("Peso neto factura vs packing list difiere sobre la tolerancia.")

    # BL vs Packing
    if diff_ratio(bl.peso_bruto, packing.peso_bruto) > tolerance_ratio:
        issues.append("Peso bruto BL vs packing list difiere sobre la tolerancia.")

    return issues


def check_contenedor(packing: PackingList, bl: BL):
    """Valida que el número de contenedor coincida entre packing list y BL."""
    issues = []
    if packing.numero_contenedor and packing.numero_contenedor != bl.numero_contenedor:
        issues.append("Número de contenedor difiere entre Packing List y BL.")
    return issues


if __name__ == "__main__":
    # Ejemplo mínimo de uso
    factura = Factura(
        numero_factura="F001-123",
        peso_neto=24000.0,
        peso_bruto=25500.0,
        hs_code="0809.29",
        valor_total=50000.0,
        variedad="Santina",
    )
    packing = PackingList(
        peso_neto=23900.0,
        peso_bruto=25450.0,
        numero_cajas=1600,
        numero_contenedor="MSCU1234567",
        variedad="Santina",
    )
    bl = BL(
        peso_bruto=25400.0,
        numero_contenedor="MSCU1234567",
        consignee="IMPORTADORA XYZ LTD.",
        puerto_origen="VALPARAISO, CL",
        puerto_destino="SHANGHAI, CN",
    )

    print("Issues de peso:", check_pesos(factura, packing, bl))
    print("Issues de contenedor:", check_contenedor(packing, bl))
