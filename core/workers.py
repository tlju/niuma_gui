"""
后台任务处理模块
使用QThread处理耗时操作，避免UI卡顿
"""
from PyQt5.QtCore import QThread, pyqtSignal
from typing import Callable, Any, Tuple, List, Optional
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
