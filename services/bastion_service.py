from __future__ import annotations

import paramiko
import threading
import time
import re
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from sqlalchemy.orm import Session
from services.param_service import ParamService
from core.logger import get_logger
from core.secure_string import SecureString

logger = get_logger(__name__)


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"


class BastionChannel:
    def __init__(self, channel: paramiko.Channel, channel_id: int, target_host: str = None):
        self.channel = channel
        self.channel_id = channel_id
        self.target_host = target_host
        self.created_at = time.time()
        self.last_activity = time.time()
        self.is_active = True
        self._lock = threading.Lock()

    def send(self, data: str) -> bool:
        with self._lock:
            if self.is_active and self.channel:
                try:
                    self.channel.send(data)
                    self.last_activity = time.time()
                    return True
                except Exception as e:
                    logger.error(f"通道 {self.channel_id} 发送数据失败: {e}")
                    self.is_active = False
                    return False
        return False

    def recv(self, size: int = 4096) -> bytes:
        with self._lock:
            if self.is_active and self.channel:
                try:
                    data = self.channel.recv(size)
                    self.last_activity = time.time()
                    return data
                except Exception as e:
                    logger.error(f"通道 {self.channel_id} 接收数据失败: {e}")
                    self.is_active = False
                    return b""
        return b""

    def recv_ready(self) -> bool:
        if self.is_active and self.channel:
            try:
                return self.channel.recv_ready()
            except Exception:
                return False
        return False

    def close(self):
        with self._lock:
            if self.channel:
                try:
                    self.channel.close()
                except Exception:
                    pass
            self.is_active = False

    def keepalive(self) -> bool:
        with self._lock:
            if self.is_active and self.channel:
                try:
                    self.channel.send("\x00")
                    return True
                except Exception:
                    self.is_active = False
                    return False
        return False


class BastionConnection:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self._secure_password = SecureString(password)
        self.client: Optional[paramiko.SSHClient] = None
        self.transport: Optional[paramiko.Transport] = None
        self.channels: List[BastionChannel] = []
        self.status = ConnectionStatus.DISCONNECTED
        self.error_message: str = ""
        self._lock = threading.Lock()
        self._keepalive_thread: Optional[threading.Thread] = None
        self._keepalive_running = False
        self._on_status_change: Optional[Callable[[ConnectionStatus, str], None]] = None
        self._auth_channel: Optional[paramiko.Channel] = None
        self._current_session_channel: Optional[BastionChannel] = None

    @property
    def password(self) -> str:
        return self._secure_password.value

    def _consume_password(self) -> str:
        return self._secure_password.consume()

    def set_status_callback(self, callback: Callable[[ConnectionStatus, str], None]):
        self._on_status_change = callback

    def _update_status(self, status: ConnectionStatus, message: str = ""):
        self.status = status
        self.error_message = message
        if self._on_status_change:
            try:
                self._on_status_change(status, message)
            except Exception as e:
                logger.error(f"状态回调异常: {e}")

    def connect_with_retry(self, max_retries: int = 3, retry_interval: int = 5, 
                           timeout: int = 30, on_retry: Callable[[int, str], None] = None) -> bool:
        last_error = None
        
        logger.info(f"堡垒机连接开始: host={self.host}, port={self.port}, username={self.username}, "
                    f"max_retries={max_retries}, retry_interval={retry_interval}, timeout={timeout}")
        
        for attempt in range(1, max_retries + 1):
            try:
                self._update_status(ConnectionStatus.CONNECTING, f"正在连接堡垒机 (尝试 {attempt}/{max_retries})")
                logger.info(f"堡垒机连接尝试 {attempt}/{max_retries}")
                result = self.connect(timeout=timeout)
                return result
            except Exception as e:
                last_error = str(e)
                logger.warning(f"堡垒机连接失败 (尝试 {attempt}/{max_retries}): {e}")
                
                if on_retry:
                    on_retry(attempt, last_error)
                
                if attempt < max_retries:
                    self._update_status(ConnectionStatus.CONNECTING, 
                                       f"连接失败，{retry_interval}秒后重试 ({attempt}/{max_retries})")
                    time.sleep(retry_interval)
        
        self._update_status(ConnectionStatus.FAILED, f"连接失败: {last_error}")
        raise Exception(f"堡垒机连接失败，已重试{max_retries}次: {last_error}")

    def connect(self, timeout: int = 30) -> bool:
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            logger.info(f"正在连接堡垒机 {self.host}:{self.port}, 用户: {self.username}, 超时: {timeout}秒")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self._consume_password(),
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False,
                banner_timeout=timeout
            )
            
            self.transport = self.client.get_transport()
            if self.transport:
                self.transport.set_keepalive(30)
            
            self._update_status(ConnectionStatus.CONNECTED, "已连接，等待二次认证")
            logger.info(f"堡垒机 {self.host}:{self.port} SSH连接成功，等待二次认证")
            return True
            
        except paramiko.AuthenticationException as e:
            error_msg = f"堡垒机认证失败: {e}"
            logger.error(error_msg)
            self._update_status(ConnectionStatus.FAILED, error_msg)
            raise Exception(error_msg)
        except paramiko.SSHException as e:
            error_msg = f"SSH连接错误: {e}"
            logger.error(error_msg)
            self._update_status(ConnectionStatus.FAILED, error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"连接堡垒机失败: {e}"
            logger.error(error_msg)
            self._update_status(ConnectionStatus.FAILED, error_msg)
            raise Exception(error_msg)

    def detect_auth_prompt(self, timeout: int = 10) -> Dict[str, Any]:
        if not self.is_connected:
            raise Exception("未连接到堡垒机")

        try:
            logger.info(f"开始检测堡垒机认证方式, timeout={timeout}")
            self._auth_channel = self.client.invoke_shell()
            self._auth_channel.settimeout(timeout)
            
            time.sleep(0.5)
            output = self._read_channel_output(self._auth_channel, timeout)
            logger.info(f"堡垒机初始输出(前500字符): {output[:500]}")
            
            auth_info = {
                "needs_password": False,
                "needs_otp": False,
                "needs_menu": False,
                "prompt_text": output,
                "has_menu": False
            }
            
            if "2nd password" in output.lower() or "2nd password:" in output.lower():
                auth_info["needs_otp"] = True
                logger.info("检测到 '2nd Password' 提示，需要二次认证")
            
            if "请选择" in output or "选择目标" in output or "Ctrl+F" in output or "目标资产列表" in output:
                auth_info["needs_menu"] = True
                auth_info["has_menu"] = True
            
            logger.info(f"堡垒机认证方式检测结果: needs_password={auth_info['needs_password']}, "
                        f"needs_otp={auth_info['needs_otp']}, needs_menu={auth_info['needs_menu']}, "
                        f"has_menu={auth_info['has_menu']}")
            
            if not auth_info["needs_otp"] and not auth_info["needs_menu"]:
                if self._auth_channel:
                    self._auth_channel.close()
                    self._auth_channel = None
            
            return auth_info
            
        except Exception as e:
            logger.error(f"检测认证提示失败: {e}")
            self._auth_channel = None
            return {
                "needs_password": False,
                "needs_otp": True,
                "needs_menu": False,
                "prompt_text": "",
                "has_menu": False
            }

    def _is_otp_prompt(self, output: str) -> bool:
        otp_patterns = [
            "2nd password",
            "验证码",
            "OTP",
            "动态口令",
            "令牌",
        ]
        output_lower = output.lower()
        for pattern in otp_patterns:
            if pattern.lower() in output_lower:
                return True
        return False

    def _parse_server_list(self, output: str) -> List[Dict[str, str]]:
        servers = []
        server_pattern = re.compile(
            r'(\d+)\s*[:：]\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(.+)',
            re.MULTILINE
        )
        for match in server_pattern.finditer(output):
            servers.append({
                "index": match.group(1).strip(),
                "ip": match.group(2).strip(),
                "name": match.group(3).strip()
            })
        
        if not servers:
            line_pattern = re.compile(
                r'^\s*(\d+)\s+.*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*(.*)',
                re.MULTILINE
            )
            for match in line_pattern.finditer(output):
                servers.append({
                    "index": match.group(1).strip(),
                    "ip": match.group(2).strip(),
                    "name": match.group(3).strip()
                })
        
        return servers

    def handle_secondary_auth(self, auth_type: str = "password", 
                               secondary_password: str = None,
                               otp_code: str = None,
                               menu_selection: str = None,
                               timeout: int = 30) -> Dict[str, Any]:
        if not self.client:
            raise Exception("未连接到堡垒机")

        self._update_status(ConnectionStatus.AUTHENTICATING, "正在进行二次认证")

        try:
            logger.info(f"开始处理二次认证: auth_type={auth_type}, "
                        f"has_otp_code={otp_code is not None}, "
                        f"has_menu_selection={menu_selection is not None}, timeout={timeout}")
            
            if self._auth_channel:
                channel = self._auth_channel
                logger.info("复用认证通道")
                output = ""
                if channel.recv_ready():
                    output = self._read_channel_output(channel, timeout=1)
                if not output:
                    time.sleep(0.3)
                    output = self._read_channel_output(channel, timeout=2)
            else:
                channel = self.client.invoke_shell()
                channel.settimeout(timeout)
                self._auth_channel = channel
                time.sleep(0.5)
                output = self._read_channel_output(channel, timeout)
            
            logger.info(f"二次认证-初始输出(前500字符): {output[:500]}")
            
            if self._is_otp_prompt(output):
                if not otp_code:
                    channel.close()
                    self._auth_channel = None
                    raise Exception("需要OTP验证码但未提供")
                
                logger.info("检测到OTP/2nd Password提示，发送验证码")
                channel.send(otp_code + "\n")
                time.sleep(1.0)
                output = self._read_channel_output(channel, timeout, max_read_time=15.0)
                logger.info(f"二次认证-OTP后输出(前500字符): {output[:500]}")
                
                if self._is_otp_prompt(output):
                    logger.warning("OTP验证失败，堡垒机再次要求输入")
                    raise Exception("OTP_RETRY")
                
                if "错误" in output or "error" in output.lower() or "失败" in output or "denied" in output.lower():
                    channel.close()
                    self._auth_channel = None
                    raise Exception("动态口令验证失败")
            
            result = {
                "authenticated": False,
                "has_server_list": False,
                "server_list": [],
                "output": output
            }
            
            if "请选择" in output or "选择目标" in output or "Ctrl+F" in output or "目标资产列表" in output:
                logger.info("检测到服务器列表菜单，开始获取完整服务器列表")
                all_servers = self._fetch_all_servers_with_pagination(channel, timeout)
                processed_servers = self._process_server_list(all_servers)
                
                result["authenticated"] = True
                result["has_server_list"] = True
                result["server_list"] = processed_servers
                logger.info(f"获取并处理服务器列表完成，共 {len(processed_servers)} 台服务器")
                
                if menu_selection:
                    logger.info(f"发送菜单选择: {menu_selection}")
                    channel.send(menu_selection + "\n")
                    time.sleep(1.0)
                    output = self._read_channel_output(channel, timeout, max_read_time=15.0)
                    result["output"] = output
                    logger.info(f"菜单选择后输出(前500字符): {output[:500]}")
                    result["has_server_list"] = False
                    result["server_list"] = []
            else:
                auth_patterns = [
                    r"欢迎",
                    r"成功",
                    r"[\$#>]\s*$",
                    r"请选择",
                    r"操作成功",
                    r"已登录"
                ]
                
                for pattern in auth_patterns:
                    if re.search(pattern, output, re.IGNORECASE):
                        result["authenticated"] = True
                        break
                
                if not result["authenticated"]:
                    result["authenticated"] = True
            
            if result["authenticated"]:
                self._update_status(ConnectionStatus.AUTHENTICATED, "认证成功")
                logger.info("堡垒机二次认证成功")
            else:
                self._update_status(ConnectionStatus.AUTHENTICATED, "认证流程完成")
                logger.info("堡垒机认证流程完成")
            
            if not result["has_server_list"]:
                if self._auth_channel:
                    self._auth_channel.close()
                    self._auth_channel = None
            
            return result
            
        except Exception as e:
            if str(e) == "OTP_RETRY":
                raise
            error_msg = f"处理二次认证失败: {e}"
            logger.error(error_msg)
            self._update_status(ConnectionStatus.FAILED, error_msg)
            if self._auth_channel:
                self._auth_channel.close()
                self._auth_channel = None
            raise Exception(error_msg)

    def _fetch_all_servers_with_pagination(self, channel, timeout: int = 30) -> List[Dict[str, str]]:
        all_servers = []
        seen_servers = set()
        max_pages = 20
        page_count = 0
        
        output = self._read_channel_output(channel, timeout=2, max_read_time=5.0)
        current_servers = self._parse_server_list(output)
        for server in current_servers:
            server_key = f"{server['ip']}_{server['name']}"
            if server_key not in seen_servers:
                seen_servers.add(server_key)
                all_servers.append(server)
        
        logger.info(f"第1页解析到 {len(current_servers)} 台服务器，累计 {len(all_servers)} 台")
        
        while page_count < max_pages:
            if "Ctrl-F" not in output and "下一页" not in output:
                logger.info("没有更多页面，停止翻页")
                break
            
            logger.info(f"发送Ctrl+F翻页，当前第 {page_count + 2} 页")
            channel.send("\x06")
            time.sleep(1.0)
            
            output = self._read_channel_output(channel, timeout=3, max_read_time=10.0)
            page_count += 1
            
            current_servers = self._parse_server_list(output)
            new_count = 0
            for server in current_servers:
                server_key = f"{server['ip']}_{server['name']}"
                if server_key not in seen_servers:
                    seen_servers.add(server_key)
                    all_servers.append(server)
                    new_count += 1
            
            logger.info(f"第{page_count + 1}页解析到 {len(current_servers)} 台服务器，新增 {new_count} 台，累计 {len(all_servers)} 台")
            
            if new_count == 0:
                logger.info("本页没有新增服务器，可能已到最后一页")
                break
        
        logger.info(f"翻页完成，共获取 {len(all_servers)} 台服务器")
        return all_servers

    def _process_server_list(self, servers: List[Dict[str, str]]) -> List[Dict[str, str]]:
        processed = []
        seen_ips = set()
        
        for server in servers:
            ip = server.get("ip", "")
            name = server.get("name", "")
            
            if "host_" in name:
                logger.debug(f"排除包含'host_'的服务器: {ip} - {name}")
                continue
            
            if ip in seen_ips:
                logger.debug(f"去重: IP {ip} 已存在")
                continue
            
            seen_ips.add(ip)
            processed.append(server)
        
        logger.info(f"服务器列表处理完成: 原始 {len(servers)} 台，处理后 {len(processed)} 台")
        return processed

    def _read_channel_output(self, channel, timeout: float = 2.0, max_read_time: float = 10.0) -> str:
        output = ""
        start_time = time.time()
        last_data_time = time.time()
        
        while True:
            elapsed_total = time.time() - start_time
            elapsed_since_data = time.time() - last_data_time
            
            if elapsed_total >= max_read_time:
                logger.debug(f"_read_channel_output: 达到最大读取时间 {max_read_time}秒，停止读取，已读取 {len(output)} 字符")
                break
            
            if elapsed_since_data >= timeout:
                break
            
            if channel.recv_ready():
                try:
                    data = channel.recv(4096)
                    if data:
                        output += data.decode('utf-8', errors='ignore')
                        last_data_time = time.time()
                except Exception:
                    break
            else:
                time.sleep(0.1)
        
        return output

    def search_and_select_asset(self, target_ip: str, timeout: int = 30) -> Dict[str, Any]:
        if not self._auth_channel or not self._auth_channel.recv_ready:
            if not self.client or self.status != ConnectionStatus.AUTHENTICATED:
                raise Exception("堡垒机未完成认证，无法搜索资产")
            
            self._auth_channel = self.client.invoke_shell()
            self._auth_channel.settimeout(timeout)
            time.sleep(0.5)
            self._read_channel_output(self._auth_channel, timeout=2)
        
        channel = self._auth_channel
        result = {
            "success": False,
            "output": "",
            "error": None
        }
        
        try:
            logger.info(f"搜索资产: {target_ip}")
            search_cmd = f"/{target_ip}\n"
            channel.send(search_cmd)
            time.sleep(1.0)
            output = self._read_channel_output(channel, timeout, max_read_time=10.0)
            logger.info(f"搜索结果(前500字符): {output[:500]}")
            
            servers = self._parse_server_list(output)
            if not servers:
                result["error"] = f"未找到IP为 {target_ip} 的资产"
                return result
            
            first_server = servers[0]
            logger.info(f"选择第一个匹配的资产: {first_server}")
            
            select_cmd = f"{first_server['index']}\n"
            channel.send(select_cmd)
            time.sleep(1.0)
            output = self._read_channel_output(channel, timeout, max_read_time=10.0)
            logger.info(f"选择资产后输出(前500字符): {output[:500]}")
            
            result["output"] = output
            result["success"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"搜索选择资产失败: {e}")
            result["error"] = str(e)
            return result

    def connect_to_asset(self, target_ip: str, asset_username: str, asset_password: str, 
                          timeout: int = 60) -> Dict[str, Any]:
        if not self.client or self.status != ConnectionStatus.AUTHENTICATED:
            raise Exception("堡垒机未完成认证，无法连接资产")

        result = {
            "success": False,
            "output": "",
            "error": None,
            "channel": None
        }

        try:
            search_result = self.search_and_select_asset(target_ip, timeout)
            if not search_result["success"]:
                result["error"] = search_result["error"]
                return result
            
            channel = self._auth_channel
            output = search_result["output"]
            
            if "login:" in output.lower() or "login" in output:
                logger.info(f"输入用户名: {asset_username}")
                channel.send(asset_username + "\n")
                time.sleep(0.5)
                output = self._read_channel_output(channel, timeout=5)
                logger.info(f"输入用户名后输出(前300字符): {output[:300]}")
            
            if "password" in output.lower() or "密码" in output:
                logger.info("输入密码")
                channel.send(asset_password + "\n")
                time.sleep(1.0)
                output = self._read_channel_output(channel, timeout=10, max_read_time=15.0)
                logger.info(f"输入密码后输出(前300字符): {output[:300]}")
            
            if "permission denied" in output.lower() or "denied" in output.lower():
                result["error"] = "资产密码错误或权限被拒绝"
                result["output"] = output
                return result
            
            if "yes/no" in output.lower():
                logger.info("确认主机密钥")
                channel.send("yes\n")
                time.sleep(0.5)
                output = self._read_channel_output(channel, timeout=5)
            
            success_patterns = [r"[\$#>]\s*$", r"欢迎", r"Last login", r"Authorized users"]
            connected = any(re.search(p, output, re.IGNORECASE) for p in success_patterns)
            
            if connected:
                bastion_channel = BastionChannel(channel, len(self.channels), target_host=target_ip)
                with self._lock:
                    self.channels.append(bastion_channel)
                    self._current_session_channel = bastion_channel
                
                self._auth_channel = None
                
                result["success"] = True
                result["output"] = output
                result["channel"] = bastion_channel
                logger.info(f"成功连接到资产 {target_ip}")
            else:
                result["error"] = f"连接资产失败，未检测到成功登录提示"
                result["output"] = output
            
            return result
            
        except Exception as e:
            logger.error(f"连接资产失败: {e}")
            result["error"] = str(e)
            return result

    def execute_command_on_asset(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        if not self._current_session_channel or not self._current_session_channel.is_active:
            return {
                "success": False,
                "output": "",
                "error": "没有活跃的资产会话"
            }
        
        channel = self._current_session_channel
        result = {
            "success": False,
            "output": "",
            "error": None
        }
        
        try:
            logger.info(f"在资产上执行命令: {command}")
            channel.send(command + "\n")
            time.sleep(0.5)
            
            output = ""
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if data:
                        output += data.decode('utf-8', errors='ignore')
                        start_time = time.time()
                else:
                    time.sleep(0.1)
                    if output and not channel.recv_ready():
                        break
            
            result["output"] = output
            result["success"] = True
            logger.info(f"命令执行完成，输出长度: {len(output)}")
            
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            result["error"] = str(e)
        
        return result

    def exit_asset_session(self, timeout: int = 10) -> Dict[str, Any]:
        if not self._current_session_channel or not self._current_session_channel.is_active:
            return {
                "success": True,
                "output": "",
                "message": "没有活跃的资产会话"
            }
        
        channel = self._current_session_channel
        result = {
            "success": False,
            "output": "",
            "error": None
        }
        
        try:
            logger.info("退出资产会话")
            channel.send("exit\n")
            time.sleep(0.5)
            
            output = self._read_channel_output(channel.channel, timeout=timeout, max_read_time=5.0)
            logger.info(f"退出后输出(前300字符): {output[:300]}")
            
            channel.close()
            with self._lock:
                if channel in self.channels:
                    self.channels.remove(channel)
            self._current_session_channel = None
            
            self._auth_channel = self.client.invoke_shell()
            self._auth_channel.settimeout(timeout)
            time.sleep(0.5)
            menu_output = self._read_channel_output(self._auth_channel, timeout=5, max_read_time=10.0)
            
            result["success"] = True
            result["output"] = output
            logger.info("已退出资产会话，返回堡垒机菜单")
            
        except Exception as e:
            logger.error(f"退出资产会话失败: {e}")
            result["error"] = str(e)
        
        return result

    def disconnect_from_bastion(self, timeout: int = 5) -> Dict[str, Any]:
        result = {
            "success": False,
            "output": "",
            "error": None
        }
        
        try:
            if self._current_session_channel and self._current_session_channel.is_active:
                self.exit_asset_session(timeout)
            
            if self._auth_channel:
                self._auth_channel.send("q\n")
                time.sleep(0.5)
                output = self._read_channel_output(self._auth_channel, timeout=timeout)
                logger.info(f"退出堡垒机输出: {output[:200]}")
            
            self.disconnect()
            result["success"] = True
            logger.info("已断开堡垒机连接")
            
        except Exception as e:
            logger.error(f"断开堡垒机连接失败: {e}")
            result["error"] = str(e)
            self.disconnect()
        
        return result

    def create_channel(self) -> Optional[BastionChannel]:
        if not self.client or self.status != ConnectionStatus.AUTHENTICATED:
            logger.error("无法创建通道: 堡垒机未完成认证")
            return None

        with self._lock:
            try:
                channel = self.transport.open_session()
                channel.get_pty()
                channel.invoke_shell()
                
                channel_id = len(self.channels)
                bastion_channel = BastionChannel(channel, channel_id)
                self.channels.append(bastion_channel)
                
                logger.info(f"创建新通道 {channel_id}，当前通道数: {len(self.channels)}")
                return bastion_channel
                
            except Exception as e:
                logger.error(f"创建通道失败: {e}")
                return None

    def close_channel(self, channel_id: int):
        with self._lock:
            for i, ch in enumerate(self.channels):
                if ch.channel_id == channel_id:
                    ch.close()
                    self.channels.pop(i)
                    logger.info(f"关闭通道 {channel_id}，剩余通道数: {len(self.channels)}")
                    return

    def start_keepalive(self, interval: int = 30):
        self._keepalive_running = True
        
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_worker,
            args=(interval,),
            daemon=True
        )
        self._keepalive_thread.start()
        logger.info(f"启动保活线程，间隔 {interval} 秒")

    def stop_keepalive(self):
        self._keepalive_running = False
        if self._keepalive_thread:
            self._keepalive_thread.join(timeout=5)
        logger.info("停止保活线程")

    def _keepalive_worker(self, interval: int):
        while self._keepalive_running:
            try:
                with self._lock:
                    self.channels = [ch for ch in self.channels if ch.is_active]
                    
                    for channel in self.channels:
                        channel.keepalive()
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"保活线程异常: {e}")
                time.sleep(5)

    def disconnect(self):
        self.stop_keepalive()
        
        with self._lock:
            for channel in self.channels:
                channel.close()
            self.channels.clear()
            
            if self._auth_channel:
                try:
                    self._auth_channel.close()
                except Exception:
                    pass
                self._auth_channel = None
            
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
            
            self._update_status(ConnectionStatus.DISCONNECTED, "已断开连接")
            logger.info("已断开堡垒机连接")

    @property
    def is_connected(self) -> bool:
        return self.status in [ConnectionStatus.CONNECTED, ConnectionStatus.AUTHENTICATING, ConnectionStatus.AUTHENTICATED]

    @property
    def is_authenticated(self) -> bool:
        return self.status == ConnectionStatus.AUTHENTICATED


class BastionService:
    _global_server_list: List[Dict[str, str]] = []
    _global_server_list_lock = threading.Lock()
    
    def __init__(self, db: Session):
        self.db = db
        self.param_service = ParamService(db)
        self._connections: Dict[str, BastionConnection] = {}
        self._lock = threading.Lock()

    @classmethod
    def get_global_server_list(cls) -> List[Dict[str, str]]:
        with cls._global_server_list_lock:
            return cls._global_server_list.copy()
    
    @classmethod
    def set_global_server_list(cls, servers: List[Dict[str, str]]):
        with cls._global_server_list_lock:
            cls._global_server_list = servers.copy()
            logger.info(f"全局服务器列表已更新，共 {len(servers)} 台服务器")
    
    @classmethod
    def clear_global_server_list(cls):
        with cls._global_server_list_lock:
            cls._global_server_list = []
            logger.info("全局服务器列表已清空")
    
    @classmethod
    def has_global_server_list(cls) -> bool:
        with cls._global_server_list_lock:
            return len(cls._global_server_list) > 0

    def get_bastion_config(self) -> Dict[str, str]:
        host_param = self.param_service.get_param_by_code("BASTION_HOST")
        user_param = self.param_service.get_param_by_code("BASTION_USER")
        password_param = self.param_service.get_param_by_code("BASTION_PASSWORD")
        
        config = {
            "host": host_param.param_value if host_param else None,
            "username": user_param.param_value if user_param else None,
            "password": password_param.param_value if password_param else None,
            "port": 22
        }
        
        if config["host"] and ":" in config["host"]:
            parts = config["host"].split(":")
            config["host"] = parts[0]
            try:
                config["port"] = int(parts[1])
            except ValueError:
                pass
        
        logger.info(f"堡垒机配置读取: host={config['host']}, port={config['port']}, "
                    f"username={config['username']}, password={'***已配置***' if config['password'] else '未配置'}")
        
        return config

    def has_bastion_config(self) -> bool:
        config = self.get_bastion_config()
        return all([config.get("host"), config.get("username"), config.get("password")])

    def connect_with_retry(self, connection_id: str = "default",
                           host: str = None, port: int = None,
                           username: str = None, password: str = None,
                           max_retries: int = 3, retry_interval: int = 5,
                           timeout: int = 30,
                           on_retry: Callable[[int, str], None] = None,
                           on_status_change: Callable[[ConnectionStatus, str], None] = None) -> BastionConnection:
        if host and username and password:
            config = {
                "host": host,
                "port": port or 22,
                "username": username,
                "password": password
            }
        else:
            config = self.get_bastion_config()
        
        if not all([config.get("host"), config.get("username"), config.get("password")]):
            raise ValueError("堡垒机配置不完整，请检查系统参数 BASTION_HOST, BASTION_USER, BASTION_PASSWORD")
        
        connection = BastionConnection(
            host=config["host"],
            port=config["port"],
            username=config["username"],
            password=config["password"]
        )
        
        if on_status_change:
            connection.set_status_callback(on_status_change)
        
        connection.connect_with_retry(
            max_retries=max_retries,
            retry_interval=retry_interval,
            timeout=timeout,
            on_retry=on_retry
        )
        
        with self._lock:
            self._connections[connection_id] = connection
        
        return connection

    def connect(self, connection_id: str = "default", 
                host: str = None, port: int = None,
                username: str = None, password: str = None,
                timeout: int = 30) -> BastionConnection:
        return self.connect_with_retry(
            connection_id=connection_id,
            host=host, port=port,
            username=username, password=password,
            max_retries=1, timeout=timeout
        )

    def detect_auth_prompt(self, connection_id: str = "default") -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        return connection.detect_auth_prompt()

    def authenticate(self, connection_id: str = "default",
                     auth_type: str = "password",
                     secondary_password: str = None,
                     otp_code: str = None,
                     menu_selection: str = None) -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        result = connection.handle_secondary_auth(
            auth_type=auth_type,
            secondary_password=secondary_password,
            otp_code=otp_code,
            menu_selection=menu_selection
        )
        
        if result.get("has_server_list") and result.get("server_list"):
            BastionService.set_global_server_list(result["server_list"])
        
        return result

    def connect_to_asset(self, connection_id: str = "default",
                         target_ip: str = "",
                         asset_username: str = None,
                         asset_password: str = None,
                         timeout: int = 60) -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        return connection.connect_to_asset(target_ip, asset_username, asset_password, timeout)

    def execute_command_on_asset(self, connection_id: str = "default",
                                  command: str = "",
                                  timeout: int = 30) -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        return connection.execute_command_on_asset(command, timeout)

    def exit_asset_session(self, connection_id: str = "default",
                           timeout: int = 10) -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        return connection.exit_asset_session(timeout)

    def disconnect_from_bastion(self, connection_id: str = "default",
                                timeout: int = 5) -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            return {"success": True, "output": "", "message": "连接不存在"}
        
        result = connection.disconnect_from_bastion(timeout)
        
        with self._lock:
            if connection_id in self._connections:
                del self._connections[connection_id]
        
        return result

    def start_keepalive(self, connection_id: str = "default",
                        interval: int = 30):
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        connection.start_keepalive(interval=interval)

    def get_channel(self, connection_id: str = "default") -> Optional[BastionChannel]:
        connection = self._connections.get(connection_id)
        if not connection:
            return None
        
        with connection._lock:
            for channel in connection.channels:
                if channel.is_active:
                    return channel
        
        return connection.create_channel()

    def execute_command(self, connection_id: str, command: str, 
                        timeout: int = 30) -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection or not connection.is_authenticated:
            raise ValueError(f"连接 {connection_id} 不可用")
        
        channel = self.get_channel(connection_id)
        if not channel:
            raise Exception("无法获取可用通道")
        
        try:
            channel.send(command + "\n")
            time.sleep(0.5)
            
            output = ""
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if channel.recv_ready():
                    data = channel.recv(4096)
                    if data:
                        output += data.decode('utf-8', errors='ignore')
                        start_time = time.time()
                else:
                    time.sleep(0.1)
            
            return {
                "success": True,
                "output": output,
                "exit_code": 0
            }
            
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }

    def get_connection_status(self, connection_id: str = "default") -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            return {
                "connected": False,
                "authenticated": False,
                "status": ConnectionStatus.DISCONNECTED.value,
                "host": None,
                "username": None,
                "error": None
            }
        
        return {
            "connected": connection.is_connected,
            "authenticated": connection.is_authenticated,
            "status": connection.status.value,
            "host": connection.host,
            "username": connection.username,
            "error": connection.error_message
        }

    def disconnect(self, connection_id: str = "default"):
        connection = self._connections.get(connection_id)
        if connection:
            connection.disconnect()
            with self._lock:
                if connection_id in self._connections:
                    del self._connections[connection_id]
