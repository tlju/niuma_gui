"""
测试PyInstaller打包环境中sys.executable问题的修复
验证get_python_executable()和get_subprocess_kwargs()函数的正确性
"""
import sys
import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from core.utils import get_python_executable, get_subprocess_kwargs
from core.node_types import ScriptNode, CommandNode, NodeStatus


class TestGetPythonExecutable:
    """测试get_python_executable函数"""

    def test_non_frozen_returns_sys_executable(self):
        """非打包环境下返回sys.executable"""
        with patch.dict(os.environ, {}, clear=False):
            with patch.object(sys, 'frozen', False, create=True):
                result = get_python_executable()
                assert result == sys.executable

    def test_frozen_with_base_executable(self):
        """打包环境下优先使用sys._base_executable"""
        original_frozen = getattr(sys, 'frozen', None)
        original_base_exec = getattr(sys, '_base_executable', None)

        try:
            sys.frozen = True
            fake_python = os.path.join(os.path.dirname(sys.executable), 'python.exe')
            sys._base_executable = fake_python

            with patch('os.path.isfile', return_value=True):
                result = get_python_executable()
                assert result == fake_python
        finally:
            if original_frozen is None:
                delattr(sys, 'frozen')
            else:
                sys.frozen = original_frozen
            if original_base_exec is None:
                if hasattr(sys, '_base_executable'):
                    delattr(sys, '_base_executable')
            else:
                sys._base_executable = original_base_exec

    def test_frozen_falls_back_to_which(self):
        """打包环境下_base_executable不可用时回退到shutil.which"""
        original_frozen = getattr(sys, 'frozen', None)
        original_base_exec = getattr(sys, '_base_executable', None)

        try:
            sys.frozen = True
            if hasattr(sys, '_base_executable'):
                delattr(sys, '_base_executable')

            with patch('shutil.which', return_value='/usr/bin/python3'):
                result = get_python_executable()
                assert result == '/usr/bin/python3'
        finally:
            if original_frozen is None:
                delattr(sys, 'frozen')
            else:
                sys.frozen = original_frozen
            if original_base_exec is not None:
                sys._base_executable = original_base_exec

    def test_frozen_no_python_found_returns_sys_executable(self):
        """打包环境下找不到Python时回退到sys.executable"""
        original_frozen = getattr(sys, 'frozen', None)
        original_base_exec = getattr(sys, '_base_executable', None)

        try:
            sys.frozen = True
            if hasattr(sys, '_base_executable'):
                delattr(sys, '_base_executable')

            with patch('shutil.which', return_value=None):
                result = get_python_executable()
                assert result == sys.executable
        finally:
            if original_frozen is None:
                delattr(sys, 'frozen')
            else:
                sys.frozen = original_frozen
            if original_base_exec is not None:
                sys._base_executable = original_base_exec


class TestGetSubprocessKwargs:
    """测试get_subprocess_kwargs函数"""

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows特定测试")
    def test_windows_adds_create_no_window(self):
        """Windows环境下添加CREATE_NO_WINDOW标志"""
        kwargs = get_subprocess_kwargs()
        assert 'creationflags' in kwargs
        assert kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW

    def test_linux_no_creationflags(self):
        """Linux环境下不添加creationflags"""
        with patch.object(sys, 'platform', 'linux'):
            kwargs = get_subprocess_kwargs()
            assert 'creationflags' not in kwargs

    @pytest.mark.skipif(sys.platform != 'win32', reason="Windows特定测试")
    def test_preserves_existing_flags(self):
        """保留已有的creationflags标志"""
        existing_flag = subprocess.CREATE_NEW_PROCESS_GROUP
        kwargs = get_subprocess_kwargs(creationflags=existing_flag)
        assert kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW
        assert kwargs['creationflags'] & existing_flag

    def test_other_kwargs_preserved(self):
        """其他参数被保留"""
        with patch.object(sys, 'platform', 'linux'):
            kwargs = get_subprocess_kwargs(shell=True, capture_output=True)
            assert kwargs['shell'] is True
            assert kwargs['capture_output'] is True


class TestScriptNodePythonExecution:
    """测试脚本节点Python执行使用正确的解释器路径"""

    def test_python_script_uses_get_python_executable(self):
        """Python脚本执行使用get_python_executable获取解释器路径"""
        node = ScriptNode(1, "测试Python脚本", {
            "script_content": "print('hello from python')",
            "script_language": "python",
            "script_name": "test.py"
        })

        with patch('core.utils.get_python_executable', return_value=sys.executable):
            result = node.execute()
            assert result.status == NodeStatus.SUCCESS
            assert "hello from python" in result.output

    def test_python_script_in_frozen_env(self):
        """模拟打包环境下Python脚本执行不会重新启动应用"""
        node = ScriptNode(1, "测试Python脚本", {
            "script_content": "print('frozen test')",
            "script_language": "python",
            "script_name": "test.py"
        })

        fake_python = sys.executable
        with patch('core.utils.get_python_executable', return_value=fake_python):
            with patch('core.utils.get_subprocess_kwargs', return_value={}):
                result = node.execute()
                assert result.status == NodeStatus.SUCCESS
                assert "frozen test" in result.output

    def test_bash_script_still_works(self):
        """Bash脚本执行不受影响"""
        node = ScriptNode(1, "测试Bash脚本", {
            "script_content": "echo hello bash",
            "script_language": "bash",
            "script_name": "test.sh"
        })

        result = node.execute()
        assert result.status == NodeStatus.SUCCESS
        assert "hello bash" in result.output


class TestCommandNodeSubprocess:
    """测试命令节点subprocess调用"""

    def test_command_uses_subprocess_kwargs(self):
        """命令节点执行使用get_subprocess_kwargs"""
        node = CommandNode(1, "测试命令", {"command": "echo test"})

        with patch('core.node_types.get_subprocess_kwargs', return_value={}) as mock_kwargs:
            result = node.execute()
            mock_kwargs.assert_called()
            assert result.status == NodeStatus.SUCCESS
            assert "test" in result.output
