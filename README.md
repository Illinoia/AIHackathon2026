# sai-tg — Telegram control + AI resume / cover-letter / auto-apply for Sai

A companion toolkit for the **Sai** AI agent that does two things:

1. **CLI + web control over Telegram** — drive your Sai agent from the command
   line or a local web UI by relaying messages through Telegram.
2. **Job-application automation** — a set of Sai skills + templates that
   generate **tailored resumes & cover letters** and **auto-apply** to LinkedIn
   Easy Apply jobs.

You can use either half on its own, but they're designed to work together: run a
**grill session** and upload your materials through the web UI, let the
`tailored-resume-cover-letter` skill produce job-specific documents, then have
`linkedin-easy-apply` submit them.

---

## Part A — Telegram control (CLI + web UI)

Programmatically drive your Sai agent by talking to it through Telegram. The CLI
logs in as **your** Telegram user account, DMs the Sai bot, and reads the
agent's replies.

### 1. Link Sai to Telegram (one time)
In the Sai app go to **Settings -> Messaging -> Link Telegram** and follow the
steps. After linking you'll have a Sai bot you can DM. Note its @username.

### 2. Get Telegram API credentials (one time)
Go to https://my.telegram.org -> **API development tools** and create an app.
Copy the **api_id** and **api_hash**.

### 3. Install (Arch Linux, via pip)
Arch enforces PEP 668, so install into a **virtual environment** with pip rather
than system-wide. From the project folder:
```bash
cd sai-telegram-cli

# create & activate a venv
python -m venv .venv
source .venv/bin/activate

# install dependencies with pip
pip install -r requirements.txt
```
> Prefer system packages instead? You can use pacman/AUR:
> `sudo pacman -S python-telethon python-flask` (then skip the venv).
> But the pip + venv route above is the recommended, self-contained method.

Re-activate the venv (`source .venv/bin/activate`) in any new shell before
running the commands below.

### 4. Configure
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
Or use environment variables: `SAI_TG_API_ID`, `SAI_TG_API_HASH`, `SAI_TG_TARGET`.

### 5. Authenticate
```bash
python sai_cli.py login
```
Enter your phone number, the Telegram login code, and 2FA password if set. A
local `sai_session.session` file is created so you won't re-login each time.

### CLI usage
```bash
python sai_cli.py send "What's on my calendar today?"
python sai_cli.py ask "Summarize my unread emails" --timeout 300
python sai_cli.py chat        # interactive REPL
python sai_cli.py watch       # stream everything the agent sends
python sai_cli.py whoami      # show account + target
```
On Windows, the bundled `sai-tg.cmd` wrapper works too: `sai-tg send "hello"`.

### Web interface (upload files + grill session)
A local web UI to **upload files** (resume, transcript, syllabi) and run a
**grill session** chat — relayed to your Sai agent over Telegram, with replies
streaming back into the page.
```bash
python sai_cli.py login      # one-time, if not done
python web_app.py            # starts the server
```
Open **http://127.0.0.1:5000**. Uploaded files go to the Sai bot as documents
and are saved under `./uploads/`. Uses the same `config.json`/session as the CLI.

> The server binds to 127.0.0.1 (local only). Don't expose it publicly — it can
> send messages as your Telegram account.

### How it works
- Auth: Telegram MTProto via Telethon (acts as your user account).
- `send/ask` registers a one-shot handler, sends your message, and resolves on
  the next inbound message from the target (with a timeout).
- `chat` keeps the connection open; `watch` prints inbound messages as they arrive.

---

## Part B — Resume, cover letter & auto-apply

The other half of the project: turn your background into **tailored,
job-specific application documents** and **auto-apply** to matching roles.

### The Sai skills
Two skills are bundled in `dist/job-application-skills.zip` (source also in
`skills/`):

| Skill | What it does |
|---|---|
| `tailored-resume-cover-letter` | Generates a job-tailored resume + cover letter from your materials. Researches the company for genuine motivation, assumes MS Office proficiency, and always upsells your skills (quantitative where measurable, qualitative otherwise). Fills the `templates/`. |
| `linkedin-easy-apply` | Auto-applies to LinkedIn Easy Apply jobs. Fresh login via the secure portal each attempt, researches the company to answer screening questions, and requires a **final confirmation before submitting**. |

### Install the skills
1. Open the **Sai app**.
2. Go to **Settings -> Import skill**.
3. Select **`dist/job-application-skills.zip`**.
4. The two skills appear in your catalog, ready to use.

> **No credentials are bundled.** On first use, Sai prompts you to connect your
> own accounts (e.g. LinkedIn login via the secure input portal). Your data stays yours.

### Templates
The `templates/` folder holds the resume/cover-letter templates (Markdown + DOCX)
that `tailored-resume-cover-letter` fills in:
- `resume.template.md`, `cover-letter.template.md`, `cover-letter-email.template.md`
- `Resume_Template_GENERAL.docx`, `Cover_Letter_Template_GENERAL.docx`,
  `Cover_Letter_EMAIL_Template.docx`, `Cover_Letter_EMAIL_Template.txt`

### Typical end-to-end flow
1. `python web_app.py` -> upload your resume/transcript and run the grill session.
2. Let `tailored-resume-cover-letter` produce job-specific docs into the templates.
3. Let `linkedin-easy-apply` find Easy Apply roles and submit (with your final OK).

---

## Notes & security
- `config.json` and `*.session` are credentials — keep them private (already in `.gitignore`).
- Respect Telegram's and LinkedIn's terms; the tools act as your personal accounts.
