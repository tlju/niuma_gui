import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bastion_service import BastionService, ConnectionStatus, BastionChannel
from core.bastion_manager import BastionManager, BastionConnectionWorker
from core.node_types import BastionNode, NodeStatus
from gui.bastion_dialog import SecondaryAuthDialog


class TestBastionService(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = Mock()
        self.bastion_service = BastionService(db=self.mock_db)
        
    def test_connection_status_enum(self):
        self.assertEqual(ConnectionStatus.DISCONNECTED.value, "disconnected")
        self.assertEqual(ConnectionStatus.CONNECTING.value, "connecting")
        self.assertEqual(ConnectionStatus.CONNECTED.value, "connected")
        self.assertEqual(ConnectionStatus.AUTHENTICATING.value, "authenticating")
        self.assertEqual(ConnectionStatus.AUTHENTICATED.value, "authenticated")
        self.assertEqual(ConnectionStatus.FAILED.value, "failed")
    
    def test_channel_creation(self):
        mock_channel = Mock()
        channel = BastionChannel(
            channel_id="test_channel_1",
            channel=mock_channel,
            target_host="192.168.1.100"
        )
        
        self.assertEqual(channel.channel_id, "test_channel_1")
        self.assertEqual(channel.target_host, "192.168.1.100")
        self.assertIsNotNone(channel.channel)
    
    def test_get_connection_status_not_connected(self):
        status = self.bastion_service.get_connection_status("nonexistent")
        
        self.assertEqual(status["status"], ConnectionStatus.DISCONNECTED.value)
        self.assertFalse(status["authenticated"])
    
    def test_get_channel_no_connection(self):
        channel = self.bastion_service.get_channel("nonexistent")
        self.assertIsNone(channel)


class TestBastionManager(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = Mock()
        self.bastion_manager = BastionManager(self.mock_db)
    
    def test_get_status_initial(self):
        status = self.bastion_manager.get_status()
        
        self.assertEqual(status["status"], ConnectionStatus.DISCONNECTED.value)
        self.assertFalse(status["authenticated"])
    
    def test_disconnect(self):
        self.bastion_manager.disconnect()
        
        status = self.bastion_manager.get_status()
        self.assertEqual(status["status"], ConnectionStatus.DISCONNECTED.value)


class TestBastionNode(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = Mock()
        self.node = BastionNode(node_id=1, name="测试堡垒机节点")
        self.node.set_services(db=self.mock_db)
    
    def test_node_properties(self):
        self.assertEqual(BastionNode.node_type, "bastion")
        self.assertEqual(BastionNode.category, "environment")
        self.assertEqual(BastionNode.display_name, "堡垒机连接")
        self.assertEqual(BastionNode.input_ports, 1)
        self.assertEqual(BastionNode.output_ports, 1)
    
    def test_get_config_schema(self):
        schema = self.node.get_config_schema()
        
        self.assertIn("target_host", schema["properties"])
    
    def test_execute_missing_target_host(self):
        self.node.config = {}
        result = self.node.execute()
        
        self.assertEqual(result.status, NodeStatus.FAILED)
        self.assertIn("未指定目标主机地址", result.error)
    
    def test_execute_missing_db(self):
        node = BastionNode(node_id=2, name="无数据库节点")
        node.config = {"operation": "connect_host"}
        result = node.execute()
        
        self.assertEqual(result.status, NodeStatus.FAILED)
        self.assertIn("数据库会话未设置", result.error)
    
    def test_replace_variables_with_input(self):
        inputs = {"output": "192.168.1.100"}
        
        result = self.node._replace_variables("@input.output", inputs)
        self.assertEqual(result, "192.168.1.100")
    
    def test_replace_variables_no_match(self):
        result = self.node._replace_variables("@unknown.variable")
        self.assertEqual(result, "@unknown.variable")


class TestBastionConnectionWorker(unittest.TestCase):
    
    def test_worker_initialization(self):
        mock_db = Mock()
        worker = BastionConnectionWorker(mock_db, max_retries=3, retry_interval=5)
        
        self.assertEqual(worker.max_retries, 3)
        self.assertEqual(worker.retry_interval, 5)
        self.assertFalse(worker._is_cancelled)


class TestSecondaryAuthDialog(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        import sys
        from PyQt5.QtWidgets import QApplication
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_dialog_initialization(self):
        dialog = SecondaryAuthDialog(retry_count=0, max_retries=5)
        
        self.assertEqual(dialog.retry_count, 0)
        self.assertEqual(dialog.max_retries, 5)
        self.assertEqual(dialog.otp_input.maxLength(), 6)
        dialog.close()
    
    def test_dialog_with_retry(self):
        dialog = SecondaryAuthDialog(retry_count=2, max_retries=5)
        
        self.assertEqual(dialog.retry_count, 2)
        dialog.close()
    
    def test_otp_validation(self):
        dialog = SecondaryAuthDialog()
        
        dialog.otp_input.setText("12345")
        self.assertFalse(dialog.ok_btn.isEnabled())
        
        dialog.otp_input.setText("123456")
        self.assertTrue(dialog.ok_btn.isEnabled())
        
        dialog.otp_input.setText("")
        self.assertFalse(dialog.ok_btn.isEnabled())
        dialog.close()
    
    def test_get_otp_code(self):
        dialog = SecondaryAuthDialog()
        dialog.otp_input.setText("654321")
        
        self.assertEqual(dialog.get_otp_code(), "654321")
        dialog.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
