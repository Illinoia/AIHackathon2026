# sai-tg — CLI control for a Sai agent over Telegram

Programmatically drive your Sai AI agent from the command line by talking to it
through Telegram. The CLI logs in as **your** Telegram user account and sends
DMs to the Sai bot, then reads the agent's replies.

## 1. Link Sai to Telegram (one time)
In the Sai app go to **Settings -> Messaging -> Link Telegram** and follow the
steps. After linking you'll have a Sai bot you can DM. Note its @username.

## 2. Get Telegram API credentials (one time)
Go to https://my.telegram.org -> **API development tools** and create an app.
Copy the **api_id** and **api_hash**.

## 3. Install (Arch Linux)
Install the Telethon dependency with your AUR helper (e.g. `yay` or `paru`).
`python-telethon` lives in the official **extra** repo, but an AUR helper
resolves it the same way:
```bash
yay -S python-telethon
# or, straight from the official repo:
# sudo pacman -S python-telethon
```
Then just run the script directly:
```bash
cd sai-telegram-cli
python sai_cli.py --help
```

## 4. Configure
Copy the template and fill it in:
```bash
cp config.example.json config.json
```
```json
{
  "api_id": "123456",
  "api_hash": "your_api_hash",
  "target": "@YourSaiBot"
}
```
Or use environment variables instead: `SAI_TG_API_ID`, `SAI_TG_API_HASH`, `SAI_TG_TARGET`.

## 5. Authenticate
```bash
python sai_cli.py login
```
Enter your phone number, the Telegram login code, and 2FA password if set.
A local `sai_session.session` file is created so you won't re-login each time.

## Usage
```bash
# Send one instruction and print the agent's reply
python sai_cli.py send "What's on my calendar today?"

# Custom reply timeout (agent tasks can take a while)
python sai_cli.py ask "Summarize my unread emails" --timeout 300

# Interactive conversation
python sai_cli.py chat

# Stream everything the agent sends
python sai_cli.py watch

# Show account + target
python sai_cli.py whoami
```

On Windows you can also use the bundled `sai-tg.cmd` wrapper:
```bat
sai-tg send "hello"
```

## How it works
- Auth: Telegram MTProto via Telethon (acts as your user account).
- `send/ask` registers a one-shot handler, sends your message, and resolves on
  the next inbound message from the target (with a timeout).
- `chat` keeps the connection open for a back-and-forth REPL.
- `watch` just prints inbound messages as they arrive.

## Notes & limits
- The session file is a credential — keep it private; add it to .gitignore.
- Reply matching is "next inbound message from the bot"; if the agent sends
  multiple chunks, `watch` or `chat` show all of them.
- Respect Telegram's terms; this uses your personal account.

---

## Web interface (upload files + grill session)

A local web UI that lets you **upload files** (resume, transcript, syllabi) and run a
**grill session** chat — everything is relayed to your Sai agent over Telegram, and
replies stream back into the page.

### Install (Arch)
```bash
yay -S python-telethon python-flask
```
(or: `pip install -r requirements.txt`)

### Run
```bash
python sai_cli.py login      # one-time, if you haven't already
python web_app.py            # starts the server
```
Then open **http://127.0.0.1:5000** in your browser.

- **Upload & send file(s)** — pick one or more files; each is sent to the Sai bot as a Telegram document.
- **Chat box** — type answers to the grill questions (Enter to send, Shift+Enter for newline). Sai's replies appear in the thread.
- Uses the **same `config.json` and session** as the CLI. Uploaded files are also saved under `./uploads/`.

> Note: the server binds to 127.0.0.1 (local only). Don't expose it publicly — it can send messages as your Telegram account.

---

## Importing the job-application skills (recommended)

This project pairs with two **Sai skills** bundled in `job-application-skills.zip` (included in this folder):

| Skill | What it does |
|---|---|
| `linkedin-easy-apply` | Applies to LinkedIn Easy Apply jobs — fresh login via secure portal each attempt, researches the company to answer screening questions, and requires a final confirmation before submitting. |
| `tailored-resume-cover-letter` | Turns the included Markdown templates into a job-tailored resume + cover letter (researches the company for motivation, assumes MS Office, always upsells skills). |

### How to install
1. Open the **Sai app**.
2. Go to **Settings -> Import skill**.
3. Select **`job-application-skills.zip`** (in this project folder).
4. The two skills now appear in your skill catalog and are ready to use.

> **No credentials are bundled.** On first use, Sai will prompt you to connect your own accounts (e.g. LinkedIn login via the secure input portal). Your data stays yours.

## Resume & cover-letter templates

The `templates/` folder contains the Markdown and DOCX templates the `tailored-resume-cover-letter` skill fills in. See `templates/` for all formats.
