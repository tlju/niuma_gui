"""
图标资源管理模块
使用Python代码生成简单的图标，避免依赖外部图片文件
"""
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QStyle


class IconProvider:
    """
    图标提供者
    使用系统标准图标，确保在各种平台上都能正常显示
    """
    _instance = None
    _style = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def style(self):
        """获取QStyle实例"""
        if self._style is None:
            from PyQt6.QtWidgets import QApplication
            self._style = QApplication.style()
        return self._style

    def app_icon(self):
        """应用图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

    def add_icon(self):
        """添加图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)

    def edit_icon(self):
        """编辑图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)

    def refresh_icon(self):
        """刷新图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload)

    def delete_icon(self):
        """删除图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon)

    def execute_icon(self):
        """执行图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)

    def ok_icon(self):
        """确定图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_DialogOkButton)

    def cancel_icon(self):
        """取消图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)

    def user_icon(self):
        """用户图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def asset_icon(self):
        """资产图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon)

    def script_icon(self):
        """脚本图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def audit_icon(self):
        """审计图标"""
        return self.style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)


# 创建全局图标提供者实例
icons = IconProvider()
