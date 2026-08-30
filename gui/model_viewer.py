import math
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, QLabel, QFrame
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QWheelEvent, QMouseEvent, QFont

from backend.app.models.intermediate import BuildingModel, FloorModel, FrameType


class ModelViewerWidget(QWidget):
    """
    2D Floor Plan & 3D Isometric View Canvas for Structural Elements.
    Supports Zoom, Pan, Fit Screen, Layer Visibility Toggles, Coordinate Readout,
    and Story Selection Highlighting.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.floor_model: Optional[FloorModel] = None
        self.building_model: Optional[BuildingModel] = None

        # View settings
        self.is_3d_mode: bool = False
        self.zoom_factor: float = 1.0
        self.pan_offset: QPointF = QPointF(0, 0)
        self.last_mouse_pos: Optional[QPointF] = None
        self.pitch_deg: float = 35.0  # 3D Elevation angle (ETABS default 35°)
        self.yaw_deg: float = 45.0    # 3D Azimuth angle (ETABS default 45°)

        # Layer visibility flags
        self.show_slabs: bool = True
        self.show_beams: bool = True
        self.show_columns: bool = True
        self.show_walls: bool = True
        self.show_openings: bool = True
        self.show_nodes: bool = True
        self.show_labels: bool = True

        # Hovered element info
        self.hover_info: str = "X: 0.00, Y: 0.00"

        self.setMouseTracking(True)
        self.setMinimumSize(400, 350)

    def set_floor_model(self, floor_model: FloorModel):
        self.floor_model = floor_model
        self.fit_to_screen()
        self.update()

    def set_building_model(self, building_model: BuildingModel):
        self.building_model = building_model
        self.update()

    def set_2d_mode(self):
        self.is_3d_mode = False
        self.pitch_deg = 90.0
        self.yaw_deg = 0.0
        self.fit_to_screen()
        self.update()

    def set_3d_mode(self):
        self.is_3d_mode = True
        self.pitch_deg = 35.0
        self.yaw_deg = 45.0
        self.fit_to_screen()
        self.update()

    def fit_to_screen(self):
        min_x, max_x = float('inf'), float('-inf')
        min_y, max_y = float('inf'), float('-inf')

        points_to_check = []
        if self.floor_model:
            for slab in self.floor_model.slabs:
                points_to_check.extend(slab.polygon)
            for bm in self.floor_model.beams:
                points_to_check.extend([bm.start_point, bm.end_point])
            for col in self.floor_model.columns_above + self.floor_model.columns_below:
                points_to_check.extend([col.start_point, col.end_point])
            for wall in self.floor_model.walls_above + self.floor_model.walls_below:
                sp = getattr(wall, 'start_point', None)
                ep = getattr(wall, 'end_point', None)
                if sp and ep:
                    points_to_check.extend([sp, ep])

        for pt in points_to_check:
            if pt.x < min_x: min_x = pt.x
            if pt.x > max_x: max_x = pt.x
            if pt.y < min_y: min_y = pt.y
            if pt.y > max_y: max_y = pt.y

        if min_x == float('inf') or max_x == min_x or max_y == min_y:
            min_x, max_x, min_y, max_y = -10, 10, -10, 10

        width = max_x - min_x
        height = max_y - min_y

        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0

        canvas_w = self.width() if self.width() > 50 else 600
        canvas_h = self.height() if self.height() > 50 else 400

        scale_x = (canvas_w * 0.75) / width
        scale_y = (canvas_h * 0.75) / height
        self.zoom_factor = min(scale_x, scale_y)

        if self.is_3d_mode:
            rad_yaw = math.radians(self.yaw_deg)
            rad_pitch = math.radians(self.pitch_deg)
            rx = cx * math.cos(rad_yaw) - cy * math.sin(rad_yaw)
            ry = cx * math.sin(rad_yaw) + cy * math.cos(rad_yaw)
            iso_cx = rx
            iso_cy = ry * math.sin(rad_pitch)
            self.pan_offset = QPointF(
                canvas_w / 2.0 - iso_cx * self.zoom_factor,
                canvas_h / 2.0 + iso_cy * self.zoom_factor
            )
        else:
            self.pan_offset = QPointF(
                canvas_w / 2.0 - cx * self.zoom_factor,
                canvas_h / 2.0 + cy * self.zoom_factor
            )

    def wheelEvent(self, event: QWheelEvent):
        angle = event.angleDelta().y()
        factor = 1.15 if angle > 0 else 0.85
        self.zoom_factor *= factor
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        self.last_mouse_pos = event.position()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()
        if self.last_mouse_pos:
            delta = pos - self.last_mouse_pos
            # Right Click OR Shift + Left Click triggers 3D Orbiting (Pitch & Yaw)
            if self.is_3d_mode and ((event.buttons() & Qt.RightButton) or (event.modifiers() & Qt.ShiftModifier and event.buttons() & Qt.LeftButton)):
                self.yaw_deg = (self.yaw_deg + delta.x() * 0.5) % 360.0
                self.pitch_deg = max(5.0, min(85.0, self.pitch_deg - delta.y() * 0.5))
            elif event.buttons() & (Qt.LeftButton | Qt.MiddleButton):
                self.pan_offset += delta
            self.last_mouse_pos = pos

        # Update hover coordinates
        world_x = (pos.x() - self.pan_offset.x()) / self.zoom_factor
        world_y = -(pos.y() - self.pan_offset.y()) / self.zoom_factor
        self.hover_info = f"X: {world_x:.2f} m, Y: {world_y:.2f} m"

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.last_mouse_pos = None

    def _world_to_screen(self, x: float, y: float, z: float = 0.0) -> QPointF:
        if self.is_3d_mode:
            rad_yaw = math.radians(self.yaw_deg)
            rad_pitch = math.radians(self.pitch_deg)
            rx = x * math.cos(rad_yaw) - y * math.sin(rad_yaw)
            ry = x * math.sin(rad_yaw) + y * math.cos(rad_yaw)
            iso_x = rx
            iso_y = ry * math.sin(rad_pitch) - z * math.cos(rad_pitch)
            sx = self.pan_offset.x() + iso_x * self.zoom_factor
            sy = self.pan_offset.y() - iso_y * self.zoom_factor
            return QPointF(sx, sy)
        else:
            sx = self.pan_offset.x() + x * self.zoom_factor
            sy = self.pan_offset.y() - y * self.zoom_factor
            return QPointF(sx, sy)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            # Dark Canvas Background
            painter.fillRect(self.rect(), QColor("#111827"))

            # Draw Grid
            pen_grid = QPen(QColor("#1f2937"), 1, Qt.DashLine)
            painter.setPen(pen_grid)
            for gx in range(-50, 60, 10):
                p1 = self._world_to_screen(gx, -50, 0.0)
                p2 = self._world_to_screen(gx, 50, 0.0)
                painter.drawLine(p1, p2)
            for gy in range(-50, 60, 10):
                p1 = self._world_to_screen(-50, gy, 0.0)
                p2 = self._world_to_screen(50, gy, 0.0)
                painter.drawLine(p1, p2)

            if not self.floor_model:
                painter.setPen(QPen(QColor("#6b7280")))
                painter.setFont(QFont("Segoe UI", 12))
                painter.drawText(self.rect(), Qt.AlignCenter, "Load an ETABS model file to view 2D/3D floor layout.")
                return

            z_level = self.floor_model.story.elevation if self.is_3d_mode else 0.0

            # 1. Draw Slabs
            if self.show_slabs and self.floor_model.slabs:
                for slab in self.floor_model.slabs:
                    poly = QPolygonF()
                    for pt in slab.polygon:
                        poly.append(self._world_to_screen(pt.x, pt.y, z_level))
                    
                    painter.setPen(QPen(QColor("#3b82f6"), 2))
                    painter.setBrush(QBrush(QColor(59, 130, 246, 45)))
                    painter.drawPolygon(poly)

            # 2. Draw Openings
            if self.show_openings and self.floor_model.openings:
                for op in self.floor_model.openings:
                    poly = QPolygonF()
                    for pt in op.polygon:
                        poly.append(self._world_to_screen(pt.x, pt.y, z_level))
                    
                    painter.setPen(QPen(QColor("#ef4444"), 2, Qt.DashLine))
                    painter.setBrush(QBrush(QColor(239, 68, 68, 60)))
                    painter.drawPolygon(poly)

            # 3. Draw Beams
            if self.show_beams and self.floor_model.beams:
                painter.setPen(QPen(QColor("#10b981"), 3))
                for bm in self.floor_model.beams:
                    z1 = bm.start_point.z if (self.is_3d_mode and hasattr(bm.start_point, 'z')) else z_level
                    z2 = bm.end_point.z if (self.is_3d_mode and hasattr(bm.end_point, 'z')) else z_level
                    p1 = self._world_to_screen(bm.start_point.x, bm.start_point.y, z1)
                    p2 = self._world_to_screen(bm.end_point.x, bm.end_point.y, z2)
                    painter.drawLine(p1, p2)

                    if self.show_labels:
                        mid_x = (p1.x() + p2.x()) / 2.0
                        mid_y = (p1.y() + p2.y()) / 2.0
                        painter.setPen(QPen(QColor("#34d399")))
                        painter.setFont(QFont("Segoe UI", 8))
                        painter.drawText(int(mid_x), int(mid_y), str(bm.id))
                        painter.setPen(QPen(QColor("#10b981"), 3))

            # 4. Draw Columns (3D Vertical Frames in 3D Mode, Cap Boxes in 2D Mode)
            if self.show_columns:
                all_cols = self.floor_model.columns_above + self.floor_model.columns_below
                for col in all_cols:
                    z1 = col.start_point.z if self.is_3d_mode else 0.0
                    z2 = col.end_point.z if self.is_3d_mode else 0.0
                    p1 = self._world_to_screen(col.start_point.x, col.start_point.y, z1)
                    p2 = self._world_to_screen(col.end_point.x, col.end_point.y, z2)
                    
                    if self.is_3d_mode:
                        # Draw 3D column vertical line
                        painter.setPen(QPen(QColor("#f59e0b"), 3))
                        painter.drawLine(p1, p2)
                        # Draw top and bottom end caps
                        painter.setBrush(QBrush(QColor("#f59e0b")))
                        r = max(3, int(4 * (self.zoom_factor / 20.0)))
                        r = min(r, 8)
                        painter.drawRect(int(p2.x() - r/2), int(p2.y() - r/2), r, r)
                    else:
                        painter.setPen(QPen(QColor("#f59e0b"), 2))
                        painter.setBrush(QBrush(QColor("#f59e0b")))
                        r = max(4, int(6 * (self.zoom_factor / 20.0)))
                        r = min(r, 12)
                        painter.drawRect(int(p1.x() - r/2), int(p1.y() - r/2), r, r)

                    if self.show_labels:
                        painter.setPen(QPen(QColor("#fbbf24")))
                        painter.setFont(QFont("Segoe UI", 8))
                        pt_label = p2 if self.is_3d_mode else p1
                        painter.drawText(int(pt_label.x() + 6), int(pt_label.y() + 3), str(col.id))

            # 5. Draw Walls (3D Quad Faces in 3D Mode, Line Segments in 2D Mode)
            if self.show_walls:
                all_walls = self.floor_model.walls_above + self.floor_model.walls_below
                for wall in all_walls:
                    w_sp = getattr(wall, 'start_point', None)
                    w_ep = getattr(wall, 'end_point', None)
                    if not w_sp or not w_ep:
                        continue
                    z1 = w_sp.z if self.is_3d_mode else 0.0
                    z2 = w_ep.z if self.is_3d_mode else 0.0
                    p1_bot = self._world_to_screen(w_sp.x, w_sp.y, z1)
                    p2_bot = self._world_to_screen(w_ep.x, w_ep.y, z1)
                    p1_top = self._world_to_screen(w_sp.x, w_sp.y, z2)
                    p2_top = self._world_to_screen(w_ep.x, w_ep.y, z2)

                    if self.is_3d_mode and abs(z2 - z1) > 0.01:
                        wall_poly = QPolygonF([p1_bot, p2_bot, p2_top, p1_top])
                        painter.setPen(QPen(QColor("#8b5cf6"), 2))
                        painter.setBrush(QBrush(QColor(139, 92, 246, 75)))
                        painter.drawPolygon(wall_poly)
                    else:
                        painter.setPen(QPen(QColor("#8b5cf6"), 4))
                        painter.drawLine(p1_bot, p2_bot)

            # 6. Draw Nodes / Joint Points
            if self.show_nodes and self.floor_model:
                all_nodes = set()
                for bm in self.floor_model.beams:
                    if bm.start_point: all_nodes.add((bm.start_point.x, bm.start_point.y, bm.start_point.z if self.is_3d_mode else z_level))
                    if bm.end_point: all_nodes.add((bm.end_point.x, bm.end_point.y, bm.end_point.z if self.is_3d_mode else z_level))
                for col in self.floor_model.columns_above + self.floor_model.columns_below:
                    if col.start_point: all_nodes.add((col.start_point.x, col.start_point.y, col.start_point.z if self.is_3d_mode else z_level))
                    if col.end_point: all_nodes.add((col.end_point.x, col.end_point.y, col.end_point.z if self.is_3d_mode else z_level))
                for wall in self.floor_model.walls_above + self.floor_model.walls_below:
                    w_sp = getattr(wall, 'start_point', None)
                    w_ep = getattr(wall, 'end_point', None)
                    if w_sp: all_nodes.add((w_sp.x, w_sp.y, w_sp.z if self.is_3d_mode else z_level))
                    if w_ep: all_nodes.add((w_ep.x, w_ep.y, w_ep.z if self.is_3d_mode else z_level))
                for slab in self.floor_model.slabs:
                    for pt in slab.polygon:
                        all_nodes.add((pt.x, pt.y, z_level))

                painter.setPen(QPen(QColor("#38bdf8"), 1))
                painter.setBrush(QBrush(QColor("#0ea5e9")))
                r = max(2, int(3 * (self.zoom_factor / 20.0)))
                r = min(r, 6)
                for nx, ny, nz in all_nodes:
                    pt_screen = self._world_to_screen(nx, ny, nz)
                    painter.drawEllipse(int(pt_screen.x() - r), int(pt_screen.y() - r), r*2, r*2)

            # 7. Draw ETABS RGB Axis Triad (Lower-Left Corner)
            triad_ox, triad_oy = 45, self.height() - 45
            axis_len = 30.0
            
            if self.is_3d_mode:
                rad_yaw = math.radians(self.yaw_deg)
                rad_pitch = math.radians(self.pitch_deg)
                
                xx_r = math.cos(rad_yaw)
                xy_r = math.sin(rad_yaw) * math.sin(rad_pitch)
                
                yx_r = -math.sin(rad_yaw)
                yy_r = math.cos(rad_yaw) * math.sin(rad_pitch)
                
                zx_r = 0.0
                zy_r = -math.cos(rad_pitch)
                
                pt_o = QPointF(triad_ox, triad_oy)
                pt_x = QPointF(triad_ox + xx_r * axis_len, triad_oy - xy_r * axis_len)
                pt_y = QPointF(triad_ox + yx_r * axis_len, triad_oy - yy_r * axis_len)
                pt_z = QPointF(triad_ox + zx_r * axis_len, triad_oy - zy_r * axis_len)

                painter.setPen(QPen(QColor("#ef4444"), 2))
                painter.drawLine(pt_o, pt_x)
                painter.drawText(int(pt_x.x() + 3), int(pt_x.y() + 3), "X")

                painter.setPen(QPen(QColor("#10b981"), 2))
                painter.drawLine(pt_o, pt_y)
                painter.drawText(int(pt_y.x() + 3), int(pt_y.y() + 3), "Y")

                painter.setPen(QPen(QColor("#3b82f6"), 2))
                painter.drawLine(pt_o, pt_z)
                painter.drawText(int(pt_z.x() + 3), int(pt_z.y() + 3), "Z")
            else:
                painter.setPen(QPen(QColor("#ef4444"), 2))
                painter.drawLine(QPointF(triad_ox, triad_oy), QPointF(triad_ox + axis_len, triad_oy))
                painter.drawText(int(triad_ox + axis_len + 3), triad_oy + 3, "X")

                painter.setPen(QPen(QColor("#10b981"), 2))
                painter.drawLine(QPointF(triad_ox, triad_oy), QPointF(triad_ox, triad_oy - axis_len))
                painter.drawText(triad_ox - 3, int(triad_oy - axis_len - 3), "Y")

            # Draw Coordinate & Mode HUD Text
            painter.setPen(QPen(QColor("#9ca3af")))
            painter.setFont(QFont("Segoe UI", 9))
            mode_str = f"3D View (Yaw: {self.yaw_deg:.0f}°, Pitch: {self.pitch_deg:.0f}° | RMB Drag to Orbit)" if self.is_3d_mode else "2D Plan View"
            hud_text = f"Mode: {mode_str} | {self.hover_info}"
            painter.drawText(100, self.height() - 12, hud_text)
        finally:
            painter.end()
