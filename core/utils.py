import sys
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from services.dict_service import DictService
    from services.param_service import ParamService


def get_python_executable() -> str:
    """
    获取Python解释器路径
    在PyInstaller打包环境中，sys.executable指向打包后的可执行文件，
    需要通过sys._base_executable或PATH查找真正的Python解释器
    """
    if not getattr(sys, 'frozen', False):
        return sys.executable

    base_exec = getattr(sys, '_base_executable', None)
    if base_exec and os.path.isfile(base_exec) and 'python' in os.path.basename(base_exec).lower():
        return base_exec

    for name in ('python', 'python3', 'python.exe', 'python3.exe'):
        found = shutil.which(name)
        if found:
            return found

    return sys.executable


def get_subprocess_kwargs(**kwargs) -> dict:
    """
    获取subprocess调用的通用参数
    在Windows编译版中添加CREATE_NO_WINDOW标志，防止控制台窗口闪现
    """
    if sys.platform == 'win32':
        creation_flags = kwargs.pop('creationflags', 0)
        kwargs['creationflags'] = creation_flags | subprocess.CREATE_NO_WINDOW
    return kwargs


def get_base_path() -> str:
    """
    获取程序的基础路径
    在编译后的程序中使用可执行文件所在目录，否则使用项目根目录
    支持 PyInstaller (sys.frozen) 打包后的程序
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_local_now() -> datetime:
    return datetime.now()


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if dt is None:
        return ""
    return dt.strftime(fmt)


def format_time(dt: Optional[datetime], fmt: str = "%H:%M:%S") -> str:
    if dt is None:
        return ""
    return dt.strftime(fmt)


def replace_variables(
    content: str,
    dict_service: Optional["DictService"] = None,
    param_service: Optional["ParamService"] = None
) -> str:
    """
    替换内容中的变量引用
    支持格式: @dict.字典代码.项名称 -> 项代码, @param.参数代码 -> 参数值

    Args:
        content: 需要替换变量的内容
        dict_service: 字典服务实例
        param_service: 参数服务实例

    Returns:
        替换后的内容
    """
    if not content or not isinstance(content, str):
        return content or ""

    def _replace_var(match: re.Match) -> str:
        var_path = match.group(1)
        parts = var_path.split('.')

        if len(parts) < 2:
            return match.group(0)

        source_type = parts[0]

        try:
            if source_type == "dict" and dict_service:
                if len(parts) >= 3:
                    dict_code = parts[1]
                    item_name = parts[2]
                    items = dict_service.get_dict_items(dict_code)
                    for item in items:
                        if item.item_name == item_name:
                            return item.item_code
            elif source_type == "param" and param_service:
                param_code = parts[1]
                param = param_service.get_param_by_code(param_code)
                if param:
                    return param.param_value
        except Exception:
            pass

        return match.group(0)

    pattern = r'@([a-zA-Z_][a-zA-Z0-9_\.]*)'
    return re.sub(pattern, _replace_var, content)
