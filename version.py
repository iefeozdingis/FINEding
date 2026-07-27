"""Uygulama sürümü — TEK KAYNAK.

Sürüm string'i önceden ui/giris.py ve ui/hakkinda.py içinde ayrı ayrı
sabit yazılıydı; ikisi de v1.6.0'da kalmıştı ve yayınlanan sürümü (v1.6.2)
yansıtmıyordu. Sürümü değiştirmek isteyen yalnızca burayı düzenler.
"""

__version__ = "1.10.0"

# Arayüzde gösterilecek biçim (ör. "v1.6.2")
SURUM_ETIKETI = f"v{__version__}"
