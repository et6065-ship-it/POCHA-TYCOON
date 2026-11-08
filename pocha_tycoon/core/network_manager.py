"""
core/network_manager.py
'전세계 길거리 음식 포차 타이쿤' 1:1 네트워크 결투 모드 전용 TCP/UDP 통신 매니저.
- 표준 라이브러리(socket, threading, queue, json)만 사용하여 외부 의존성 없이 동작
- TCP 소켓(TCP_NODELAY) 기반 줄바꿈(\n) 구분 JSON 패킷 송수신
- 방 만들기(Host 서버) / IP 직접 참가(Client) / 로컬(127.0.0.1) 원클릭 참가 지원
- UDP 브로드캐스트(포트 15433) 기반 LAN 열린 방 자동 탐색(Discovery) 지원
"""

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import config


def _score_ip(ip: str) -> int:
    """실제 LAN/공유기 및 게이밍 VPN(Radmin/Hamachi/Tailscale) 대역을 가상 어댑터(WSL/Hyper-V)보다 우선순위를 높게 부여한다."""
    if not ip or ip.startswith("127.") or ip.startswith("169.254."):
        return -1
    if ip.startswith("192.168."):
        return 100
    if ip.startswith("10."):
        return 90
    if ip.startswith("26.") or ip.startswith("25.") or ip.startswith("100."):
        return 85
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
            if 16 <= second <= 31:
                return 20  # WSL / Docker / Hyper-V 대역일 가능성 높음
        except Exception:
            pass
    return 60


def get_all_local_ips() -> List[str]:
    """현재 PC의 활성화된 모든 IPv4 사설/VPN IP 목록을 우선순위 순으로 반환한다."""
    import sys
    if sys.platform == "emscripten":
        return ["127.0.0.1"]
    candidates: List[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.3)
            s.connect(("8.8.8.8", 80))
            primary = s.getsockname()[0]
            if primary and not primary.startswith("127."):
                candidates.append(str(primary))
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        for ip in ip_list:
            if ip and not ip.startswith("127.") and not ip.startswith("169.254.") and ip not in candidates:
                candidates.append(str(ip))
    except Exception:
        pass

    candidates.sort(key=_score_ip, reverse=True)
    return candidates if candidates else ["127.0.0.1"]


def get_local_ip() -> str:
    """현재 PC의 대표 LAN 사설 IP 주소(예: 192.168.x.x)를 조회한다. 실패 시 127.0.0.1 반환."""
    ips = get_all_local_ips()
    return ips[0] if ips else "127.0.0.1"


def _disable_udp_connreset(sock: socket.socket) -> None:
    """
    Windows Winsock에서 UDP sendto 대상 포트가 닫혀 있을 때(ICMP Port Unreachable)
    직후 recvfrom()에서 ConnectionResetError(WinError 10054)가 발생하는 현상을 방지한다.
    """
    if hasattr(socket, "SIO_UDP_CONNRESET"):
        try:
            sock.ioctl(socket.SIO_UDP_CONNRESET, False)  # type: ignore[attr-defined]
        except Exception:
            pass


class DuelNetworkManager:
    """
    1:1 실시간 매출 타임어택 결투를 위한 비동기 TCP + UDP LAN 탐색 네트워크 매니저.
    메인 게임 루프에서는 poll_messages()만 호출하여 스레드 안전하게 패킷을 처리한다.
    """

    _instance: Optional["DuelNetworkManager"] = None

    @classmethod
    def get_instance(cls) -> "DuelNetworkManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.role: str = "NONE"  # "NONE" | "HOST" | "CLIENT"
        self.connected: bool = False
        self.connecting: bool = False
        self.hosting: bool = False
        self.status_text: str = "대기 중"
        self.error_text: str = ""

        self.local_ip: str = get_local_ip()
        self.tcp_port: int = config.DEFAULT_DUEL_PORT
        self.peer_address: str = ""
        self.latency_ms: int = 0

        # 로비 동기화 메타데이터 (UDP LAN 탐색 응답용)
        self.room_meta: Dict[str, Any] = {
            "host_name": "1P 포차마스터",
            "host_char": "chef_kr",
            "chapter": "KR",
            "duration": config.DUEL_DEFAULT_DURATION,
            "station_level": config.DUEL_DEFAULT_STATION_LEVEL,
            "in_game": False,
        }

        self._server_sock: Optional[socket.socket] = None
        self._conn_sock: Optional[socket.socket] = None
        self._udp_sock: Optional[socket.socket] = None
        self._stop_event: threading.Event = threading.Event()
        self._send_lock: threading.Lock = threading.Lock()

        self.inbox: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._outbox: "queue.Queue[bytes]" = queue.Queue()
        self.discovered_rooms: List[Dict[str, Any]] = []
        self._discovery_lock: threading.Lock = threading.Lock()
        self._scanning: bool = False
        self._last_ping_sent: float = 0.0

    @property
    def is_host(self) -> bool:
        """현재 인스턴스가 1:1 결투 호스트(방장)인지 여부를 반환한다."""
        return self.role == "HOST" or bool(self.hosting)

    @property
    def running(self) -> bool:
        """네트워크 세션이 활성(호스팅/연결됨/연결 시도 중) 상태인지 여부를 반환한다."""
        return not self._stop_event.is_set() and (self.hosting or self.connected or self.connecting)

    # ==========================================================================
    # 호스트(방 만들기) 시작
    # ==========================================================================
    def start_host(self, port: int = config.DEFAULT_DUEL_PORT) -> bool:
        """지정한 TCP 포트에서 1:1 결투 호스트 서버 및 UDP LAN 탐색 응답기를 시작한다."""
        self.close()
        self._stop_event.clear()
        self.error_text = ""

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        bound_port = int(port)
        bound_ok = False
        for candidate_port in (bound_port, bound_port + 1, bound_port + 2):
            try:
                server_sock.bind(("0.0.0.0", candidate_port))
                bound_port = candidate_port
                bound_ok = True
                break
            except OSError:
                continue

        if not bound_ok:
            try:
                server_sock.close()
            except Exception:
                pass
            self.error_text = f"포트 {port} 바인딩에 실패했습니다. 이미 실행 중인 서버를 확인하세요."
            self.status_text = self.error_text
            return False

        server_sock.listen(2)
        server_sock.settimeout(0.5)
        self._server_sock = server_sock
        self.tcp_port = bound_port
        self.role = "HOST"
        self.hosting = True
        self.connected = False
        self.connecting = False
        self.local_ip = get_local_ip()
        self.status_text = f"방 개설 완료! 참가자 대기 중 ({self.local_ip}:{self.tcp_port})"

        threading.Thread(target=self._host_accept_loop, daemon=True).start()
        threading.Thread(target=self._udp_responder_loop, daemon=True).start()
        return True

    def _host_accept_loop(self) -> None:
        while not self._stop_event.is_set() and self._server_sock is not None:
            if self.connected and self._conn_sock is not None:
                time.sleep(0.2)
                continue
            try:
                client_sock, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass

            while not self._outbox.empty():
                try:
                    self._outbox.get_nowait()
                except queue.Empty:
                    break

            self._conn_sock = client_sock
            self.connected = True
            self.peer_address = f"{addr[0]}:{addr[1]}"
            self.status_text = f"도전자 연결됨 ({addr[0]})"
            self.inbox.put({"type": "NET_CONNECTED", "peer_addr": self.peer_address})
            threading.Thread(target=self._send_loop, args=(client_sock,), daemon=True).start()
            threading.Thread(target=self._recv_loop, args=(client_sock,), daemon=True).start()

    def _udp_responder_loop(self) -> None:
        """LAN 내 클라이언트의 방 탐색 브로드캐스트에 현재 방 정보를 응답한다."""
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_sock.bind(("0.0.0.0", config.DEFAULT_DISCOVERY_PORT))
            _disable_udp_connreset(udp_sock)
            udp_sock.settimeout(0.5)
            self._udp_sock = udp_sock
        except Exception:
            try:
                udp_sock.close()
            except Exception:
                pass
            return

        while not self._stop_event.is_set() and self.hosting:
            try:
                data, addr = udp_sock.recvfrom(1024)
            except (socket.timeout, ConnectionResetError, BlockingIOError):
                continue
            except OSError:
                break

            try:
                msg = data.decode("utf-8", errors="ignore").strip()
                if msg == "POCHA_DISCOVER_V1" and not self.connected and not self.room_meta.get("in_game", False):
                    reply = {
                        "magic": "POCHA_ROOM_V1",
                        "host_name": self.room_meta.get("host_name", "1P 포차마스터"),
                        "host_char": self.room_meta.get("host_char", "chef_kr"),
                        "chapter": self.room_meta.get("chapter", "KR"),
                        "duration": self.room_meta.get("duration", config.DUEL_DEFAULT_DURATION),
                        "station_level": self.room_meta.get("station_level", config.DUEL_DEFAULT_STATION_LEVEL),
                        "tcp_port": self.tcp_port,
                        "host_ip": self.local_ip,
                    }
                    payload = json.dumps(reply, ensure_ascii=False).encode("utf-8")
                    udp_sock.sendto(payload, addr)
            except Exception:
                continue

    # ==========================================================================
    # 클라이언트(방 참가하기) 연결
    # ==========================================================================
    def connect_to_host(self, host_ip: str, port: int = config.DEFAULT_DUEL_PORT) -> None:
        """비동기 스레드로 지정한 호스트 IP:Port에 TCP 연결을 시도한다."""
        self.close()
        self._stop_event.clear()
        self.role = "CLIENT"
        self.connecting = True
        self.connected = False
        self.error_text = ""

        clean_ip = (host_ip or "127.0.0.1").strip()
        if ":" in clean_ip:
            parts = clean_ip.rsplit(":", 1)
            clean_ip = parts[0].strip() or "127.0.0.1"
            try:
                port = int(parts[1].strip())
            except ValueError:
                pass

        self.tcp_port = int(port)
        self.status_text = f"{clean_ip}:{self.tcp_port} 서버에 접속 중..."
        threading.Thread(
            target=self._client_connect_worker,
            args=(clean_ip, self.tcp_port),
            daemon=True,
        ).start()

    def _client_connect_worker(self, host_ip: str, port: int) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        try:
            sock.connect((host_ip, port))
            if self._stop_event.is_set() or not self.running or self.role != "CLIENT":
                try:
                    sock.close()
                except Exception:
                    pass
                return
            try:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass
            self._conn_sock = sock
            self.connected = True
            self.connecting = False
            self.peer_address = f"{host_ip}:{port}"
            self.status_text = f"연결 완료 ({self.peer_address})"
            self.inbox.put({"type": "NET_CONNECTED", "peer_addr": self.peer_address})
            threading.Thread(target=self._send_loop, args=(sock,), daemon=True).start()
            self._recv_loop(sock)
        except Exception as exc:
            try:
                sock.close()
            except Exception:
                pass
            if self._stop_event.is_set() or self.role != "CLIENT":
                return
            self.connecting = False
            self.connected = False
            self.role = "NONE"
            err_msg = f"연결 실패 ({host_ip}:{port}) - 방이 열려 있는지 확인하세요."
            self.error_text = err_msg
            self.status_text = err_msg
            self.inbox.put({"type": "NET_ERROR", "message": err_msg, "detail": str(exc)})

    # ==========================================================================
    # 공통 수신 루프 & 패킷 송신
    # ==========================================================================
    def _recv_loop(self, sock: socket.socket) -> None:
        sock.settimeout(0.5)
        buffer = ""
        max_buffer_size = 65536
        while not self._stop_event.is_set():
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="ignore")
                if len(buffer) > max_buffer_size and "\n" not in buffer:
                    buffer = ""
                    continue
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        if isinstance(msg, dict):
                            mtype = msg.get("type")
                            if mtype == "PING":
                                self.send({"type": "PONG", "ts": msg.get("ts", time.time())})
                            elif mtype == "PONG":
                                raw_ts = msg.get("ts")
                                sent_ts = float(raw_ts) if raw_ts is not None else time.time()
                                self.latency_ms = max(1, int((time.time() - sent_ts) * 1000))
                            else:
                                self.inbox.put(msg)
                    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
                        continue
                if len(buffer) > max_buffer_size:
                    buffer = buffer[-max_buffer_size:]
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception:
                break

        # 연결 종료 처리
        was_connected = self.connected
        self.connected = False
        if self._conn_sock is sock:
            try:
                sock.close()
            except Exception:
                pass
            self._conn_sock = None

        if not self._stop_event.is_set() and was_connected:
            if self.role == "HOST":
                self.status_text = f"상대방 연결이 끊어졌습니다. 재접속 대기 중 ({self.local_ip}:{self.tcp_port})"
            else:
                self.status_text = "호스트와의 연결이 종료되었습니다."
                self.role = "NONE"
            self.inbox.put({"type": "NET_DISCONNECTED"})

    def _send_loop(self, sock: socket.socket) -> None:
        """비동기 송신 워커 스레드 (메인 렌더링 루프 블로킹 완벽 방지)."""
        while not self._stop_event.is_set() and self.connected and self._conn_sock is sock:
            try:
                raw = self._outbox.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                with self._send_lock:
                    sock.sendall(raw)
            except Exception:
                break

    def send(self, payload: Dict[str, Any]) -> bool:
        """현재 연결된 상대방에게 JSON 패킷 1개를 논블로킹 큐로 즉시 전송한다."""
        if not self.connected or self._conn_sock is None:
            return False
        try:
            raw = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            self._outbox.put_nowait(raw)
            return True
        except Exception:
            return False

    def send_ping_if_needed(self, interval: float = 2.0) -> None:
        """주기적으로 PING을 전송하여 지연시간(ms)을 측정한다."""
        if not self.connected:
            return
        now = time.time()
        if now - self._last_ping_sent >= interval:
            self._last_ping_sent = now
            self.send({"type": "PING", "ts": now})

    def poll_messages(self) -> List[Dict[str, Any]]:
        """수신 큐에 쌓인 모든 메시지를 꺼내 리스트로 반환한다."""
        messages: List[Dict[str, Any]] = []
        while True:
            try:
                messages.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return messages

    # ==========================================================================
    # LAN 열린 방 자동 탐색 (UDP Broadcast + Localhost)
    # ==========================================================================
    def trigger_lan_scan(self) -> None:
        """비동기 스레드로 로컬(127.0.0.1) 및 LAN 브로드캐스트 방 탐색을 수행한다."""
        if self._scanning:
            return
        self._scanning = True
        threading.Thread(target=self._lan_scan_worker, daemon=True).start()

    def _lan_scan_worker(self) -> None:
        found: List[Dict[str, Any]] = []
        seen_keys = set()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            _disable_udp_connreset(sock)
            sock.settimeout(0.15)
            probe = b"POCHA_DISCOVER_V1"

            targets = ["127.0.0.1", "<broadcast>", "255.255.255.255"]
            for local_ip in get_all_local_ips():
                parts = local_ip.split(".")
                if len(parts) == 4:
                    subnet_bcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                    if subnet_bcast not in targets:
                        targets.append(subnet_bcast)

            for target_ip in targets:
                try:
                    sock.sendto(probe, (target_ip, config.DEFAULT_DISCOVERY_PORT))
                except Exception:
                    continue

            deadline = time.time() + 0.45
            while time.time() < deadline:
                try:
                    data, addr = sock.recvfrom(2048)
                except (socket.timeout, ConnectionResetError, BlockingIOError):
                    continue
                except OSError:
                    break
                try:
                    info = json.loads(data.decode("utf-8", errors="ignore"))
                    if isinstance(info, dict) and info.get("magic") == "POCHA_ROOM_V1":
                        ip_str = addr[0]
                        t_port = int(info.get("tcp_port", config.DEFAULT_DUEL_PORT))
                        key = f"{ip_str}:{t_port}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            info["ip"] = ip_str
                            info["key"] = key
                            found.append(info)
                except Exception:
                    continue
        finally:
            try:
                sock.close()
            except Exception:
                pass
            with self._discovery_lock:
                self.discovered_rooms = found
            self._scanning = False

    def get_discovered_rooms(self) -> List[Dict[str, Any]]:
        with self._discovery_lock:
            return list(self.discovered_rooms)

    # ==========================================================================
    # 세션 종료 및 정리
    # ==========================================================================
    def close(self) -> None:
        """모든 소켓과 백그라운드 스레드를 안전하게 종료한다."""
        self._stop_event.set()
        self.connected = False
        self.connecting = False
        self.hosting = False
        self.role = "NONE"
        self.peer_address = ""

        for s in (self._conn_sock, self._server_sock, self._udp_sock):
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
        self._conn_sock = None
        self._server_sock = None
        self._udp_sock = None

        while not self.inbox.empty():
            try:
                self.inbox.get_nowait()
            except queue.Empty:
                break

        while not self._outbox.empty():
            try:
                self._outbox.get_nowait()
            except queue.Empty:
                break


# 모듈 레벨 싱글톤 인스턴스
duel_network: DuelNetworkManager = DuelNetworkManager.get_instance()
