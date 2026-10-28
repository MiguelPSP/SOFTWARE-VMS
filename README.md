# INTERFACE SOFTWARE VMS - Central de Gerenciamento de Vídeo CFTV

Software Desktop corporativo de alto desempenho na identidade visual **Preto e Amarelo Ouro**, projetado para monitoramento e gerenciamento local de até **64 câmeras IP simultâneas** de marcas mistas (**Hikvision**, **HiLook**, **Intelbras**, **Dahua**, **Holowits** e **Genéricos ONVIF/RTSP**), desenvolvido em **Python** com **PyQt6** e decodificação acelerada via **OpenCV/FFmpeg**.

Inspirado nas plataformas industriais **iVMS-4200** e **Intelbras SIM Next**.

---

## 🏛️ Arquitetura e Engenharia do Sistema

### 1. Política Inteligente de Dual Stream (Zero CPU Choke)
A decodificação simultânea de 64 streams em resolução 1080p ou 4K esgotaria os limites de CPU e barramento PCI-e de qualquer computador. Para resolver isso:
- **Modo Grade Multi-View (Grids 2x2, 3x3, 4x4, 8x8):** O sistema conecta compulsoriamente no **Substream** (D1 / 360p, 15 FPS, H.264/H.265 leve).
- **Modo Câmera Única / Foco (1x1):** Ao dar **duplo clique** em qualquer câmera na grade, o sistema executa um *hot-swap* assíncrono para o **Stream Principal (Alta Resolução / 1080p/4K)**. Ao restaurar a grade, o canal retorna instantaneamente para o Substream.

### 2. Eliminação de Latência e Buffer Bloat (Zero-Lag)
O OpenCV nativo mantém buffers acumulados que causam atraso progressivo (lag de vários segundos). O VMS aplica na camada de baixo nível:
```python
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|"   # Obriga TCP (elimina quadros rasgados em Wi-Fi)
    "fflags;nobuffer|"      # Desativa buffer do libavformat
    "max_delay;500000|"     # Atraso máximo tolerado de 500ms
    "flags;low_delay|"      # Prioridade total para baixa latência
    "stimeout;5000000"      # Timeout de 5s para auto-reconexão
)
```
Adicionalmente, cada `StreamWorker` opera com fila de tamanho 1 (`queue maxsize=1`), descartando quadros defasados para garantir exibição estritamente em tempo real.

---

## 📡 Engenharia Reversa de Protocolos e Rotas RTSP

O módulo `core/rtsp_profiles.py` implementa a geração automática das URLs segundo os manuais e engenharia reversa dos fabricantes:

| Fabricante | Perfil Main Stream (Alta Resolução) | Perfil Substream (Baixa Resolução) |
| :--- | :--- | :--- |
| **Hikvision** | `rtsp://user:pass@ip:554/Streaming/Channels/{ch}01` | `rtsp://user:pass@ip:554/Streaming/Channels/{ch}02` |
| **HiLook** | `rtsp://user:pass@ip:554/Streaming/Channels/{ch}01` | `rtsp://user:pass@ip:554/Streaming/Channels/{ch}02` |
| **Intelbras** | `rtsp://user:pass@ip:554/cam/realmonitor?channel={ch}&subtype=0` | `rtsp://user:pass@ip:554/cam/realmonitor?channel={ch}&subtype=1` |
| **Dahua** | `rtsp://user:pass@ip:554/cam/realmonitor?channel={ch}&subtype=0` | `rtsp://user:pass@ip:554/cam/realmonitor?channel={ch}&subtype=1` |
| **Genérico** | `rtsp://user:pass@ip:554/live/ch{ch}` | `rtsp://user:pass@ip:554/live/ch{ch}_sub` |

*Exemplo Hikvision Canal 1:* Main = `/Channels/101`, Sub = `/Channels/102`.  
*Exemplo Intelbras Canal 1:* Main = `channel=1&subtype=0`, Sub = `channel=1&subtype=1`.

---

## 📂 Estrutura Modular do Código

```
vms_desktop/
├── core/
│   ├── config.py           # Flags FFmpeg, diretórios de mídia, limites de FPS
│   ├── models.py           # Entidades estruturadas (Camera, Area, StreamType, Status)
│   ├── rtsp_profiles.py    # Gerador dinâmico de URLs RTSP por fabricante
│   ├── database.py         # SQLite: CRUD de até 64 canais, áreas e preferências
│   ├── stream_worker.py    # Thread QThread com captura assíncrona, reconexão e gravação
│   └── stream_manager.py   # Orquestrador de Dual Stream (auto-swap Main <-> Sub)
├── gui/
│   ├── theme.py            # QSS Dark VMS corporativo (estilo iVMS-4200)
│   ├── video_cell.py       # Célula individual (QPainter, OSD, Snapshot, Rec, Fullscreen)
│   ├── video_grid.py       # Grade multi-view (1x1, 2x2, 3x3, 4x4, 8x8) e paginação
│   ├── camera_tree.py      # Árvore lateral com Drag-and-Drop e busca em tempo real
│   ├── camera_dialog.py    # Formulário de cadastro com teste de conexão em tempo real
│   └── main_window.py      # Janela principal com toolbar, F11 e monitoramento
├── utils/
│   └── helpers.py          # Gerador de 64 câmeras demo e funções de apoio
├── recordings/             # Armazenamento padrão de arquivos .mp4 gravados
├── snapshots/              # Armazenamento padrão de imagens .jpg capturadas
├── vms_data.db             # Banco de dados local persistente
├── main.py                 # Ponto de entrada da aplicação
├── requirements.txt        # Dependências do projeto
└── README.md
```

---

## 🚀 Instalação e Execução

### 1. Pré-requisitos
- Python 3.10 ou superior instalado.
- Git (opcional).

### 2. Criar Ambiente Virtual e Instalar Dependências
No terminal (PowerShell ou Bash):
```bash
# Entrar no diretório do projeto
cd C:\Users\mayla\.gemini\antigravity\scratch\vms_desktop

# Criar e ativar ambiente virtual
python -m venv venv
.\venv\Scripts\activate   # No Linux/Mac: source venv/bin/activate

# Instalar bibliotecas necessárias
pip install -r requirements.txt
```

### 3. Executar o VMS
```bash
python main.py
```

---

## 🧪 Testando com 64 Câmeras sem Hardware Físico

O software inclui um **Gerador de Demonstração e Teste de Carga**:
1. Abra o VMS com `python main.py`.
2. Clique no botão **"⚡ Gerar 64 Câmeras Demo"** na barra superior.
3. O VMS criará automaticamente 64 câmeras no banco SQLite divididas entre Hikvision, HiLook, Intelbras e Dahua.
4. O **Modo Demonstração** será ativado, gerando fluxos de vídeo sintéticos SMPTE com telemetria, data/hora e resolução dinâmica para cada um dos 64 canais na grade **8x8**.
5. Dê **duplo clique** em qualquer uma das 64 células para ver o chaveamento instantâneo para 1080p (Main Stream) e duplo clique para retornar à grade.

---

## 📦 Como Compilar para Executável Standalone (.exe)

Para distribuir o software sem necessidade de instalar Python no computador de destino:

```bash
pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed ^
  --name "VMS_Pro_Enterprise" ^
  --add-data "core;core" ^
  --add-data "gui;gui" ^
  --add-data "utils;utils" ^
  main.py
```
O executável final estará disponível na pasta `dist/VMS_Pro_Enterprise/VMS_Pro_Enterprise.exe`.

---

## 🛡️ Recursos Operacionais
- **Snapshot Local (📷):** Salva instantaneamente imagem JPEG de alta qualidade na pasta `snapshots/`.
- **Gravação Manual (⏺):** Codifica o fluxo em formato MP4 na pasta `recordings/` com OSD de carimbo de data e hora.
- **Auto-Reconexão:** Se o cabo de rede for desconectado ou o Wi-Fi oscilar, a thread entra em modo backoff e restabelece a imagem assim que o dispositivo responder.
- **Atalhos Úteis:**
  - `F11`: Alternar Tela Cheia.
  - `Esc`: Sair de Tela Cheia ou restaurar grade ao estar em 1x1.
  - `Duplo Clique na Câmera da Grade`: Maximizar com Main Stream / Restaurar para Substream.
  - `Duplo Clique na Câmera da Árvore`: Carregar câmera na célula atualmente selecionada.
