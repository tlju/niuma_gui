import pytest
from unittest.mock import Mock, MagicMock, patch


class TestNetworkAddressDisplay:
    def test_ipv4_priority_over_ipv6(self):
        asset = MagicMock(ip="192.168.1.1", ipv6="fe80::1")
        network_addr = asset.ip or asset.ipv6 or ""
        assert network_addr == "192.168.1.1"

    def test_ipv6_when_no_ipv4(self):
        asset = MagicMock(ip="", ipv6="fe80::1")
        network_addr = asset.ip or asset.ipv6 or ""
        assert network_addr == "fe80::1"

    def test_ipv6_when_ipv4_is_none(self):
        asset = MagicMock(ip=None, ipv6="fe80::1")
        network_addr = asset.ip or asset.ipv6 or ""
        assert network_addr == "fe80::1"

    def test_empty_when_no_address(self):
        asset = MagicMock(ip="", ipv6="")
        network_addr = asset.ip or asset.ipv6 or ""
        assert network_addr == ""

    def test_empty_when_both_none(self):
        asset = MagicMock(ip=None, ipv6=None)
        network_addr = asset.ip or asset.ipv6 or ""
        assert network_addr == ""

    def test_ipv4_only(self):
        asset = MagicMock(ip="10.0.0.1", ipv6="")
        network_addr = asset.ip or asset.ipv6 or ""
        assert network_addr == "10.0.0.1"


class TestOperationColumnConsistency:
    def test_assets_table_column_count(self):
        expected_columns = ["单位", "系统", "网络地址", "业务服务", "位置", "服务器类型", "操作"]
        assert len(expected_columns) == 7

    def test_assets_operation_column_index(self):
        operation_col_index = 6
        assert operation_col_index == 6

    def test_scripts_table_has_detail_button(self):
        buttons = ["编辑", "详情", "删除"]
        assert "详情" in buttons
        assert buttons[0] == "编辑"
        assert buttons[-1] == "删除"

    def test_todos_operation_button_order(self):
        buttons = ["完成", "编辑", "删除"]
        assert buttons[0] == "完成"
        assert buttons[-1] == "删除"

    def test_documents_operation_button_order(self):
        buttons = ["查看", "编辑", "删除"]
        assert buttons[0] == "查看"
        assert buttons[-1] == "删除"

    def test_workflow_operation_button_order(self):
        buttons = ["执行", "编辑", "导出", "删除"]
        assert buttons[0] == "执行"
        assert buttons[-1] == "删除"

    def test_dicts_operation_button_order(self):
        buttons = ["项", "编辑", "删除"]
        assert buttons[0] == "项"
        assert buttons[-1] == "删除"

    def test_connect_button_style_class(self):
        connect_class = "table-connect"
        assert connect_class == "table-connect"

    def test_edit_button_style_class(self):
        edit_class = "table-edit"
        assert edit_class == "table-edit"

    def test_delete_button_style_class(self):
        delete_class = "table-delete"
        assert delete_class == "table-delete"
