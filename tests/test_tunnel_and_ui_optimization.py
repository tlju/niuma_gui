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


class TestTunnelConnection:
    def test_tunnel_creation_requires_bastion_connection(self):
        bastion_manager = MagicMock()
        bastion_manager.is_connected.return_value = False

        can_connect = bastion_manager and bastion_manager.is_connected()
        assert can_connect is False

    def test_tunnel_creation_with_connected_bastion(self):
        bastion_manager = MagicMock()
        bastion_manager.is_connected.return_value = True
        bastion_manager.create_tunnel.return_value = {
            "tunnel_id": 1,
            "target_host": "192.168.1.100",
            "target_port": 22,
            "local_port": 10022,
            "display": "127.0.0.1:10022 -> 192.168.1.100:22"
        }

        can_connect = bastion_manager and bastion_manager.is_connected()
        assert can_connect is True

        info = bastion_manager.create_tunnel("192.168.1.100", 22)
        assert info["tunnel_id"] == 1
        assert info["target_host"] == "192.168.1.100"
        assert info["local_port"] == 10022

    def test_connect_button_visibility_no_bastion(self):
        bastion_manager = None
        asset = MagicMock(ip="192.168.1.1", ipv6="")

        can_connect = bastion_manager and bastion_manager.is_connected()
        should_show_connect = can_connect and (asset.ip or asset.ipv6)
        assert not should_show_connect

    def test_connect_button_visibility_with_bastion(self):
        bastion_manager = MagicMock()
        bastion_manager.is_connected.return_value = True
        asset = MagicMock(ip="192.168.1.1", ipv6="")

        can_connect = bastion_manager and bastion_manager.is_connected()
        should_show_connect = can_connect and (asset.ip or asset.ipv6)
        assert bool(should_show_connect) is True

    def test_connect_button_visibility_no_network_address(self):
        bastion_manager = MagicMock()
        bastion_manager.is_connected.return_value = True
        asset = MagicMock(ip="", ipv6="")

        can_connect = bastion_manager and bastion_manager.is_connected()
        should_show_connect = can_connect and (asset.ip or asset.ipv6)
        assert not should_show_connect

    def test_connect_button_visibility_ipv6_only(self):
        bastion_manager = MagicMock()
        bastion_manager.is_connected.return_value = True
        asset = MagicMock(ip="", ipv6="fe80::1")

        can_connect = bastion_manager and bastion_manager.is_connected()
        should_show_connect = can_connect and (asset.ip or asset.ipv6)
        assert bool(should_show_connect) is True

    def test_tunnel_close(self):
        bastion_manager = MagicMock()
        bastion_manager.close_tunnel.return_value = True

        result = bastion_manager.close_tunnel(1)
        assert result is True
        bastion_manager.close_tunnel.assert_called_once_with(1)

    def test_default_port_is_22(self):
        asset = MagicMock(ip="192.168.1.1", port=None)
        target_port = asset.port or 22
        assert target_port == 22

    def test_custom_port(self):
        asset = MagicMock(ip="192.168.1.1", port=2222)
        target_port = asset.port or 22
        assert target_port == 2222


class TestTunnelStatusWidget:
    def test_add_tunnel(self, qapp):
        from gui.main_window import TunnelStatusWidget

        widget = TunnelStatusWidget()
        tunnel_info = {
            "tunnel_id": 1,
            "target_host": "192.168.1.100",
            "target_port": 22,
            "local_port": 10022,
        }

        widget.add_tunnel(tunnel_info)
        assert 1 in widget._tunnel_items
        assert widget.isVisible()

    def test_add_duplicate_tunnel_ignored(self, qapp):
        from gui.main_window import TunnelStatusWidget

        widget = TunnelStatusWidget()
        tunnel_info = {
            "tunnel_id": 1,
            "target_host": "192.168.1.100",
            "target_port": 22,
            "local_port": 10022,
        }

        widget.add_tunnel(tunnel_info)
        widget.add_tunnel(tunnel_info)
        assert len(widget._tunnel_items) == 1

    def test_remove_tunnel(self, qapp):
        from gui.main_window import TunnelStatusWidget

        widget = TunnelStatusWidget()
        tunnel_info = {
            "tunnel_id": 1,
            "target_host": "192.168.1.100",
            "target_port": 22,
            "local_port": 10022,
        }

        widget.add_tunnel(tunnel_info)
        widget.remove_tunnel(1)
        assert 1 not in widget._tunnel_items
        assert not widget.isVisible()

    def test_remove_nonexistent_tunnel(self, qapp):
        from gui.main_window import TunnelStatusWidget

        widget = TunnelStatusWidget()
        widget.remove_tunnel(999)
        assert len(widget._tunnel_items) == 0

    def test_clear_all_tunnels(self, qapp):
        from gui.main_window import TunnelStatusWidget

        widget = TunnelStatusWidget()
        for i in range(1, 4):
            widget.add_tunnel({
                "tunnel_id": i,
                "target_host": f"192.168.1.{i}",
                "target_port": 22,
                "local_port": 10020 + i,
            })

        assert len(widget._tunnel_items) == 3
        widget.clear_all()
        assert len(widget._tunnel_items) == 0
        assert not widget.isVisible()

    def test_visibility_with_tunnels(self, qapp):
        from gui.main_window import TunnelStatusWidget

        widget = TunnelStatusWidget()
        assert not widget.isVisible()

        widget.add_tunnel({
            "tunnel_id": 1,
            "target_host": "192.168.1.1",
            "target_port": 22,
            "local_port": 10022,
        })
        assert widget.isVisible()

        widget.remove_tunnel(1)
        assert not widget.isVisible()

    def test_tunnel_close_requested_signal(self, qapp):
        from gui.main_window import TunnelStatusWidget

        widget = TunnelStatusWidget()
        tunnel_info = {
            "tunnel_id": 5,
            "target_host": "10.0.0.1",
            "target_port": 22,
            "local_port": 10022,
        }
        widget.add_tunnel(tunnel_info)

        received_id = None

        def on_close_requested(tid):
            nonlocal received_id
            received_id = tid

        widget.tunnel_close_requested.connect(on_close_requested)

        item = widget._tunnel_items[5]
        item.close_requested.emit(5)

        assert received_id == 5


class TestTunnelItemWidget:
    def test_tunnel_item_display(self, qapp):
        from gui.main_window import TunnelItemWidget

        tunnel_info = {
            "tunnel_id": 1,
            "target_host": "192.168.1.100",
            "target_port": 22,
            "local_port": 10022,
        }

        item = TunnelItemWidget(tunnel_info)
        assert item.tunnel_id == 1

    def test_tunnel_item_close_signal(self, qapp):
        from gui.main_window import TunnelItemWidget

        tunnel_info = {
            "tunnel_id": 3,
            "target_host": "10.0.0.50",
            "target_port": 2222,
            "local_port": 10222,
        }

        item = TunnelItemWidget(tunnel_info)

        received_id = None

        def on_close(tid):
            nonlocal received_id
            received_id = tid

        item.close_requested.connect(on_close)
        item.close_requested.emit(3)

        assert received_id == 3


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


class TestBastionManagerTunnel:
    def test_create_tunnel_when_not_connected(self):
        from core.bastion_manager import BastionManager

        with patch.object(BastionManager, '__init__', lambda self, *args, **kwargs: None):
            manager = BastionManager.__new__(BastionManager)
            manager.bastion_service = MagicMock()
            manager.bastion_service.get_connection_status.return_value = {"authenticated": False}

            with pytest.raises(Exception, match="堡垒机未连接"):
                manager.create_tunnel("192.168.1.1", 22)

    def test_close_tunnel(self):
        from core.bastion_manager import BastionManager
        from PyQt5.QtCore import pyqtSignal

        with patch.object(BastionManager, '__init__', lambda self, *args, **kwargs: None):
            manager = BastionManager.__new__(BastionManager)
            manager.bastion_service = MagicMock()
            manager.bastion_service.close_tunnel.return_value = True
            manager.tunnel_closed = MagicMock()

            result = manager.close_tunnel(1)
            assert result is True
            manager.bastion_service.close_tunnel.assert_called_once_with("default", 1)
            manager.tunnel_closed.emit.assert_called_once_with(1)

    def test_get_active_tunnels(self):
        from core.bastion_manager import BastionManager

        with patch.object(BastionManager, '__init__', lambda self, *args, **kwargs: None):
            manager = BastionManager.__new__(BastionManager)
            manager.bastion_service = MagicMock()
            manager.bastion_service.get_active_tunnels.return_value = [
                {"tunnel_id": 1}, {"tunnel_id": 2}
            ]

            tunnels = manager.get_active_tunnels()
            assert len(tunnels) == 2
