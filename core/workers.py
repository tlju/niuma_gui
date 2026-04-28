"""
后台任务处理模块
使用QThread处理耗时操作，避免UI卡顿
"""
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from typing import Callable, Any, Optional, List, Tuple
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


class AssetExportWorker(BaseWorker):
    """
    资产导出工作线程
    用于在后台线程导出资产到Excel文件
    """
    def __init__(self, asset_service, asset_ids: Optional[List[int]] = None, include_password: bool = False):
        super().__init__()
        self.asset_service = asset_service
        self.asset_ids = asset_ids
        self.include_password = include_password

    def execute(self) -> bytes:
        return self.asset_service.export_assets(
            asset_ids=self.asset_ids,
            include_password=self.include_password
        )


class AssetImportWorker(BaseWorker):
    """
    资产导入工作线程
    用于在后台线程从Excel文件导入资产
    """
    def __init__(self, asset_service, file_data: bytes, update_existing: bool = False, skip_errors: bool = True):
        super().__init__()
        self.asset_service = asset_service
        self.file_data = file_data
        self.update_existing = update_existing
        self.skip_errors = skip_errors

    def execute(self) -> Tuple[int, int, List[str]]:
        return self.asset_service.import_assets(
            file_data=self.file_data,
            update_existing=self.update_existing,
            skip_errors=self.skip_errors
        )


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


class WorkflowLoadWorker(BaseWorker):
    """
    工作流加载工作线程
    用于在后台线程加载工作流列表
    """
    def __init__(self, workflow_service):
        super().__init__()
        self.workflow_service = workflow_service

    def execute(self) -> list:
        return self.workflow_service.get_all()


class WorkflowExportWorker(BaseWorker):
    """
    工作流导出工作线程
    用于在后台线程导出工作流
    """
    def __init__(self, workflow_service, workflow_id: int):
        super().__init__()
        self.workflow_service = workflow_service
        self.workflow_id = workflow_id

    def execute(self) -> dict:
        return self.workflow_service.export_workflow(self.workflow_id)


class WorkflowImportWorker(BaseWorker):
    """
    工作流导入工作线程
    用于在后台线程导入工作流
    """
    def __init__(self, workflow_service, import_data: dict, user_id: int = None):
        super().__init__()
        self.workflow_service = workflow_service
        self.import_data = import_data
        self.user_id = user_id

    def execute(self):
        return self.workflow_service.import_workflow(self.import_data, user_id=self.user_id)


class DeleteWorker(BaseWorker):
    """
    通用删除工作线程
    用于在后台线程执行删除操作
    """
    def __init__(self, delete_func: Callable, *args, **kwargs):
        super().__init__()
        self.delete_func = delete_func
        self.args = args
        self.kwargs = kwargs

    def execute(self) -> Any:
        return self.delete_func(*self.args, **self.kwargs)


class GenericWorker(BaseWorker):
    """
    通用工作线程
    用于在后台线程执行任意函数
    """
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def execute(self) -> Any:
        return self.func(*self.args, **self.kwargs)
