"""
代码审查修复的测试用例
覆盖：CRYPTO_KEY 强制校验、表达式解析器安全、堡垒机密码消费、
事务回滚、白名单校验、CryptoManager PBKDF2、SecureString 实例锁等
"""
import pytest
import os
import threading
from unittest.mock import patch, MagicMock

from core.secure_string import SecureString
from core.expression_parser import safe_eval, ExpressionParseError
from services.crypto import CryptoManager, hash_password, verify_password


class TestCryptoKeyValidation:
    """测试 CRYPTO_KEY 强制校验（问题1.1）"""

    def test_empty_crypto_key_raises_error(self):
        """空 CRYPTO_KEY 应在 Settings 实例化时抛出 ValueError"""
        with patch.dict(os.environ, {"CRYPTO_KEY": ""}, clear=False):
            # 需要重新导入以触发校验
            import importlib
            import core.config
            with pytest.raises(ValueError, match="CRYPTO_KEY 未配置"):
                importlib.reload(core.config)

    def test_short_crypto_key_raises_error(self):
        """过短的 CRYPTO_KEY 应抛出 ValueError"""
        with patch.dict(os.environ, {"CRYPTO_KEY": "short"}, clear=False):
            import importlib
            import core.config
            with pytest.raises(ValueError, match="长度过短"):
                importlib.reload(core.config)

    def test_valid_crypto_key_passes(self):
        """有效的 CRYPTO_KEY 应通过校验"""
        with patch.dict(os.environ, {"CRYPTO_KEY": "test-crypto-key-for-unit-tests-only-32b"}, clear=False):
            import importlib
            import core.config
            # 不应抛出异常
            importlib.reload(core.config)


class TestExpressionParserSecurity:
    """测试表达式解析器安全性（问题1.6）"""

    def test_underscore_attribute_blocked(self):
        """禁止访问以 _ 开头的属性"""
        context = {"data": {"_secret": "hidden", "name": "visible"}}
        # _secret 应返回空字符串而不是 "hidden"
        result = safe_eval("data._secret == 'hidden'", context)
        assert result is False

    def test_dunder_attribute_blocked(self):
        """禁止访问 __class__ 等双下划线属性"""
        context = {"obj": {"__class__": "dangerous"}}
        result = safe_eval("obj.__class__ == 'dangerous'", context)
        assert result is False

    def test_normal_dict_access_works(self):
        """正常的字典访问应正常工作"""
        context = {"data": {"value": 10, "name": "test"}}
        assert safe_eval("data.value == 10", context) is True
        assert safe_eval("data.name == 'test'", context) is True

    def test_non_dict_object_returns_empty(self):
        """非字典对象的属性访问应返回空字符串"""
        context = {"num": 42}
        # num 是 int，不是 dict，访问 .real 应返回空
        result = safe_eval("num.real == 42", context)
        assert result is False


class TestCryptoManagerPBKDF2:
    """测试 CryptoManager 使用 PBKDF2 密钥派生（问题4.5）"""

    def test_encrypt_decrypt_roundtrip(self):
        """加密解密应完整往返"""
        crypto = CryptoManager("my-secret-key-for-testing")
        original = "sensitive_password_123"
        encrypted = crypto.encrypt(original)
        decrypted = crypto.decrypt(encrypted)
        assert decrypted == original

    def test_different_keys_produce_different_results(self):
        """不同密钥应产生不同加密结果"""
        crypto1 = CryptoManager("key-one-12345")
        crypto2 = CryptoManager("key-two-67890")
        data = "same_data"
        e1 = crypto1.encrypt(data)
        # 用不同密钥解密应失败
        with pytest.raises(Exception):
            crypto2.decrypt(e1)

    def test_short_key_works(self):
        """短密钥应通过 PBKDF2 派生为有效密钥"""
        crypto = CryptoManager("short")
        encrypted = crypto.encrypt("test")
        assert crypto.decrypt(encrypted) == "test"

    def test_long_key_works(self):
        """长密钥应通过 PBKDF2 正确处理"""
        crypto = CryptoManager("a" * 200)
        encrypted = crypto.encrypt("test")
        assert crypto.decrypt(encrypted) == "test"


class TestSecureStringInstanceLock:
    """测试 SecureString 实例级别锁（问题4.7）"""

    def test_instances_have_separate_locks(self):
        """不同实例应有独立的锁"""
        s1 = SecureString("pass1")
        s2 = SecureString("pass2")
        assert s1._lock is not s2._lock

    def test_concurrent_access_safe(self):
        """多线程并发访问不同实例应安全"""
        results = []
        errors = []

        def worker(value, index):
            try:
                s = SecureString(value)
                # 模拟并发操作
                consumed = s.consume()
                results.append((index, consumed))
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(f"password_{i}", i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

    def test_consume_only_once(self):
        """consume 只能消费一次"""
        s = SecureString("secret")
        first = s.consume()
        assert first == "secret"
        second = s.consume()
        assert second == ""


class TestBastionPasswordRetry:
    """测试堡垒机密码重试修复（问题2.1）"""

    def test_password_property_available_after_failed_connect(self):
        """连接失败后 password 属性仍应可用"""
        from services.bastion_service import BastionConnection
        conn = BastionConnection("host", 22, "user", "mypassword")
        # password 使用 SecureString，未调用 consume()，所以始终可用
        assert conn.password == "mypassword"
        # 再次获取仍然可用（不再是 consume 一次性模式）
        assert conn.password == "mypassword"


class TestAssetServiceUpdateWhitelist:
    """测试 AssetService.update 字段白名单（问题4.3）"""

    def test_updatable_fields_does_not_include_id(self):
        """白名单中不应包含 id 字段"""
        from services.asset_service import AssetService
        assert "id" not in AssetService.UPDATABLE_FIELDS

    def test_updatable_fields_does_not_include_is_active(self):
        """白名单中不应包含 is_active 等敏感字段"""
        from services.asset_service import AssetService
        assert "is_active" not in AssetService.UPDATABLE_FIELDS

    def test_updatable_fields_includes_allowed_fields(self):
        """白名单应包含允许更新的字段"""
        from services.asset_service import AssetService
        allowed = {"unit_name", "system_name", "ip", "ipv6", "port",
                   "host_name", "username", "notes", "business_service",
                   "location", "server_type", "vip"}
        assert allowed.issubset(AssetService.UPDATABLE_FIELDS)


class TestWorkflowServiceUpdateWhitelist:
    """测试 WorkflowService.update 字段白名单（问题4.4）"""

    def test_updatable_fields_does_not_include_id(self):
        """白名单中不应包含 id 字段"""
        from services.workflow_service import WorkflowService
        assert "id" not in WorkflowService.UPDATABLE_FIELDS

    def test_updatable_fields_does_not_include_is_active(self):
        """白名单中不应包含 is_active 字段"""
        from services.workflow_service import WorkflowService
        assert "is_active" not in WorkflowService.UPDATABLE_FIELDS

    def test_updatable_fields_includes_allowed_fields(self):
        """白名单应包含 name, description, graph_data"""
        from services.workflow_service import WorkflowService
        assert "name" in WorkflowService.UPDATABLE_FIELDS
        assert "description" in WorkflowService.UPDATABLE_FIELDS
        assert "graph_data" in WorkflowService.UPDATABLE_FIELDS
