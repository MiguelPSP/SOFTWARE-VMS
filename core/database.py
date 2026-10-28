"""
Camada de persistência local em SQLite para o VMS.
Armazena cadastro de até 64 câmeras, áreas físicas e preferências de layout.
"""

import sqlite3
from typing import List, Optional
from core.config import DATABASE_PATH
from core.models import Area, Brand, Camera


class DatabaseManager:
    """Gerencia a conexão e operações no banco de dados SQLite local."""

    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = str(db_path)
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Cria as tabelas caso ainda não existam e insere dados iniciais se vazio."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabela de Áreas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS areas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT
                )
            """)

            # Tabela de Câmeras
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    ip TEXT NOT NULL,
                    port INTEGER DEFAULT 554,
                    username TEXT DEFAULT 'admin',
                    password TEXT DEFAULT '',
                    channel INTEGER DEFAULT 1,
                    brand TEXT NOT NULL,
                    area_id INTEGER,
                    is_active INTEGER DEFAULT 1,
                    custom_main_url TEXT,
                    custom_sub_url TEXT,
                    FOREIGN KEY (area_id) REFERENCES areas (id) ON DELETE SET NULL
                )
            """)

            # Tabela de Configurações de Layout
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS layouts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()

        # Seed inicial se o banco estiver vazio
        if not self.get_all_areas():
            self._seed_initial_data()

    def _seed_initial_data(self):
        """Popula áreas e exemplos de câmeras representativas das marcas solicitadas."""
        area_portaria = self.add_area("Portaria Principal", "Controle de acesso e cancelas")
        area_perimetro = self.add_area("Perímetro Externo", "Muros e cercas perimetrais")
        area_estacionamento = self.add_area("Estacionamento", "Vagas e circulação interna")

        # Exemplo Câmera 1 - Hikvision (Portaria)
        self.add_camera(Camera(
            id=None,
            name="CAM 01 - Portaria Entrada",
            ip="192.168.1.100",
            port=554,
            username="admin",
            password="Password123",
            channel=1,
            brand=Brand.HIKVISION,
            area_id=area_portaria
        ))

        # Exemplo Câmera 2 - HiLook (Estacionamento)
        self.add_camera(Camera(
            id=None,
            name="CAM 02 - Estacionamento Vagas",
            ip="192.168.1.101",
            port=554,
            username="admin",
            password="Password123",
            channel=1,
            brand=Brand.HILOOK,
            area_id=area_estacionamento
        ))

        # Exemplo Câmera 3 - Intelbras (Perímetro)
        self.add_camera(Camera(
            id=None,
            name="CAM 03 - Muro Norte",
            ip="192.168.1.102",
            port=554,
            username="admin",
            password="Password123",
            channel=1,
            brand=Brand.INTELBRAS,
            area_id=area_perimetro
        ))

        # Exemplo Câmera 4 - Dahua / Intelbras (Portaria)
        self.add_camera(Camera(
            id=None,
            name="CAM 04 - Portaria Saída",
            ip="192.168.1.103",
            port=554,
            username="admin",
            password="Password123",
            channel=2,
            brand=Brand.DAHUA,
            area_id=area_portaria
        ))

    # --- Operações de Áreas ---
    def add_area(self, name: str, description: str = "") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO areas (name, description) VALUES (?, ?)", (name, description))
            conn.commit()
            return cursor.lastrowid

    def get_all_areas(self) -> List[Area]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, description FROM areas ORDER BY name ASC")
            return [Area(id=row["id"], name=row["name"], description=row["description"] or "") for row in cursor.fetchall()]

    # --- Operações de Câmeras ---
    def add_camera(self, camera: Camera) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cameras (name, ip, port, username, password, channel, brand, area_id, is_active, custom_main_url, custom_sub_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                camera.name,
                camera.ip,
                camera.port,
                camera.username,
                camera.password,
                camera.channel,
                camera.brand.value if isinstance(camera.brand, Brand) else str(camera.brand),
                camera.area_id,
                1 if camera.is_active else 0,
                camera.custom_main_url,
                camera.custom_sub_url
            ))
            conn.commit()
            return cursor.lastrowid

    def update_camera(self, camera: Camera) -> bool:
        if not camera.id:
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cameras
                SET name=?, ip=?, port=?, username=?, password=?, channel=?, brand=?, area_id=?, is_active=?, custom_main_url=?, custom_sub_url=?
                WHERE id=?
            """, (
                camera.name,
                camera.ip,
                camera.port,
                camera.username,
                camera.password,
                camera.channel,
                camera.brand.value if isinstance(camera.brand, Brand) else str(camera.brand),
                camera.area_id,
                1 if camera.is_active else 0,
                camera.custom_main_url,
                camera.custom_sub_url,
                camera.id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def delete_camera(self, camera_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cameras WHERE id=?", (camera_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_cameras(self) -> List[Camera]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, ip, port, username, password, channel, brand, area_id, is_active, custom_main_url, custom_sub_url
                FROM cameras
                ORDER BY id ASC
            """)
            cameras = []
            for row in cursor.fetchall():
                try:
                    brand_val = Brand(row["brand"])
                except ValueError:
                    brand_val = Brand.GENERIC_ONVIF

                cameras.append(Camera(
                    id=row["id"],
                    name=row["name"],
                    ip=row["ip"],
                    port=row["port"],
                    username=row["username"],
                    password=row["password"],
                    channel=row["channel"],
                    brand=brand_val,
                    area_id=row["area_id"],
                    is_active=bool(row["is_active"]),
                    custom_main_url=row["custom_main_url"],
                    custom_sub_url=row["custom_sub_url"]
                ))
            return cameras

    def get_camera_by_id(self, camera_id: int) -> Optional[Camera]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cameras WHERE id=?", (camera_id,))
            row = cursor.fetchone()
            if not row:
                return None
            try:
                brand_val = Brand(row["brand"])
            except ValueError:
                brand_val = Brand.GENERIC_ONVIF

            return Camera(
                id=row["id"],
                name=row["name"],
                ip=row["ip"],
                port=row["port"],
                username=row["username"],
                password=row["password"],
                channel=row["channel"],
                brand=brand_val,
                area_id=row["area_id"],
                is_active=bool(row["is_active"]),
                custom_main_url=row["custom_main_url"],
                custom_sub_url=row["custom_sub_url"]
            )

    # --- Persistência de Preferências ---
    def set_preference(self, key: str, value: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO layouts (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_preference(self, key: str, default: str = "") -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM layouts WHERE key=?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
