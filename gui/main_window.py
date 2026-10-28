"""
Janela Principal do VMS Desktop (MainWindow).
Integra a Barra Lateral Hierárquica, a Grade de Vídeo Multi-Canal (1x1 até 8x8),
a Toolbar de Ações Rápidas, o Auto-Discovery e o Gerenciador Central de Streams.
"""

import os
import subprocess
import sys
from datetime import datetime
from typing import List

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.config import RECORDINGS_DIR, SNAPSHOTS_DIR
from core.database import DatabaseManager
from core.models import Camera, StreamType
from core.stream_manager import StreamManager
from gui.camera_dialog import CameraDialog
from gui.camera_tree import CameraTree
from gui.discovery_dialog import DiscoveryDialog
from gui.theme import DARK_THEME_QSS
from gui.video_grid import VideoGrid
from utils.helpers import populate_64_test_cameras


class MainWindow(QMainWindow):
    """Janela principal corporativa do sistema de monitoramento de CFTV."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("INTERFACE SOFTWARE VMS - Central de Monitoramento CFTV")
        self.resize(1400, 900)
        self.setMinimumSize(1024, 600)

        # Inicializa banco de dados e motor de stream
        self.db = DatabaseManager()
        self.stream_manager = StreamManager(mock_mode_by_default=False)

        # Aplica folha de estilo corporativa Preto e Amarelo
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_ui()
        self._init_shortcuts()
        self._init_status_timer()
        self._auto_populate_first_grid()

    def _init_ui(self):
        # 1. Barra de Ferramentas Superior (Quick Actions & Grids)
        self.toolbar = QToolBar("Barra Principal", self)
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(self.toolbar)

        # Título da Marca no Topo
        self.lbl_logo_title = QLabel(" INTERFACE VMS  ")
        self.lbl_logo_title.setStyleSheet("font-weight: 900; font-size: 15px; color: #f5b800; padding: 2px 6px;")
        self.toolbar.addWidget(self.lbl_logo_title)

        # Botão de Destaque: Auto-Discovery (Preto e Amarelo)
        self.btn_discovery = QPushButton("🔍 Buscar Câmeras na Rede (Auto-Discovery)")
        self.btn_discovery.setStyleSheet("""
            QPushButton {
                background-color: #f5b800;
                color: #0b0c0e;
                font-weight: bold;
                padding: 6px 14px;
                border: 1px solid #f5b800;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #ffd000;
            }
        """)
        self.btn_discovery.clicked.connect(self._open_discovery_dialog)
        self.toolbar.addWidget(self.btn_discovery)

        self.toolbar.addSeparator()

        # Botões de Seleção de Grade
        self.lbl_grids = QLabel(" Layout: ")
        self.lbl_grids.setStyleSheet("font-weight: bold; color: #a0a6b5;")
        self.toolbar.addWidget(self.lbl_grids)

        grid_buttons = [
            ("1x1", "1x1"),
            ("2x2", "2x2"),
            ("3x3", "3x3"),
            ("4x4", "4x4"),
            ("5x5", "5x5"),
            ("6x6", "6x6"),
            ("7x7", "7x7"),
            ("8x8 (64 Ch)", "8x8"),
        ]

        for label, layout_key in grid_buttons:
            btn = QPushButton(label)
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked, k=layout_key: self.video_grid.apply_layout(k))
            self.toolbar.addWidget(btn)

        self.toolbar.addSeparator()

        # Botão Adicionar Câmera Manual
        self.btn_add_cam = QPushButton("➕ Adicionar Manual")
        self.btn_add_cam.clicked.connect(self._open_add_camera_dialog)
        self.toolbar.addWidget(self.btn_add_cam)

        # Botão Teste de Estresse (64 Câmeras Demo)
        self.btn_stress = QPushButton("⚡ Gerar 64 Câmeras Demo")
        self.btn_stress.setToolTip("Popula 64 canais mistos (Hikvision, HiLook, Intelbras, Dahua) para teste de estresse")
        self.btn_stress.clicked.connect(self._generate_64_demo_cameras)
        self.toolbar.addWidget(self.btn_stress)

        # Toggle Modo Simulação
        self.btn_mock_toggle = QPushButton("🎮 Modo Demonstração: OFF")
        self.btn_mock_toggle.setCheckable(True)
        self.btn_mock_toggle.setToolTip("Gera streams sintéticos SMPTE com telemetria para testar sem rede física")
        self.btn_mock_toggle.clicked.connect(self._toggle_mock_mode)
        self.toolbar.addWidget(self.btn_mock_toggle)

        self.toolbar.addSeparator()

        # Abrir Pasta de Capturas
        self.btn_folder = QPushButton("📁 Arquivos")
        self.btn_folder.setToolTip("Abrir pasta de gravações e snapshots")
        self.btn_folder.clicked.connect(self._open_media_folder)
        self.toolbar.addWidget(self.btn_folder)

        # Tela Cheia
        self.btn_fullscreen = QPushButton("⛶ F11")
        self.btn_fullscreen.setToolTip("Alternar Modo Tela Cheia (F11)")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        self.toolbar.addWidget(self.btn_fullscreen)

        # 2. Painel Central Dividido (Splitter)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Lado Esquerdo: Árvore de Câmeras
        self.camera_tree = CameraTree(self.db, self.splitter)
        self.camera_tree.setMinimumWidth(260)
        self.camera_tree.setMaximumWidth(450)
        self.camera_tree.camera_selected_for_cell.connect(self._on_tree_camera_selected)
        self.camera_tree.add_camera_requested.connect(self._open_add_camera_dialog)
        self.camera_tree.edit_camera_requested.connect(self._open_edit_camera_dialog)
        self.camera_tree.delete_camera_requested.connect(self._delete_camera)
        self.camera_tree.auto_discovery_requested.connect(self._open_discovery_dialog)

        # Lado Direito: Grade de Vídeo
        self.video_grid = VideoGrid(self.stream_manager, self.splitter)
        self.video_grid.status_message_emitted.connect(self._show_status_message)
        self.video_grid.edit_camera_requested.connect(self._open_edit_camera_dialog)

        self.splitter.addWidget(self.camera_tree)
        self.splitter.addWidget(self.video_grid)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        self.setCentralWidget(self.splitter)

        # 3. Barra de Status Inferior
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.lbl_status_msg = QLabel("INTERFACE SOFTWARE VMS Pronto. Use 'Buscar Câmeras na Rede' para localizar seus dispositivos.")
        self.lbl_status_stats = QLabel("Canais: 0 ativos | Modo: SUBSTREAM")
        self.lbl_status_time = QLabel("")

        self.status_bar.addWidget(self.lbl_status_msg, 1)
        self.status_bar.addPermanentWidget(self.lbl_status_stats)
        self.status_bar.addPermanentWidget(self.lbl_status_time)

    def _init_shortcuts(self):
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self, self._on_escape_pressed)

    def _init_status_timer(self):
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status_bar)
        self.status_timer.start(1000)

    def _update_status_bar(self):
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.lbl_status_time.setText(f"🕒 {now_str}  ")

        active_workers = len(self.stream_manager._workers)
        stream_mode = "[MAIN ALTA RES]" if self.video_grid.is_maximized_1x1 else "[SUBSTREAM RESUMO]"
        self.lbl_status_stats.setText(f"Canais Ativos: {active_workers} | {stream_mode}  ")

    def _show_status_message(self, message: str):
        self.lbl_status_msg.setText(message)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _on_escape_pressed(self):
        if self.isFullScreen():
            self.showNormal()
        elif self.video_grid.is_maximized_1x1:
            self.video_grid.apply_layout(self.video_grid.previous_layout_name)

    def _toggle_mock_mode(self):
        enabled = self.btn_mock_toggle.isChecked()
        self.stream_manager.set_mock_mode(enabled)
        if enabled:
            self.btn_mock_toggle.setText("🎮 Modo Demonstração: ON")
            self.btn_mock_toggle.setStyleSheet("background-color: #2e7d32; color: white;")
            self._show_status_message("Modo Demonstração ativado (Gerando streams SMPTE para testes).")
        else:
            self.btn_mock_toggle.setText("🎮 Modo Demonstração: OFF")
            self.btn_mock_toggle.setStyleSheet("")
            self._show_status_message("Modo Demonstração desativado (Conectando a RTSP real).")

    def _open_discovery_dialog(self):
        """Abre a janela de Auto-Discovery e carrega os canais importados."""
        dialog = DiscoveryDialog(self.db, parent=self)
        dialog.cameras_added.connect(self._on_cameras_discovered_and_added)
        dialog.exec()

    def _on_cameras_discovered_and_added(self, added_cameras: List[Camera]):
        """Atualiza a árvore e preenche a grade com as câmeras recém-adicionadas."""
        self.camera_tree.reload_data()
        for i, cam in enumerate(added_cameras):
            if i < 64:
                self.video_grid.assign_camera_to_cell(i, cam)

        if len(added_cameras) > 4:
            self.video_grid.apply_layout("3x3" if len(added_cameras) <= 9 else "4x4")

        self._show_status_message(f"✅ {len(added_cameras)} câmeras importadas e conectadas na grade!")

    def _open_add_camera_dialog(self):
        dialog = CameraDialog(self.db, parent=self)
        if dialog.exec():
            self.camera_tree.reload_data()
            self._show_status_message("Nova câmera adicionada com sucesso!")

    def _open_edit_camera_dialog(self, camera_id: int):
        cam = self.db.get_camera_by_id(camera_id)
        if cam:
            dialog = CameraDialog(self.db, camera=cam, parent=self)
            if dialog.exec():
                self.camera_tree.reload_data()
                # Atualiza na grade se estiver ativa
                for idx, c in self.video_grid.cell_camera_map.items():
                    if c and c.id == camera_id:
                        updated_cam = self.db.get_camera_by_id(camera_id)
                        if updated_cam:
                            self.video_grid.assign_camera_to_cell(idx, updated_cam)
                        break
                self._show_status_message(f"Câmera {cam.name} atualizada.")

    def _delete_camera(self, camera_id: int):
        cam = self.db.get_camera_by_id(camera_id)
        if not cam:
            return
        reply = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Deseja realmente remover a câmera '{cam.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 1. Desvincula imediatamente da grade para evitar sinais de pintura em células mortas
            for idx, c in list(self.video_grid.cell_camera_map.items()):
                if c and c.id == camera_id:
                    self.video_grid.cells[idx].assign_camera(None)
                    self.video_grid.cell_camera_map[idx] = None

            # 2. Encerra a thread via stream_manager (com retenção de referência para evitar crash)
            self.stream_manager.stop_camera_stream(camera_id)

            # 3. Remove do banco SQLite
            self.db.delete_camera(camera_id)

            # 4. Atualiza a árvore de forma segura e assíncrona
            QTimer.singleShot(50, self.camera_tree.reload_data)
            self._show_status_message(f"Câmera '{cam.name}' excluída com sucesso.")

    def _generate_64_demo_cameras(self):
        reply = QMessageBox.question(
            self,
            "Gerar 64 Câmeras de Teste",
            "Deseja popular o banco de dados com 64 canais distribuídos entre Hikvision, HiLook, Intelbras e Dahua para teste de carga?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            populate_64_test_cameras(self.db)
            self.camera_tree.reload_data()
            self.btn_mock_toggle.setChecked(True)
            self._toggle_mock_mode()
            self._populate_grid_with_cameras()
            self.video_grid.apply_layout("8x8")
            self._show_status_message("64 Câmeras carregadas na grade 8x8 com sucesso!")

    def _auto_populate_first_grid(self):
        self._populate_grid_with_cameras()

    def _populate_grid_with_cameras(self):
        all_cams = self.db.get_all_cameras()
        for i, cam in enumerate(all_cams[:64]):
            self.video_grid.assign_camera_to_cell(i, cam)

    def _on_tree_camera_selected(self, camera: Camera):
        selected_idx = self.video_grid.selected_cell_index
        self.video_grid.assign_camera_to_cell(selected_idx, camera)
        self._show_status_message(f"Câmera '{camera.name}' carregada na Célula #{selected_idx + 1}")

    def _open_media_folder(self):
        target_dir = str(RECORDINGS_DIR if os.path.exists(RECORDINGS_DIR) else SNAPSHOTS_DIR)
        if sys.platform == "win32":
            os.startfile(target_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target_dir])
        else:
            subprocess.Popen(["xdg-open", target_dir])

    def closeEvent(self, event):
        self._show_status_message("Encerrando fluxos de vídeo com segurança...")
        self.stream_manager.stop_all()
        event.accept()
