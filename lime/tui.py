import curses
import queue
import time
import uuid
from typing import Callable, Optional

from lime.art import ART_HEIGHT, ART_WIDTH, LIME_GRID, draw_lime
from lime.config import VERSION
from lime.message import Message
from lime.store import MessageStore

C_GREEN = 1
C_BROWN = 2
C_WHITE = 3
C_CYAN = 4
C_DIM = 5
C_RED = 6
C_YELLOW = 7


class LimeTUI:
    def __init__(
        self,
        name: str,
        tag: str,
        store: MessageStore,
        ui_queue: queue.Queue,
        send_cb: Callable,
        connect_cb: Callable[[str, int], None],
        dm_cb: Optional[Callable] = None,
    ):
        self.name = name
        self.tag = tag
        self.store = store
        self.ui_queue = ui_queue
        self.send_cb = send_cb
        self.connect_cb = connect_cb
        self.dm_cb = dm_cb

        self.input_buf = ""
        self.input_mode = False
        self.show_header = True
        self.mentions_only = False
        self.mention_count = 0
        self.peer_count = 0
        self.mining = False
        self.scroll_offset = 0
        self.status_msg = ""
        self.status_expire = 0.0
        self.relay_connected = False
        self.e2e_active = False

        self.current_board = "general"
        self.current_thread_id = ""
        self.current_thread_title = ""
        self.show_thread_list = False
        self.show_help = False
        self.show_dms = False
        self.dm_count_unread = 0
        self.first_run_tip = True

        self._tab_candidates: list[str] = []
        self._tab_index = -1
        self._tab_prefix = ""

    # ------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------

    def run(self, stdscr):
        self._scr = stdscr
        curses.curs_set(0)
        curses.halfdelay(2)
        stdscr.clear()
        self._setup_colors()

        while True:
            self._drain_events()
            self._draw()
            key = stdscr.getch()
            if key == curses.KEY_RESIZE:
                stdscr.clear()
                continue
            if key == -1:
                continue
            if self.input_mode:
                if self._key_input(key):
                    break
            else:
                if self._key_feed(key):
                    break

    # ------------------------------------------------------------------
    # Key handling — feed mode
    # ------------------------------------------------------------------

    def _key_feed(self, key) -> bool:
        if key in (ord("q"), ord("Q")):
            if self.current_thread_id:
                self.current_thread_id = ""
                self.current_thread_title = ""
                self.show_thread_list = False
                self.scroll_offset = 0
                return False
            if self.show_thread_list:
                self.show_thread_list = False
                self.scroll_offset = 0
                return False
            return True

        if key == 27:  # Esc
            if self.current_thread_id:
                self.current_thread_id = ""
                self.current_thread_title = ""
                self.show_thread_list = False
                self.scroll_offset = 0
                return False
            if self.show_thread_list:
                self.show_thread_list = False
                self.scroll_offset = 0
                return False
            return True

        if key in (ord("i"), 10):
            self.input_mode = True
            curses.curs_set(1)
            self.first_run_tip = False
        elif key == ord("?"):
            self.show_help = not self.show_help
            self.scroll_offset = 0
        elif key == ord("d"):
            self.show_dms = not self.show_dms
            if self.show_dms:
                self.dm_count_unread = 0
            self.scroll_offset = 0
        elif key == ord("n"):
            self.mentions_only = not self.mentions_only
            self.scroll_offset = 0
        elif key == ord("h"):
            self.show_header = not self.show_header
        elif key == ord("t"):
            if not self.current_thread_id:
                self.show_thread_list = not self.show_thread_list
                self.scroll_offset = 0
        elif key == curses.KEY_UP:
            self.scroll_offset += 1
        elif key == curses.KEY_DOWN:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif self.show_thread_list and ord("1") <= key <= ord("9"):
            self._enter_thread_by_number(key - ord("0"))
        elif key in (curses.KEY_BACKSPACE, 8):
            if self.current_thread_id:
                self.current_thread_id = ""
                self.current_thread_title = ""
                self.show_thread_list = False
                self.scroll_offset = 0
        return False

    def _enter_thread_by_number(self, num: int):
        threads = self.store.get_threads(self.current_board)
        if num < 1 or num > len(threads):
            self._flash(f"thread #{num} not found")
            return
        t = threads[num - 1]
        self.current_thread_id = t["thread_id"]
        self.current_thread_title = t["title"]
        self.show_thread_list = False
        self.scroll_offset = 0

    # ------------------------------------------------------------------
    # Key handling — input mode
    # ------------------------------------------------------------------

    _COMPLETIONS = [
        "/t ", "/b ", "/boards", "/threads", "/back",
        "/reply ", "/connect ", "/dm ", "/file ", "/save ",
        "/help", "@",
    ]

    def _key_input(self, key) -> bool:
        if key == 27:
            self._cancel_input()
            return False
        if key == 10:
            self._tab_reset()
            self._submit_input()
            return False
        if key in (curses.KEY_BACKSPACE, 127, 8):
            self.input_buf = self.input_buf[:-1]
            self._tab_reset()
            return False
        if key == 3:
            self._cancel_input()
            return False
        if key == 9:  # Tab
            self._tab_complete()
            return False
        if 32 <= key <= 126:
            self.input_buf += chr(key)
            self._tab_reset()
        return False

    def _tab_complete(self):
        buf = self.input_buf

        if self._tab_candidates:
            self._tab_index = (self._tab_index + 1) % len(self._tab_candidates)
            self.input_buf = self._tab_candidates[self._tab_index]
            return

        prefix = buf
        if prefix.startswith("@"):
            self._tab_complete_mention(prefix)
            return

        matches = [c for c in self._COMPLETIONS if c.startswith(prefix)]
        if not matches:
            return
        self._tab_prefix = prefix
        self._tab_candidates = matches
        self._tab_index = 0
        self.input_buf = matches[0]

    def _tab_complete_mention(self, prefix: str):
        partial = prefix[1:].lower()
        msgs = self.store.get_all()
        seen: set[str] = set()
        names: list[str] = []
        for m in msgs:
            author = m.display_author
            if author not in seen:
                seen.add(author)
                if not partial or author.lower().startswith(partial):
                    names.append(f"@{author} ")
        if not names:
            return
        self._tab_prefix = prefix
        self._tab_candidates = names
        self._tab_index = 0
        self.input_buf = names[0]

    def _tab_reset(self):
        self._tab_candidates = []
        self._tab_index = -1
        self._tab_prefix = ""

    def _submit_input(self):
        text = self.input_buf.strip()
        self.input_buf = ""
        self.input_mode = False
        curses.curs_set(0)
        if not text:
            return

        # /connect
        if text.startswith("/connect "):
            addr = text[9:].strip()
            if ":" in addr:
                host, port_s = addr.rsplit(":", 1)
                try:
                    self.connect_cb(host, int(port_s))
                    self._flash(f"connecting to {addr}...")
                except ValueError:
                    self._flash("bad port")
            return

        # /b [board] — switch board
        if text.startswith("/b "):
            board_name = text[3:].strip().lower().replace("/", "")
            if not board_name:
                self._flash("usage: /b [board]")
                return
            self.current_board = board_name
            self.current_thread_id = ""
            self.current_thread_title = ""
            self.show_thread_list = False
            self.scroll_offset = 0
            self._flash(f"switched to /{board_name}/")
            return

        # /boards — list boards
        if text == "/boards":
            boards = self.store.get_boards()
            self._flash("boards: " + " ".join(f"/{b}/" for b in boards))
            return

        # /t [title] — create a new thread
        if text.startswith("/t "):
            title = text[3:].strip()
            if not title:
                self._flash("usage: /t [title]")
                return
            tid = f"t_{uuid.uuid4().hex[:6]}"
            self.send_cb(title, "text", self.current_board, tid, title, "")
            self.current_thread_id = tid
            self.current_thread_title = title
            self.show_thread_list = False
            self.scroll_offset = 0
            self.mining = True
            return

        # /threads — list threads
        if text == "/threads":
            self.show_thread_list = True
            self.scroll_offset = 0
            return

        # /dm @name message — send a DM
        if text.startswith("/dm "):
            parts = text[4:].strip().split(" ", 1)
            if len(parts) < 2:
                self._flash("usage: /dm @name message")
                return
            target = parts[0].lstrip("@")
            message = parts[1]
            if self.dm_cb:
                self.dm_cb(message, target)
                self._flash(f"dm sent to {target}")
            else:
                self._flash("DMs not available")
            return

        # /help — show help overlay
        if text == "/help":
            self.show_help = True
            self.scroll_offset = 0
            return

        # /back — return to board chat
        if text == "/back":
            self.current_thread_id = ""
            self.current_thread_title = ""
            self.show_thread_list = False
            self.show_help = False
            self.show_dms = False
            self.scroll_offset = 0
            return

        # /reply [#] [message] — post into a thread by number
        if text.startswith("/reply "):
            parts = text[7:].strip().split(" ", 1)
            if len(parts) < 2:
                self._flash("usage: /reply [#] [message]")
                return
            try:
                thread_num = int(parts[0])
                message = parts[1]
            except ValueError:
                self._flash("usage: /reply [#] [message]")
                return
            threads = self.store.get_threads(self.current_board)
            if thread_num < 1 or thread_num > len(threads):
                self._flash(f"thread #{thread_num} not found")
                return
            t = threads[thread_num - 1]
            self.send_cb(message, "text", self.current_board, t["thread_id"], "", "")
            self.mining = True
            return

        # /file path — share a file
        if text.startswith("/file "):
            filepath = text[6:].strip()
            self._send_file(filepath)
            return

        # /save # [path] — save a received file
        if text.startswith("/save "):
            parts = text[6:].strip().split(" ", 1)
            try:
                idx = int(parts[0].lstrip("#")) - 1
                dest = parts[1] if len(parts) > 1 else ""
                self._save_file(idx, dest)
            except (ValueError, IndexError):
                self._flash("usage: /save #num [path]")
            return

        # Regular message — board-level chat or inside a thread
        ct = "code" if text.startswith("```") else "text"
        if ct == "code":
            text = text.strip("`").strip()

        self.send_cb(text, ct, self.current_board, self.current_thread_id, "", "")
        self.mining = True

    def _cancel_input(self):
        self.input_buf = ""
        self.input_mode = False
        curses.curs_set(0)

    def _flash(self, msg: str, seconds: float = 4.0):
        self.status_msg = msg
        self.status_expire = time.time() + seconds

    # ------------------------------------------------------------------
    # Event queue
    # ------------------------------------------------------------------

    def _drain_events(self):
        while True:
            try:
                ev = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            kind = ev[0]
            if kind == "new_msg":
                msg: Message = ev[1]
                if f"@{self.name}" in msg.content and msg.author_name != self.name:
                    self.mention_count += 1
                    curses.beep()
                self.mining = False
            elif kind == "msg_sent":
                self.mining = False
            elif kind == "new_dm":
                dm_msg: Message = ev[1]
                if not self.show_dms:
                    self.dm_count_unread += 1
                    curses.beep()
            elif kind == "peer_joined":
                self.peer_count += 1
                self._flash(f"{ev[1]} joined")
            elif kind == "peer_left":
                self.peer_count = max(0, self.peer_count - 1)
                self._flash(f"{ev[1]} left")
            elif kind == "error":
                self._flash(str(ev[1]))
            elif kind == "status":
                msg_str = str(ev[1])
                if "relay connected" in msg_str:
                    self.relay_connected = True
                self._flash(msg_str)
            elif kind == "e2e":
                self.e2e_active = bool(ev[1])
                self._flash("e2e encryption active")

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw(self):
        scr = self._scr
        scr.erase()
        H, W = scr.getmaxyx()
        row = 0

        if self.show_header:
            row = self._draw_header(row, W)
        else:
            self._draw_board_path(0, W)
            row = 1

        self._hline(row, W)
        row += 1

        feed_bottom = H - 3

        if self.show_help:
            self._draw_help(row, feed_bottom, W)
        elif self.show_dms:
            self._draw_dm_feed(row, feed_bottom, W)
        elif self.mentions_only:
            self._draw_feed(row, feed_bottom, W)
        elif self.current_thread_id:
            self._draw_thread_header(row, W)
            self._draw_feed(row + 1, feed_bottom, W)
        elif self.show_thread_list:
            self._draw_thread_list(row, feed_bottom, W)
        else:
            self._draw_feed(row, feed_bottom, W)

        self._draw_input(H - 2, W)
        self._draw_status(H - 1, W)

        scr.refresh()

    # -- header --------------------------------------------------------

    def _draw_header(self, start: int, W: int) -> int:
        art_x = max(0, (W - ART_WIDTH) // 2)
        draw_lime(self._scr, start + 1, art_x)
        ty = start + ART_HEIGHT + 2
        self._centered(ty, "L I M E S", curses.color_pair(C_GREEN) | curses.A_BOLD)
        self._centered(ty + 1, "anonymous ephemeral broadcast network",
                        curses.color_pair(C_DIM) | curses.A_DIM)
        self._centered(ty + 2, f"v{VERSION}", curses.color_pair(C_DIM))
        return ty + 4

    def _draw_board_path(self, row: int, W: int):
        path = f" /{self.current_board}/"
        if self.current_thread_id:
            title_trunc = self.current_thread_title[:40]
            path += f" > {title_trunc}"
        version = f"limes v{VERSION}"
        try:
            self._scr.addstr(row, 0, path, curses.color_pair(C_GREEN) | curses.A_BOLD)
            self._scr.addstr(row, W - len(version) - 1, version, curses.color_pair(C_DIM))
        except curses.error:
            pass

    def _draw_thread_header(self, row: int, W: int):
        title = self.current_thread_title[:W - 6]
        try:
            self._scr.addstr(row, 1, f"> {title}",
                             curses.color_pair(C_CYAN) | curses.A_BOLD)
        except curses.error:
            pass

    # -- thread list ---------------------------------------------------

    def _draw_thread_list(self, top: int, bottom: int, W: int):
        threads = self.store.get_threads(self.current_board)
        avail = bottom - top
        if avail <= 0:
            return

        try:
            self._scr.addstr(top, 1, f"/{self.current_board}/ threads  [q] back to chat",
                             curses.color_pair(C_DIM) | curses.A_DIM)
        except curses.error:
            pass

        if not threads:
            try:
                self._scr.addstr(top + 2, 2, "no active threads",
                                 curses.color_pair(C_DIM))
                self._scr.addstr(top + 3, 2, "use /t [title] to create one",
                                 curses.color_pair(C_DIM) | curses.A_DIM)
            except curses.error:
                pass
            return

        for i, t in enumerate(threads):
            row_base = top + 1 + (i * 2)
            if row_base + 1 >= bottom:
                break

            num = f" [{i+1}] "
            title = t["title"]
            if len(title) > 35:
                title = title[:34] + "~"
            count = f"{t['count']}"
            age = self._format_age(t["latest"])

            try:
                self._scr.addstr(row_base, 0, num,
                                 curses.color_pair(C_CYAN) | curses.A_BOLD)
                col = len(num)
                self._scr.addstr(row_base, col, title,
                                 curses.color_pair(C_GREEN) | curses.A_BOLD)
                info = f" {count} msgs  {age}"
                info_x = W - len(info) - 1
                if info_x > col + len(title):
                    self._scr.addstr(row_base, info_x, info,
                                     curses.color_pair(C_DIM))
            except curses.error:
                pass

            preview = t.get("preview", "")
            if preview:
                author = t.get("preview_author", "")
                line = f"      {author}: {preview}"
                if len(line) > W - 2:
                    line = line[:W - 3] + "~"
                try:
                    self._scr.addstr(row_base + 1, 0, line,
                                     curses.color_pair(C_DIM) | curses.A_DIM)
                except curses.error:
                    pass

    # -- message feed --------------------------------------------------

    def _draw_feed(self, top: int, bottom: int, W: int):
        if self.mentions_only:
            msgs = self.store.get_mentions(self.name)
        elif self.current_thread_id:
            msgs = self.store.get_by_thread(self.current_thread_id)
        else:
            msgs = self.store.get_board_chat(self.current_board)

        avail = bottom - top
        if avail <= 0:
            return

        total = len(msgs)
        max_off = max(0, total - avail)
        if self.scroll_offset > max_off:
            self.scroll_offset = max_off

        start_idx = max(0, total - avail - self.scroll_offset)
        end_idx = min(total, start_idx + avail)

        for i, msg in enumerate(msgs[start_idx:end_idx]):
            r = top + i
            if r >= bottom:
                break
            self._draw_msg(r, W, msg)

    def _draw_msg(self, row: int, W: int, msg: Message):
        scr = self._scr
        author = msg.display_author
        prefix = f" {author}: "
        remaining = f" {msg.remaining_display} "
        max_content = W - len(prefix) - len(remaining) - 1
        if msg.content_type == "file" and msg.file_name:
            kb = msg.file_size // 1024
            content = f"[file: {msg.file_name} ({kb}KB)] /save #{self._file_index(msg)}"
        else:
            content = msg.content.replace("\n", " ")
        if len(content) > max_content:
            content = content[: max_content - 1] + "~"

        try:
            scr.addstr(row, 0, prefix, curses.color_pair(C_GREEN) | curses.A_BOLD)
            col = len(prefix)
            self._render_content(row, col, content, W - len(remaining) - 1)
            time_attr = curses.color_pair(C_DIM) | curses.A_DIM
            if msg.remaining_seconds < 120:
                time_attr = curses.color_pair(C_RED) | curses.A_BOLD
            scr.addstr(row, W - len(remaining) - 1, remaining, time_attr)
        except curses.error:
            pass

    def _render_content(self, row: int, col: int, content: str, max_col: int):
        scr = self._scr
        parts = content.split("@")
        for j, part in enumerate(parts):
            if col >= max_col:
                break
            if j == 0:
                seg = part[: max_col - col]
                try:
                    scr.addstr(row, col, seg, curses.color_pair(C_DIM))
                except curses.error:
                    pass
                col += len(seg)
            else:
                space = part.find(" ")
                if space == -1:
                    mention, rest = part, ""
                else:
                    mention, rest = part[:space], part[space:]
                m_text = f"@{mention}"[: max_col - col]
                try:
                    scr.addstr(row, col, m_text, curses.color_pair(C_CYAN) | curses.A_BOLD)
                except curses.error:
                    pass
                col += len(m_text)
                if rest and col < max_col:
                    r_text = rest[: max_col - col]
                    try:
                        scr.addstr(row, col, r_text, curses.color_pair(C_DIM))
                    except curses.error:
                        pass
                    col += len(r_text)

    # -- input line ----------------------------------------------------

    def _draw_input(self, row: int, W: int):
        scr = self._scr
        prompt = f" {self.name}#{self.tag} > "
        if self.mining:
            prompt = " mining... "
        try:
            if self.input_mode:
                scr.addstr(row, 0, prompt, curses.color_pair(C_GREEN))
                buf_space = W - len(prompt) - 1
                visible = self.input_buf[-buf_space:] if len(self.input_buf) > buf_space else self.input_buf
                scr.addstr(row, len(prompt), visible, curses.color_pair(C_DIM))
            else:
                scr.addstr(row, 0, prompt, curses.color_pair(C_DIM) | curses.A_DIM)
                if self.show_help:
                    hint = "[?] close help  [q] quit"
                elif self.show_dms:
                    hint = "[i] type  [d] back to chat"
                elif self.current_thread_id:
                    hint = "[i] type  [q] back to chat"
                elif self.show_thread_list:
                    hint = "[1-9] enter thread  [q] back"
                else:
                    hint = "[i] type  [t] threads  [d] DMs  [?] help"
                scr.addstr(row, len(prompt), hint,
                           curses.color_pair(C_DIM) | curses.A_DIM)
        except curses.error:
            pass

    # -- status bar ----------------------------------------------------

    def _draw_status(self, row: int, W: int):
        if self.first_run_tip and not self.status_msg:
            left = " tip: press [i] to type, [t] threads, [d] DMs, [?] help"
        elif self.status_msg and time.time() < self.status_expire:
            left = f" {self.status_msg}"
        else:
            board_path = f"/{self.current_board}/"
            if self.current_thread_id:
                tt = self.current_thread_title[:15]
                board_path += f" > {tt}"
            thread_count = len(self.store.get_threads(self.current_board))
            threads_info = f" {thread_count}t" if thread_count and not self.current_thread_id else ""
            mode = " [mentions]" if self.mentions_only else ""
            dm_info = f" dm({self.dm_count_unread})" if self.dm_count_unread else ""
            left = f" {board_path}{threads_info} [n]otif({self.mention_count}){dm_info}{mode}"

        relay = " relay:on" if self.relay_connected else ""
        e2e = " e2e:on" if self.e2e_active else ""
        right = f"peers:{self.peer_count} msgs:{self.store.count()}{relay}{e2e} "
        pad = W - len(left) - len(right)
        line = left + (" " * max(0, pad)) + right
        try:
            self._scr.addstr(row, 0, line[: W - 1], curses.A_REVERSE)
        except curses.error:
            pass

    def _file_index(self, msg: Message) -> int:
        file_msgs = [m for m in self.store.get_board_chat(self.current_board)
                     if m.content_type == "file" and m.file_data]
        for i, m in enumerate(file_msgs):
            if m.id == msg.id:
                return i + 1
        return 0

    # -- file sharing --------------------------------------------------

    MAX_FILE_SIZE = 45_000  # ~45KB raw, fits within 64KB after base64 + overhead

    def _send_file(self, filepath: str):
        import base64
        from pathlib import Path
        p = Path(filepath)
        if not p.exists():
            self._flash(f"file not found: {filepath}")
            return
        size = p.stat().st_size
        if size > self.MAX_FILE_SIZE:
            self._flash(f"file too large ({size // 1024}KB > {self.MAX_FILE_SIZE // 1024}KB)")
            return
        data = p.read_bytes()
        b64 = base64.b64encode(data).decode()
        display = f"[file: {p.name} ({size // 1024}KB)]"
        self.send_cb(
            display, "file", self.current_board,
            self.current_thread_id, "", "",
            file_name=p.name, file_data=b64, file_size=size,
        )
        self.mining = True
        self._flash(f"sharing {p.name}...")

    def _save_file(self, idx: int, dest: str):
        import base64
        from pathlib import Path
        msgs = self.store.get_board_chat(self.current_board)
        file_msgs = [m for m in msgs if m.content_type == "file" and m.file_data]
        if idx < 0 or idx >= len(file_msgs):
            self._flash(f"file #{idx + 1} not found")
            return
        msg = file_msgs[idx]
        data = base64.b64decode(msg.file_data)
        out = Path(dest) if dest else Path(msg.file_name)
        out.write_bytes(data)
        self._flash(f"saved: {out}")

    # -- help screen ---------------------------------------------------

    def _draw_help(self, top: int, bottom: int, W: int):
        lines = [
            ("COMMANDS", True),
            ("  /help           show this help", False),
            ("  /t [title]      create a thread", False),
            ("  /b [board]      switch boards", False),
            ("  /boards         list boards", False),
            ("  /threads        list threads", False),
            ("  /reply # msg    reply to thread", False),
            ("  /back           back to board", False),
            ("  /dm @name msg   send a DM", False),
            ("  /file path      share a file", False),
            ("  /save # [path]  save a file", False),
            ("  /connect h:p    connect to peer", False),
            ("  @name           mention a user", False),
            ("", False),
            ("KEYBINDINGS", True),
            ("  i / Enter    input mode", False),
            ("  Esc / q      back / quit", False),
            ("  t            thread list", False),
            ("  d            toggle DMs", False),
            ("  n            mentions filter", False),
            ("  h            toggle header", False),
            ("  ?            this help", False),
            ("  1-9          enter thread", False),
            ("  Up/Down      scroll", False),
        ]
        for i, (text, is_header) in enumerate(lines):
            r = top + i
            if r >= bottom:
                break
            try:
                attr = curses.color_pair(C_GREEN) | curses.A_BOLD if is_header else curses.color_pair(C_DIM)
                self._scr.addstr(r, 1, text[:W-2], attr)
            except curses.error:
                pass

    # -- DM feed -------------------------------------------------------

    def _draw_dm_feed(self, top: int, bottom: int, W: int):
        dms = self.store.get_dms(self.name)
        avail = bottom - top
        if avail <= 0:
            return

        try:
            self._scr.addstr(top, 1, "direct messages  [d] back to chat",
                             curses.color_pair(C_DIM) | curses.A_DIM)
        except curses.error:
            pass

        if not dms:
            try:
                self._scr.addstr(top + 2, 2, "no DMs yet",
                                 curses.color_pair(C_DIM))
                self._scr.addstr(top + 3, 2, "use /dm @name message to send one",
                                 curses.color_pair(C_DIM) | curses.A_DIM)
            except curses.error:
                pass
            return

        start = max(0, len(dms) - (avail - 1))
        for i, msg in enumerate(dms[start:]):
            r = top + 1 + i
            if r >= bottom:
                break
            self._draw_msg(r, W, msg)

    # -- helpers -------------------------------------------------------

    def _format_age(self, timestamp: float) -> str:
        diff = max(0, int(time.time() - timestamp))
        if diff < 60:
            return f"{diff}s ago"
        elif diff < 3600:
            return f"{diff // 60}m ago"
        else:
            return f"{diff // 3600}h ago"

    def _centered(self, y: int, text: str, attr=0):
        _, W = self._scr.getmaxyx()
        x = max(0, (W - len(text)) // 2)
        try:
            self._scr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def _hline(self, y: int, W: int):
        try:
            self._scr.addstr(y, 0, "-" * (W - 1), curses.color_pair(C_DIM) | curses.A_DIM)
        except curses.error:
            pass

    # -- colors --------------------------------------------------------

    def _setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        if curses.can_change_color():
            curses.init_color(10, 0, 920, 0)
            curses.init_color(11, 396, 263, 129)
            curses.init_pair(C_GREEN, 10, -1)
            curses.init_pair(C_BROWN, 11, -1)
        else:
            curses.init_pair(C_GREEN, curses.COLOR_GREEN, -1)
            curses.init_pair(C_BROWN, curses.COLOR_YELLOW, -1)
        curses.init_pair(C_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(C_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(C_DIM, curses.COLOR_WHITE, -1)
        curses.init_pair(C_RED, curses.COLOR_RED, -1)
        curses.init_pair(C_YELLOW, curses.COLOR_YELLOW, -1)
