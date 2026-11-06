"""
scenes/duel_lobby_scene.py
'전세계 길거리 음식 포차 타이쿤' 1:1 네트워크 결투 대기실 및 매칭 로비 씬 (DuelLobbyScene).
- 방 만들기(Host 서버 개설) / IP:Port 직접 입력 참가 / 로컬(127.0.0.1) 원클릭 참가 지원
- UDP 브로드캐스트 기반 LAN 열린 방 자동 탐색 목록 제공
- 한 PC에서 바로 1:1 네트워크 결투를 테스트할 수 있는 [2P 클라이언트 창 바로 띄우기] 원클릭 지원
- 대기실에서 양측 포차 마스터(4인 전원 해금) 선택, 결투 국가(KR/JP/MX/TW), 제한 시간(60/90/120초),
  공정 기구 강화 레벨(Lv.0~Lv.3) 실시간 동기화 및 3초 카운트다운 후 동시 입장
"""

from __future__ import annotations

import math
import os
import random
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import pygame

import config
from core import art_renderer
from core.effects import ParticleSystem, sound_fx
from core.game_manager import GameManager
from core.network_manager import DuelNetworkManager, duel_network
from core.scene_manager import BaseScene, SceneManager
from data.chapters import CHAPTER_ORDER, CHAPTERS
from data.characters import CHARACTER_ORDER, CHARACTERS


class DuelLobbyScene(BaseScene):
    """1:1 네트워크 결투 매칭 및 대기실 씬."""

    def __init__(
        self,
        game_mgr: Optional[GameManager] = None,
        scene_mgr: Optional[SceneManager] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(game_mgr, scene_mgr, **kwargs)
        self.net: DuelNetworkManager = duel_network
        self.time_tick: float = 0.0
        self.particles: ParticleSystem = ParticleSystem()
        self._hover_pos: Tuple[int, int] = (0, 0)

        # 접속 UI 상태
        self.ip_input: str = str(kwargs.get("default_ip", f"127.0.0.1:{config.DEFAULT_DUEL_PORT}"))
        self.ip_focused: bool = False
        self.scan_timer: float = 0.2

        # 로비 대기실 상태 (호스트 & 클라이언트 동기화)
        default_char = self.game_mgr.selected_character if self.game_mgr else "chef_kr"
        self.host_name: str = "1P 호스트 마스터"
        self.client_name: str = "2P 도전자 마스터"
        self.host_char: str = default_char
        self.client_char: str = "chef_jp" if default_char == "chef_kr" else "chef_kr"
        self.selected_chapter: str = (self.game_mgr.current_chapter if self.game_mgr else "KR") or "KR"
        self.match_duration: int = config.DUEL_DEFAULT_DURATION
        self.station_level: int = config.DUEL_DEFAULT_STATION_LEVEL
        self.client_ready: bool = False

        # 카운트다운 상태
        self.countdown_active: bool = False
        self.countdown_timer: float = 0.0
        self.match_seed: int = 0
        self._last_countdown_int: int = 0

        # UI Rect 정의
        self.back_btn_rect: pygame.Rect = pygame.Rect(40, 22, 165, 42)
        self.options_btn_rect: pygame.Rect = pygame.Rect(792, 22, 108, 42)

        # 1) 미연결 초기 화면 Rect
        self.host_create_btn: pygame.Rect = pygame.Rect(72, 260, 510, 66)
        self.local_dual_btn: pygame.Rect = pygame.Rect(72, 344, 510, 62)
        self.local_join_btn: pygame.Rect = pygame.Rect(72, 424, 510, 58)

        self.ip_box_rect: pygame.Rect = pygame.Rect(695, 232, 365, 48)
        self.ip_connect_btn: pygame.Rect = pygame.Rect(1072, 232, 138, 48)
        self.refresh_lan_btn: pygame.Rect = pygame.Rect(1080, 310, 130, 34)
        self.lan_room_rects: List[Tuple[Dict[str, Any], pygame.Rect]] = []

        # 2) 대기실(연결/호스팅 중) Rect
        self.spawn_2p_btn_rect: pygame.Rect = pygame.Rect(910, 22, 330, 42)
        self.host_char_page: int = 0
        self.client_char_page: int = 0
        self.host_prev_page_btn: pygame.Rect = pygame.Rect(246, 360, 48, 24)
        self.host_next_page_btn: pygame.Rect = pygame.Rect(332, 360, 48, 24)
        self.client_prev_page_btn: pygame.Rect = pygame.Rect(1086, 360, 48, 24)
        self.client_next_page_btn: pygame.Rect = pygame.Rect(1172, 360, 48, 24)
        self.host_char_btns: List[Tuple[str, pygame.Rect]] = []
        self.client_char_btns: List[Tuple[str, pygame.Rect]] = []
        self.chapter_btns: List[Tuple[str, pygame.Rect]] = []
        self.duration_btns: List[Tuple[int, pygame.Rect]] = []
        self.level_btns: List[Tuple[int, pygame.Rect]] = []
        self.ready_or_start_btn: pygame.Rect = pygame.Rect(440, 636, 400, 56)
        self.leave_room_btn: pygame.Rect = pygame.Rect(40, 642, 190, 46)

        self._build_waiting_room_rects()

    def _build_waiting_room_rects(self) -> None:
        total_pages = max(1, (len(CHARACTER_ORDER) + 3) // 4)
        self.host_char_page = max(0, min(getattr(self, "host_char_page", 0), total_pages - 1))
        self.client_char_page = max(0, min(getattr(self, "client_char_page", 0), total_pages - 1))

        # 1P 캐릭터 선택 버튼 4개 (페이지네이션 지원, 좌측 카드 하단)
        self.host_char_btns = []
        h_slice = CHARACTER_ORDER[self.host_char_page * 4 : (self.host_char_page + 1) * 4]
        for idx, cid in enumerate(h_slice):
            col = idx % 2
            row = idx // 2
            r = pygame.Rect(60 + col * 164, 486 + row * 48, 156, 42)
            self.host_char_btns.append((cid, r))

        # 2P 캐릭터 선택 버튼 4개 (페이지네이션 지원, 우측 카드 하단)
        self.client_char_btns = []
        c_slice = CHARACTER_ORDER[self.client_char_page * 4 : (self.client_char_page + 1) * 4]
        for idx, cid in enumerate(c_slice):
            col = idx % 2
            row = idx // 2
            r = pygame.Rect(900 + col * 164, 486 + row * 48, 156, 42)
            self.client_char_btns.append((cid, r))

        # 중앙 패널: 챕터(국가) 버튼 9개 (5 + 4 2줄 깔끔 배치)
        self.chapter_btns = []
        for idx, ch_id in enumerate(CHAPTER_ORDER):
            col = idx % 5
            row = idx // 5
            r = pygame.Rect(442 + col * 80, 260 + row * 32, 74, 28)
            self.chapter_btns.append((ch_id, r))

        # 중앙 패널: 제한 시간 버튼 3개 (60초, 90초, 120초)
        self.duration_btns = []
        for idx, sec in enumerate(config.DUEL_DURATION_OPTIONS):
            r = pygame.Rect(442 + idx * 134, 362, 124, 40)
            self.duration_btns.append((sec, r))

        # 중앙 패널: 공정 기구 레벨 버튼 4개 (Lv.0 ~ Lv.3)
        self.level_btns = []
        for idx, lvl in enumerate((0, 1, 2, 3)):
            r = pygame.Rect(442 + idx * 100, 454, 92, 40)
            self.level_btns.append((lvl, r))

    def on_enter(self, **kwargs: Any) -> None:
        self.net.room_meta["in_game"] = False
        self.countdown_active = False
        self.countdown_timer = 0.0

        # 재대결(Rematch)로 돌아온 경우 기존 연결 유지
        if kwargs.get("rematch") and self.net.connected:
            self.client_ready = False
            if self.net.role == "HOST":
                self._sync_lobby_from_host()
            else:
                self.net.send(
                    {
                        "type": "CLIENT_UPDATE",
                        "client_name": self.client_name,
                        "client_char": self.client_char,
                        "client_ready": self.client_ready,
                    }
                )
            return

        # 명령줄 --duel-client 또는 auto_join_ip 인자로 진입한 경우 즉시 접속 시도
        auto_join_ip = kwargs.get("auto_join_ip")
        if auto_join_ip:
            self.ip_input = f"{auto_join_ip}:{config.DEFAULT_DUEL_PORT}"
            self._start_client_connect(self.ip_input)
        elif not self.net.connected and not self.net.hosting:
            self.net.trigger_lan_scan()

    def _start_host_room(self) -> bool:
        ok = self.net.start_host(config.DEFAULT_DUEL_PORT)
        if ok:
            sound_fx.play_cash()
            self.client_ready = False
            self._update_host_room_meta()
            self.particles.spawn_floating_text(
                f"결투 방 개설 완료! (포트 {self.net.tcp_port})",
                config.SCREEN_WIDTH // 2,
                110,
                color=config.TEXT_SUCCESS,
                size=22,
            )
        else:
            sound_fx.play_burn()
        return ok

    def _start_client_connect(self, target_ip_port: str) -> None:
        sound_fx.play_click()
        host_ip = target_ip_port.strip() or "127.0.0.1"
        port = config.DEFAULT_DUEL_PORT
        if ":" in host_ip:
            ip_part, port_part = host_ip.rsplit(":", 1)
            host_ip = ip_part.strip() or "127.0.0.1"
            try:
                port = int(port_part.strip())
            except ValueError:
                port = config.DEFAULT_DUEL_PORT
        self.net.connect_to_host(host_ip, port)

    def _spawn_second_client_window(self) -> None:
        """같은 PC에서 1:1 대전을 즉시 테스트할 수 있도록 두 번째 클라이언트 창을 서브프로세스로 띄운다."""
        if not self.net.hosting:
            if not self._start_host_room():
                return
        sound_fx.play_skill()
        target_arg = f"127.0.0.1:{self.net.tcp_port}"
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--duel-client", target_arg]
        else:
            main_script = os.path.join(config.BASE_DIR, "main.py")
            cmd = [sys.executable, main_script, "--duel-client", target_arg]
        try:
            subprocess.Popen(cmd, cwd=config.BASE_DIR)
            self.particles.spawn_floating_text(
                "2P 도전자 창을 실행했습니다! 잠시 후 자동 연결됩니다.",
                config.SCREEN_WIDTH // 2,
                110,
                color=config.NEON_CYAN,
                size=21,
            )
        except Exception as exc:
            self.particles.spawn_floating_text(
                f"2P 창 실행 실패: {exc}",
                config.SCREEN_WIDTH // 2,
                110,
                color=config.TEXT_WARNING,
                size=18,
            )

    def _update_host_room_meta(self) -> None:
        self.net.room_meta.update(
            {
                "host_name": self.host_name,
                "host_char": self.host_char,
                "chapter": self.selected_chapter,
                "duration": self.match_duration,
                "station_level": self.station_level,
                "in_game": False,
            }
        )

    def _sync_lobby_from_host(self) -> None:
        self._update_host_room_meta()
        if self.net.role == "HOST" and self.net.connected:
            self.net.send(
                {
                    "type": "LOBBY_SYNC",
                    "host_name": self.host_name,
                    "host_char": self.host_char,
                    "client_name": self.client_name,
                    "client_char": self.client_char,
                    "chapter": self.selected_chapter,
                    "duration": self.match_duration,
                    "station_level": self.station_level,
                    "client_ready": self.client_ready,
                }
            )

    def _trigger_match_countdown(self) -> None:
        if self.net.role != "HOST" or not self.net.connected:
            return
        self.match_seed = random.randint(100000, 999999)
        self.countdown_active = True
        self.countdown_timer = 3.0
        self._last_countdown_int = 3
        sound_fx.play_ready()
        self.net.send(
            {
                "type": "MATCH_COUNTDOWN",
                "seed": self.match_seed,
                "chapter": self.selected_chapter,
                "duration": self.match_duration,
                "station_level": self.station_level,
                "host_char": self.host_char,
                "client_char": self.client_char,
                "host_name": self.host_name,
                "client_name": self.client_name,
            }
        )

    def _launch_duel_play(self) -> None:
        self.net.room_meta["in_game"] = True
        is_host = self.net.role == "HOST"
        my_char = self.host_char if is_host else self.client_char
        opp_char = self.client_char if is_host else self.host_char
        my_name = self.host_name if is_host else self.client_name
        opp_name = self.client_name if is_host else self.host_name

        if self.scene_mgr:
            self.scene_mgr.change_scene(
                "duel_play",
                chapter=self.selected_chapter,
                day_duration=float(self.match_duration),
                station_level=self.station_level,
                my_char=my_char,
                opp_char=opp_char,
                my_name=my_name,
                opp_name=opp_name,
                match_seed=self.match_seed,
            )

    # ==========================================================================
    # 이벤트 처리
    # ==========================================================================
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # 상단 뒤로가기 버튼
            if self.back_btn_rect.collidepoint(mx, my):
                sound_fx.play_click()
                self.net.close()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title")
                return

            # 상단 옵션 버튼
            if self.options_btn_rect.collidepoint(mx, my):
                if self.scene_mgr:
                    self.scene_mgr.open_options()
                return

            in_waiting_room = self.net.hosting or self.net.connected or self.net.connecting
            if not in_waiting_room:
                self._handle_setup_click(mx, my)
            else:
                self._handle_waiting_room_click(mx, my)

        elif event.type == pygame.KEYDOWN:
            in_waiting_room = self.net.hosting or self.net.connected or self.net.connecting
            if not in_waiting_room and self.ip_focused:
                if event.key == pygame.K_RETURN:
                    self._start_client_connect(self.ip_input)
                elif event.key == pygame.K_BACKSPACE:
                    self.ip_input = self.ip_input[:-1]
                elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                    try:
                        if not pygame.scrap.get_init():
                            pygame.scrap.init()
                        clip = pygame.scrap.get(pygame.SCRAP_TEXT)
                        if clip:
                            txt = clip.decode("utf-8", errors="ignore").strip("\x00").strip()
                            self.ip_input += txt
                    except Exception:
                        pass
                else:
                    ch = event.unicode
                    if ch and ch in "0123456789.:localhostABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
                        if len(self.ip_input) < 28:
                            self.ip_input += ch
                return

            if event.key == pygame.K_ESCAPE:
                sound_fx.play_click()
                self.net.close()
                if self.scene_mgr:
                    self.scene_mgr.change_scene("title")
                return

            if in_waiting_room and not self.countdown_active and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._trigger_primary_room_action()

    def _handle_setup_click(self, mx: int, my: int) -> None:
        self.ip_focused = self.ip_box_rect.collidepoint(mx, my)

        # 1) 호스트 방 만들기
        if self.host_create_btn.collidepoint(mx, my):
            self._start_host_room()
            return

        # 2) 한 PC에서 호스트 개설 + 2P 테스트 창 동시 실행
        if self.local_dual_btn.collidepoint(mx, my):
            self._spawn_second_client_window()
            return

        # 3) 로컬(127.0.0.1) 원클릭 참가
        if self.local_join_btn.collidepoint(mx, my):
            self.ip_input = f"127.0.0.1:{config.DEFAULT_DUEL_PORT}"
            self._start_client_connect(self.ip_input)
            return

        # 4) IP 직접 접속 버튼
        if self.ip_connect_btn.collidepoint(mx, my):
            self._start_client_connect(self.ip_input)
            return

        # 5) LAN 방 새로고침
        if self.refresh_lan_btn.collidepoint(mx, my):
            sound_fx.play_click()
            self.net.trigger_lan_scan()
            return

        # 6) 탐색된 LAN 방 클릭 참가
        for room_info, r_rect in self.lan_room_rects:
            if r_rect.collidepoint(mx, my):
                target_key = str(room_info.get("key", f"127.0.0.1:{config.DEFAULT_DUEL_PORT}"))
                self.ip_input = target_key
                self._start_client_connect(target_key)
                return

    def _handle_waiting_room_click(self, mx: int, my: int) -> None:
        if self.leave_room_btn.collidepoint(mx, my):
            sound_fx.play_click()
            self.net.close()
            self.countdown_active = False
            return

        if self.net.role == "HOST" and not self.net.connected and self.spawn_2p_btn_rect.collidepoint(mx, my):
            self._spawn_second_client_window()
            return

        if self.countdown_active:
            return

        # 1P (호스트) 캐릭터 선택 및 32인 페이지 전환
        if self.net.role == "HOST":
            total_pages = max(1, (len(CHARACTER_ORDER) + 3) // 4)
            if self.host_prev_page_btn.collidepoint(mx, my):
                sound_fx.play_click()
                self.host_char_page = (self.host_char_page - 1) % total_pages
                self._build_waiting_room_rects()
                return
            if self.host_next_page_btn.collidepoint(mx, my):
                sound_fx.play_click()
                self.host_char_page = (self.host_char_page + 1) % total_pages
                self._build_waiting_room_rects()
                return
            for cid, r in self.host_char_btns:
                if r.collidepoint(mx, my):
                    sound_fx.play_click()
                    self.host_char = cid
                    self._sync_lobby_from_host()
                    return

            # 챕터 변경
            for ch_id, r in self.chapter_btns:
                if r.collidepoint(mx, my):
                    sound_fx.play_click()
                    self.selected_chapter = ch_id
                    self._sync_lobby_from_host()
                    return

            # 제한 시간 변경
            for sec, r in self.duration_btns:
                if r.collidepoint(mx, my):
                    sound_fx.play_click()
                    self.match_duration = sec
                    self._sync_lobby_from_host()
                    return

            # 기구 레벨 변경
            for lvl, r in self.level_btns:
                if r.collidepoint(mx, my):
                    sound_fx.play_click()
                    self.station_level = lvl
                    self._sync_lobby_from_host()
                    return

        # 2P (클라이언트) 캐릭터 선택 및 32인 페이지 전환
        elif self.net.role == "CLIENT":
            total_pages = max(1, (len(CHARACTER_ORDER) + 3) // 4)
            if self.client_prev_page_btn.collidepoint(mx, my):
                sound_fx.play_click()
                self.client_char_page = (self.client_char_page - 1) % total_pages
                self._build_waiting_room_rects()
                return
            if self.client_next_page_btn.collidepoint(mx, my):
                sound_fx.play_click()
                self.client_char_page = (self.client_char_page + 1) % total_pages
                self._build_waiting_room_rects()
                return
            for cid, r in self.client_char_btns:
                if r.collidepoint(mx, my):
                    sound_fx.play_click()
                    self.client_char = cid
                    self.net.send(
                        {
                            "type": "CLIENT_UPDATE",
                            "client_name": self.client_name,
                            "client_char": self.client_char,
                            "client_ready": self.client_ready,
                        }
                    )
                    return

        # 하단 중앙 [결투 시작!] 또는 [준비 완료!] 버튼
        if self.ready_or_start_btn.collidepoint(mx, my):
            self._trigger_primary_room_action()

    def _trigger_primary_room_action(self) -> None:
        if self.net.role == "HOST":
            if not self.net.connected:
                sound_fx.play_burn()
                self.particles.spawn_floating_text(
                    "아직 도전자가 입장하지 않았습니다! (우측 상단 2P 테스트 창 버튼을 눌러보세요)",
                    config.SCREEN_WIDTH // 2,
                    595,
                    color=config.TEXT_WARNING,
                    size=18,
                )
                return
            self._trigger_match_countdown()
        elif self.net.role == "CLIENT" and self.net.connected:
            sound_fx.play_ready()
            self.client_ready = not self.client_ready
            self.net.send(
                {
                    "type": "CLIENT_UPDATE",
                    "client_name": self.client_name,
                    "client_char": self.client_char,
                    "client_ready": self.client_ready,
                }
            )

    # ==========================================================================
    # 업데이트 및 네트워크 메시지 폴링
    # ==========================================================================
    def update(self, dt: float) -> None:
        self.time_tick += dt
        self.particles.update(dt)

        # 미연결 상태에서는 주기적으로 LAN 방 자동 스캔
        if not self.net.hosting and not self.net.connected and not self.net.connecting:
            self.scan_timer -= dt
            if self.scan_timer <= 0.0:
                self.scan_timer = 1.8
                self.net.trigger_lan_scan()
        else:
            self.net.send_ping_if_needed(interval=1.5)

        # 네트워크 수신 메시지 처리
        for msg in self.net.poll_messages():
            mtype = msg.get("type")
            if mtype == "NET_CONNECTED":
                sound_fx.play_fanfare()
                self.client_ready = True
                if self.net.role == "HOST":
                    self._sync_lobby_from_host()
                else:
                    self.net.send(
                        {
                            "type": "CLIENT_UPDATE",
                            "client_name": self.client_name,
                            "client_char": self.client_char,
                            "client_ready": True,
                        }
                    )
                self.particles.spawn_floating_text(
                    "상대 포차 마스터와 연결되었습니다!",
                    config.SCREEN_WIDTH // 2,
                    115,
                    color=config.NEON_GREEN,
                    size=22,
                )

            elif mtype == "NET_DISCONNECTED":
                sound_fx.play_burn()
                self.countdown_active = False
                self.client_ready = False
                self.particles.spawn_floating_text(
                    "상대방과의 연결이 종료되었습니다.",
                    config.SCREEN_WIDTH // 2,
                    115,
                    color=config.TEXT_WARNING,
                    size=20,
                )

            elif mtype == "CLIENT_UPDATE" and self.net.role == "HOST":
                self.client_name = str(msg.get("client_name", self.client_name))
                c_char = str(msg.get("client_char", self.client_char))
                if c_char in CHARACTERS:
                    self.client_char = c_char
                self.client_ready = bool(msg.get("client_ready", True))
                self._sync_lobby_from_host()

            elif mtype == "LOBBY_SYNC" and self.net.role == "CLIENT":
                self.host_name = str(msg.get("host_name", self.host_name))
                h_char = str(msg.get("host_char", self.host_char))
                if h_char in CHARACTERS:
                    self.host_char = h_char
                ch = str(msg.get("chapter", self.selected_chapter)).upper()
                if ch in CHAPTERS:
                    self.selected_chapter = ch
                self.match_duration = int(msg.get("duration", self.match_duration))
                self.station_level = int(msg.get("station_level", self.station_level))
                self.client_ready = bool(msg.get("client_ready", self.client_ready))

            elif mtype == "MATCH_COUNTDOWN" and self.net.role == "CLIENT":
                self.match_seed = int(msg.get("seed", 123456))
                self.selected_chapter = str(msg.get("chapter", self.selected_chapter))
                self.match_duration = int(msg.get("duration", self.match_duration))
                self.station_level = int(msg.get("station_level", self.station_level))
                self.host_char = str(msg.get("host_char", self.host_char))
                self.client_char = str(msg.get("client_char", self.client_char))
                self.countdown_active = True
                self.countdown_timer = 3.0
                self._last_countdown_int = 3
                sound_fx.play_ready()

        # 카운트다운 진행
        if self.countdown_active:
            self.countdown_timer -= dt
            cur_int = int(math.ceil(max(0.0, self.countdown_timer)))
            if cur_int != self._last_countdown_int and cur_int > 0:
                self._last_countdown_int = cur_int
                sound_fx.play_ready()
            if self.countdown_timer <= 0.0:
                self.countdown_active = False
                self._launch_duel_play()

    # ==========================================================================
    # 화면 렌더링
    # ==========================================================================
    def draw(self, surface: pygame.Surface) -> None:
        bg_rect = pygame.Rect(0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        art_renderer.draw_country_background(
            surface,
            bg_rect,
            country_id=self.selected_chapter,
            interior_levels={"lighting": 1, "signboard": 1, "prop": 1, "seating": 1},
            time_tick=self.time_tick,
        )

        art_renderer.draw_alpha_overlay(surface, bg_rect, (14, 12, 26, 185))

        self._draw_top_bar(surface)

        in_waiting_room = self.net.hosting or self.net.connected or self.net.connecting
        if not in_waiting_room:
            self._draw_setup_panels(surface)
        else:
            self._draw_waiting_room(surface)

        if self.countdown_active:
            self._draw_countdown_overlay(surface)

        self.particles.draw(surface)

    def _draw_top_bar(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos
        b_hov = self.back_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if b_hov else config.UI_PANEL,
            self.back_btn_rect,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.GOLD if b_hov else config.UI_BORDER, self.back_btn_rect, width=2, border_radius=10)
        bf = config.get_font(15, bold=True)
        bt = bf.render("◀ 타이틀로 이동", True, config.WHITE)
        surface.blit(bt, (self.back_btn_rect.centerx - bt.get_width() // 2, self.back_btn_rect.centery - bt.get_height() // 2))

        title_f = config.get_font(28, bold=True)
        sub_f = config.get_font(14, bold=True)
        t_surf = title_f.render("⚔ 1:1 네트워크 포차 결투 모드 (ONLINE / LAN DUEL)", True, config.GOLD)
        surface.blit(t_surf, (230, 18))

        status_col = config.TEXT_SUCCESS if self.net.connected else (config.NEON_CYAN if self.net.hosting else config.TEXT_SECONDARY)
        ping_str = f"  ·  PING {self.net.latency_ms}ms" if self.net.connected and self.net.latency_ms > 0 else ""
        s_surf = sub_f.render(f"📡 상태: {self.net.status_text}{ping_str}", True, status_col)
        surface.blit(s_surf, (232, 54))

        # 우측 상단 옵션 버튼
        o_hov = self.options_btn_rect.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if o_hov else config.UI_PANEL,
            self.options_btn_rect,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.GOLD if o_hov else config.UI_BORDER, self.options_btn_rect, width=2, border_radius=10)
        ot = bf.render("⚙️ 옵션", True, config.GOLD if o_hov else config.WHITE)
        surface.blit(ot, ot.get_rect(center=self.options_btn_rect.center))

        # 호스트 대기 중일 때 우측 상단에 [2P 테스트 창 바로 띄우기] 버튼 노출
        if self.net.role == "HOST" and not self.net.connected:
            sp_hov = self.spawn_2p_btn_rect.collidepoint(mx, my)
            pygame.draw.rect(
                surface,
                config.NEON_CYAN if sp_hov else (36, 98, 128),
                self.spawn_2p_btn_rect,
                border_radius=10,
            )
            pygame.draw.rect(surface, config.WHITE, self.spawn_2p_btn_rect, width=2, border_radius=10)
            spt = bf.render("🖥️ 한 PC에서 2P 테스트 창 바로 띄우기", True, (16, 14, 24) if sp_hov else config.WHITE)
            surface.blit(
                spt,
                (
                    self.spawn_2p_btn_rect.centerx - spt.get_width() // 2,
                    self.spawn_2p_btn_rect.centery - spt.get_height() // 2,
                ),
            )

    def _draw_setup_panels(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos
        left_panel = pygame.Rect(40, 96, 575, 584)
        right_panel = pygame.Rect(665, 96, 575, 584)

        for p, border_c in ((left_panel, config.POCHA_ORANGE), (right_panel, config.NEON_CYAN)):
            pygame.draw.rect(surface, (28, 24, 44), p, border_radius=18)
            pygame.draw.rect(surface, border_c, p, width=2, border_radius=18)

        h_font = config.get_font(24, bold=True)
        sub_f = config.get_font(15, bold=False)
        bold_f = config.get_font(16, bold=True)
        btn_f = config.get_font(18, bold=True)

        # --- 좌측: 방 만들기 (HOST) & 원클릭 로컬 테스트 ---
        lh = h_font.render("🏮 방 만들기 (Host) & 빠른 로컬 대전", True, config.GOLD)
        surface.blit(lh, (left_panel.x + 28, left_panel.y + 24))

        ip_info = bold_f.render(
            f"내 PC 네트워크 주소: {self.net.local_ip}:{config.DEFAULT_DUEL_PORT}  (로컬: 127.0.0.1)",
            True,
            config.NEON_YELLOW,
        )
        surface.blit(ip_info, (left_panel.x + 28, left_panel.y + 68))

        desc1 = sub_f.render("• 방을 개설하면 같은 공유기(LAN) 또는 IP로 친구가 접속할 수 있습니다.", True, config.TEXT_SECONDARY)
        desc2 = sub_f.render("• 혼자서도 즉시 테스트하려면 아래 [한 PC에서 2창 바로 실행]을 클릭하세요!", True, config.TEXT_PRIMARY)
        surface.blit(desc1, (left_panel.x + 28, left_panel.y + 100))
        surface.blit(desc2, (left_panel.x + 28, left_panel.y + 124))

        host_btns = [
            (
                self.host_create_btn,
                "🔥 1:1 결투 방 만들기 (Host 서버 열기)",
                "내 PC에 대기실을 열고 도전자의 접속을 기다립니다",
                config.POCHA_ORANGE,
            ),
            (
                self.local_dual_btn,
                "🖥️ 한 PC에서 1P + 2P 두 창 바로 실행 (추천 테스트)",
                "호스트 방 개설과 동시에 2P 클라이언트 창을 자동으로 띄워 즉시 연결합니다",
                config.NEON_GREEN,
            ),
            (
                self.local_join_btn,
                "⚡ 로컬(127.0.0.1) 열린 방에 원클릭 즉시 참가",
                "이미 이 PC에 다른 창으로 열린 호스트 방이 있을 때 바로 접속합니다",
                config.NEON_CYAN,
            ),
        ]

        for rect, title_s, sub_s, col in host_btns:
            hov = rect.collidepoint(mx, my)
            bg = col if hov else (46, 40, 68)
            fg = (18, 14, 26) if hov else config.WHITE
            pygame.draw.rect(surface, bg, rect, border_radius=12)
            pygame.draw.rect(surface, config.WHITE if hov else col, rect, width=2, border_radius=12)
            t1 = btn_f.render(title_s, True, fg)
            t2 = config.get_font(13, bold=False).render(sub_s, True, (30, 26, 40) if hov else config.TEXT_SECONDARY)
            surface.blit(t1, (rect.centerx - t1.get_width() // 2, rect.y + 9))
            surface.blit(t2, (rect.centerx - t2.get_width() // 2, rect.bottom - 22))

        # 하단 규칙 요약 박스
        rule_box = pygame.Rect(left_panel.x + 28, 504, left_panel.width - 56, 152)
        pygame.draw.rect(surface, (20, 17, 32), rule_box, border_radius=12)
        pygame.draw.rect(surface, config.UI_BORDER, rule_box, width=1, border_radius=12)
        rt = bold_f.render("🏆 1:1 결투 모드 핵심 규칙 (공정 실력 타임어택)", True, config.GOLD)
        surface.blit(rt, (rule_box.x + 16, rule_box.y + 12))
        rules = [
            "1. 순수 실시간 매출 대결: 제한 시간 동안 더 높은 매출을 달성하면 승리!",
            "2. 100% 공정한 조건: 양측 동일 조리 기구 레벨 & 모든 마스터/국가 선택 가능!",
            "3. 동일 손님 시드(Seed): 양측에 동일한 손님 주문 흐름이 제공되어 실력으로 승부!",
            "4. 실시간 스코어보드: 상단 줄다리기 게이지로 상대와의 매출 격차를 실시간 확인!",
        ]
        rf = config.get_font(13, bold=False)
        for idx, line in enumerate(rules):
            rs = rf.render(line, True, config.TEXT_SECONDARY)
            surface.blit(rs, (rule_box.x + 16, rule_box.y + 42 + idx * 25))

        # --- 우측: 방 참가하기 (IP 직접 입력 & LAN 자동 탐색) ---
        rh = h_font.render("🌐 방 참가하기 (Client) — IP 접속 & LAN 탐색", True, config.NEON_CYAN)
        surface.blit(rh, (right_panel.x + 28, right_panel.y + 24))

        ip_lbl = bold_f.render("호스트 IP : 포트 직접 입력 (클릭 후 타이핑 / Ctrl+V 붙여넣기):", True, config.TEXT_PRIMARY)
        surface.blit(ip_lbl, (right_panel.x + 28, right_panel.y + 98))

        # IP 입력 텍스트박스
        pygame.draw.rect(surface, (18, 16, 28), self.ip_box_rect, border_radius=10)
        pygame.draw.rect(
            surface,
            config.NEON_YELLOW if self.ip_focused else config.UI_BORDER,
            self.ip_box_rect,
            width=2,
            border_radius=10,
        )
        cursor = "|" if (self.ip_focused and int(self.time_tick * 2) % 2 == 0) else ""
        ip_txt = btn_f.render(f"{self.ip_input}{cursor}", True, config.WHITE)
        surface.blit(ip_txt, (self.ip_box_rect.x + 14, self.ip_box_rect.centery - ip_txt.get_height() // 2))

        # 접속 버튼
        c_hov = self.ip_connect_btn.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.NEON_CYAN if c_hov else config.UI_BUTTON_ACTIVE,
            self.ip_connect_btn,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.WHITE, self.ip_connect_btn, width=2, border_radius=10)
        ct = btn_f.render("접속하기 ▶", True, (18, 16, 26) if c_hov else config.WHITE)
        surface.blit(ct, (self.ip_connect_btn.centerx - ct.get_width() // 2, self.ip_connect_btn.centery - ct.get_height() // 2))

        # LAN 자동 탐색 섹션 헤더
        lan_hdr = bold_f.render("📡 LAN / 로컬 열린 결투 방 목록 (자동 탐색):", True, config.GOLD)
        surface.blit(lan_hdr, (right_panel.x + 28, 316))

        ref_hov = self.refresh_lan_btn.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if ref_hov else config.UI_PANEL,
            self.refresh_lan_btn,
            border_radius=8,
        )
        pygame.draw.rect(surface, config.NEON_CYAN, self.refresh_lan_btn, width=1, border_radius=8)
        rt_surf = config.get_font(13, bold=True).render("🔄 새로고침", True, config.WHITE)
        surface.blit(
            rt_surf,
            (
                self.refresh_lan_btn.centerx - rt_surf.get_width() // 2,
                self.refresh_lan_btn.centery - rt_surf.get_height() // 2,
            ),
        )

        # LAN 방 리스트 박스
        list_box = pygame.Rect(right_panel.x + 28, 356, right_panel.width - 56, 296)
        pygame.draw.rect(surface, (20, 17, 32), list_box, border_radius=12)
        pygame.draw.rect(surface, config.UI_BORDER, list_box, width=1, border_radius=12)

        rooms = self.net.get_discovered_rooms()
        self.lan_room_rects = []
        if not rooms:
            empty_s = sub_f.render("현재 탐색된 열린 방이 없습니다.", True, config.TEXT_MUTED)
            tip_s = config.get_font(13, bold=False).render(
                "좌측에서 [방 만들기]를 누르거나 상대방이 방을 열면 여기에 자동으로 표시됩니다!",
                True,
                config.TEXT_SECONDARY,
            )
            surface.blit(empty_s, (list_box.centerx - empty_s.get_width() // 2, list_box.centery - 22))
            surface.blit(tip_s, (list_box.centerx - tip_s.get_width() // 2, list_box.centery + 8))
        else:
            for idx, rinfo in enumerate(rooms[:4]):
                item_rect = pygame.Rect(list_box.x + 12, list_box.y + 12 + idx * 68, list_box.width - 24, 60)
                self.lan_room_rects.append((rinfo, item_rect))
                ihov = item_rect.collidepoint(mx, my)
                pygame.draw.rect(
                    surface,
                    (52, 46, 82) if ihov else (34, 30, 52),
                    item_rect,
                    border_radius=10,
                )
                pygame.draw.rect(
                    surface,
                    config.NEON_CYAN if ihov else config.UI_BORDER,
                    item_rect,
                    width=2 if ihov else 1,
                    border_radius=10,
                )
                ch_code = str(rinfo.get("chapter", "KR"))
                dur = int(rinfo.get("duration", 90))
                lvl = int(rinfo.get("station_level", 2))
                hname = str(rinfo.get("host_name", "호스트"))
                key_addr = str(rinfo.get("key", "127.0.0.1:15432"))

                r_title = bold_f.render(f"🏮 {hname}의 결투장  [{ch_code} · {dur}초 · 기구 Lv.{lvl}]", True, config.WHITE)
                r_sub = config.get_font(13, bold=False).render(f"주소: {key_addr}  —  클릭하여 즉시 입장 ▶", True, config.NEON_CYAN)
                surface.blit(r_title, (item_rect.x + 16, item_rect.y + 8))
                surface.blit(r_sub, (item_rect.x + 16, item_rect.y + 34))

    def _draw_waiting_room(self, surface: pygame.Surface) -> None:
        mx, my = self._hover_pos

        # 1) 좌측 1P 호스트 카드
        left_card = pygame.Rect(40, 96, 360, 520)
        self._draw_player_slot_card(
            surface,
            rect=left_card,
            slot_title="👑 1P 호스트 (방장)",
            player_name=self.host_name,
            char_id=self.host_char,
            is_connected=True,
            is_ready=True,
            can_edit=(self.net.role == "HOST"),
            char_btns=self.host_char_btns,
            accent_color=config.POCHA_ORANGE,
        )

        # 2) 우측 2P 클라이언트 카드
        right_card = pygame.Rect(880, 96, 360, 520)
        self._draw_player_slot_card(
            surface,
            rect=right_card,
            slot_title="⚔ 2P 도전자 (클라이언트)",
            player_name=self.client_name if self.net.connected else "참가자 대기 중...",
            char_id=self.client_char,
            is_connected=self.net.connected,
            is_ready=self.client_ready and self.net.connected,
            can_edit=(self.net.role == "CLIENT"),
            char_btns=self.client_char_btns,
            accent_color=config.NEON_CYAN,
        )

        # 3) 중앙 결투 설정 패널
        center_card = pygame.Rect(420, 96, 440, 520)
        pygame.draw.rect(surface, (30, 26, 48), center_card, border_radius=18)
        pygame.draw.rect(surface, config.GOLD, center_card, width=2, border_radius=18)

        vs_font = config.get_font(30, bold=True)
        sec_font = config.get_font(15, bold=True)
        small_f = config.get_font(13, bold=False)

        vs_txt = vs_font.render("⚡ VS 결투 스테이지 설정 ⚡", True, config.GOLD)
        surface.blit(vs_txt, (center_card.centerx - vs_txt.get_width() // 2, center_card.y + 20))

        addr_str = f"방 주소: {self.net.local_ip}:{self.net.tcp_port}  (로컬: 127.0.0.1:{self.net.tcp_port})"
        addr_s = small_f.render(addr_str, True, config.NEON_YELLOW)
        surface.blit(addr_s, (center_card.centerx - addr_s.get_width() // 2, center_card.y + 62))

        is_host = self.net.role == "HOST"
        role_hint = "방장(1P)이 스테이지와 규칙을 선택합니다" if is_host else "방장(1P)의 설정이 실시간으로 동기화됩니다"
        rh_s = small_f.render(role_hint, True, config.TEXT_SECONDARY)
        surface.blit(rh_s, (center_card.centerx - rh_s.get_width() // 2, center_card.y + 84))

        # (A) 결투 야시장 국가 선택
        ch_name = CHAPTERS.get(self.selected_chapter, CHAPTERS["KR"])["name"]
        l1 = sec_font.render(f"🗺️ 결투 야시장 챕터: {ch_name}", True, config.WHITE)
        surface.blit(l1, (center_card.x + 24, 238))
        for ch_id, r in self.chapter_btns:
            sel = self.selected_chapter == ch_id
            hov = is_host and r.collidepoint(mx, my)
            bg = config.POCHA_ORANGE if sel else (config.UI_BUTTON_HOVER if hov else config.UI_PANEL)
            pygame.draw.rect(surface, bg, r, border_radius=8)
            pygame.draw.rect(surface, config.GOLD if sel else config.UI_BORDER, r, width=2 if sel else 1, border_radius=8)
            t = sec_font.render(ch_id, True, config.WHITE)
            surface.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

        # (B) 영업 제한 시간 선택
        l2 = sec_font.render(f"⏱️ 결투 제한 시간: {self.match_duration}초 타임어택", True, config.WHITE)
        surface.blit(l2, (center_card.x + 24, 332))
        for sec, r in self.duration_btns:
            sel = self.match_duration == sec
            hov = is_host and r.collidepoint(mx, my)
            bg = config.NEON_CYAN if sel else (config.UI_BUTTON_HOVER if hov else config.UI_PANEL)
            fg = (18, 16, 26) if sel else config.WHITE
            pygame.draw.rect(surface, bg, r, border_radius=8)
            pygame.draw.rect(surface, config.WHITE if sel else config.UI_BORDER, r, width=2 if sel else 1, border_radius=8)
            t = sec_font.render(f"{sec}초", True, fg)
            surface.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

        # (C) 공정 기구 강화 레벨 선택
        lvl_names = {0: "Lv.0 기본", 1: "Lv.1 숙련", 2: "Lv.2 상급", 3: "Lv.3 풀강"}
        l3 = sec_font.render(f"🛠️ 공정 조리 기구 레벨: {lvl_names.get(self.station_level, 'Lv.2')}", True, config.WHITE)
        surface.blit(l3, (center_card.x + 24, 424))
        for lvl, r in self.level_btns:
            sel = self.station_level == lvl
            hov = is_host and r.collidepoint(mx, my)
            bg = config.NEON_GREEN if sel else (config.UI_BUTTON_HOVER if hov else config.UI_PANEL)
            fg = (18, 16, 26) if sel else config.WHITE
            pygame.draw.rect(surface, bg, r, border_radius=8)
            pygame.draw.rect(surface, config.WHITE if sel else config.UI_BORDER, r, width=2 if sel else 1, border_radius=8)
            t = config.get_font(13, bold=True).render(lvl_names[lvl], True, fg)
            surface.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

        # 공정 대결 안내 박스
        fair_box = pygame.Rect(center_card.x + 22, 514, center_card.width - 44, 82)
        pygame.draw.rect(surface, (20, 18, 34), fair_box, border_radius=10)
        pygame.draw.rect(surface, config.UI_BORDER, fair_box, width=1, border_radius=10)
        f1 = small_f.render("• 양측 동일한 기구 레벨 & 동일한 손님 주문 시드(Seed) 적용!", True, config.GOLD)
        f2 = small_f.render("• 싱글플레이 세이브 데이터(보유 골드)에 영향을 주지 않습니다.", True, config.TEXT_SECONDARY)
        f3 = small_f.render("• 제한 시간 동안 달성한 총 매출액이 높은 플레이어가 승리!", True, config.TEXT_PRIMARY)
        surface.blit(f1, (fair_box.x + 12, fair_box.y + 8))
        surface.blit(f2, (fair_box.x + 12, fair_box.y + 32))
        surface.blit(f3, (fair_box.x + 12, fair_box.y + 54))

        # 4) 하단 방 나가기 & 시작/준비 버튼
        lv_hov = self.leave_room_btn.collidepoint(mx, my)
        pygame.draw.rect(
            surface,
            config.UI_BUTTON_HOVER if lv_hov else config.UI_PANEL,
            self.leave_room_btn,
            border_radius=10,
        )
        pygame.draw.rect(surface, config.TEXT_WARNING, self.leave_room_btn, width=2, border_radius=10)
        lvt = sec_font.render("◀ 대기실 나가기", True, config.TEXT_WARNING)
        surface.blit(
            lvt,
            (
                self.leave_room_btn.centerx - lvt.get_width() // 2,
                self.leave_room_btn.centery - lvt.get_height() // 2,
            ),
        )

        act_hov = self.ready_or_start_btn.collidepoint(mx, my)
        if is_host:
            can_start = self.net.connected
            btn_col = (config.POCHA_ORANGE if act_hov else (218, 86, 36)) if can_start else config.UI_DISABLED
            btn_label = "🔥 1:1 결투 시작하기! [SPACE / ENTER]" if can_start else "⏳ 도전자 입장 대기 중..."
        else:
            btn_col = config.TEXT_SUCCESS if self.client_ready else config.NEON_CYAN
            btn_label = "★ 준비 완료 상태! (클릭 시 해제) [SPACE]" if self.client_ready else "⚡ 준비 완료하기! [SPACE]"

        pygame.draw.rect(surface, btn_col, self.ready_or_start_btn, border_radius=14)
        pygame.draw.rect(surface, config.GOLD if act_hov else config.WHITE, self.ready_or_start_btn, width=2, border_radius=14)
        act_f = config.get_font(20, bold=True)
        act_s = act_f.render(btn_label, True, config.WHITE)
        surface.blit(
            act_s,
            (
                self.ready_or_start_btn.centerx - act_s.get_width() // 2,
                self.ready_or_start_btn.centery - act_s.get_height() // 2,
            ),
        )

    def _draw_player_slot_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        slot_title: str,
        player_name: str,
        char_id: str,
        is_connected: bool,
        is_ready: bool,
        can_edit: bool,
        char_btns: List[Tuple[str, pygame.Rect]],
        accent_color: Tuple[int, int, int],
    ) -> None:
        mx, my = self._hover_pos
        pygame.draw.rect(surface, (30, 26, 48), rect, border_radius=18)
        pygame.draw.rect(surface, accent_color if is_connected else config.UI_BORDER, rect, width=2, border_radius=18)

        hdr_f = config.get_font(18, bold=True)
        name_f = config.get_font(21, bold=True)
        small_f = config.get_font(13, bold=False)
        bold_s = config.get_font(13, bold=True)

        h_surf = hdr_f.render(slot_title, True, accent_color)
        surface.blit(h_surf, (rect.centerx - h_surf.get_width() // 2, rect.y + 16))

        if not is_connected:
            wait_f = config.get_font(18, bold=True)
            w1 = wait_f.render("⏳ 도전자 접속 대기 중...", True, config.TEXT_SECONDARY)
            w2 = small_f.render("상대방이 IP 또는 LAN 목록에서 참가하거나", True, config.TEXT_MUTED)
            w3 = small_f.render("상단 [2P 테스트 창 띄우기]를 눌러보세요!", True, config.NEON_CYAN)
            surface.blit(w1, (rect.centerx - w1.get_width() // 2, rect.centery - 30))
            surface.blit(w2, (rect.centerx - w2.get_width() // 2, rect.centery + 8))
            surface.blit(w3, (rect.centerx - w3.get_width() // 2, rect.centery + 32))
            return

        char_data = CHARACTERS.get(char_id, CHARACTERS["chef_kr"])
        av_rect = pygame.Rect(rect.centerx - 54, rect.y + 52, 108, 108)
        art_renderer.draw_chef_avatar(
            surface,
            av_rect,
            character_id=char_id,
            state="COOKING" if is_ready else "IDLE",
            time_tick=self.time_tick,
        )

        # 준비 상태 배지
        badge_rect = pygame.Rect(rect.right - 98, rect.y + 16, 82, 24)
        pygame.draw.rect(
            surface,
            config.TEXT_SUCCESS if is_ready else config.UI_PANEL_LIGHT,
            badge_rect,
            border_radius=12,
        )
        b_txt = bold_s.render("READY ★" if is_ready else "대기 중", True, (16, 20, 16) if is_ready else config.TEXT_SECONDARY)
        surface.blit(b_txt, (badge_rect.centerx - b_txt.get_width() // 2, badge_rect.centery - b_txt.get_height() // 2))

        p_surf = name_f.render(f"{char_data['name']} ({char_data['country']})", True, config.WHITE)
        t_surf = bold_s.render(f"{player_name} · {char_data['title']}", True, config.GOLD)
        surface.blit(p_surf, (rect.centerx - p_surf.get_width() // 2, rect.y + 170))
        surface.blit(t_surf, (rect.centerx - t_surf.get_width() // 2, rect.y + 198))

        # 패시브 & 액티브 스킬 요약 박스
        info_box = pygame.Rect(rect.x + 18, rect.y + 228, rect.width - 36, 126)
        pygame.draw.rect(surface, (20, 18, 34), info_box, border_radius=10)
        pygame.draw.rect(surface, config.UI_BORDER, info_box, width=1, border_radius=10)

        pas_lbl = bold_s.render("◆ 고유 패시브:", True, config.NEON_CYAN)
        pas_val = small_f.render(str(char_data["passive_desc"])[:26], True, config.TEXT_PRIMARY)
        sk_lbl = bold_s.render(f"⚡ 액티브 스킬 [{char_data['skill_name']}]:", True, config.GOLD)
        sk_val = small_f.render(str(char_data["skill_desc"])[:26], True, config.TEXT_SECONDARY)

        surface.blit(pas_lbl, (info_box.x + 12, info_box.y + 10))
        surface.blit(pas_val, (info_box.x + 12, info_box.y + 32))
        surface.blit(sk_lbl, (info_box.x + 12, info_box.y + 64))
        surface.blit(sk_val, (info_box.x + 12, info_box.y + 86))

        # 하단 캐릭터 32인 변경 버튼 (페이지당 4명)
        sel_hdr = bold_s.render(
            "👨‍🍳 32인 마스터 선택:" if can_edit else "👨‍🍳 상대방 마스터:",
            True,
            config.TEXT_SECONDARY,
        )
        surface.blit(sel_hdr, (rect.x + 20, rect.y + 364))

        if can_edit:
            is_left = rect.x < 500
            p_btn = self.host_prev_page_btn if is_left else self.client_prev_page_btn
            n_btn = self.host_next_page_btn if is_left else self.client_next_page_btn
            cur_pg = self.host_char_page if is_left else self.client_char_page
            tot_pg = max(1, (len(CHARACTER_ORDER) + 3) // 4)
            for b_r, b_lbl in ((p_btn, "◀"), (n_btn, "▶")):
                pygame.draw.rect(surface, (52, 46, 78), b_r, border_radius=6)
                pygame.draw.rect(surface, accent_color, b_r, width=1, border_radius=6)
                bs = bold_s.render(b_lbl, True, config.WHITE)
                surface.blit(bs, bs.get_rect(center=b_r.center))
            pg_s = small_f.render(f"{cur_pg + 1}/{tot_pg}", True, config.GOLD)
            surface.blit(pg_s, pg_s.get_rect(center=((p_btn.right + n_btn.left) // 2, p_btn.centery)))

        for cid, btn_r in char_btns:
            cdata = CHARACTERS[cid]
            is_sel = cid == char_id
            is_hov = can_edit and btn_r.collidepoint(mx, my)
            bg = accent_color if is_sel else (config.UI_BUTTON_HOVER if is_hov else config.UI_PANEL)
            fg = (18, 14, 24) if is_sel else (config.WHITE if can_edit else config.TEXT_MUTED)
            pygame.draw.rect(surface, bg, btn_r, border_radius=8)
            pygame.draw.rect(
                surface,
                config.WHITE if is_sel else config.UI_BORDER,
                btn_r,
                width=2 if is_sel else 1,
                border_radius=8,
            )
            lbl = bold_s.render(f"[{cdata['country']}] {cdata['name']}", True, fg)
            surface.blit(lbl, (btn_r.centerx - lbl.get_width() // 2, btn_r.centery - lbl.get_height() // 2))

    def _draw_countdown_overlay(self, surface: pygame.Surface) -> None:
        art_renderer.draw_alpha_overlay(
            surface,
            (0, 0, config.SCREEN_WIDTH, config.SCREEN_HEIGHT),
            (10, 8, 20, 190),
        )

        sec = max(1, int(math.ceil(self.countdown_timer)))
        big_f = config.get_font(96, bold=True)
        sub_f = config.get_font(28, bold=True)

        msg = sub_f.render("🔥 잠시 후 1:1 포차 매출 결투가 시작됩니다! 🔥", True, config.GOLD)
        num = big_f.render(str(sec), True, config.NEON_CYAN)

        surface.blit(msg, (config.SCREEN_WIDTH // 2 - msg.get_width() // 2, 250))
        surface.blit(num, (config.SCREEN_WIDTH // 2 - num.get_width() // 2, 320))
