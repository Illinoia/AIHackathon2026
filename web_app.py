#!/usr/bin/env python3
"""
sai-web — local web interface to control a Sai AI agent over Telegram.

  * Upload files (resume, transcript, syllabi, ...) -> forwarded to the Sai bot
  * "Grill session" chat -> messages relayed to the agent, replies streamed back
  * DOWNLOAD files the agent sends back (generated resume / cover letter, etc.)
  * Reuses the same Telethon session / config.json as sai_cli.py

Run:    python web_app.py        # then open http://127.0.0.1:5000
Deps:   pip install telethon flask   (Arch: yay -S python-telethon python-flask)
Config: same config.json as the CLI (api_id, api_hash, target) or env vars
        SAI_TG_API_ID / SAI_TG_API_HASH / SAI_TG_TARGET
"""
import asyncio, json, os, sys, threading, shutil
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    sys.exit("Flask not installed. Run:  pip install flask   (Arch: yay -S python-flask)")
try:
    from telethon import TelegramClient, events
except ImportError:
    sys.exit("Telethon not installed. Run:  pip install telethon   (Arch: yay -S python-telethon)")

HERE = Path(__file__).resolve().parent
SESSION_PATH = str(HERE / "sai_session")
CONFIG_PATH = HERE / "config.json"
UPLOAD_DIR = HERE / "uploads"
DOWNLOAD_DIR = HERE / "downloads"
# The Sai AGENT lives in its SimularFiles directory: it reads the files the user
# sends from SimularFiles/uploads and SAVES generated docs (resume/cover letter) into
# SimularFiles/artifacts. Resolve that directory ABSOLUTELY so the files bar always
# shows the AGENT's output — never files from wherever this app happens to be run
# (e.g. the Desktop). Override with the SAI_AGENT_FILES env var if needed.
def _resolve_sai_files():
    env = os.getenv("SAI_AGENT_FILES")
    if env:
        return Path(env)
    appdata = os.getenv("APPDATA")  # Windows
    if appdata:
        p = Path(appdata) / "simular-unified-ui" / "SimularFiles"
        if p.exists():
            return p
    home = Path.home() / "AppData" / "Roaming" / "simular-unified-ui" / "SimularFiles"
    if home.exists():
        return home
    return HERE.parent.parent  # fallback to the old layout assumption

SAI_FILES_DIR = _resolve_sai_files()
ARTIFACT_DIR = SAI_FILES_DIR / "artifacts"
AGENT_INTAKE_DIR = SAI_FILES_DIR / "uploads"
# Extensions we treat as downloadable generated documents.
DOC_EXTS = {".md", ".pdf", ".docx", ".doc", ".txt", ".rtf"}
UPLOAD_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Sai Grill Session — via Telegram</title>
<style>
  :root { --bg:#0e1116; --panel:#171b22; --accent:#3b82f6; --you:#2563eb; --sai:#2a2f3a; --text:#e6e9ef; --muted:#8b93a3; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; background:var(--bg); color:var(--text); height:100vh; display:flex; flex-direction:column; }
  header { padding:14px 20px; background:var(--panel); border-bottom:1px solid #232833; display:flex; align-items:center; gap:10px; }
  header h1 { font-size:16px; margin:0; font-weight:600; }
  header .dot { width:9px; height:9px; border-radius:50%; background:#22c55e; }
  header .sub { color:var(--muted); font-size:12px; margin-left:auto; }
  #log { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:12px; }
  .msg { max-width:72%; padding:10px 14px; border-radius:14px; line-height:1.45; white-space:pre-wrap; word-wrap:break-word; font-size:14px; }
  .you { align-self:flex-end; background:var(--you); border-bottom-right-radius:4px; }
  .sai { align-self:flex-start; background:var(--sai); border-bottom-left-radius:4px; }
  .role { font-size:11px; color:var(--muted); margin:0 6px 2px; }
  .you-wrap,.sai-wrap { display:flex; flex-direction:column; }
  .you-wrap { align-items:flex-end; } .sai-wrap { align-items:flex-start; }
  .filelink { display:inline-flex; align-items:center; gap:8px; margin-top:6px; padding:9px 13px; background:#1f2937; border:1px solid #374151; border-radius:10px; color:#93c5fd; text-decoration:none; font-size:13px; font-weight:600; }
  .filelink:hover { background:#263244; }
  footer { padding:14px 20px; background:var(--panel); border-top:1px solid #232833; display:flex; flex-direction:column; gap:10px; }
  .row { display:flex; gap:10px; align-items:center; }
  #text { flex:1; resize:none; height:44px; padding:11px 14px; border-radius:10px; border:1px solid #2a2f3a; background:#0e1116; color:var(--text); font-size:14px; font-family:inherit; }
  button { background:var(--accent); color:#fff; border:none; border-radius:10px; padding:0 18px; height:44px; font-size:14px; font-weight:600; cursor:pointer; }
  button:disabled { opacity:.5; cursor:default; }
  .upload { display:flex; gap:8px; align-items:center; font-size:13px; color:var(--muted); }
  .uploadbtn { background:#374151; height:36px; padding:0 14px; font-size:13px; }
  .hint { font-size:11px; color:var(--muted); }
  .typing-wrap { display:flex; flex-direction:column; align-items:flex-start; }
  .typing { align-self:flex-start; background:var(--sai); border-bottom-left-radius:4px; padding:13px 16px; border-radius:14px; display:flex; gap:5px; align-items:center; }
  .typing span { width:7px; height:7px; border-radius:50%; background:var(--muted); display:inline-block; animation:blink 1.4s infinite both; }
  .typing span:nth-child(2){ animation-delay:.2s; }
  .typing span:nth-child(3){ animation-delay:.4s; }
  @keyframes blink { 0%,80%,100%{ opacity:.25; transform:translateY(0); } 40%{ opacity:1; transform:translateY(-4px); } }
  /* quick actions */
  .quick { display:flex; gap:8px; flex-wrap:wrap; }
  .quick button { height:34px; padding:0 13px; font-size:12.5px; background:#374151; font-weight:600; }
  .quick button:hover { background:#445063; }
</style>
</head>
<body>
  <header>
    <span class="dot"></span>
    <h1>Sai Grill Session</h1>
    <span class="sub">relayed to your Sai agent over Telegram</span>
  </header>
  <div id="log"></div>
  <div id="filesbar" style="padding:8px 20px;background:#12161d;border-top:1px solid #232833;">
    <div style="font-size:11px;color:var(--muted);margin-bottom:6px;">📥 Generated files (click to download)</div>
    <div id="files" style="display:flex;flex-wrap:wrap;gap:8px;"></div>
    <div id="files-empty" style="font-size:12px;color:var(--muted);">No generated files yet — they'll appear here when Sai creates them.</div>
  </div>
  <footer>
    <div class="quick">
      <button type="button" data-msg="Let's start a grill session so you can learn more about me.">🎤 Start grill</button>
      <button type="button" data-needmaterial="1" data-msg="I want to add more information to my profile.">📎 Add info</button>
      <button type="button" data-needmaterial="1" data-marks-list="1" data-msg="Please generate my ranked list of suitable jobs.">📋 Generate job list</button>
      <button type="button" data-needmaterial="1" data-msg="Please generate a general resume and cover letter for me, without tailoring to a specific job.">📄 Generate resume/cover letter</button>
      <button type="button" data-needlist="1" data-msg="I'd like to tailor a resume and cover letter for a job from the list.">✍️ Tailor for a job</button>
      <button type="button" data-needresume="1" data-msg="I'd like to apply to a job on LinkedIn using Easy Apply, using the resume that was just generated. Ask me which job from my list, fill in the application, then show me a summary of the exact answers you'll submit and WAIT for me to reply 'yes' here in this chat before you submit. Do NOT rely on a separate approval dialog or any auto-approve mechanism — get my confirmation as a normal chat reply first.">🚀 Apply to a job</button>
    </div>
    <div class="upload">
      <input type="file" id="file" multiple />
      <button class="uploadbtn" id="uploadBtn" type="button">Upload &amp; send file(s)</button>
      <span class="hint" id="uploadStatus"></span>
    </div>
    <div class="row">
      <textarea id="text" placeholder="Answer the grill questions or type a message… (Enter to send, Shift+Enter for newline)"></textarea>
      <button id="sendBtn" type="button">Send</button>
    </div>
  </footer>
<script>
let lastId = 0;
const log = document.getElementById('log');
const text = document.getElementById('text');
const sendBtn = document.getElementById('sendBtn');
const fileInput = document.getElementById('file');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');

let intakeReady = false; // true once the user has uploaded a file or started the grill
let listReady = false;   // true once a job list has been generated (gates "Tailor for a job")
let resumeReady = false; // true once a general/tailored resume file exists (gates "Apply to a job")
function gateButtons() {
  // "Start grill" is always available. data-needmaterial buttons appear once the user
  // has provided material (uploaded a file) or started interacting. data-needlist
  // buttons ("Tailor for a job") appear only AFTER a job list has been generated.
  document.querySelectorAll('.quick button').forEach(b => {
    if (b.dataset.needresume === '1') { b.style.display = resumeReady ? '' : 'none'; return; }
    if (b.dataset.needlist === '1') { b.style.display = listReady ? '' : 'none'; return; }
    const gated = b.dataset.needmaterial === '1';
    b.style.display = (!gated || intakeReady) ? '' : 'none';
  });
}
const STAGE_RE = /STAGE:\s*(INTAKE|GRILL|LIST|TAILOR|APPLY)/i;
const MATERIAL_RE = /MATERIAL:\s*(ready|yes|1|true)/i;

function addMsg(msg) {
  const role = msg.role;
  const wrap = document.createElement('div');
  wrap.className = role === 'you' ? 'you-wrap' : 'sai-wrap';
  const r = document.createElement('div'); r.className = 'role'; r.textContent = role === 'you' ? 'You' : 'Sai';
  wrap.appendChild(r);
  if (msg.text) {
    let t = msg.text;
    const sm = t.match(STAGE_RE);
    if (sm && /^(LIST|TAILOR|APPLY)$/i.test(sm[1])) { listReady = true; gateButtons(); }
    t = t.replace(STAGE_RE, '').replace(/^[\s\n]+/, '').trim();  // strip STAGE marker from display
    const mm = t.match(MATERIAL_RE);
    if (mm) { intakeReady = true; gateButtons(); t = t.replace(MATERIAL_RE, '').replace(/^[\s\n]+/, '').trim(); }
    if (t) { const m = document.createElement('div'); m.className = 'msg ' + role; m.textContent = t; wrap.appendChild(m); }
  }
  if (msg.file) {
    const a = document.createElement('a'); a.className = 'filelink';
    a.href = '/api/download/' + encodeURIComponent(msg.file); a.download = msg.file;
    a.textContent = '\u2B07\uFE0F  ' + msg.file; wrap.appendChild(a);
    if (!resumeReady && /resume/i.test(msg.file)) { resumeReady = true; gateButtons(); }
  }
  log.appendChild(wrap); log.scrollTop = log.scrollHeight;
}

let typingEl = null;
function showTyping() {
  if (typingEl) return;
  typingEl = document.createElement('div');
  typingEl.className = 'typing-wrap';
  const r = document.createElement('div'); r.className = 'role'; r.textContent = 'Sai';
  const b = document.createElement('div'); b.className = 'typing';
  b.innerHTML = '<span></span><span></span><span></span>';
  typingEl.appendChild(r); typingEl.appendChild(b);
  log.appendChild(typingEl); log.scrollTop = log.scrollHeight;
}
function hideTyping() {
  if (typingEl) { typingEl.remove(); typingEl = null; }
}

async function poll() {
  try {
    const res = await fetch('/api/messages?after=' + lastId);
    const data = await res.json();
    for (const msg of data.messages) { if (msg.role === 'sai') hideTyping(); addMsg(msg); lastId = Math.max(lastId, msg.id); }
  } catch (e) {}
}
setInterval(poll, 1500); poll();

async function send() {
  const t = text.value.trim(); if (!t) return;
  sendBtn.disabled = true;
  try {
    const res = await fetch('/api/send', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ text: t }) });
    if (res.ok) { text.value = ''; intakeReady = true; gateButtons(); await poll(); showTyping(); } else { const e = await res.json(); alert('Send failed: ' + (e.error||res.status)); }
  } finally { sendBtn.disabled = false; text.focus(); }
}
sendBtn.onclick = send;
text.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

uploadBtn.onclick = async () => {
  const files = fileInput.files;
  if (!files.length) { uploadStatus.textContent = 'Choose file(s) first.'; return; }
  uploadBtn.disabled = true;
  for (const f of files) {
    uploadStatus.textContent = 'Uploading ' + f.name + '…';
    const fd = new FormData(); fd.append('file', f);
    try {
      const res = await fetch('/api/upload', { method:'POST', body: fd });
      if (!res.ok) { const e = await res.json(); uploadStatus.textContent = 'Failed: ' + (e.error||res.status); } else { intakeReady = true; gateButtons(); poll(); }
    } catch (e) { uploadStatus.textContent = 'Error: ' + e.message; }
  }
  uploadStatus.textContent = 'Done.'; fileInput.value = ''; uploadBtn.disabled = false;
};

document.querySelectorAll('.quick button').forEach(btn => {
  btn.onclick = () => { if (btn.dataset.marksList === '1') { listReady = true; gateButtons(); } text.value = btn.dataset.msg; send(); };
});
gateButtons(); // reveal Start grill; gated buttons appear after upload or first message

const filesbar = document.getElementById('filesbar');
const filesDiv = document.getElementById('files');
async function pollFiles() {
  try {
    const res = await fetch('/api/files');
    const data = await res.json();
    const empty = document.getElementById('files-empty');
    filesDiv.innerHTML = '';
    if (data.files && data.files.length) {
      if (empty) empty.style.display = 'none';
      for (const name of data.files) {
        const a = document.createElement('a');
        a.className = 'filelink';
        a.href = '/api/download/' + encodeURIComponent(name);
        a.download = name;
        a.textContent = '\u2B07\uFE0F  ' + name;
        filesDiv.appendChild(a);
      }
      if (!resumeReady && data.files.some(n => /resume/i.test(n))) { resumeReady = true; gateButtons(); }
    } else if (empty) { empty.style.display = ''; }
  } catch (e) {}
}
setInterval(pollFiles, 3000); pollFiles();
</script>
</body>
</html>"""


def clean_slate():
    """Wipe local per-session state so every run starts fresh.
    Removes uploaded + downloaded files. Keeps config.json and the
    Telegram login session (sai_session) so you stay authenticated.
    Set env SAI_KEEP_FILES=1 to skip this."""
    if os.getenv("SAI_KEEP_FILES") == "1":
        return
    for d in (UPLOAD_DIR, DOWNLOAD_DIR):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        d.mkdir(exist_ok=True)
    # Also clear the Sai agent's own intake folder (SimularFiles/uploads) so the
    # agent can't pick up stale files the user uploaded in a previous session.
    intake_cleared = 0
    if AGENT_INTAKE_DIR.exists() and AGENT_INTAKE_DIR.resolve() != UPLOAD_DIR.resolve():
        for p in AGENT_INTAKE_DIR.iterdir():
            try:
                if p.is_file():
                    p.unlink(); intake_cleared += 1
                elif p.is_dir():
                    shutil.rmtree(p, ignore_errors=True); intake_cleared += 1
            except Exception:
                pass
    # Also remove generated deliverables (resume/cover docs) that the
    # "Generated files" panel surfaces from the artifacts folder, so the
    # panel starts empty each run. Uses the same filter as api_files().
    removed = 0
    if ARTIFACT_DIR.exists():
        for p in ARTIFACT_DIR.iterdir():
            if not (p.is_file() and p.suffix.lower() in DOC_EXTS):
                continue
            low = p.name.lower()
            if "template" in low or low == "readme.md":
                continue
            if not ("resume" in low or "cover" in low):
                continue
            try:
                p.unlink(); removed += 1
            except Exception:
                pass
    print(f"[clean slate] cleared uploads/, downloads/, {intake_cleared} agent-intake item(s), and {removed} generated doc(s)")


def load_config():
    cfg = {}
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for k, env in (("api_id","SAI_TG_API_ID"),("api_hash","SAI_TG_API_HASH"),("target","SAI_TG_TARGET")):
        if os.getenv(env):
            cfg[k] = os.getenv(env)
    for k in ("api_id","api_hash","target"):
        if not cfg.get(k):
            sys.exit(f"Missing '{k}'. Set it in config.json or env vars.")
    return cfg


class TgBridge:
    """Runs a Telethon client in a private asyncio loop on a worker thread."""
    def __init__(self, cfg):
        self.cfg = cfg
        self.loop = asyncio.new_event_loop()
        self.client = None
        self.entity = None
        self.messages = []          # {id, role, text?, file?}
        self._next_id = 1
        self._lock = threading.Lock()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _add(self, role, text=None, file=None):
        with self._lock:
            mid = self._next_id; self._next_id += 1
            self.messages.append({"id": mid, "role": role, "text": text, "file": file})
        return mid

    def get_since(self, after_id):
        with self._lock:
            return [m for m in self.messages if m["id"] > after_id]

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start())
        self.loop.run_forever()

    async def _start(self):
        target = self.cfg["target"]
        if isinstance(target, str) and target.lstrip("-").isdigit():
            target = int(target)
        self.client = TelegramClient(SESSION_PATH, int(self.cfg["api_id"]), str(self.cfg["api_hash"]))
        await self.client.start()
        self.entity = await self.client.get_entity(target)

        # Register the reply handler FIRST, before sending anything, so the
        # agent's response to the reset/welcome is never missed. (Previously this
        # was registered AFTER the reset send, so the first reply could be lost.)
        @self.client.on(events.NewMessage(from_users=self.entity))
        async def _on_reply(event):
            msg = event.message
            # text part
            if msg.message:
                self._add("sai", text=msg.message)
            # file/document part -> download and expose
            if msg.media:
                try:
                    saved = await self.client.download_media(msg, file=str(DOWNLOAD_DIR) + os.sep)
                    if saved:
                        self._add("sai", file=Path(saved).name)
                except Exception as e:
                    self._add("sai", text=f"[failed to download attachment: {e}]")

        # Local welcome / starting message (always shown as the first bubble,
        # added before the reset so it can't be lost). Matches the gated flow:
        # only upload or grill are available at intake.
        self._add("sai", text=(
            "\U0001F44B Welcome! Let's start your job hunt. First, tell me about yourself:\n\n"
            "\u2022 \U0001F4CE Upload your resume / transcript (use the upload button below), or\n"
            "\u2022 \U0001F3A4 Start a grill session and I'll ask a few quick questions.\n\n"
            "Once I have your background, you'll be able to generate a ranked job list or a resume / cover letter."
        ))

        # Reset the agent's context so each app run starts fresh. The handler is
        # already active above, so the agent's reply will be captured.
        # Disable with env SAI_NO_RESET=1.
        if os.getenv("SAI_NO_RESET") != "1":
            try:
                await self.client.send_message(
                    self.entity,
                    "[NEW SESSION] Please forget all previous context and conversation "
                    "history. We are starting a brand-new session from a clean slate."
                )
            except Exception as e:
                print(f"[reset] could not send reset message: {e}")

        self.ready.set()

    def send_text(self, text):
        self.ready.wait(timeout=30)
        asyncio.run_coroutine_threadsafe(self.client.send_message(self.entity, text), self.loop).result(timeout=30)
        self._add("you", text=text)

    def send_file(self, path, caption=None):
        self.ready.wait(timeout=30)
        asyncio.run_coroutine_threadsafe(self.client.send_file(self.entity, path, caption=caption or ""), self.loop).result(timeout=120)
        self._add("you", text=f"\U0001F4CE Sent file: {Path(path).name}")

    def start(self):
        self.thread.start()


app = Flask(__name__)
bridge = None


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/messages")
def api_messages():
    after = int(request.args.get("after", 0))
    return jsonify({"messages": bridge.get_since(after)})


@app.route("/api/send", methods=["POST"])
def api_send():
    text = (request.json or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400
    try:
        bridge.send_text(text); return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    dest = UPLOAD_DIR / f.filename
    f.save(dest)
    try:
        bridge.send_file(str(dest), caption=request.form.get("caption", ""))
        return jsonify({"ok": True, "name": f.filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<path:name>")
def api_download(name):
    # Serve from downloads/ (Telegram-delivered) first, then artifacts/ (agent-generated).
    safe = os.path.basename(name)
    if (DOWNLOAD_DIR / safe).is_file():
        return send_from_directory(DOWNLOAD_DIR, safe, as_attachment=True)
    if (ARTIFACT_DIR / safe).is_file() and Path(safe).suffix.lower() in DOC_EXTS:
        return send_from_directory(ARTIFACT_DIR, safe, as_attachment=True)
    return jsonify({"error": "not found"}), 404


@app.route("/api/files")
def api_files():
    # Files the agent sent via Telegram (downloads/) PLUS generated docs the
    # agent saved into the artifacts folder (no Telegram round-trip needed).
    seen, files = set(), []
    for p in sorted(DOWNLOAD_DIR.iterdir()) if DOWNLOAD_DIR.exists() else []:
        if p.is_file() and p.name not in seen:
            seen.add(p.name); files.append(p.name)
    for p in sorted(ARTIFACT_DIR.iterdir()) if ARTIFACT_DIR.exists() else []:
        if not (p.is_file() and p.suffix.lower() in DOC_EXTS):
            continue
        low = p.name.lower()
        # Only surface real generated deliverables (resume/cover letter);
        # never list unrelated documents that happen to sit in the folder.
        if "template" in low or low == "readme.md":
            continue
        if not ("resume" in low or "cover" in low):
            continue
        if p.name not in seen:
            seen.add(p.name); files.append(p.name)
    return jsonify({"files": files})


def main():
    global bridge
    clean_slate()
    cfg = load_config()
    bridge = TgBridge(cfg); bridge.start()
    print("Open http://127.0.0.1:5000  (make sure you've run 'python sai_cli.py login' first)")
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()