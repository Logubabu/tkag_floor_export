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
                if hasattr(wall, 'polygon') and wall.polygon:
                    points_to_check.extend(wall.polygon)
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
            rx = cx * math.cos(rad_yaw) + cy * math.sin(rad_yaw)
            ry = cx * math.sin(rad_yaw) - cy * math.cos(rad_yaw)
            iso_cx = rx
            iso_cy = (self.floor_model.story.elevation if self.floor_model and self.floor_model.story else 0.0) * math.cos(rad_pitch) - ry * math.sin(rad_pitch)
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

            # ETABS Standard Axonometric Isometric View Projection:
            # X & Y axes rotated around Z-axis, Z elevation projects vertically UP (+Screen Y)
            iso_x = x * math.cos(rad_yaw) - y * math.sin(rad_yaw)
            iso_y = (x * math.sin(rad_yaw) + y * math.cos(rad_yaw)) * math.sin(rad_pitch) + z * math.cos(rad_pitch)

            sx = self.pan_offset.x() + iso_x * self.zoom_factor
            sy = self.pan_offset.y() - iso_y * self.zoom_factor
            return QPointF(sx, sy)
        else:
            sx = self.pan_offset.x() + x * self.zoom_factor
            sy = self.pan_offset.y() - y * self.zoom_factor
            return QPointF(sx, sy)

    def _resolve_color(self, element_color: Optional[str], default_hex: str) -> QColor:
        if element_color and isinstance(element_color, str):
            c = element_color.strip()
            if c.startswith("#"):
                return QColor(c)
            elif c.isdigit():
                # ETABS integer color index mapping
                try:
                    idx = int(c)
                    palette = ["#1e40af", "#d946ef", "#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"]
                    return QColor(palette[idx % len(palette)])
                except Exception:
                    pass
            elif len(c) == 6 and all(ch in '0123456789ABCDEFabcdef' for ch in c):
                return QColor(f"#{c}")
        return QColor(default_hex)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            # ETABS Canvas Background
            painter.fillRect(self.rect(), QColor("#ffffff"))

            # Draw Grid Lines
            pen_grid = QPen(QColor("#e879f9"), 1, Qt.SolidLine)
            painter.setPen(pen_grid)
            for gx in range(-50, 60, 10):
                p1 = self._world_to_screen(gx, -50, 0.0)
                p2 = self._world_to_screen(gx, 50, 0.0)
                painter.drawLine(p1, p2)
            for gy in range(-50, 60, 10):
                p1 = self._world_to_screen(-50, gy, 0.0)
                p2 = self._world_to_screen(-50, gy, 0.0)
                painter.drawLine(p1, p2)

            if not self.floor_model:
                painter.setPen(QPen(QColor("#6b7280")))
                painter.setFont(QFont("Segoe UI", 12))
                painter.drawText(self.rect(), Qt.AlignCenter, "Load an ETABS model file to view 2D/3D floor layout.")
                return

            z_level = self.floor_model.story.elevation if (self.is_3d_mode and self.floor_model and self.floor_model.story) else 0.0
            story_h = self.floor_model.story.height if (self.floor_model and self.floor_model.story and self.floor_model.story.height > 0) else 3.5

            # 1. Draw Slabs (Dynamic extracted color or ETABS default)
            if self.show_slabs and self.floor_model.slabs:
                for slab in self.floor_model.slabs:
                    poly = QPolygonF()
                    slab_z = slab.elevation if self.is_3d_mode else 0.0
                    for pt in slab.polygon:
                        poly.append(self._world_to_screen(pt.x, pt.y, slab_z))
                    
                    s_color = self._resolve_color(getattr(slab, 'color', None), "#3b82f6")
                    painter.setPen(QPen(s_color, 2))
                    fill_color = QColor(s_color)
                    fill_color.setAlpha(120)
                    painter.setBrush(QBrush(fill_color))
                    painter.drawPolygon(poly)

            # 2. Draw Openings
            if self.show_openings and self.floor_model.openings:
                for op in self.floor_model.openings:
                    poly = QPolygonF()
                    op_z = op.elevation if self.is_3d_mode else 0.0
                    for pt in op.polygon:
                        poly.append(self._world_to_screen(pt.x, pt.y, op_z))
                    
                    painter.setPen(QPen(QColor("#000000"), 2, Qt.SolidLine))
                    painter.setBrush(QBrush(QColor(255, 255, 255)))
                    painter.drawPolygon(poly)

            # 3. Draw Beams (Dynamic extracted section color or ETABS beam magenta)
            if self.show_beams and self.floor_model.beams:
                for bm in self.floor_model.beams:
                    bm_color = self._resolve_color(getattr(bm, 'color', None), "#d946ef")
                    painter.setPen(QPen(bm_color, 2))
                    sp = bm.start_point
                    ep = bm.end_point
                    if not sp or not ep:
                        continue
                    z1 = sp.z if self.is_3d_mode else 0.0
                    z2 = ep.z if self.is_3d_mode else 0.0
                    p1 = self._world_to_screen(sp.x, sp.y, z1)
                    p2 = self._world_to_screen(ep.x, ep.y, z2)
                    painter.drawLine(p1, p2)
                    painter.drawLine(p1, p2)

                    if self.show_labels:
                        mid_x = (p1.x() + p2.x()) / 2.0
                        mid_y = (p1.y() + p2.y()) / 2.0
                        painter.setPen(QPen(QColor("#34d399")))
                        painter.setFont(QFont("Segoe UI", 8))
                        painter.drawText(int(mid_x), int(mid_y), str(bm.id))

            # 4. Draw Columns (Dynamic extracted column color or ETABS blue/amber)
            if self.show_columns:
                # Process columns below (supporting floor from below)
                for col in self.floor_model.columns_below:
                    sp = col.start_point
                    ep = col.end_point
                    if not sp or not ep:
                        continue

                    col_color = self._resolve_color(getattr(col, 'color', None), "#1e40af")
                    if self.is_3d_mode:
                        max_z = max(sp.z, ep.z)
                        min_z = min(sp.z, ep.z)
                        if abs(max_z - min_z) < 0.01:
                            top_z = z_level
                            bot_z = z_level - story_h
                        else:
                            top_z = max_z
                            bot_z = min_z

                        col_x = ep.x if abs(ep.z - top_z) < 0.1 else sp.x
                        col_y = ep.y if abs(ep.z - top_z) < 0.1 else sp.y

                        p_bot = self._world_to_screen(col_x, col_y, bot_z)
                        p_top = self._world_to_screen(col_x, col_y, top_z)

                        painter.setPen(QPen(col_color, 3))
                        painter.drawLine(p_bot, p_top)
                        painter.setBrush(QBrush(col_color))
                        r = max(3, int(4 * (self.zoom_factor / 20.0)))
                        r = min(r, 8)
                        painter.drawRect(int(p_bot.x() - r/2), int(p_bot.y() - r/2), r, r)
                        painter.drawRect(int(p_top.x() - r/2), int(p_top.y() - r/2), r, r)
                    else:
                        p1 = self._world_to_screen(sp.x, sp.y, 0.0)
                        painter.setPen(QPen(col_color, 2))
                        col_fill = QColor(col_color)
                        col_fill.setAlpha(40)
                        painter.setBrush(QBrush(col_fill))
                        r = max(5, int(7 * (self.zoom_factor / 20.0)))
                        r = min(r, 14)
                        painter.drawRect(int(p1.x() - r/2), int(p1.y() - r/2), r, r)

                    if self.show_labels:
                        painter.setPen(QPen(QColor("#fbbf24")))
                        painter.setFont(QFont("Segoe UI", 8))
                        pt_label = p_top if self.is_3d_mode else p1
                        painter.drawText(int(pt_label.x() + 6), int(pt_label.y() + 3), str(col.id))

                # Process columns above (reactions above floor)
                for col in self.floor_model.columns_above:
                    sp = col.start_point
                    ep = col.end_point
                    if not sp or not ep:
                        continue

                    col_color = self._resolve_color(getattr(col, 'color', None), "#a855f7")
                    if self.is_3d_mode:
                        max_z = max(sp.z, ep.z)
                        min_z = min(sp.z, ep.z)
                        if abs(max_z - min_z) < 0.01:
                            bot_z = z_level
                            top_z = z_level + story_h
                        else:
                            bot_z = min_z
                            top_z = max_z

                        col_x = sp.x if abs(sp.z - bot_z) < 0.1 else ep.x
                        col_y = sp.y if abs(sp.z - bot_z) < 0.1 else ep.y

                        p_bot = self._world_to_screen(col_x, col_y, bot_z)
                        p_top = self._world_to_screen(col_x, col_y, top_z)

                        painter.setPen(QPen(col_color, 3))
                        painter.drawLine(p_bot, p_top)
                        painter.setBrush(QBrush(col_color))
                        r = max(3, int(4 * (self.zoom_factor / 20.0)))
                        r = min(r, 8)
                        painter.drawRect(int(p_bot.x() - r/2), int(p_bot.y() - r/2), r, r)
                        painter.drawRect(int(p_top.x() - r/2), int(p_top.y() - r/2), r, r)
                    else:
                        p1 = self._world_to_screen(sp.x, sp.y, 0.0)
                        painter.setPen(QPen(col_color, 2))
                        col_fill = QColor(col_color)
                        col_fill.setAlpha(40)
                        painter.setBrush(QBrush(col_fill))
                        r = max(5, int(7 * (self.zoom_factor / 20.0)))
                        r = min(r, 14)
                        painter.drawRect(int(p1.x() - r/2), int(p1.y() - r/2), r, r)

                    if self.show_labels:
                        painter.setPen(QPen(QColor("#c084fc")))
                        painter.setFont(QFont("Segoe UI", 8))
                        pt_label = p_top if self.is_3d_mode else p1
                        painter.drawText(int(pt_label.x() + 6), int(pt_label.y() + 3), str(col.id))

            # 5. Draw Walls (Dynamic extracted wall color or ETABS red)
            if self.show_walls:
                all_walls = self.floor_model.walls_above + self.floor_model.walls_below
                for wall in all_walls:
                    w_sp = getattr(wall, 'start_point', None)
                    w_ep = getattr(wall, 'end_point', None)
                    if not w_sp or not w_ep:
                        continue
                    w_color = self._resolve_color(getattr(wall, 'color', None), "#ef4444")
                    z1 = w_sp.z if self.is_3d_mode else 0.0
                    z2 = w_ep.z if self.is_3d_mode else 0.0
                    p1_bot = self._world_to_screen(w_sp.x, w_sp.y, z1)
                    p2_bot = self._world_to_screen(w_ep.x, w_ep.y, z1)
                    p1_top = self._world_to_screen(w_sp.x, w_sp.y, z2)
                    p2_top = self._world_to_screen(w_ep.x, w_ep.y, z2)

                    if self.is_3d_mode and abs(z2 - z1) > 0.01:
                        wall_poly = QPolygonF([p1_bot, p2_bot, p2_top, p1_top])
                        painter.setPen(QPen(w_color, 2))
                        w_fill = QColor(w_color)
                        w_fill.setAlpha(60)
                        painter.setBrush(QBrush(w_fill))
                        painter.drawPolygon(wall_poly)
                    else:
                        painter.setPen(QPen(w_color, 4))
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
