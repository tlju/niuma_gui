import paramiko
import threading
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class SSHSession:
    session_id: str
    user_id: int
    server_id: int
    client: Optional[paramiko.SSHClient]
    channel: Optional[paramiko.Channel]
    status: str = "active"

    def send(self, data: bytes) -> int:
        if self.channel:
            return self.channel.send(data)
        return 0

    def recv(self, size: int = 4096) -> bytes:
        if self.channel and self.channel.recv_ready():
            return self.channel.recv(size)
        return b""

    def is_active(self) -> bool:
        if self.client:
            transport = self.client.get_transport()
            return transport and transport.is_active()
        return False

    def close(self):
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.status = "closed"

class SessionManager:
    def __init__(self):
        self.sessions: dict[str, SSHSession] = {}
        self.lock = threading.RLock()

    def create_session(
        self,
        user_id: int,
        server_id: int,
        get_password_fn: Callable[[int], str]
    ) -> Optional[SSHSession]:
        import uuid
        session_id = str(uuid.uuid4())

        password = get_password_fn(server_id)
        if not password:
            return None

        from models.server_asset import ServerAsset
        from core.database import get_db_session
        db = get_db_session()

        server = db.query(ServerAsset).filter(
            ServerAsset.id == server_id
        ).first()
        db.close()

        if not server:
            return None

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=password,
                timeout=30
            )
            channel = client.invoke_shell()

            session = SSHSession(
                session_id=session_id,
                user_id=user_id,
                server_id=server_id,
                client=client,
                channel=channel
            )

            with self.lock:
                self.sessions[session_id] = session

            return session

        except Exception as e:
            print(f"SSH connection failed: {e}")
            return None

    def get_session(self, session_id: str) -> Optional[SSHSession]:
        with self.lock:
            return self.sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        with self.lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.close()
                return True
        return False

    def get_user_sessions(self, user_id: int) -> list[SSHSession]:
        with self.lock:
            return [
                s for s in self.sessions.values()
                if s.user_id == user_id
            ]
