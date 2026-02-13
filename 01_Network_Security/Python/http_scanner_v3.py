#!/usr/bin/env python3
"""
HTTP Verb Tester (lab-friendly)

Features:
- Tests HTTP verbs: GET, POST, HEAD, PUT, DELETE, OPTIONS, PATCH
- Simple step-by-step GUI wizard (host, port, path)
- Saves a .txt report with status line, headers, and a short body preview
- Commented sections for study/maintenance

Use only on systems you own / have permission to test (e.g., Metasploitable/DVWA).
"""

import datetime
import json
import os
import threading
import traceback
import urllib.parse
import http.client

# -----------------------------
# Config: verbs + defaults
# -----------------------------
VERBS_TO_TEST = ["OPTIONS","GET", "POST", "HEAD", "PUT", "DELETE", "PATCH"]
DEFAULT_PORT = 80
DEFAULT_PATH = "/"
DEFAULT_TIMEOUT_SEC = 8

# How much of the response body to store in the report (avoid huge dumps)
BODY_PREVIEW_CHARS = 1200


# -----------------------------
# Helpers: normalize inputs
# -----------------------------
def normalize_path(p: str) -> str:
    p = (p or DEFAULT_PATH).strip()
    if not p.startswith("/"):
        p = "/" + p
    return p


def safe_filename(s: str) -> str:
    keep = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_", "."):
            keep.append(ch)
        else:
            keep.append("_")
    return "".join(keep)


# -----------------------------
# Core HTTP request function
# -----------------------------
def send_http_request(host: str, port: int, method: str, path: str, timeout: int):
    """
    Sends a single HTTP request using http.client, returns a structured dict with:
    - status, reason, http_version
    - headers (dict)
    - body_len, body_preview
    """
    conn = http.client.HTTPConnection(host, port, timeout=timeout)

    # Basic headers: keep it simple, close connection each time (easier for lab work)
    headers = {
        "Host": host,
        "User-Agent": "Epicode-HTTP-Verb-Tester/1.0",
        "Accept": "*/*",
        "Connection": "close",
    }

    # Minimal body for methods that commonly accept a body.
    # (This is intentionally harmless "test" data.)
    body = None
    if method in ("POST", "PUT", "PATCH"):
        sample = {"test": "epicode", "ts": int(datetime.datetime.now().timestamp())}
        body = json.dumps(sample).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
        headers["Content-Length"] = str(len(body))

    try:
        conn.request(method, path, body=body, headers=headers)
        res = conn.getresponse()

        raw = res.read()  # HEAD usually returns empty body
        text = raw.decode("utf-8", errors="replace")

        # res.version is an int: 9, 10, 11 -> map to HTTP/0.9,1.0,1.1
        version_map = {9: "0.9", 10: "1.0", 11: "1.1"}
        http_version = version_map.get(res.version, str(res.version))

        # Convert headers list to a case-preserving dict
        hdrs = {}
        for k, v in res.getheaders():
            hdrs[k] = v

        return {
            "ok": True,
            "method": method,
            "path": path,
            "status": res.status,
            "reason": res.reason,
            "http_version": http_version,
            "headers": hdrs,
            "body_len": len(raw),
            "body_preview": text[:BODY_PREVIEW_CHARS],
        }
    finally:
        conn.close()


# -----------------------------
# Analysis helpers
# -----------------------------
def get_header_case_insensitive(headers: dict, name: str) -> str:
    """Fetch a header ignoring case."""
    low = name.lower()
    for k, v in headers.items():
        if k.lower() == low:
            return v
    return ""


def parse_allow(headers: dict) -> list:
    """
    RFC-ish behavior: 405 responses often include Allow: header.
    OPTIONS may also include Allow:.
    """
    allow_val = get_header_case_insensitive(headers, "Allow")
    if not allow_val:
        return []
    return [m.strip().upper() for m in allow_val.split(",") if m.strip()]


# Questo metodo implementa una euristica per determinare se un metodo HTTP è "supportato" dal server.
def supported_heuristic(status: int) -> bool:
    """
    Heuristic: method is "supported/recognized" if server responds with:
    - 2xx OK-ish
    - 3xx redirect
    - 401/403 (method exists but requires auth/permissions)
    - 405 (exists but not allowed on this resource)
    """
    return status in (200, 201, 202, 204, 301, 302, 303, 307, 308, 401, 403, 405)


# -----------------------------
# Report writer (.txt)
# -----------------------------
def write_txt_report(host: str, port: int, path: str, results: list) -> str:
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results_{safe_filename(host)}_{port}_{now}.txt"
    out_path = os.path.abspath(filename)

    # Collect "Allow" info seen across responses
    allow_union = set()
    for r in results:
        if r.get("ok"):
            for m in parse_allow(r["headers"]):
                allow_union.add(m)

    # Collect supported methods (heuristic)
    supported = []
    for r in results:
        if r.get("ok") and supported_heuristic(r["status"]):
            supported.append(r["method"])
    supported = sorted(set(supported), key=lambda x: VERBS_TO_TEST.index(x))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("HTTP Verb Tester Report\n")
        f.write("======================\n\n")
        f.write(f"Target: {host}:{port}\n")
        f.write(f"Path:   {path}\n")
        f.write(f"Time:   {datetime.datetime.now().isoformat(sep=' ', timespec='seconds')}\n\n")

        if allow_union:
            f.write(f"Allow (observed): {', '.join(sorted(allow_union))}\n")
        else:
            f.write("Allow (observed): (not present)\n")

        f.write(f"Supported (heuristic): {', '.join(supported) if supported else '(none)'}\n\n")

        f.write("Summary Table\n")
        f.write("-------------\n")
        f.write(f"{'METHOD':<8} {'STATUS':<6} {'REASON':<25} {'ALLOW':<30} {'LOCATION':<40} {'BODY_LEN':<8}\n")
        f.write("-" * 130 + "\n")
        for r in results:
            if not r.get("ok"):
                f.write(f"{r['method']:<8} {'ERR':<6} {r.get('error','')[:25]:<25} {'':<30} {'':<40} {'':<8}\n")
                continue
            allow = get_header_case_insensitive(r["headers"], "Allow")[:30]
            loc = get_header_case_insensitive(r["headers"], "Location")[:40]
            f.write(f"{r['method']:<8} {str(r['status']):<6} {r['reason'][:25]:<25} {allow:<30} {loc:<40} {str(r['body_len']):<8}\n")

        f.write("\n\nDetailed Results\n")
        f.write("----------------\n")
        for r in results:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"{r['method']} {path}\n")
            if not r.get("ok"):
                f.write(f"ERROR: {r.get('error','unknown error')}\n")
                continue

            f.write(f"HTTP/{r['http_version']} {r['status']} {r['reason']}\n\n")
            f.write("Headers:\n")
            for k, v in r["headers"].items():
                f.write(f"  {k}: {v}\n")

            f.write(f"\nBody length: {r['body_len']} bytes\n")
            if r["body_preview"]:
                f.write(f"Body preview (first {BODY_PREVIEW_CHARS} chars):\n")
                f.write(r["body_preview"])
                f.write("\n")
            else:
                f.write("Body preview: (empty)\n")

    return out_path


# -----------------------------
# Scan runner (used by GUI)
# -----------------------------
def run_scan(host: str, port: int, path: str, timeout: int, log_fn):
    """
    Runs the verb tests and returns (results, report_path).
    log_fn(msg) is used to update UI/log.
    """
    path = normalize_path(path)
    results = []

    log_fn(f"Target: {host}:{port}  Path: {path}")
    log_fn(f"Testing verbs: {', '.join(VERBS_TO_TEST)}")
    log_fn("")

    for method in VERBS_TO_TEST:
        try:
            log_fn(f"-> {method} {path}")
            r = send_http_request(host, port, method, path, timeout)
            allow = get_header_case_insensitive(r["headers"], "Allow")
            loc = get_header_case_insensitive(r["headers"], "Location")
            log_fn(f"   {r['status']} {r['reason']}  Allow={allow or '-'}  Location={loc or '-'}  BodyLen={r['body_len']}")
            results.append(r)
        except Exception as e:
            results.append({"ok": False, "method": method, "error": str(e)})
            log_fn(f"   ERROR: {e}")

    report_path = write_txt_report(host, port, path, results)
    log_fn("\n✅Sanning Done.")
    log_fn(f"Saved report: {report_path}")

    return results, report_path


# -----------------------------
# GUI Wizard (Tkinter)
# -----------------------------
def start_gui():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except Exception:
        # Fallback to CLI if Tkinter is missing
        return start_cli_fallback()

    class Wizard(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("HTTP Verb Tester - Wizard")
            self.geometry("800x520")

            self.host_var = tk.StringVar(value="")
            self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
            self.path_var = tk.StringVar(value=DEFAULT_PATH)

            self.step = 1
            self._build_ui()

        def _build_ui(self):
            self.container = ttk.Frame(self, padding=16)
            self.container.pack(fill="both", expand=True)

            self.header = ttk.Label(self.container, text="Step 1/3 - Enter Host", font=("Arial", 14, "bold"))
            self.header.pack(anchor="w")

            self.body = ttk.Frame(self.container)
            self.body.pack(fill="both", expand=True, pady=(12, 8))

            # Nav buttons
            nav = ttk.Frame(self.container)
            nav.pack(fill="x")

            self.back_btn = ttk.Button(nav, text="Back", command=self.on_back, state="disabled")
            self.back_btn.pack(side="left")

            self.next_btn = ttk.Button(nav, text="Next", command=self.on_next)
            self.next_btn.pack(side="right")

            self._render_step()

        def _clear_body(self):
            for w in self.body.winfo_children():
                w.destroy()

        def _render_step(self):
            self._clear_body()

            if self.step == 1:
                self.header.config(text="Step 1/3 - Enter Host (IP or hostname)")
                ttk.Label(self.body, text="Example: 192.168.1.16").pack(anchor="w", pady=(0, 6))
                entry = ttk.Entry(self.body, textvariable=self.host_var, width=40)
                entry.pack(anchor="w")
                entry.focus_set()

                self.back_btn.config(state="disabled")
                self.next_btn.config(text="Next")

            elif self.step == 2:
                self.header.config(text="Step 2/3 - Enter Port")
                ttk.Label(self.body, text="Default is 80 for Metasploitable web service.").pack(anchor="w", pady=(0, 6))
                entry = ttk.Entry(self.body, textvariable=self.port_var, width=10)
                entry.pack(anchor="w")
                entry.focus_set()

                self.back_btn.config(state="normal")
                self.next_btn.config(text="Next")

            elif self.step == 3:
                self.header.config(text="Step 3/3 - Enter Path")
                ttk.Label(self.body, text='Examples: /  |  /dvwa/  |  /phpMyAdmin/  |  /phpMyAdmin/index.php').pack(anchor="w", pady=(0, 6))
                entry = ttk.Entry(self.body, textvariable=self.path_var, width=60)
                entry.pack(anchor="w")
                entry.focus_set()

                self.back_btn.config(state="normal")
                self.next_btn.config(text="Run")

        def on_back(self):
            if self.step > 1:
                self.step -= 1
                self._render_step()

        def on_next(self):
            # Validate each step
            if self.step == 1:
                host = self.host_var.get().strip()
                if not host:
                    messagebox.showerror("Input error", "Host cannot be empty.")
                    return
                self.step = 2
                self._render_step()
                return

            if self.step == 2:
                try:
                    port = int(self.port_var.get().strip())
                    if not (1 <= port <= 65535):
                        raise ValueError
                except Exception:
                    messagebox.showerror("Input error", "Port must be a number between 1 and 65535.")
                    return
                self.step = 3
                self._render_step()
                return

            if self.step == 3:
                # Run scan in a new window with live logs
                host = self.host_var.get().strip()
                port = int(self.port_var.get().strip())
                path = normalize_path(self.path_var.get())

                self._open_runner_window(host, port, path)

        def _open_runner_window(self, host: str, port: int, path: str):
            from tkinter.scrolledtext import ScrolledText

            runner = tk.Toplevel(self)
            runner.title("Running scan...")
            runner.geometry("860x560")

            ttk.Label(runner, text=f"Target: {host}:{port}  Path: {path}", font=("Arial", 11, "bold")).pack(anchor="w", padx=12, pady=(12, 6))

            log_box = ScrolledText(runner, wrap="word")
            log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            log_box.configure(state="disabled")

            def log(msg: str):
                log_box.configure(state="normal")
                log_box.insert("end", msg + "\n")
                log_box.see("end")
                log_box.configure(state="disabled")

            def worker():
                try:
                    run_scan(host, port, path, DEFAULT_TIMEOUT_SEC, log)
                    log("\nTip: Open the .txt report and compare status codes, Allow/Location/Set-Cookie across verbs.")
                except Exception:
                    log("\nFATAL ERROR:\n" + traceback.format_exc())

            threading.Thread(target=worker, daemon=True).start()

    app = Wizard()
    app.mainloop()


# -----------------------------
# CLI fallback (if no Tkinter)
# -----------------------------
def start_cli_fallback():
    print("Tkinter not available. Falling back to CLI mode.\n")

    host = input("Host/IP: ").strip()
    while not host:
        host = input("Host/IP (cannot be empty): ").strip()

    port_s = input(f"Port (default {DEFAULT_PORT}): ").strip()
    port = DEFAULT_PORT if not port_s else int(port_s)

    path = input(f'Path (default "{DEFAULT_PATH}"): ').strip() or DEFAULT_PATH
    path = normalize_path(path)

    def log(msg: str):
        print(msg)

    run_scan(host, port, path, DEFAULT_TIMEOUT_SEC, log)


# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    start_gui()
