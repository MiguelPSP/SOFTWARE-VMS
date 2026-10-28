"""
Funções auxiliares para formatação, validação e geração de cenários de teste de 64 canais.
"""

from typing import List
from core.database import DatabaseManager
from core.models import Brand, Camera


def populate_64_test_cameras(db: DatabaseManager):
    """
    Popula o banco de dados com 64 câmeras industriais distribuídas entre
    as 4 marcas requeridas (Hikvision, HiLook, Intelbras, Dahua).
    Permite validar a grade 8x8 imediatamente.
    """
    # Cria ou busca áreas
    areas = db.get_all_areas()
    area_map = {a.name: a.id for a in areas}

    required_areas = ["Portaria e Acesso", "Perímetro e Muros", "Estacionamento e Pátio", "Galpão e Estoque"]
    for a_name in required_areas:
        if a_name not in area_map:
            aid = db.add_area(a_name, "Área de monitoramento")
            area_map[a_name] = aid

    brands_cycle = [Brand.HIKVISION, Brand.HILOOK, Brand.INTELBRAS, Brand.DAHUA]
    area_names_list = list(area_map.keys())

    existing_cams = db.get_all_cameras()
    existing_count = len(existing_cams)

    for i in range(existing_count + 1, 65):
        brand = brands_cycle[(i - 1) % len(brands_cycle)]
        area_name = area_names_list[(i - 1) % len(area_names_list)]
        area_id = area_map[area_name]

        # IP fictício padronizado de CFTV
        ip = f"192.168.1.{100 + i}"
        ch = ((i - 1) % 16) + 1

        cam = Camera(
            id=None,
            name=f"CAM {i:02d} - {brand.value} {area_name[:8]}",
            ip=ip,
            port=554,
            username="admin",
            password="Password123",
            channel=ch,
            brand=brand,
            area_id=area_id,
            is_active=True
        )
        db.add_camera(cam)


def format_bytes(size_bytes: int) -> str:
    """Formata bytes em KB, MB, GB de forma legível."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
