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
    # 信号定义
    finished = pyqtSignal(object)  # 任务完成，返回结果
    error = pyqtSignal(str)  # 任务出错，返回错误信息

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        """执行任务的入口方法，子类需要实现"""
        try:
            result = self.execute()
            self.finished.emit(result)
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)

    def execute(self) -> Any:
        """子类实现具体的任务逻辑"""
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


class ScriptExecutionWorker(BaseWorker):
    """
    脚本执行工作线程
    用于在后台线程执行SSH命令，避免UI卡顿
    """
    # 进度信号
    progress = pyqtSignal(str)  # 执行进度信息

    def __init__(self, script_service, script: Any, server_id: int, user_id: int):
        super().__init__()
        self.script_service = script_service
        self.script = script
        self.server_id = server_id
        self.user_id = user_id

    def execute(self) -> int:
        self.progress.emit("开始连接服务器...")
        exec_log_id = self.script_service.execute(
            self.script,
            self.server_id,
            self.user_id
        )
        self.progress.emit("执行完成")
        return exec_log_id


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
