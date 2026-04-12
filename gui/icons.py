from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QFontMetrics, QPainterPath, QPen
from PyQt6.QtCore import Qt, QRect, QSize, QRectF
from PyQt6.QtWidgets import QStyle, QApplication


class IconProvider:
    _instance = None
    _style = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def style(self):
        if self._style is None:
            self._style = QApplication.style()
        return self._style

    def _create_icon(self, draw_func, size=32):
        cache_key = (draw_func.__name__, size)
        if cache_key in self._cache:
            return self._cache[cache_key]

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        draw_func(painter, size)
        painter.end()

        icon = QIcon(pixmap)
        self._cache[cache_key] = icon
        return icon

    def _draw_plus(self, painter, size):
        color = QColor("#145a32")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        r = size / 2
        painter.drawRoundedRect(int(r - size * 0.06), int(r - size * 0.35), int(size * 0.12), int(size * 0.7), 2, 2)
        painter.drawRoundedRect(int(r - size * 0.35), int(r - size * 0.06), int(size * 0.7), int(size * 0.12), 2, 2)

    def _draw_refresh(self, painter, size):
        color = QColor("#1a5276")
        pen = QPen(color, max(2, size * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        margin = size * 0.2
        rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
        painter.drawArc(rect, 30 * 16, 300 * 16)
        end_angle = 330
        cx = margin + (size - 2 * margin) / 2
        cy = margin + (size - 2 * margin) / 2
        radius = (size - 2 * margin) / 2
        import math
        ex = cx + radius * math.cos(math.radians(end_angle))
        ey = cy - radius * math.sin(math.radians(end_angle))
        arrow_size = size * 0.15
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        path = QPainterPath()
        path.moveTo(ex, ey)
        path.lineTo(ex + arrow_size, ey - arrow_size * 0.5)
        path.lineTo(ex + arrow_size * 0.3, ey + arrow_size * 0.6)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_play(self, painter, size):
        color = QColor("#5b2c6f")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        margin = size * 0.2
        path = QPainterPath()
        path.moveTo(margin, margin)
        path.lineTo(size - margin, size / 2)
        path.lineTo(margin, size - margin)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_trash(self, painter, size):
        color = QColor("#922b21")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        body_top = size * 0.35
        body_bottom = size * 0.8
        body_left = size * 0.25
        body_right = size * 0.75
        painter.drawRoundedRect(QRectF(body_left, body_top, body_right - body_left, body_bottom - body_top), 2, 2)
        painter.drawRect(QRectF(size * 0.2, size * 0.25, size * 0.6, size * 0.12))
        painter.drawRect(QRectF(size * 0.38, size * 0.15, size * 0.24, size * 0.12))
        lid_color = QColor("#ffffff")
        painter.setPen(QPen(lid_color, max(1, size * 0.04)))
        x1 = size * 0.35
        x2 = size * 0.65
        for y in [size * 0.48, size * 0.6, size * 0.72]:
            painter.drawLine(int(x1), int(y), int(x2), int(y))

    def _draw_edit(self, painter, size):
        color = QColor("#1a5276")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.save()
        cx = size * 0.55
        cy = size * 0.55
        painter.translate(cx, cy)
        painter.rotate(-45)
        pen_w = size * 0.12
        pen_h = size * 0.55
        painter.drawRoundedRect(QRectF(-pen_w / 2, -pen_h, pen_w, pen_h), 2, 2)
        tip_w = pen_w * 1.2
        tip_h = size * 0.12
        painter.drawRoundedRect(QRectF(-tip_w / 2, 0, tip_w, tip_h), 1, 1)
        painter.restore()

    def _draw_check(self, painter, size):
        color = QColor("#145a32")
        pen = QPen(color, max(2, size * 0.1), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        path = QPainterPath()
        path.moveTo(size * 0.2, size * 0.5)
        path.lineTo(size * 0.4, size * 0.7)
        path.lineTo(size * 0.8, size * 0.3)
        painter.drawPath(path)

    def _draw_cross(self, painter, size):
        color = QColor("#922b21")
        pen = QPen(color, max(2, size * 0.1), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        margin = size * 0.25
        painter.drawLine(int(margin), int(margin), int(size - margin), int(size - margin))
        painter.drawLine(int(size - margin), int(margin), int(margin), int(size - margin))

    def _draw_user(self, painter, size):
        color = QColor("#3498db")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        cx = size * 0.5
        head_r = size * 0.15
        painter.drawEllipse(QRectF(cx - head_r, size * 0.18, head_r * 2, head_r * 2))
        body_path = QPainterPath()
        body_path.moveTo(cx - size * 0.25, size * 0.85)
        body_path.quadTo(cx - size * 0.25, size * 0.5, cx, size * 0.5)
        body_path.quadTo(cx + size * 0.25, size * 0.5, cx + size * 0.25, size * 0.85)
        body_path.closeSubpath()
        painter.drawPath(body_path)

    def _draw_computer(self, painter, size):
        color = QColor("#2c3e50")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        screen_rect = QRectF(size * 0.15, size * 0.12, size * 0.7, size * 0.5)
        painter.drawRoundedRect(screen_rect, 3, 3)
        screen_inner = QRectF(size * 0.2, size * 0.17, size * 0.6, size * 0.4)
        painter.setBrush(QColor("#3498db"))
        painter.drawRoundedRect(screen_inner, 2, 2)
        painter.setBrush(color)
        stand_rect = QRectF(size * 0.35, size * 0.65, size * 0.3, size * 0.08)
        painter.drawRect(stand_rect)
        base_rect = QRectF(size * 0.25, size * 0.75, size * 0.5, size * 0.06)
        painter.drawRoundedRect(base_rect, 2, 2)

    def _draw_hdd(self, painter, size):
        color = QColor("#2c3e50")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        body = QRectF(size * 0.12, size * 0.25, size * 0.76, size * 0.5)
        painter.drawRoundedRect(body, 4, 4)
        painter.setBrush(QColor("#1abc9c"))
        indicator = QRectF(size * 0.6, size * 0.42, size * 0.08, size * 0.08)
        painter.drawEllipse(indicator)
        painter.setBrush(QColor("#ecf0f1"))
        slot = QRectF(size * 0.2, size * 0.38, size * 0.3, size * 0.06)
        painter.drawRoundedRect(slot, 1, 1)

    def _draw_file(self, painter, size):
        color = QColor("#3498db")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        margin = size * 0.18
        fold = size * 0.15
        path = QPainterPath()
        path.moveTo(margin, margin * 0.5)
        path.lineTo(size - margin - fold, margin * 0.5)
        path.lineTo(size - margin, margin * 0.5 + fold)
        path.lineTo(size - margin, size - margin * 0.5)
        path.lineTo(margin, size - margin * 0.5)
        path.closeSubpath()
        painter.drawPath(path)
        fold_path = QPainterPath()
        fold_path.moveTo(size - margin - fold, margin * 0.5)
        fold_path.lineTo(size - margin - fold, margin * 0.5 + fold)
        fold_path.lineTo(size - margin, margin * 0.5 + fold)
        fold_path.closeSubpath()
        painter.setBrush(QColor("#2980b9"))
        painter.drawPath(fold_path)
        painter.setPen(QPen(QColor("#ffffff"), max(1, size * 0.04)))
        line_y_start = size * 0.4
        for i in range(3):
            y = line_y_start + i * size * 0.12
            painter.drawLine(int(size * 0.28), int(y), int(size * 0.65), int(y))

    def _draw_info(self, painter, size):
        color = QColor("#3498db")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        cx = size / 2
        cy = size / 2
        r = size * 0.4
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        dot_r = size * 0.06
        painter.drawEllipse(QRectF(cx - dot_r, cy - r * 0.5, dot_r * 2, dot_r * 2))
        bar_w = size * 0.1
        bar_h = size * 0.25
        painter.drawRoundedRect(QRectF(cx - bar_w / 2, cy - r * 0.15, bar_w, bar_h), 2, 2)

    def _draw_download(self, painter, size):
        color = QColor("#145a32")
        pen = QPen(color, max(2, size * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        cx = size / 2
        cy = size / 2
        arrow_size = size * 0.25
        
        path = QPainterPath()
        path.moveTo(cx, cy - arrow_size * 0.5)
        path.lineTo(cx, cy + arrow_size * 0.5)
        path.lineTo(cx - arrow_size * 0.5, cy)
        path.moveTo(cx, cy + arrow_size * 0.5)
        path.lineTo(cx + arrow_size * 0.5, cy)
        painter.drawPath(path)
        
        base_y = cy + arrow_size * 0.7
        painter.drawLine(int(cx - arrow_size * 0.6), int(base_y), int(cx + arrow_size * 0.6), int(base_y))

    def _draw_upload(self, painter, size):
        color = QColor("#1a5276")
        pen = QPen(color, max(2, size * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        cx = size / 2
        cy = size / 2
        arrow_size = size * 0.25
        
        base_y = cy - arrow_size * 0.7
        painter.drawLine(int(cx - arrow_size * 0.6), int(base_y), int(cx + arrow_size * 0.6), int(base_y))
        
        path = QPainterPath()
        path.moveTo(cx, cy + arrow_size * 0.5)
        path.lineTo(cx, cy - arrow_size * 0.5)
        path.lineTo(cx - arrow_size * 0.5, cy)
        path.moveTo(cx, cy - arrow_size * 0.5)
        path.lineTo(cx + arrow_size * 0.5, cy)
        painter.drawPath(path)

    def _draw_settings(self, painter, size):
        color = QColor("#7f8c8d")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        cx = size / 2
        cy = size / 2
        outer_r = size * 0.4
        inner_r = size * 0.15
        painter.drawEllipse(QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2))
        painter.setBrush(QColor("#f5f6fa"))
        painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))
        painter.setBrush(color)
        tooth_w = size * 0.1
        tooth_h = size * 0.15
        for i in range(8):
            angle = i * 45
            import math
            rad = math.radians(angle)
            tx = cx + (outer_r - tooth_h * 0.3) * math.cos(rad)
            ty = cy + (outer_r - tooth_h * 0.3) * math.sin(rad)
            painter.save()
            painter.translate(tx, ty)
            painter.rotate(angle + 90)
            painter.drawRoundedRect(QRectF(-tooth_w / 2, 0, tooth_w, tooth_h), 2, 2)
            painter.restore()

    def _draw_book(self, painter, size):
        color = QColor("#9b59b6")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        margin = size * 0.15
        book_w = size - 2 * margin
        book_h = size - 2 * margin
        painter.drawRoundedRect(QRectF(margin, margin, book_w, book_h), 3, 3)
        spine_x = margin + book_w * 0.15
        painter.setPen(QPen(QColor("#8e44ad"), max(1, size * 0.03)))
        painter.drawLine(int(spine_x), int(margin + size * 0.05), int(spine_x), int(margin + book_h - size * 0.05))
        painter.setPen(QPen(QColor("#ffffff"), max(1, size * 0.025)))
        for i in range(3):
            y = margin + size * 0.2 + i * size * 0.18
            painter.drawLine(int(spine_x + size * 0.08), int(y), int(margin + book_w - size * 0.1), int(y))

    def _draw_checklist(self, painter, size):
        color = QColor("#e67e22")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        margin = size * 0.15
        list_w = size - 2 * margin
        list_h = size - 2 * margin
        painter.drawRoundedRect(QRectF(margin, margin, list_w, list_h), 4, 4)
        painter.setPen(QPen(QColor("#ffffff"), max(1, size * 0.04)))
        check_color = QColor("#27ae60")
        for i in range(3):
            y = margin + size * 0.22 + i * size * 0.2
            box_size = size * 0.1
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#ffffff"), max(1, size * 0.03)))
            painter.drawRoundedRect(QRectF(margin + size * 0.08, y - box_size / 2, box_size, box_size), 2, 2)
            painter.drawLine(int(margin + size * 0.25), int(y), int(margin + list_w - size * 0.1), int(y))
        painter.setPen(QPen(check_color, max(1.5, size * 0.05), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        y1 = margin + size * 0.22
        painter.drawLine(int(margin + size * 0.1), int(y1), int(margin + size * 0.14), int(y1 + size * 0.05))
        painter.drawLine(int(margin + size * 0.14), int(y1 + size * 0.05), int(margin + size * 0.18), int(y1 - size * 0.03))

    def _draw_document(self, painter, size):
        color = QColor("#2980b9")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        margin = size * 0.15
        fold = size * 0.12
        path = QPainterPath()
        path.moveTo(margin, margin)
        path.lineTo(size - margin - fold, margin)
        path.lineTo(size - margin, margin + fold)
        path.lineTo(size - margin, size - margin)
        path.lineTo(margin, size - margin)
        path.closeSubpath()
        painter.drawPath(path)
        fold_path = QPainterPath()
        fold_path.moveTo(size - margin - fold, margin)
        fold_path.lineTo(size - margin - fold, margin + fold)
        fold_path.lineTo(size - margin, margin + fold)
        fold_path.closeSubpath()
        painter.setBrush(QColor("#1a5276"))
        painter.drawPath(fold_path)
        painter.setPen(QPen(QColor("#ffffff"), max(1, size * 0.035)))
        for i in range(4):
            y = margin + size * 0.2 + i * size * 0.12
            line_w = size * 0.4 if i == 3 else size * 0.5
            painter.drawLine(int(margin + size * 0.1), int(y), int(margin + size * 0.1 + line_w), int(y))

    def _draw_workflow(self, painter, size):
        color = QColor("#16a085")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        box_size = size * 0.22
        gap = size * 0.08
        painter.drawRoundedRect(QRectF(size * 0.1, size * 0.1, box_size, box_size), 3, 3)
        painter.drawRoundedRect(QRectF(size * 0.1, size * 0.68 - gap, box_size, box_size), 3, 3)
        painter.drawRoundedRect(QRectF(size * 0.68 - gap, size * 0.39 - box_size / 2, box_size, box_size), 3, 3)
        pen = QPen(color, max(2, size * 0.05), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        start_x = size * 0.1 + box_size
        mid_x = size * 0.68 - gap
        top_y = size * 0.1 + box_size / 2
        bot_y = size * 0.68 - gap + box_size / 2
        right_y = size * 0.39
        painter.drawLine(int(start_x), int(top_y), int(mid_x), int(top_y))
        painter.drawLine(int(mid_x), int(top_y), int(mid_x), int(right_y - box_size / 2))
        painter.drawLine(int(start_x), int(bot_y), int(mid_x), int(bot_y))
        painter.drawLine(int(mid_x), int(bot_y), int(mid_x), int(right_y + box_size / 2))

    def _draw_about(self, painter, size):
        color = QColor("#3498db")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        cx = size / 2
        cy = size / 2
        r = size * 0.38
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        painter.setBrush(QColor("#ffffff"))
        dot_r = size * 0.055
        painter.drawEllipse(QRectF(cx - dot_r, cy - r * 0.45, dot_r * 2, dot_r * 2))
        bar_w = size * 0.09
        bar_h = size * 0.22
        painter.drawRoundedRect(QRectF(cx - bar_w / 2, cy - r * 0.1, bar_w, bar_h), 2, 2)

    def app_icon(self):
        return self._create_icon(self._draw_computer)

    def add_icon(self):
        return self._create_icon(self._draw_plus)

    def edit_icon(self):
        return self._create_icon(self._draw_edit)

    def refresh_icon(self):
        return self._create_icon(self._draw_refresh)

    def delete_icon(self):
        return self._create_icon(self._draw_trash)

    def execute_icon(self):
        return self._create_icon(self._draw_play)

    def ok_icon(self):
        return self._create_icon(self._draw_check)

    def cancel_icon(self):
        return self._create_icon(self._draw_cross)

    def user_icon(self):
        return self._create_icon(self._draw_user)

    def asset_icon(self):
        return self._create_icon(self._draw_hdd)

    def script_icon(self):
        return self._create_icon(self._draw_file)

    def audit_icon(self):
        return self._create_icon(self._draw_info)

    def download_icon(self):
        return self._create_icon(self._draw_download)

    def upload_icon(self):
        return self._create_icon(self._draw_upload)

    def settings_icon(self):
        return self._create_icon(self._draw_settings)

    def dict_icon(self):
        return self._create_icon(self._draw_book)

    def todo_icon(self):
        return self._create_icon(self._draw_checklist)

    def document_icon(self):
        return self._create_icon(self._draw_document)

    def workflow_icon(self):
        return self._create_icon(self._draw_workflow)

    def about_icon(self):
        return self._create_icon(self._draw_about)


icons = IconProvider()
