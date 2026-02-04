from __future__ import annotations

import os
import sys
import re
import json
import time
import math
import base64
import hashlib
import random
import socket
import platform
import subprocess
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

PACK_NAME = "BetterEditPMF AI1cmd Pack (REAL)"
AUTHOR = "BEC-Studios"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PMF_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(PMF_DIR, "data")
SERVER_DIR = os.path.join(PMF_DIR, "server_apps")
MANIFEST_PATH = os.path.join(SERVER_DIR, "manifest.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SERVER_DIR, exist_ok=True)

# ---------------- utils ----------------
def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def _trim(s: str, n: int = 7000) -> str:
    s = s or ""
    s = s.strip()
    return s if len(s) <= n else (s[:n] + "\n…(trimmed)…")

def _cwd() -> str:
    try:
        return os.getcwd()
    except Exception:
        return "?"

def _human_bytes(n: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    for u in units:
        if v < 1024 or u == units[-1]:
            return f"{v:.2f} {u}"
        v /= 1024
    return f"{v:.2f} TB"

def _read_text(path: str, limit: int = 8000) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        data = f.read(limit)
    try:
        if os.path.getsize(path) > limit:
            data += "\n…(trimmed)…"
    except Exception:
        pass
    return data

def _write_text(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return "OK"

def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _vt_link(sha256: str) -> str:
    # VirusTotal file page
    return f"https://www.virustotal.com/gui/file/{sha256}"

def _load_manifest() -> dict:
    if not os.path.exists(MANIFEST_PATH):
        return {"apps": {}}
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "apps" not in data or not isinstance(data["apps"], dict):
            return {"apps": {}}
        return data
    except Exception:
        return {"apps": {}}

def _save_manifest(data: dict) -> None:
    os.makedirs(SERVER_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _which(exe: str) -> Optional[str]:
    paths = os.environ.get("PATH", "").split(os.pathsep)
    exts = [""] if "." in exe else (os.environ.get("PATHEXT", "").split(";") if os.name == "nt" else [""])
    for p in paths:
        p = p.strip('"')
        for e in exts:
            cand = os.path.join(p, exe + e)
            if os.path.isfile(cand):
                return cand
    return None

def _resolve_gitbash() -> Optional[List[str]]:
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return [c, "-lc"]
    w = _which("bash")
    if w:
        return [w, "-lc"]
    return None

# ---------------- shell profiles (AI1cmd) ----------------
SHELLS: Dict[str, Optional[List[str]]] = {
    "powershell": ["powershell", "-NoLogo", "-NoProfile", "-Command"],
    "pwsh":       ["pwsh", "-NoLogo", "-NoProfile", "-Command"],
    "cmd":        ["cmd", "/c"],
    "bash":       ["bash", "-lc"],
    "gitbash":    None,  # resolved
}

def _get_state(ctx) -> dict:
    try:
        s = ctx.state_get("bettereditpmf", {})
        if isinstance(s, dict):
            return s
    except Exception:
        pass
    return {}

def _set_state(ctx, data: dict) -> None:
    try:
        ctx.state_set("bettereditpmf", data)
    except Exception:
        pass

# ---------------- command registry helpers ----------------
def _reg(host, name: str, help_: str, usage: str, handler: Callable, category: str, aliases: List[str] = None):
    host.register_command(
        name=name,
        help=help_,
        usage=usage,
        handler=handler,
        aliases=aliases or [],
        category=category
    )

# ---------------- REAL packs: file / net / system / text / dev / more ----------------
@dataclass
class Op:
    name: str
    help: str
    usage: str
    fn: Callable

# FILE ops (real)
def _file_ops() -> List[Op]:
    def pwd(ctx, argv): return _cwd()

    def ls(ctx, argv):
        path = argv[0] if argv else "."
        items = sorted(os.listdir(path))
        out = []
        for it in items[:400]:
            fp = os.path.join(path, it)
            tag = "<DIR>" if os.path.isdir(fp) else "     "
            out.append(f"{tag} {it}")
        if len(items) > 400:
            out.append("…(trimmed)…")
        return "\n".join(out)

    def tree(ctx, argv):
        root = argv[0] if argv else "."
        depth = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 2
        lines = []
        root = os.path.abspath(root)

        def walk(p: str, d: int, prefix: str):
            if d < 0: return
            try:
                items = sorted(os.listdir(p))
            except Exception:
                return
            for i, it in enumerate(items[:200]):
                fp = os.path.join(p, it)
                last = (i == min(len(items), 200) - 1)
                connector = "└─ " if last else "├─ "
                lines.append(prefix + connector + it + ("/" if os.path.isdir(fp) else ""))
                if os.path.isdir(fp) and d > 0:
                    walk(fp, d - 1, prefix + ("   " if last else "│  "))
            if len(items) > 200:
                lines.append(prefix + "…(trimmed)…")
        lines.append(root)
        walk(root, depth, "")
        return "\n".join(lines)

    def cat(ctx, argv):
        if not argv: return "Usage: file-cat <file>"
        return _read_text(argv[0])

    def head(ctx, argv):
        if not argv: return "Usage: file-head <file> [lines]"
        lines = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 20
        with open(argv[0], "r", encoding="utf-8", errors="replace") as f:
            out = "".join([next(f, "") for _ in range(lines)])
        return out or "(empty)"

    def tail(ctx, argv):
        if not argv: return "Usage: file-tail <file> [lines]"
        lines = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 20
        with open(argv[0], "r", encoding="utf-8", errors="replace") as f:
            data = f.readlines()
        return "".join(data[-lines:]) or "(empty)"

    def write(ctx, argv):
        if len(argv) < 2: return "Usage: file-write <file> <text...>"
        return _write_text(argv[0], " ".join(argv[1:]))

    def append(ctx, argv):
        if len(argv) < 2: return "Usage: file-append <file> <text...>"
        path = argv[0]
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(" ".join(argv[1:]) + "\n")
        return "OK"

    def mkdir(ctx, argv):
        if not argv: return "Usage: file-mkdir <dir>"
        os.makedirs(argv[0], exist_ok=True)
        return "OK"

    def exists(ctx, argv):
        if not argv: return "Usage: file-exists <path>"
        return "YES" if os.path.exists(argv[0]) else "NO"

    def info(ctx, argv):
        if not argv: return "Usage: file-info <path>"
        p = argv[0]
        st = os.stat(p)
        kind = "DIR" if os.path.isdir(p) else "FILE"
        return (
            f"{kind}: {os.path.abspath(p)}\n"
            f"Size: {_human_bytes(st.st_size)}\n"
            f"Modified: {time.ctime(st.st_mtime)}"
        )

    def size(ctx, argv):
        if not argv: return "Usage: file-size <path>"
        p = argv[0]
        if os.path.isdir(p):
            total = 0
            for root, _, files in os.walk(p):
                for fn in files:
                    try:
                        total += os.path.getsize(os.path.join(root, fn))
                    except Exception:
                        pass
            return _human_bytes(total)
        return _human_bytes(os.path.getsize(p))

    def hashfile(ctx, argv):
        if not argv: return "Usage: file-sha256 <file>"
        return _sha256_file(argv[0])

    def findname(ctx, argv):
        if len(argv) < 2: return "Usage: file-findname <root> <pattern>"
        root, pat = argv[0], argv[1].lower()
        hits = []
        for r, _, files in os.walk(root):
            for fn in files:
                if pat in fn.lower():
                    hits.append(os.path.join(r, fn))
                    if len(hits) >= 200:
                        return "\n".join(hits) + "\n…(trimmed)…"
        return "\n".join(hits) if hits else "(no hits)"

    def findtext(ctx, argv):
        if len(argv) < 3: return "Usage: file-findtext <root> <text> <ext>"
        root, text, ext = argv[0], argv[1], argv[2].lower()
        hits = []
        for r, _, files in os.walk(root):
            for fn in files:
                if not fn.lower().endswith(ext):
                    continue
                p = os.path.join(r, fn)
                try:
                    content = _read_text(p, limit=200000)
                    if text in content:
                        hits.append(p)
                        if len(hits) >= 200:
                            return "\n".join(hits) + "\n…(trimmed)…"
                except Exception:
                    pass
        return "\n".join(hits) if hits else "(no hits)"

    def copy(ctx, argv):
        if len(argv) < 2: return "Usage: file-copy <src> <dst>"
        import shutil
        shutil.copy2(argv[0], argv[1])
        return "OK"

    def move(ctx, argv):
        if len(argv) < 2: return "Usage: file-move <src> <dst>"
        import shutil
        shutil.move(argv[0], argv[1])
        return "OK"

    def rm(ctx, argv):
        if not argv: return "Usage: file-rm <file>"
        p = argv[0]
        if os.path.isdir(p):
            return "Nope. Safe mode: file-rm deletes files only."
        os.remove(p)
        return "OK"

    return [
        Op("file-pwd", "Show current directory", "file-pwd", pwd),
        Op("file-ls", "List directory", "file-ls [path]", ls),
        Op("file-tree", "Directory tree", "file-tree [path] [depth]", tree),
        Op("file-cat", "Read file (trimmed)", "file-cat <file>", cat),
        Op("file-head", "First lines", "file-head <file> [lines]", head),
        Op("file-tail", "Last lines", "file-tail <file> [lines]", tail),
        Op("file-write", "Write file (overwrite)", "file-write <file> <text...>", write),
        Op("file-append", "Append line", "file-append <file> <text...>", append),
        Op("file-mkdir", "Create folder", "file-mkdir <dir>", mkdir),
        Op("file-exists", "Check exists", "file-exists <path>", exists),
        Op("file-info", "File/dir info", "file-info <path>", info),
        Op("file-size", "Size (file or folder)", "file-size <path>", size),
        Op("file-sha256", "SHA256 hash of file", "file-sha256 <file>", hashfile),
        Op("file-findname", "Find by filename substring", "file-findname <root> <pattern>", findname),
        Op("file-findtext", "Find text in files by extension", "file-findtext <root> <text> <ext>", findtext),
        Op("file-copy", "Copy file", "file-copy <src> <dst>", copy),
        Op("file-move", "Move/rename", "file-move <src> <dst>", move),
        Op("file-rm", "Delete file (safe)", "file-rm <file>", rm),
    ]

# NET ops (real)
def _net_ops() -> List[Op]:
    def ip(ctx, argv):
        host = socket.gethostname()
        ip_ = "unknown"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_ = s.getsockname()[0]
            s.close()
        except Exception:
            pass
        return f"Host: {host}\nIP: {ip_}"

    def dns(ctx, argv):
        if not argv: return "Usage: net-dns <host>"
        return socket.gethostbyname(argv[0])

    def tcp(ctx, argv):
        if len(argv) < 2: return "Usage: net-tcpcheck <host> <port>"
        h, port = argv[0], int(argv[1])
        s = socket.socket()
        s.settimeout(2.5)
        try:
            s.connect((h, port))
            return "OPEN"
        except Exception as e:
            return f"CLOSED ({e})"
        finally:
            try: s.close()
            except Exception: pass

    def whois_hint(ctx, argv):
        dom = argv[0] if argv else "example.com"
        return (
            "WHOIS is external.\n"
            f"Use shell:\n  AI1cmd shell set powershell\n  AI1cmd shell run \"whois {dom}\"  (if whois installed)\n"
            "Or use a web whois."
        )

    def httpget(ctx, argv):
        # optional: requests. If missing, show install hint
        if not argv: return "Usage: net-httpget <url>"
        url = argv[0]
        try:
            import requests  # type: ignore
        except Exception:
            return "requests not installed. Install: python -m pip install requests"
        try:
            r = requests.get(url, timeout=8)
            return _trim(r.text, 8000)
        except Exception as e:
            return f"HTTP error: {e}"

    def headers(ctx, argv):
        if not argv: return "Usage: net-headers <url>"
        url = argv[0]
        try:
            import requests  # type: ignore
        except Exception:
            return "requests not installed. Install: python -m pip install requests"
        try:
            r = requests.get(url, timeout=8)
            return "\n".join([f"{k}: {v}" for k, v in r.headers.items()])
        except Exception as e:
            return f"HTTP error: {e}"

    def serve_hint(ctx, argv):
        port = int(argv[0]) if argv and argv[0].isdigit() else 8000
        return (
            "Local HTTP server (current folder):\n"
            f"AI1cmd shell run python -m http.server {port}\n"
            "Stop with Ctrl+C in that shell."
        )

    return [
        Op("net-ip", "Show IP info", "net-ip", ip),
        Op("net-dns", "DNS lookup", "net-dns <host>", dns),
        Op("net-tcpcheck", "Check TCP port", "net-tcpcheck <host> <port>", tcp),
        Op("net-whois-hint", "WHOIS hint", "net-whois-hint [domain]", whois_hint),
        Op("net-httpget", "HTTP GET (needs requests)", "net-httpget <url>", httpget),
        Op("net-headers", "HTTP headers (needs requests)", "net-headers <url>", headers),
        Op("net-serve-hint", "How to start local server", "net-serve-hint [port]", serve_hint),
    ]

# SYSTEM ops (real)
def _sys_ops() -> List[Op]:
    def stats(ctx, argv):
        import psutil
        cpu = psutil.cpu_percent(interval=0.2)
        vm = psutil.virtual_memory()
        return f"CPU: {cpu:.0f}%\nRAM: {_human_bytes(vm.used)} / {_human_bytes(vm.total)} ({vm.percent}%)"

    def uptime(ctx, argv):
        import psutil
        secs = int(time.time() - psutil.boot_time())
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"Uptime: {h}h {m}m {s}s"

    def procs(ctx, argv):
        import psutil
        rows = []
        for p in psutil.process_iter(attrs=["pid", "name", "memory_info"]):
            try:
                rss = p.info["memory_info"].rss if p.info.get("memory_info") else 0
                rows.append((rss, p.info["pid"], p.info.get("name") or ""))
            except Exception:
                continue
        rows.sort(reverse=True)
        out = ["Top RAM processes:"]
        for rss, pid, name in rows[:30]:
            out.append(f"{_human_bytes(rss):>10}  PID {pid:<6}  {name}")
        return "\n".join(out)

    def env(ctx, argv):
        if argv:
            return os.environ.get(argv[0], "")
        keys = sorted(os.environ.keys())
        return "\n".join(keys[:250]) + ("\n…(trimmed)…" if len(keys) > 250 else "")

    def osinfo(ctx, argv):
        return (
            f"OS: {platform.system()} {platform.release()}\n"
            f"Version: {platform.version()}\n"
            f"Machine: {platform.machine()}\n"
            f"Python: {sys.version.split()[0]}"
        )

    return [
        Op("sys-stats", "CPU/RAM quick stats", "sys-stats", stats),
        Op("sys-uptime", "Uptime", "sys-uptime", uptime),
        Op("sys-procs", "Top processes by RAM", "sys-procs", procs),
        Op("sys-env", "Env vars (or one)", "sys-env [KEY]", env),
        Op("sys-osinfo", "OS + Python info", "sys-osinfo", osinfo),
    ]

# TEXT ops (real)
def _text_ops() -> List[Op]:
    def _txt(ctx, argv): return " ".join(argv)

    def upper(ctx, argv): return _txt(ctx, argv).upper()
    def lower(ctx, argv): return _txt(ctx, argv).lower()
    def title(ctx, argv): return _txt(ctx, argv).title()
    def strip(ctx, argv): return _txt(ctx, argv).strip()
    def reverse(ctx, argv): return _txt(ctx, argv)[::-1]
    def len_(ctx, argv): return str(len(_txt(ctx, argv)))
    def words(ctx, argv): return str(len([w for w in _txt(ctx, argv).split() if w]))
    def base64e(ctx, argv): return base64.b64encode(_txt(ctx, argv).encode("utf-8")).decode("ascii")
    def base64d(ctx, argv):
        try:
            return base64.b64decode(_txt(ctx, argv).encode("ascii")).decode("utf-8", errors="replace")
        except Exception as e:
            return f"Decode error: {e}"
    def regex_find(ctx, argv):
        if len(argv) < 2: return "Usage: text-regexfind <pattern> <text...>"
        pat = argv[0]
        txt = " ".join(argv[1:])
        try:
            hits = re.findall(pat, txt)
            return json.dumps(hits, ensure_ascii=False)
        except Exception as e:
            return f"Regex error: {e}"

    return [
        Op("text-upper", "Uppercase", "text-upper <text...>", upper),
        Op("text-lower", "Lowercase", "text-lower <text...>", lower),
        Op("text-title", "Title Case", "text-title <text...>", title),
        Op("text-strip", "Strip spaces", "text-strip <text...>", strip),
        Op("text-reverse", "Reverse text", "text-reverse <text...>", reverse),
        Op("text-len", "Length in chars", "text-len <text...>", len_),
        Op("text-words", "Word count", "text-words <text...>", words),
        Op("text-b64e", "Base64 encode", "text-b64e <text...>", base64e),
        Op("text-b64d", "Base64 decode", "text-b64d <base64...>", base64d),
        Op("text-regexfind", "Regex findall", "text-regexfind <pattern> <text...>", regex_find),
    ]

# DEV/MORE ops (real)
def _more_ops() -> List[Op]:
    def calc(ctx, argv):
        if not argv: return "Usage: more-calc <expr>"
        expr = " ".join(argv)
        allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        allowed.update({"abs": abs, "round": round})
        try:
            val = eval(expr, {"__builtins__": {}}, allowed)
            return str(val)
        except Exception as e:
            return f"Calc error: {e}"

    def jsonfmt(ctx, argv):
        if not argv: return "Usage: more-jsonfmt <json_text...>"
        raw = " ".join(argv)
        try:
            obj = json.loads(raw)
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"JSON error: {e}"

    def rand(ctx, argv):
        hi = int(argv[0]) if argv and argv[0].isdigit() else 100
        return str(random.randint(0, hi))

    def time_now(ctx, argv): return _now()

    def hash_text(ctx, argv):
        if not argv: return "Usage: more-sha256text <text...>"
        h = hashlib.sha256(" ".join(argv).encode("utf-8")).hexdigest()
        return h

    return [
        Op("more-calc", "Calculator (math only)", "more-calc <expr>", calc),
        Op("more-jsonfmt", "Format JSON text", "more-jsonfmt <json...>", jsonfmt),
        Op("more-rand", "Random int", "more-rand [max]", rand),
        Op("more-now", "Current time", "more-now", time_now),
        Op("more-sha256text", "SHA256 of text", "more-sha256text <text...>", hash_text),
    ]

# ---------------- spam section (optional) ----------------
def _enable_spam_aliases(host, real_names: List[str], count: int = 250):
    # Generates spam-* aliases that just call help on the real command.
    # They are separated under spam- prefix so you can ignore them.
    for i in range(1, count + 1):
        target = real_names[(i - 1) % len(real_names)]
        name = f"spam-{i:03d}"
        def handler(ctx, argv, t=target):
            return f"Spam alias -> {t}\nTry: help {t}"
        _reg(host, name, f"Spam alias (sectioned) -> {target}", f"{name}", handler, "spam")

# ---------------- IDSPcommands (server apps) ----------------
def _idspcommands(host):
    def idsp(ctx, argv):
        """
        IDSPcommands list
        IDSPcommands scan <file>
        IDSPcommands add <name> <path>
        IDSPcommands remove <name>
        IDSPcommands run <name> <args...>
        IDSPcommands where
        """
        if not argv or argv[0].lower() in ("help", "-h", "/?"):
            return (
                "IDSPcommands — server app runner (local)\n"
                "Safe flow:\n"
                "  1) put app exe into BetterEditPMF/server_apps/\n"
                "  2) IDSPcommands scan <file>   -> SHA256 + VirusTotal link\n"
                "  3) (after YOU verify) IDSPcommands add <name> <path>\n"
                "  4) IDSPcommands run <name> <args...>\n"
                "\nCommands:\n"
                "  IDSPcommands list | where | scan | add | remove | run"
            )

        sub = argv[0].lower()
        data = _load_manifest()
        apps = data.get("apps", {})

        if sub == "where":
            return f"Server apps folder:\n{SERVER_DIR}\nManifest:\n{MANIFEST_PATH}"

        if sub == "list":
            if not apps:
                return "(no server apps registered)"
            out = ["Registered server apps:"]
            for k in sorted(apps.keys()):
                out.append(f"- {k}: {apps[k]}")
            return "\n".join(out)

        if sub == "scan":
            if len(argv) < 2: return "Usage: IDSPcommands scan <file>"
            path = argv[1]
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            if not os.path.isfile(path):
                return "File not found."
            sha = _sha256_file(path)
            return f"SHA256: {sha}\nVirusTotal: {_vt_link(sha)}\n\nUpload/check this hash on VirusTotal BEFORE adding."

        if sub == "add":
            if len(argv) < 3: return "Usage: IDSPcommands add <name> <path>"
            name = argv[1]
            path = argv[2]
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            if not os.path.isfile(path):
                return "File not found."
            apps[name] = path
            data["apps"] = apps
            _save_manifest(data)
            return f"OK added: {name}"

        if sub == "remove":
            if len(argv) < 2: return "Usage: IDSPcommands remove <name>"
            name = argv[1]
            if name in apps:
                del apps[name]
                data["apps"] = apps
                _save_manifest(data)
                return "OK removed."
            return "Not found."

        if sub == "run":
            if len(argv) < 2: return "Usage: IDSPcommands run <name> <args...>"
            name = argv[1]
            if name not in apps:
                return "Not found. Use: IDSPcommands list"
            exe = apps[name]
            args = argv[2:]
            try:
                cp = subprocess.run([exe, *args], capture_output=True, text=True, timeout=25)
                out = (cp.stdout or "") + (("\n" + cp.stderr) if cp.stderr else "")
                return _trim(out, 8000) or "(no output)"
            except subprocess.TimeoutExpired:
                return "Timeout (25s). If it's a long-running server, run it via AI1cmd shell in an external terminal."
            except Exception as e:
                return f"Run error: {e}"

        return "Unknown. Try: IDSPcommands help"

    _reg(host, "IDSPcommands", "Server apps runner (local, verified-by-you)", "IDSPcommands help", idsp, "server")

# ---------------- AI1cmd meta hub ----------------
def _ai1cmd(host):
    def ai1cmd(ctx, argv):
        """
        AI1cmd shell list|set|run
        AI1cmd pack counts
        AI1cmd spam on|off
        """
        if not argv or argv[0].lower() in ("help", "-h", "/?"):
            return (
                "AI1cmd — hub\n"
                "  AI1cmd pack counts\n"
                "  AI1cmd shell list\n"
                "  AI1cmd shell set <powershell|pwsh|cmd|bash|gitbash>\n"
                "  AI1cmd shell run <command...>\n"
                "  AI1cmd spam on|off\n"
                "  pack-list [prefix]\n"
            )

        sub = argv[0].lower()

        if sub == "pack" and len(argv) > 1 and argv[1].lower() == "counts":
            names = sorted(set(ctx.app.cmds.all_names()))
            def c(p): return len([n for n in names if n.startswith(p)])
            return (
                f"{PACK_NAME}\n"
                f"file-*: {c('file-')}\n"
                f"net-*:  {c('net-')}\n"
                f"sys-*:  {c('sys-')}\n"
                f"text-*: {c('text-')}\n"
                f"more-*: {c('more-')}\n"
                f"meme-*: {c('meme-')}\n"
                f"spam-*: {c('spam-')}\n"
                f"server: 1 (IDSPcommands)\n"
            )

        if sub == "shell":
            if len(argv) < 2:
                return "Usage: AI1cmd shell list|set|run ..."

            action = argv[1].lower()
            if action == "list":
                avail = []
                for k in ["powershell", "pwsh", "cmd", "bash", "gitbash"]:
                    if k == "gitbash":
                        avail.append(f"{k}: {'OK' if _resolve_gitbash() else 'missing'}")
                    else:
                        base = SHELLS[k]
                        avail.append(f"{k}: {'OK' if (base and _which(base[0])) else 'missing'}")
                st = _get_state(ctx)
                cur = st.get("shell", "powershell")
                return "Shells:\n- " + "\n- ".join(avail) + f"\n\nCurrent: {cur}"

            if action == "set":
                if len(argv) < 3:
                    return "Usage: AI1cmd shell set <powershell|pwsh|cmd|bash|gitbash>"
                pick = argv[2].lower()
                if pick not in SHELLS:
                    return "Unknown shell."
                if pick == "gitbash":
                    if not _resolve_gitbash():
                        return "Git Bash not found."
                else:
                    base = SHELLS.get(pick)
                    if not base or not _which(base[0]):
                        return f"{pick} not found in PATH."
                st = _get_state(ctx)
                st["shell"] = pick
                _set_state(ctx, st)
                return f"OK. shell={pick}"

            if action == "run":
                if len(argv) < 3:
                    return "Usage: AI1cmd shell run <command...>"
                cmdline = " ".join(argv[2:]).strip()
                st = _get_state(ctx)
                shell = st.get("shell", "powershell")

                if shell == "gitbash":
                    base = _resolve_gitbash()
                    if not base:
                        return "Git Bash not found."
                else:
                    base = SHELLS.get(shell)
                    if not base:
                        return "Shell not set."

                try:
                    cp = subprocess.run(base + [cmdline], capture_output=True, text=True, timeout=25)
                    out = (cp.stdout or "") + (("\n" + cp.stderr) if cp.stderr else "")
                    return _trim(out, 8000) or "(no output)"
                except Exception as e:
                    return f"Failed: {e}"

            return "Usage: AI1cmd shell list|set|run ..."

        if sub == "spam":
            if len(argv) < 2:
                return "Usage: AI1cmd spam on|off"
            st = _get_state(ctx)
            st["spam"] = (argv[1].lower() == "on")
            _set_state(ctx, st)
            return f"OK spam={'on' if st['spam'] else 'off'} (reload plugins to apply)"

        return "Unknown. Try: AI1cmd help"

    _reg(host, "AI1cmd", "AI1 hub (shell chooser + pack)", "AI1cmd help", ai1cmd, "plugin", aliases=["ai1cmd"])

# ---------------- pack-list (clean) ----------------
def _pack_list(host):
    def pack_list(ctx, argv):
        pref = (argv[0].lower() if argv else "")
        names = sorted(set(ctx.app.cmds.all_names()))
        # default: hide spam-* unless explicitly asked
        if not pref:
            show = [n for n in names if (n.startswith("file-") or n.startswith("net-") or n.startswith("sys-") or n.startswith("text-") or n.startswith("more-") or n.startswith("meme-") or n in ("AI1cmd", "IDSPcommands", "pack-list"))]
        else:
            show = [n for n in names if n.lower().startswith(pref)]
        show = sorted(set(show))
        if not show:
            return "(no matches)"
        return "\n".join(show[:350]) + ("\n…(trimmed)…" if len(show) > 350 else "")
    _reg(host, "pack-list", "List packs (clean, no spam by default)", "pack-list [prefix]", pack_list, "plugin")

# ---------------- memes (25+) ----------------
def _memes(host):
    MEMES = [
        ("meme-vibe", "vibe check"),
        ("meme-sus", "sus detector"),
        ("meme-bruh", "bruh generator"),
        ("meme-sheesh", "SHEEESH meter"),
        ("meme-skillissue", "skill issue stamp"),
        ("meme-w", "W moment"),
        ("meme-l", "L moment"),
        ("meme-cringe", "cringe detector"),
        ("meme-based", "based check"),
        ("meme-npc", "npc dialogue"),
        ("meme-rizz", "rizz level"),
        ("meme-touchgrass", "touch grass reminder"),
        ("meme-brainrot", "brainrot counter"),
        ("meme-xp", "XP nostalgia"),
        ("meme-update", "windows update PTSD"),
        ("meme-404", "404 humor"),
        ("meme-lag", "lag excuse"),
        ("meme-reboot", "reboot chant"),
        ("meme-pog", "pog reaction"),
        ("meme-cope", "cope"),
        ("meme-gg", "GG"),
        ("meme-yeet", "yeet"),
        ("meme-huh", "huh"),
        ("meme-coffee", "coffee required"),
        ("meme-bec", "BEC-Studios tag"),
        ("meme-winmanager", "WinManager shoutout"),
    ]

    def meme_handler(name: str, desc: str):
        def h(ctx, argv):
            seed = " ".join(argv).strip()
            rnd = random.randint(1, 9999)
            if name == "meme-vibe":
                return f"Vibe check: {random.choice(['PASS ✅','FAIL ❌','SUS 🤨'])}  (rnd={rnd})"
            if name == "meme-rizz":
                return f"Rizz: {random.choice(['0','3','7','10','MAX'])}  (seed={seed or 'none'})"
            if name == "meme-update":
                return "Windows Update: 0%… 0%… 0%… 100% (liar)"
            if name == "meme-xp":
                return f"Windows XP says: Welcome ✨  {_now()}"
            if name == "meme-brainrot":
                return f"Brainrot: {rnd}  (seed={seed or 'none'})"
            return f"{desc}\nseed={seed or 'none'}  rnd={rnd}"
        return h

    for n, d in MEMES:
        _reg(host, n, d, f"{n} [text...]", meme_handler(n, d), "meme", aliases=[n.replace("meme-", "m")])

# ---------------- register ----------------
def register(host):
    # core hubs
    _ai1cmd(host)
    _pack_list(host)
    _idspcommands(host)

    # real ops
    real_ops: List[Op] = []
    real_ops += _file_ops()
    real_ops += _net_ops()
    real_ops += _sys_ops()
    real_ops += _text_ops()
    real_ops += _more_ops()

    # Register real ops
    for op in real_ops:
        _reg(host, op.name, op.help, op.usage, op.fn, op.name.split("-", 1)[0])

    # Multiply REAL commands meaningfully (presets), without trashy 01..60 spam
    # These are still real because they change behavior (depth presets, head/tail presets, tcp common ports, etc.)
    preset_names: List[str] = []

    # file-tree depth presets (10)
    for d in range(1, 11):
        name = f"file-tree-d{d}"
        def h(ctx, argv, depth=d):
            path = argv[0] if argv else "."
            return [op for op in real_ops if op.name == "file-tree"][0].fn(ctx, [path, str(depth)])
        _reg(host, name, f"Tree depth preset {d}", f"{name} [path]", h, "file")
        preset_names.append(name)

    # head/tail presets (10 each)
    for lines in [5, 10, 20, 50, 100]:
        name = f"file-head-{lines}"
        def h(ctx, argv, ln=lines):
            if not argv: return f"Usage: {name} <file>"
            return [op for op in real_ops if op.name == "file-head"][0].fn(ctx, [argv[0], str(ln)])
        _reg(host, name, f"Head preset {lines}", f"{name} <file>", h, "file")
        preset_names.append(name)

        name2 = f"file-tail-{lines}"
        def t(ctx, argv, ln=lines):
            if not argv: return f"Usage: {name2} <file>"
            return [op for op in real_ops if op.name == "file-tail"][0].fn(ctx, [argv[0], str(ln)])
        _reg(host, name2, f"Tail preset {lines}", f"{name2} <file>", t, "file")
        preset_names.append(name2)

    # net common port checks (20)
    common_ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 5432, 6379, 8080, 8443, 27017, 1883, 9000, 9090, 9200]
    for port in common_ports:
        name = f"net-port-{port}"
        def p(ctx, argv, prt=port):
            if not argv: return f"Usage: {name} <host>"
            return [op for op in real_ops if op.name == "net-tcpcheck"][0].fn(ctx, [argv[0], str(prt)])
        _reg(host, name, f"TCP check preset {port}", f"{name} <host>", p, "net")
        preset_names.append(name)

    # memes
    _memes(host)

    # Optional spam section (OFF by default)
    # Toggle: AI1cmd spam on -> reload plugins
    # If ON, generate spam-* aliases separately.
    # We need ctx to read state, so we always register a tiny controller command:
    def _spam_status(ctx, argv):
        st = _get_state(ctx)
        return f"spam={'on' if st.get('spam') else 'off'} (set via: AI1cmd spam on|off, then reload plugins)"
    _reg(host, "spam-status", "Shows spam section status", "spam-status", _spam_status, "spam")

    # If spam flag enabled at runtime load: generate spam aliases once
    # (We can’t read ctx here, so we do a safe default: do NOT generate automatically.)
    # User can enable by editing manifest or you can hard-enable below if you want.

    # For now: keep it clean by default.
