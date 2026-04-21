from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
    QFrame, QSpacerItem, QSizePolicy, QGroupBox,
    QFormLayout, QSpinBox, QApplication, QFileDialog,
    QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from core.workers import AssetLoadWorker
from core.logger import get_logger
from gui.icons import icons
from gui.style_manager import load_combined_stylesheet
from datetime import datetime

logger = get_logger(__name__)


class AssetsPage(QWidget):
    def __init__(self, asset_service, current_user_id, dict_service=None, parent=None):
        super().__init__(parent)
        self.asset_service = asset_service
        self.current_user_id = current_user_id
        self.dict_service = dict_service
        self.loading_worker = None
        self.all_assets = []
        self.filtered_assets = []
        self.dict_cache = {}
        self._load_dict_cache()
        self.init_ui()
        self.load_assets()

    def _load_dict_cache(self):
        if self.dict_service:
            for dict_code in ["unit", "system", "location", "server_type"]:
                items = self.dict_service.get_dict_items(dict_code)
                self.dict_cache[dict_code] = {item.item_code: item.item_name for item in items}

    def _get_item_name(self, dict_code, item_code):
        if not item_code:
            return ""
        if dict_code in self.dict_cache and item_code in self.dict_cache[dict_code]:
            return self.dict_cache[dict_code][item_code]
        return item_code

    def _load_filter_combos(self):
        if self.dict_service:
            unit_items = self.dict_service.get_dict_items("unit")
            self.unit_filter_combo.clear()
            self.unit_filter_combo.addItem("全部", None)
            for item in unit_items:
                self.unit_filter_combo.addItem(item.item_name, item.item_code)

            system_items = self.dict_service.get_dict_items("system")
            self.system_filter_combo.clear()
            self.system_filter_combo.addItem("全部", None)
            for item in system_items:
                self.system_filter_combo.addItem(item.item_name, item.item_code)

    def init_ui(self):
        load_combined_stylesheet(QApplication.instance(), ["common", "assets_page"])

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        toolbar_frame = QFrame()
        toolbar_frame.setProperty("class", "toolbar")
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_layout.setSpacing(10)

        self.add_btn = QPushButton("添加资产")
        self.add_btn.setIcon(icons.add_icon())
        self.add_btn.setProperty("class", "success")
        self.add_btn.setMinimumHeight(34)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(icons.refresh_icon())
        self.refresh_btn.setMinimumHeight(34)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self.refresh_btn)

        toolbar_layout.addSpacing(10)

        self.export_btn = QPushButton("导出")
        self.export_btn.setIcon(icons.download_icon())
        self.export_btn.setMinimumHeight(34)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("导入")
        self.import_btn.setIcon(icons.upload_icon())
        self.import_btn.setMinimumHeight(34)
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar_layout.addWidget(self.import_btn)

        toolbar_layout.addSpacing(20)

        unit_filter_label = QLabel("单位:")
        toolbar_layout.addWidget(unit_filter_label)

        self.unit_filter_combo = QComboBox()
        self.unit_filter_combo.setFixedWidth(120)
        self.unit_filter_combo.setMinimumHeight(34)
        self.unit_filter_combo.view().setMinimumWidth(250)
        self.unit_filter_combo.addItem("全部", None)
        self.unit_filter_combo.currentTextChanged.connect(lambda: self._filter_assets(self.search_input.text()))
        toolbar_layout.addWidget(self.unit_filter_combo)

        system_filter_label = QLabel("系统:")
        toolbar_layout.addWidget(system_filter_label)

        self.system_filter_combo = QComboBox()
        self.system_filter_combo.setFixedWidth(120)
        self.system_filter_combo.setMinimumHeight(34)
        self.system_filter_combo.view().setMinimumWidth(350)
        self.system_filter_combo.addItem("全部", None)
        self.system_filter_combo.currentTextChanged.connect(lambda: self._filter_assets(self.search_input.text()))
        toolbar_layout.addWidget(self.system_filter_combo)

        toolbar_layout.addSpacing(10)

        search_label = QLabel("搜索:")
        toolbar_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入名称、IP或主机名搜索...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setMinimumHeight(34)
        self.search_input.textChanged.connect(self._filter_assets)
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addStretch()

        self.count_label = QLabel("共 0 条记录")
        self.count_label.setProperty("class", "count")
        toolbar_layout.addWidget(self.count_label)

        layout.addWidget(toolbar_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "单位", "系统", "IP地址", "IPv6", "端口", "主机名", "用户名", "业务服务", "位置", "服务器类型", "操作"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(10, 150)

        self.table.verticalHeader().setDefaultSectionSize(42)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self._load_filter_combos()

        self.add_btn.clicked.connect(self.show_add_dialog)
        self.refresh_btn.clicked.connect(self.load_assets)
        self.export_btn.clicked.connect(self.export_assets)
        self.import_btn.clicked.connect(self.import_assets)

    def load_assets(self):
        if self.loading_worker and self.loading_worker.isRunning():
            logger.warning("资产加载任务正在进行中，跳过")
            return

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("加载中...")
        self.loading_worker = AssetLoadWorker(self.asset_service)
        self.loading_worker.finished.connect(self._on_assets_loaded)
        self.loading_worker.error.connect(self._on_load_error)
        self.loading_worker.start()
        logger.debug("开始加载资产列表")

    def _on_assets_loaded(self, assets):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("刷新")
        self.all_assets = assets
        self.filtered_assets = assets
        self._populate_table(assets)
        self._update_count_label()
        logger.debug(f"成功加载 {len(assets)} 个资产")

    def _on_load_error(self, error_msg):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("刷新")
        logger.error(f"加载资产失败: {error_msg}")
        QMessageBox.critical(self, "错误", f"加载资产失败:\n{error_msg}")

    def _filter_assets(self, text):
        unit_filter = self.unit_filter_combo.currentData()
        system_filter = self.system_filter_combo.currentData()
        
        filtered = self.all_assets
        
        if unit_filter:
            filtered = [a for a in filtered if a.unit_name == unit_filter]
        
        if system_filter:
            filtered = [a for a in filtered if a.system_name == system_filter]
        
        if text:
            text = text.lower()
            filtered = [
                a for a in filtered
                if text in (self._get_item_name("unit", a.unit_name) or "").lower()
                or text in (self._get_item_name("system", a.system_name) or "").lower()
                or text in (a.ip or "").lower()
                or text in (a.ipv6 or "").lower()
                or text in (a.host_name or "").lower()
                or text in (a.username or "").lower()
                or text in (a.business_service or "").lower()
                or text in (self._get_item_name("location", a.location) or "").lower()
                or text in (self._get_item_name("server_type", a.server_type) or "").lower()
            ]
        
        self.filtered_assets = filtered
        self._populate_table(filtered)
        self._update_count_label()

    def _update_count_label(self):
        count = self.table.rowCount()
        total = len(self.all_assets)
        if count == total:
            self.count_label.setText(f"共 {count} 条记录")
        else:
            self.count_label.setText(f"显示 {count} / {total} 条记录")

    def _populate_table(self, assets):
        self.table.setRowCount(len(assets))

        for row, asset in enumerate(assets):
            self.table.setItem(row, 0, QTableWidgetItem(self._get_item_name("unit", asset.unit_name)))
            self.table.setItem(row, 1, QTableWidgetItem(self._get_item_name("system", asset.system_name)))
            self.table.setItem(row, 2, QTableWidgetItem(asset.ip or ""))
            self.table.setItem(row, 3, QTableWidgetItem(asset.ipv6 or ""))

            port_item = QTableWidgetItem(str(asset.port or ""))
            port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, port_item)

            self.table.setItem(row, 5, QTableWidgetItem(asset.host_name or ""))
            self.table.setItem(row, 6, QTableWidgetItem(asset.username or ""))
            self.table.setItem(row, 7, QTableWidgetItem(asset.business_service or ""))
            self.table.setItem(row, 8, QTableWidgetItem(self._get_item_name("location", asset.location)))
            self.table.setItem(row, 9, QTableWidgetItem(self._get_item_name("server_type", asset.server_type)))

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            edit_btn = QPushButton("编辑")
            edit_btn.setProperty("class", "table-edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, a=asset: self.show_edit_dialog(a))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setProperty("class", "table-delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, a=asset.id: self.delete_asset(a))
            btn_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 10, btn_widget)

    def _on_cell_double_clicked(self, row, column):
        if row < len(self.filtered_assets):
            asset = self.filtered_assets[row]
            dialog = AssetDetailDialog(self, asset, self.dict_service, self.asset_service)
            dialog.exec()

    def show_add_dialog(self):
        dialog = AssetDialog(self, dict_service=self.dict_service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.asset_service.create(**data, user_id=self.current_user_id)
                self.load_assets()
                QMessageBox.information(self, "成功", "资产添加成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加资产失败: {e}")

    def show_edit_dialog(self, asset):
        dialog = AssetDialog(self, asset, dict_service=self.dict_service)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.asset_service.update(asset.id, user_id=self.current_user_id, **data)
                self.load_assets()
                QMessageBox.information(self, "成功", "资产更新成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新资产失败: {e}")

    def delete_asset(self, asset_id: int):
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该资产吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.asset_service.delete(asset_id, self.current_user_id)
                self.load_assets()
                QMessageBox.information(self, "成功", "资产删除成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除资产失败: {e}")

    def export_assets(self):
        dialog = ExportDialog(self, len(self.all_assets))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            try:
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "导出资产",
                    f"资产列表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    "Excel 文件 (*.xlsx)"
                )
                
                if file_path:
                    asset_ids = None if options["export_all"] else [
                        self.filtered_assets[i].id for i in range(self.table.rowCount())
                    ]
                    
                    file_data = self.asset_service.export_assets(
                        asset_ids=asset_ids,
                        include_password=options["include_password"]
                    )
                    
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    QMessageBox.information(self, "成功", f"成功导出 {len(self.all_assets) if options['export_all'] else self.table.rowCount()} 个资产")
                    logger.info(f"资产导出成功: {file_path}")
                    
            except Exception as e:
                logger.error(f"导出资产失败: {e}")
                QMessageBox.critical(self, "错误", f"导出资产失败:\n{e}")

    def import_assets(self):
        dialog = ImportDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            options = dialog.get_options()
            try:
                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "导入资产",
                    "",
                    "Excel 文件 (*.xlsx *.xls)"
                )
                
                if file_path:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    success_count, fail_count, errors = self.asset_service.import_assets(
                        file_data=file_data,
                        update_existing=options["update_existing"],
                        skip_errors=options["skip_errors"]
                    )
                    
                    self.load_assets()
                    
                    result_msg = f"导入完成!\n成功: {success_count} 个\n失败: {fail_count} 个"
                    if errors:
                        result_msg += f"\n\n错误详情:\n" + "\n".join(errors[:10])
                        if len(errors) > 10:
                            result_msg += f"\n... 还有 {len(errors) - 10} 个错误"
                    
                    if fail_count > 0:
                        QMessageBox.warning(self, "导入完成", result_msg)
                    else:
                        QMessageBox.information(self, "导入成功", result_msg)
                    
                    logger.info(f"资产导入完成: 成功 {success_count}, 失败 {fail_count}")
                    
            except Exception as e:
                logger.error(f"导入资产失败: {e}")
                QMessageBox.critical(self, "错误", f"导入资产失败:\n{e}")


class AssetDialog(QDialog):
    def __init__(self, parent=None, asset=None, dict_service=None):
        super().__init__(parent)
        self.asset = asset
        self.dict_service = dict_service
        self.setWindowTitle("编辑资产" if asset else "添加资产")
        self.setMinimumSize(800, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()
        self._load_dict_data()
        if asset:
            self._populate_data()

    def _load_dict_data(self):
        if self.dict_service:
            unit_dict = self.dict_service.get_dict_by_code("unit")
            if unit_dict:
                unit_items = self.dict_service.get_dict_items("unit")
                self.unit_name_combo.addItem("", None)
                for item in unit_items:
                    self.unit_name_combo.addItem(item.item_name, item.item_code)

            system_dict = self.dict_service.get_dict_by_code("system")
            if system_dict:
                system_items = self.dict_service.get_dict_items("system")
                self.system_name_combo.addItem("", None)
                for item in system_items:
                    self.system_name_combo.addItem(item.item_name, item.item_code)

            location_dict = self.dict_service.get_dict_by_code("location")
            if location_dict:
                location_items = self.dict_service.get_dict_items("location")
                self.location_combo.addItem("", None)
                for item in location_items:
                    self.location_combo.addItem(item.item_name, item.item_code)

            server_type_dict = self.dict_service.get_dict_by_code("server_type")
            if server_type_dict:
                server_type_items = self.dict_service.get_dict_items("server_type")
                self.server_type_combo.addItem("", None)
                for item in server_type_items:
                    self.server_type_combo.addItem(item.item_name, item.item_code)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        title_label = QLabel("编辑资产信息" if self.asset else "添加新资产")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(12, 12, 12, 12)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)

        self.unit_name_combo = QComboBox()
        self.unit_name_combo.setMinimumHeight(34)
        left_layout.addWidget(QLabel("单位名称 *:"))
        left_layout.addWidget(self.unit_name_combo)

        self.system_name_combo = QComboBox()
        self.system_name_combo.setMinimumHeight(34)
        left_layout.addWidget(QLabel("系统名称 *:"))
        left_layout.addWidget(self.system_name_combo)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("例如: 192.168.1.100")
        self.ip_input.setMinimumHeight(34)
        left_layout.addWidget(QLabel("IP地址:"))
        left_layout.addWidget(self.ip_input)

        self.ipv6_input = QLineEdit()
        self.ipv6_input.setPlaceholderText("例如: 2001:db8::1")
        self.ipv6_input.setMinimumHeight(34)
        left_layout.addWidget(QLabel("IPv6地址:"))
        left_layout.addWidget(self.ipv6_input)

        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        self.port_input.setMinimumHeight(34)
        left_layout.addWidget(QLabel("端口:"))
        left_layout.addWidget(self.port_input)

        self.host_name_input = QLineEdit()
        self.host_name_input.setPlaceholderText("可选")
        self.host_name_input.setMinimumHeight(34)
        left_layout.addWidget(QLabel("主机名:"))
        left_layout.addWidget(self.host_name_input)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)

        self.location_combo = QComboBox()
        self.location_combo.setMinimumHeight(34)
        right_layout.addWidget(QLabel("位置:"))
        right_layout.addWidget(self.location_combo)

        self.server_type_combo = QComboBox()
        self.server_type_combo.setMinimumHeight(34)
        right_layout.addWidget(QLabel("服务器类型:"))
        right_layout.addWidget(self.server_type_combo)

        self.vip_input = QLineEdit()
        self.vip_input.setPlaceholderText("可选")
        self.vip_input.setMinimumHeight(34)
        right_layout.addWidget(QLabel("VIP:"))
        right_layout.addWidget(self.vip_input)

        self.business_service_input = QLineEdit()
        self.business_service_input.setPlaceholderText("可选")
        self.business_service_input.setMinimumHeight(34)
        right_layout.addWidget(QLabel("业务服务:"))
        right_layout.addWidget(self.business_service_input)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("SSH 登录用户名")
        self.username_input.setMinimumHeight(34)
        right_layout.addWidget(QLabel("用户名 *:"))
        right_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("SSH 登录密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(34)
        right_layout.addWidget(QLabel("密码 *:"))
        right_layout.addWidget(self.password_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("可选")
        self.notes_input.setMinimumHeight(80)
        self.notes_input.setMaximumHeight(120)
        right_layout.addWidget(QLabel("备注:"))
        right_layout.addWidget(self.notes_input)

        columns_layout = QHBoxLayout()
        columns_layout.addLayout(left_layout)
        columns_layout.addSpacing(20)
        columns_layout.addLayout(right_layout)
        columns_layout.addStretch()

        layout.addLayout(columns_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "success")
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(self.ok_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _populate_data(self):
        self._set_combo_value(self.unit_name_combo, self.asset.unit_name or "")
        self._set_combo_value(self.system_name_combo, self.asset.system_name or "")
        self.ip_input.setText(self.asset.ip or "")
        self.ipv6_input.setText(self.asset.ipv6 or "")
        self.port_input.setValue(self.asset.port or 22)
        self.host_name_input.setText(self.asset.host_name or "")
        self._set_combo_value(self.location_combo, self.asset.location or "")
        self._set_combo_value(self.server_type_combo, self.asset.server_type or "")
        self.vip_input.setText(self.asset.vip or "")
        self.business_service_input.setText(self.asset.business_service or "")
        self.username_input.setText(self.asset.username or "")
        self.password_input.setText(self.asset.password_cipher or "")
        self.notes_input.setText(self.asset.notes or "")

    def _set_combo_value(self, combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)

    def _validate_and_accept(self):
        if not self.unit_name_combo.currentText().strip():
            QMessageBox.warning(self, "提示", "请选择单位名称")
            self.unit_name_combo.setFocus()
            return
        if not self.system_name_combo.currentText().strip():
            QMessageBox.warning(self, "提示", "请选择系统名称")
            self.system_name_combo.setFocus()
            return
        if not self.username_input.text().strip():
            QMessageBox.warning(self, "提示", "请输入用户名")
            self.username_input.setFocus()
            return
        if not self.password_input.text():
            QMessageBox.warning(self, "提示", "请输入密码")
            self.password_input.setFocus()
            return
        self.accept()

    def get_data(self):
        return {
            "unit_name": self.unit_name_combo.currentData() or None,
            "system_name": self.system_name_combo.currentData() or None,
            "ip": self.ip_input.text().strip() or None,
            "ipv6": self.ipv6_input.text().strip() or None,
            "port": self.port_input.value() if self.port_input.value() != 22 else None,
            "host_name": self.host_name_input.text().strip() or None,
            "business_service": self.business_service_input.text().strip() or None,
            "location": self.location_combo.currentData() or None,
            "server_type": self.server_type_combo.currentData() or None,
            "vip": self.vip_input.text().strip() or None,
            "username": self.username_input.text().strip(),
            "password": self.password_input.text(),
            "notes": self.notes_input.toPlainText().strip() or None,
        }


class ExportDialog(QDialog):
    def __init__(self, parent=None, total_count=0):
        super().__init__(parent)
        self.total_count = total_count
        self.setWindowTitle("导出资产")
        self.setMinimumSize(400, 250)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(24, 20, 24, 20)

        title_label = QLabel("导出资产设置")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        info_label = QLabel(f"当前共有 {self.total_count} 个资产")
        info_label.setObjectName("dialogInfo")
        layout.addWidget(info_label)

        self.export_all_radio = QCheckBox("导出所有资产")
        self.export_all_radio.setChecked(True)
        layout.addWidget(self.export_all_radio)

        self.include_password_check = QCheckBox("包含密码字段")
        self.include_password_check.setChecked(False)
        layout.addWidget(self.include_password_check)

        warning_label = QLabel("⚠️ 注意: 包含密码字段会导出解密后的密码,请注意文件安全!")
        warning_label.setObjectName("dialogWarning")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "success")
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_options(self):
        return {
            "export_all": self.export_all_radio.isChecked(),
            "include_password": self.include_password_check.isChecked()
        }


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导入资产")
        self.setMinimumSize(450, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(24, 20, 24, 20)

        title_label = QLabel("导入资产设置")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        format_label = QLabel("支持格式: Excel (.xlsx, .xls)")
        format_label.setObjectName("dialogFormat")
        layout.addWidget(format_label)

        required_label = QLabel("必填字段: 单位名称*、系统名称*、用户名*、IP地址或IPv6地址*")
        required_label.setObjectName("dialogRequired")
        layout.addWidget(required_label)

        self.update_existing_check = QCheckBox("更新已存在的资产 (根据单位名称+系统名称+IP地址+IPv6地址+用户名匹配)")
        self.update_existing_check.setChecked(False)
        layout.addWidget(self.update_existing_check)

        self.skip_errors_check = QCheckBox("跳过错误继续导入")
        self.skip_errors_check.setChecked(True)
        layout.addWidget(self.skip_errors_check)

        note_label = QLabel("💡 提示: 可以先导出资产作为模板,然后填写数据后导入")
        note_label.setObjectName("dialogNote")
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setProperty("class", "secondary")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setProperty("class", "success")
        self.ok_btn.setMinimumHeight(40)
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_options(self):
        return {
            "update_existing": self.update_existing_check.isChecked(),
            "skip_errors": self.skip_errors_check.isChecked()
        }


class AssetDetailDialog(QDialog):
    def __init__(self, parent=None, asset=None, dict_service=None, asset_service=None):
        super().__init__(parent)
        self.asset = asset
        self.dict_service = dict_service
        self.asset_service = asset_service
        self.setWindowTitle("资产详情")
        self.setMinimumSize(600, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._init_ui()
        self._populate_data()

    def _get_item_name(self, dict_code, item_code):
        if not item_code:
            return "-"
        if self.dict_service:
            items = self.dict_service.get_dict_items(dict_code)
            for item in items:
                if item.item_code == item_code:
                    return item.item_name
        return item_code

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        title_label = QLabel("资产详情")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        info_frame = QFrame()
        info_frame.setObjectName("infoFrame")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(8)

        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(40)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        left_layout.addWidget(self._create_field_row("单位:", "unit_label"))
        left_layout.addWidget(self._create_field_row("系统:", "system_label"))
        left_layout.addWidget(self._create_field_row("IP地址:", "ip_label"))
        left_layout.addWidget(self._create_field_row("IPv6:", "ipv6_label"))
        left_layout.addWidget(self._create_field_row("端口:", "port_label"))
        left_layout.addWidget(self._create_field_row("主机名:", "host_name_label"))

        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        right_layout.addWidget(self._create_field_row("位置:", "location_label"))
        right_layout.addWidget(self._create_field_row("服务器类型:", "server_type_label"))
        right_layout.addWidget(self._create_field_row("VIP:", "vip_label"))
        right_layout.addWidget(self._create_field_row("业务服务:", "business_service_label"))
        right_layout.addWidget(self._create_field_row("用户名:", "username_label"))
        right_layout.addWidget(self._create_password_row())

        grid_layout.addLayout(left_layout)
        grid_layout.addLayout(right_layout)
        grid_layout.addStretch()

        info_layout.addLayout(grid_layout)

        notes_layout = QVBoxLayout()
        notes_layout.setSpacing(4)
        notes_title = QLabel("备注:")
        notes_title.setObjectName("notesTitle")
        self.notes_text = QTextEdit()
        self.notes_text.setObjectName("notesText")
        self.notes_text.setReadOnly(True)
        self.notes_text.setMinimumHeight(80)
        self.notes_text.setMaximumHeight(120)
        notes_layout.addWidget(notes_title)
        notes_layout.addWidget(self.notes_text)
        info_layout.addLayout(notes_layout)

        layout.addWidget(info_frame)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.close_btn = QPushButton("关闭")
        self.close_btn.setProperty("class", "secondary")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.setMinimumHeight(40)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _create_field_row(self, label_text, attr_name):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        label = QLabel(label_text)
        label.setObjectName("detailLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        value_label = QLabel("-")
        value_label.setObjectName("detailValue")
        value_label.setWordWrap(True)
        setattr(self, attr_name, value_label)

        row_layout.addWidget(label)
        row_layout.addWidget(value_label)
        row_layout.addStretch()

        return row_widget

    def _create_password_row(self):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        label = QLabel("密码:")
        label.setObjectName("detailLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        self.password_btn = QPushButton("点击查看密码")
        self.password_btn.setProperty("class", "secondary")
        self.password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.password_btn.clicked.connect(self._show_password)

        row_layout.addWidget(label)
        row_layout.addWidget(self.password_btn)
        row_layout.addStretch()

        return row_widget

    def _show_password(self):
        if not self.asset or not self.asset_service:
            return
        
        password = self.asset_service.get_password(self.asset.id)
        if password:
            dialog = PasswordDialog(self, password)
            dialog.exec()
        else:
            QMessageBox.information(self, "提示", "未设置密码")

    def _populate_data(self):
        if not self.asset:
            return

        self.unit_label.setText(self._get_item_name("unit", self.asset.unit_name) or "-")
        self.system_label.setText(self._get_item_name("system", self.asset.system_name) or "-")
        self.ip_label.setText(self.asset.ip or "-")
        self.ipv6_label.setText(self.asset.ipv6 or "-")
        self.port_label.setText(str(self.asset.port) if self.asset.port else "-")
        self.host_name_label.setText(self.asset.host_name or "-")
        self.location_label.setText(self._get_item_name("location", self.asset.location) or "-")
        self.server_type_label.setText(self._get_item_name("server_type", self.asset.server_type) or "-")
        self.vip_label.setText(self.asset.vip or "-")
        self.business_service_label.setText(self.asset.business_service or "-")
        self.username_label.setText(self.asset.username or "-")
        self.notes_text.setText(self.asset.notes or "-")


class PasswordDialog(QDialog):
    def __init__(self, parent=None, password: str = ""):
        super().__init__(parent)
        self.password = password
        self.setWindowTitle("密码详情")
        self.setMinimumSize(400, 180)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        title_label = QLabel("解密后的密码")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        self.password_input = QLineEdit()
        self.password_input.setObjectName("passwordDisplay")
        self.password_input.setText(self.password)
        self.password_input.setReadOnly(True)
        self.password_input.setMinimumHeight(36)
        layout.addWidget(self.password_input)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.copy_btn = QPushButton("复制密码")
        self.copy_btn.setProperty("class", "success")
        self.copy_btn.setMinimumHeight(36)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_password)
        btn_layout.addWidget(self.copy_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setProperty("class", "secondary")
        self.close_btn.setMinimumHeight(36)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _copy_password(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.password)
        self.copy_btn.setText("已复制!")
        self.copy_btn.setEnabled(False)
