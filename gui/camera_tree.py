"""
Árvore Lateral de Dispositivos e Áreas (CameraTree).
Layout hierárquico corporativo (Áreas -> NVRs/Marcas -> Câmeras),
com busca rápida em tempo real, suporte a Drag-and-Drop, Auto-Discovery e menu de contexto seguro.
"""

from typing import Dict, List, Optional

from PyQt6.QtCore import QByteArray, QMimeData, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDrag, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import DatabaseManager
from core.models import Area, Camera


class DraggableCameraTreeWidget(QTreeWidget):
    """QTreeWidget customizado para suportar início de Drag-and-Drop com ID da câmera."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return

        cam_id = item.data(0, Qt.ItemDataRole.UserRole)
        if cam_id is None:
            return

        mime_data = QMimeData()
        mime_data.setData("application/x-vms-camera-id", QByteArray(str(cam_id).encode()))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)


class CameraTree(QWidget):
    """
    Barra lateral esquerda do VMS.
    Exibe a árvore de locais e dispositivos e permite atribuição rápida à grade.
    """

    camera_selected_for_cell = pyqtSignal(object)  # Camera
    edit_camera_requested = pyqtSignal(int)        # camera_id
    delete_camera_requested = pyqtSignal(int)      # camera_id
    add_camera_requested = pyqtSignal()
    auto_discovery_requested = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.cameras: List[Camera] = []
        self.areas: List[Area] = []

        self._init_ui()
        self.reload_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Botão de Destaque: Auto-Discovery
        self.btn_discovery = QPushButton("🔍 Auto-Discovery (Buscar na Rede)", self)
        self.btn_discovery.setStyleSheet("""
            QPushButton {
                background-color: #f5b800;
                color: #0b0c0e;
                font-weight: bold;
                padding: 7px;
                border: 1px solid #f5b800;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #ffd000;
            }
        """)
        self.btn_discovery.clicked.connect(self.auto_discovery_requested.emit)
        layout.addWidget(self.btn_discovery)

        # Barra de Busca Rápida
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("Filtrar câmeras, marcas ou IPs...")
        self.txt_search.textChanged.connect(self._filter_tree)
        layout.addWidget(self.txt_search)

        # Árvore de Dispositivos
        self.tree = DraggableCameraTreeWidget(self)
        self.tree.setHeaderLabels(["Dispositivos & Locais", "IP / Marca"])
        self.tree.setColumnWidth(0, 180)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree, 1)

        # Botão Inferior de Adição Manual
        btn_layout = QHBoxLayout()
        self.btn_add_cam = QPushButton("➕ Manual", self)
        self.btn_add_cam.clicked.connect(self.add_camera_requested.emit)
        btn_layout.addWidget(self.btn_add_cam)

        layout.addLayout(btn_layout)

    def reload_data(self):
        """Recarrega todas as áreas e câmeras do SQLite e remonta a árvore."""
        self.tree.clear()
        self.areas = self.db.get_all_areas()
        self.cameras = self.db.get_all_cameras()

        area_nodes: Dict[int, QTreeWidgetItem] = {}

        for area in self.areas:
            node = QTreeWidgetItem(self.tree)
            node.setText(0, f"📁 {area.name}")
            node.setText(1, area.description)
            node.setFont(0, QFont("Segoe UI", 9, QFont.Weight.Bold))
            node.setData(0, Qt.ItemDataRole.UserRole, None)
            if area.id is not None:
                area_nodes[area.id] = node

        unassigned_node = None

        for cam in self.cameras:
            if cam.area_id and cam.area_id in area_nodes:
                parent_node = area_nodes[cam.area_id]
            else:
                if unassigned_node is None:
                    unassigned_node = QTreeWidgetItem(self.tree)
                    unassigned_node.setText(0, "📁 Câmeras Gerais")
                    unassigned_node.setData(0, Qt.ItemDataRole.UserRole, None)
                parent_node = unassigned_node

            cam_item = QTreeWidgetItem(parent_node)
            cam_item.setText(0, f"📹 {cam.name}")
            cam_item.setText(1, f"{cam.ip} ({cam.brand.value})")
            cam_item.setData(0, Qt.ItemDataRole.UserRole, cam.id)
            cam_item.setToolTip(0, f"Marca: {cam.brand.value}\nCanal: {cam.channel}\nRTSP Port: {cam.port}")

        self.tree.expandAll()

    def _filter_tree(self, text: str):
        query = text.lower().strip()
        for i in range(self.tree.topLevelItemCount()):
            area_item = self.tree.topLevelItem(i)
            area_visible = False
            for j in range(area_item.childCount()):
                cam_item = area_item.child(j)
                name_match = query in cam_item.text(0).lower()
                ip_match = query in cam_item.text(1).lower()
                is_match = name_match or ip_match or not query
                cam_item.setHidden(not is_match)
                if is_match:
                    area_visible = True
            area_item.setHidden(not area_visible and bool(query))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        cam_id = item.data(0, Qt.ItemDataRole.UserRole)
        if cam_id is not None:
            cam = next((c for c in self.cameras if c.id == cam_id), None)
            if cam:
                self.camera_selected_for_cell.emit(cam)

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return

        cam_id = item.data(0, Qt.ItemDataRole.UserRole)
        if cam_id is None:
            return

        menu = QMenu(self)
        action_play = menu.addAction("▶ Exibir na Célula Ativa")
        action_edit = menu.addAction("✏ Editar Configurações")
        action_delete = menu.addAction("🗑 Excluir Câmera")

        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        cam = next((c for c in self.cameras if c.id == cam_id), None)

        if action == action_play and cam:
            self.camera_selected_for_cell.emit(cam)
        elif action == action_edit:
            # Uso de QTimer para desacoplar a ação da pilha de eventos do menu de contexto
            QTimer.singleShot(0, lambda cid=cam_id: self.edit_camera_requested.emit(cid))
        elif action == action_delete:
            QTimer.singleShot(0, lambda cid=cam_id: self.delete_camera_requested.emit(cid))
