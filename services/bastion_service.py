import paramiko
import threading
import time
import re
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from sqlalchemy.orm import Session
from services.param_service import ParamService
from core.logger import get_logger

logger = get_logger(__name__)


class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    FAILED = "failed"


class BastionTunnel:
    MAX_TUNNELS = 3

    def __init__(self, transport: paramiko.Transport, target_host: str, target_port: int, local_port: int, tunnel_id: int):
        self.transport = transport
        self.target_host = target_host
        self.target_port = target_port
        self.local_port = local_port
        self.tunnel_id = tunnel_id
        self.is_active = True
        self._server_socket = None
        self._listen_thread = None
        self._forward_threads = []
        self._lock = threading.Lock()
        self._running = False

    def start(self):
        import socket
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind(('127.0.0.1', self.local_port))
            self._server_socket.listen(5)
            self._server_socket.settimeout(1.0)
            self._running = True

            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()
            logger.info(f"隧道 {self.tunnel_id} 已启动: 127.0.0.1:{self.local_port} -> {self.target_host}:{self.target_port}")
        except Exception as e:
            self.is_active = False
            logger.error(f"隧道 {self.tunnel_id} 启动失败: {e}")
            raise

    def _listen_loop(self):
        import socket
        while self._running:
            try:
                client_sock, _ = self._server_socket.accept()
                t = threading.Thread(target=self._forward, args=(client_sock,), daemon=True)
                t.start()
                self._forward_threads.append(t)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.error(f"隧道 {self.tunnel_id} 接受连接失败: {e}")
                break

    def _forward(self, client_sock):
        import socket
        try:
            dest_addr = (self.target_host, self.target_port)
            local_addr = ('127.0.0.1', self.local_port)
            channel = self.transport.open_channel("direct-tcpip", dest_addr, local_addr)

            if channel is None:
                client_sock.close()
                return

            def pipe(src, dst, is_channel=False):
                try:
                    while self._running:
                        if is_channel:
                            if not src.recv_ready():
                                time.sleep(0.05)
                                continue
                            data = src.recv(4096)
                        else:
                            data = src.recv(4096)
                        if not data:
                            break
                        dst.sendall(data if is_channel else data)
                except Exception:
                    pass
                finally:
                    try:
                        src.close()
                    except Exception:
                        pass
                    try:
                        dst.close()
                    except Exception:
                        pass

            t1 = threading.Thread(target=pipe, args=(channel, client_sock), kwargs={"is_channel": True}, daemon=True)
            t2 = threading.Thread(target=pipe, args=(client_sock, channel), daemon=True)
            t1.start()
            t2.start()
            t1.join(timeout=300)
            t2.join(timeout=300)
        except Exception as e:
            logger.error(f"隧道 {self.tunnel_id} 转发连接失败: {e}")
        finally:
            try:
                client_sock.close()
            except Exception:
                pass

    def close(self):
        with self._lock:
            self._running = False
            self.is_active = False
            if self._server_socket:
                try:
                    self._server_socket.close()
                except Exception:
                    pass
            logger.info(f"隧道 {self.tunnel_id} 已关闭: 127.0.0.1:{self.local_port} -> {self.target_host}:{self.target_port}")

    def get_display_info(self) -> str:
        return f"{self.target_host}:{self.target_port} (本地:{self.local_port})"


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
        self.password = password
        self.client: Optional[paramiko.SSHClient] = None
        self.transport: Optional[paramiko.Transport] = None
        self.channels: List[BastionChannel] = []
        self.tunnels: List[BastionTunnel] = []
        self._next_tunnel_id = 1
        self.status = ConnectionStatus.DISCONNECTED
        self.error_message: str = ""
        self._lock = threading.Lock()
        self._keepalive_thread: Optional[threading.Thread] = None
        self._keepalive_running = False
        self._min_channels = 1
        self._max_channels = 5
        self._current_target_host: str = None
        self._on_status_change: Optional[Callable[[ConnectionStatus, str], None]] = None
        self._auth_channel = None

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
                password=self.password,
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
            
            if "密码" in output or "password" in output.lower() or "口令" in output:
                if not auth_info["needs_otp"]:
                    auth_info["needs_password"] = True
            
            if "验证码" in output or "OTP" in output.upper() or "动态口令" in output or "令牌" in output:
                auth_info["needs_otp"] = True
            
            if "菜单" in output or "menu" in output.lower() or "选择" in output or "请输入" in output:
                auth_info["needs_menu"] = True
                auth_info["has_menu"] = True
            
            logger.info(f"堡垒机认证方式检测结果: needs_password={auth_info['needs_password']}, "
                        f"needs_otp={auth_info['needs_otp']}, needs_menu={auth_info['needs_menu']}, "
                        f"has_menu={auth_info['has_menu']}")
            
            if not auth_info["needs_otp"] and not auth_info["needs_password"] and not auth_info["needs_menu"]:
                if self._auth_channel:
                    self._auth_channel.close()
                    self._auth_channel = None
            
            return auth_info
            
        except Exception as e:
            logger.error(f"检测认证提示失败: {e}")
            self._auth_channel = None
            return {
                "needs_password": True,
                "needs_otp": False,
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
                        f"has_secondary_password={secondary_password is not None}, "
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
            
            elif "密码" in output or "password" in output.lower() or "口令" in output:
                if secondary_password:
                    logger.info("检测到密码提示，发送二次密码")
                    channel.send(secondary_password + "\n")
                    time.sleep(0.5)
                    output = self._read_channel_output(channel, timeout)
                    logger.info(f"二次认证-密码认证后输出(前500字符): {output[:500]}")
                    
                    if self._is_otp_prompt(output):
                        if otp_code:
                            logger.info("密码认证后检测到OTP提示，发送验证码")
                            channel.send(otp_code + "\n")
                            time.sleep(1.0)
                            output = self._read_channel_output(channel, timeout, max_read_time=15.0)
                            logger.info(f"二次认证-密码+OTP后输出(前500字符): {output[:500]}")
                            
                            if self._is_otp_prompt(output):
                                logger.warning("OTP验证失败，堡垒机再次要求输入")
                                raise Exception("OTP_RETRY")
                        else:
                            channel.close()
                            self._auth_channel = None
                            raise Exception("需要OTP验证码但未提供")
                    
                    if "错误" in output or "error" in output.lower() or "失败" in output or "incorrect" in output.lower():
                        channel.close()
                        self._auth_channel = None
                        raise Exception("二次认证失败，密码错误")
            
            result = {
                "authenticated": False,
                "has_server_list": False,
                "server_list": [],
                "output": output
            }
            
            if "请选择" in output or "选择目标" in output or "Ctrl+F" in output:
                logger.info("检测到服务器列表菜单，解析服务器列表")
                servers = self._parse_server_list(output)
                result["has_server_list"] = True
                result["server_list"] = servers
                result["authenticated"] = True
                logger.info(f"解析到 {len(servers)} 台服务器")
                
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

    def connect_to_host(self, host: str, username: str = None, password: str = None,
                        timeout: int = 30) -> Optional[BastionChannel]:
        if not self.client or self.status != ConnectionStatus.AUTHENTICATED:
            raise Exception("堡垒机未完成认证，无法连接目标主机")

        try:
            channel = self.transport.open_session()
            channel.get_pty()
            channel.invoke_shell()
            
            time.sleep(0.3)
            output = self._read_channel_output(channel, timeout=2)
            
            connect_cmd = f"ssh {username + '@' if username else ''}{host}\n"
            channel.send(connect_cmd)
            time.sleep(0.5)
            output = self._read_channel_output(channel, timeout=5)
            
            if "password" in output.lower() or "密码" in output:
                if password:
                    channel.send(password + "\n")
                    time.sleep(0.5)
                    output = self._read_channel_output(channel, timeout=5)
            
            if "yes/no" in output.lower():
                channel.send("yes\n")
                time.sleep(0.5)
                output = self._read_channel_output(channel, timeout=5)
            
            success_patterns = [r"[\$#>]\s*$", r"欢迎", r"Last login"]
            connected = any(re.search(p, output, re.IGNORECASE) for p in success_patterns)
            
            if connected:
                bastion_channel = BastionChannel(channel, len(self.channels), target_host=host)
                with self._lock:
                    self.channels.append(bastion_channel)
                    self._current_target_host = host
                
                logger.info(f"成功连接到目标主机 {host}")
                return bastion_channel
            else:
                channel.close()
                raise Exception(f"连接目标主机 {host} 失败: {output}")
                
        except Exception as e:
            logger.error(f"连接目标主机失败: {e}")
            raise

    def get_host_ips(self, channel: BastionChannel, timeout: int = 10) -> List[str]:
        if not channel or not channel.is_active:
            raise Exception("通道不可用")

        try:
            ip_commands = [
                "ip addr show | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1",
                "hostname -I",
                "ifconfig | grep 'inet ' | awk '{print $2}'"
            ]
            
            ips = []
            for cmd in ip_commands:
                channel.send(cmd + "\n")
                time.sleep(0.5)
                output = ""
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    if channel.recv_ready():
                        data = channel.recv(4096)
                        if data:
                            output += data.decode('utf-8', errors='ignore')
                            if re.search(r'[\$#>]\s*$', output):
                                break
                    time.sleep(0.1)
                
                ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
                found_ips = re.findall(ip_pattern, output)
                
                for ip in found_ips:
                    if ip not in ips and not ip.startswith('127.'):
                        ips.append(ip)
                
                if ips:
                    break
            
            logger.info(f"获取到主机IP地址: {ips}")
            return ips
            
        except Exception as e:
            logger.error(f"获取主机IP失败: {e}")
            return []

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

    def create_channel(self) -> Optional[BastionChannel]:
        if not self.client or self.status != ConnectionStatus.AUTHENTICATED:
            logger.error("无法创建通道: 堡垒机未完成认证")
            return None

        with self._lock:
            if len(self.channels) >= self._max_channels:
                logger.warning(f"已达到最大通道数 {self._max_channels}")
                return None

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

    def start_keepalive(self, interval: int = 30, min_channels: int = 1, max_channels: int = 5):
        self._min_channels = min_channels
        self._max_channels = max_channels
        self._keepalive_running = True
        
        self._keepalive_thread = threading.Thread(
            target=self._keepalive_worker,
            args=(interval,),
            daemon=True
        )
        self._keepalive_thread.start()
        logger.info(f"启动保活线程，间隔 {interval} 秒，通道范围 {min_channels}-{max_channels}")

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
                    
                    while len(self.channels) < self._min_channels:
                        new_channel = self.create_channel()
                        if not new_channel:
                            break
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"保活线程异常: {e}")
                time.sleep(5)

    def create_tunnel(self, target_host: str, target_port: int = 22) -> Optional[BastionTunnel]:
        if not self.is_authenticated:
            raise Exception("堡垒机未完成认证，无法创建隧道")

        import socket
        with self._lock:
            active_tunnels = [t for t in self.tunnels if t.is_active]
            if len(active_tunnels) >= BastionTunnel.MAX_TUNNELS:
                raise Exception(f"已达到最大隧道数量 ({BastionTunnel.MAX_TUNNELS})")

            for port in range(20000, 30000):
                try:
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(0.1)
                    result = test_sock.connect_ex(('127.0.0.1', port))
                    test_sock.close()
                    if result != 0:
                        local_port = port
                        break
                except Exception:
                    continue
            else:
                raise Exception("无法找到可用的本地端口")

            tunnel_id = self._next_tunnel_id
            self._next_tunnel_id += 1

            tunnel = BastionTunnel(
                transport=self.transport,
                target_host=target_host,
                target_port=target_port,
                local_port=local_port,
                tunnel_id=tunnel_id
            )
            tunnel.start()
            self.tunnels.append(tunnel)
            logger.info(f"创建隧道 {tunnel_id}: 127.0.0.1:{local_port} -> {target_host}:{target_port}")
            return tunnel

    def close_tunnel(self, tunnel_id: int):
        with self._lock:
            for i, tunnel in enumerate(self.tunnels):
                if tunnel.tunnel_id == tunnel_id:
                    tunnel.close()
                    self.tunnels.pop(i)
                    logger.info(f"关闭隧道 {tunnel_id}")
                    return True
        return False

    def get_active_tunnels(self) -> List[BastionTunnel]:
        with self._lock:
            self.tunnels = [t for t in self.tunnels if t.is_active]
            return list(self.tunnels)

    def disconnect(self):
        self.stop_keepalive()
        
        with self._lock:
            for tunnel in self.tunnels:
                tunnel.close()
            self.tunnels.clear()

            for channel in self.channels:
                channel.close()
            self.channels.clear()
            
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
    def __init__(self, db: Session):
        self.db = db
        self.param_service = ParamService(db)
        self._connections: Dict[str, BastionConnection] = {}
        self._lock = threading.Lock()

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
        
        return connection.handle_secondary_auth(
            auth_type=auth_type,
            secondary_password=secondary_password,
            otp_code=otp_code,
            menu_selection=menu_selection
        )

    def connect_to_host(self, connection_id: str = "default",
                        host: str = "", username: str = None, password: str = None,
                        timeout: int = 30) -> Optional[BastionChannel]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        return connection.connect_to_host(host, username, password, timeout)

    def get_host_ips(self, connection_id: str = "default",
                     channel: BastionChannel = None, timeout: int = 10) -> List[str]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        if channel:
            return connection.get_host_ips(channel, timeout)
        
        active_channel = self.get_channel(connection_id)
        if active_channel:
            return connection.get_host_ips(active_channel, timeout)
        
        return []

    def start_keepalive(self, connection_id: str = "default",
                        interval: int = 30,
                        min_channels: int = 1,
                        max_channels: int = 5):
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        
        connection.start_keepalive(
            interval=interval,
            min_channels=min_channels,
            max_channels=max_channels
        )

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
                "command": command
            }
            
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

    def disconnect(self, connection_id: str = "default"):
        with self._lock:
            connection = self._connections.pop(connection_id, None)
            if connection:
                connection.disconnect()

    def disconnect_all(self):
        with self._lock:
            for connection in list(self._connections.values()):
                connection.disconnect()
            self._connections.clear()

    def get_connection_status(self, connection_id: str = "default") -> Dict[str, Any]:
        connection = self._connections.get(connection_id)
        if not connection:
            return {
                "exists": False,
                "status": ConnectionStatus.DISCONNECTED.value,
                "connected": False,
                "authenticated": False,
                "channels": 0,
                "tunnels": 0,
                "error_message": ""
            }
        
        active_tunnels = connection.get_active_tunnels()
        return {
            "exists": True,
            "status": connection.status.value,
            "connected": connection.is_connected,
            "authenticated": connection.is_authenticated,
            "channels": len([ch for ch in connection.channels if ch.is_active]),
            "tunnels": len(active_tunnels),
            "host": connection.host,
            "username": connection.username,
            "error_message": connection.error_message,
            "current_target_host": connection._current_target_host
        }

    def create_tunnel(self, connection_id: str = "default",
                      target_host: str = "", target_port: int = 22) -> Optional[BastionTunnel]:
        connection = self._connections.get(connection_id)
        if not connection:
            raise ValueError(f"未找到连接: {connection_id}")
        return connection.create_tunnel(target_host, target_port)

    def close_tunnel(self, connection_id: str = "default", tunnel_id: int = 0) -> bool:
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        return connection.close_tunnel(tunnel_id)

    def get_active_tunnels(self, connection_id: str = "default") -> List[BastionTunnel]:
        connection = self._connections.get(connection_id)
        if not connection:
            return []
        return connection.get_active_tunnels()

    def get_connection(self, connection_id: str = "default") -> Optional[BastionConnection]:
        return self._connections.get(connection_id)

    def get_connected_hosts(self, connection_id: str = "default") -> List[str]:
        connection = self._connections.get(connection_id)
        if not connection:
            return []
        
        hosts = []
        with connection._lock:
            for channel in connection.channels:
                if channel.is_active and channel.target_host:
                    if channel.target_host not in hosts:
                        hosts.append(channel.target_host)
        
        if connection._current_target_host and connection._current_target_host not in hosts:
            hosts.append(connection._current_target_host)
        
        return hosts

    def get_all_connected_hosts(self) -> List[str]:
        all_hosts = []
        with self._lock:
            for connection_id, connection in self._connections.items():
                hosts = self.get_connected_hosts(connection_id)
                for host in hosts:
                    if host not in all_hosts:
                        all_hosts.append(host)
        return all_hosts
