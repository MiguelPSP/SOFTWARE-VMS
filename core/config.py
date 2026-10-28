"""
Configurações globais e parâmetros de otimização de baixo nível para o VMS.
"""

import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = BASE_DIR / "recordings"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
ASSETS_DIR = BASE_DIR / "assets"
DATABASE_PATH = BASE_DIR / "vms_data.db"
LOGO_PATH = ASSETS_DIR / "logo_interface.png"

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Copia a logo fornecida pelo usuário se ainda não estiver na pasta de assets
import shutil
SOURCE_LOGO = Path("C:/Users/mayla/.gemini/antigravity/brain/0d16ea79-1841-4b81-b03c-2a3adfdcf27c/.user_uploaded/media_1793207640593.png")
if SOURCE_LOGO.exists() and not LOGO_PATH.exists():
    try:
        shutil.copy2(str(SOURCE_LOGO), str(LOGO_PATH))
    except Exception:
        pass

# -------------------------------------------------------------------------
# Otimizações FFmpeg para OpenCV (Estabilidade contra telas cinzas e baixa latência)
# -------------------------------------------------------------------------
# Força TCP estrito com buffer de 2MB para absorver oscilações de Wi-Fi e rede
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"       # TCP obrigatório (evita perda de pacotes RTP que causa tela cinza)
    "buffer_size;2097152|"      # 2 Megabytes de buffer de socket (absorve rajadas)
    "reorder_queue_size;100|"   # Fila de reordenação de pacotes para montagem correta de quadros
    "max_delay;1000000|"        # Tolera até 1.0s de jitter antes de descartar
    "stimeout;4000000|"         # Timeout de socket de 4 segundos
    "flags;low_delay"           # Decodificação otimizada
)

ENABLE_HW_ACCELERATION = True

# Parâmetros de Streaming e Reconexão
DEFAULT_RECONNECT_DELAY = 3.0      # Segundos antes de tentar reconectar
MAX_RECONNECT_DELAY = 12.0         # Limite máximo de backoff
FRAME_DROP_THRESHOLD = 2           # Descarte de quadros acumulados
DEFAULT_SUB_FPS_LIMIT = 15         # Limite de FPS no modo Grade (poupa CPU/GPU)
DEFAULT_MAIN_FPS_LIMIT = 30        # FPS pleno no modo 1x1

# Presets de Grade Suportados
SUPPORTED_GRIDS = {
    "1x1": (1, 1),
    "2x2": (2, 2),
    "3x3": (3, 3),
    "4x4": (4, 4),
    "5x5": (5, 5),
    "6x6": (6, 6),
    "7x7": (7, 7),
    "8x8": (8, 8),
}

MAX_CAMERAS = 64
