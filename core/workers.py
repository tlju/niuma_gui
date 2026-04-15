"""
后台任务处理模块
使用QThread处理耗时操作，避免UI卡顿
"""
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from typing import Callable, Any, Optional
import traceback


class BaseWorker(QThread):
    """
    后台任务工作线程基类
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            result = self.execute()
            self.finished.emit(result)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

    def execute(self) -> Any:
        raise NotImplementedError


class DatabaseWorker(BaseWorker):
    """
    数据库操作工作线程
    用于在后台线程执行数据库查询，避免UI卡顿
    """
    def __init__(self, db_func: Callable, *args, **kwargs):
        super().__init__()
        self.db_func = db_func
        self.args = args
        self.kwargs = kwargs

    def execute(self) -> Any:
        return self.db_func(*self.args, **self.kwargs)


class AssetLoadWorker(BaseWorker):
    """
    资产加载工作线程
    用于在后台线程加载资产列表
    """
    def __init__(self, asset_service):
        super().__init__()
        self.asset_service = asset_service

    def execute(self) -> list:
        return self.asset_service.get_all()


class ScriptLoadWorker(BaseWorker):
    """
    脚本加载工作线程
    用于在后台线程加载脚本列表
    """
    def __init__(self, script_service):
        super().__init__()
        self.script_service = script_service

    def execute(self) -> list:
        return self.script_service.get_all()


class AuditLogLoadWorker(BaseWorker):
    """
    审计日志加载工作线程
    用于在后台线程加载审计日志
    """
    def __init__(self, audit_service, action_type: Optional[str] = None):
        super().__init__()
        self.audit_service = audit_service
        self.action_type = action_type

    def execute(self) -> list:
        if self.action_type:
            return self.audit_service.get_logs(action_type=self.action_type)
        return self.audit_service.get_logs()
