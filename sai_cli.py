#!/usr/bin/env python3
"""
sai-tg — a local CLI to programmatically control a Sai AI agent over Telegram.

Sai is reachable as a Telegram bot once you link it in the Sai app
(Settings -> Messaging -> Link Telegram). This tool acts as YOUR Telegram
user account, sending DMs to that bot and reading its replies, so you can
script / automate the agent from the command line.

Auth uses Telegram MTProto via Telethon. You need an api_id + api_hash from
https://my.telegram.org (Login -> API development tools).

Commands:
  sai-tg login                 Authenticate & create a local session
  sai-tg send "text"           Send one message, wait for & print the reply
  sai-tg ask "text" [--timeout N]  Same as send, with custom reply timeout
  sai-tg chat                  Interactive REPL with the agent
  sai-tg watch                 Stream all incoming messages from the bot
  sai-tg whoami                Show logged-in account + configured target

Config resolution order (highest first):
  1. CLI flags
  2. Environment variables: SAI_TG_API_ID, SAI_TG_API_HASH, SAI_TG_TARGET
  3. ./config.json  (see config.example.json)
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

try:
    from telethon import TelegramClient, events
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    sys.exit("Telethon is not installed. Run:  pip install -r requirements.txt")

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
SESSION_PATH = str(HERE / "sai_session")


def load_config():
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: could not parse config.json ({e})", file=sys.stderr)
    # env overrides
    cfg.setdefault("api_id", os.getenv("SAI_TG_API_ID"))
    cfg.setdefault("api_hash", os.getenv("SAI_TG_API_HASH"))
    cfg.setdefault("target", os.getenv("SAI_TG_TARGET"))
    if os.getenv("SAI_TG_API_ID"):
        cfg["api_id"] = os.getenv("SAI_TG_API_ID")
    if os.getenv("SAI_TG_API_HASH"):
        cfg["api_hash"] = os.getenv("SAI_TG_API_HASH")
    if os.getenv("SAI_TG_TARGET"):
        cfg["target"] = os.getenv("SAI_TG_TARGET")
    return cfg


def require(cfg, key, hint):
    val = cfg.get(key)
    if not val:
        sys.exit(f"Missing '{key}'. {hint}")
    return val


def make_client(cfg):
    api_id = require(cfg, "api_id",
                     "Set it in config.json or SAI_TG_API_ID (from my.telegram.org).")
    api_hash = require(cfg, "api_hash",
                       "Set it in config.json or SAI_TG_API_HASH.")
    return TelegramClient(SESSION_PATH, int(api_id), str(api_hash))


def resolve_target(cfg, override=None):
    target = override or cfg.get("target")
    if not target:
        sys.exit("No target set. Use --target, SAI_TG_TARGET, or config.json "
                 "(e.g. your Sai bot's @username).")
    # numeric chat ids
    if isinstance(target, str) and target.lstrip("-").isdigit():
        return int(target)
    return target


# ---------- commands ----------

async def cmd_login(cfg, args):
    client = make_client(cfg)
    await client.start()  # interactive: prompts for phone, code, 2FA if needed
    me = await client.get_me()
    print(f"Logged in as {me.first_name} (@{me.username or me.id}). "
          f"Session saved to {SESSION_PATH}.session")
    await client.disconnect()


async def _send_and_wait(client, target, text, timeout):
    """Send text, then wait for the next incoming message from target."""
    entity = await client.get_entity(target)
    name = getattr(entity, "username", None) or getattr(entity, "title", None) or getattr(entity, "id", target)
    reply_future = asyncio.get_event_loop().create_future()

    @client.on(events.NewMessage(from_users=entity))
    async def handler(event):
        if not reply_future.done():
            reply_future.set_result(event.message.message)

    sent = await client.send_message(entity, text)
    print(f"[sent to: {name} (id={entity.id})  msg_id={sent.id}]  waiting up to {timeout:.0f}s...",
          file=sys.stderr)
    try:
        reply = await asyncio.wait_for(reply_future, timeout=timeout)
        return reply
    except asyncio.TimeoutError:
        return None


async def cmd_send(cfg, args):
    client = make_client(cfg)
    await client.start()
    target = resolve_target(cfg, args.target)
    reply = await _send_and_wait(client, target, args.text, args.timeout)
    if reply is None:
        print(f"(no reply within {args.timeout}s)", file=sys.stderr)
        sys.exit(2)
    print(reply)
    await client.disconnect()


async def cmd_chat(cfg, args):
    client = make_client(cfg)
    await client.start()
    target = resolve_target(cfg, args.target)
    entity = await client.get_entity(target)
    print(f"Connected to {getattr(entity, 'username', target)}. "
          f"Type messages; Ctrl-C or 'exit' to quit.\n")

    @client.on(events.NewMessage(from_users=entity))
    async def on_reply(event):
        print(f"\nsai> {event.message.message}\n")

    loop = asyncio.get_event_loop()
    try:
        while True:
            line = await loop.run_in_executor(None, lambda: input("you> "))
            if line.strip().lower() in ("exit", "quit"):
                break
            if line.strip():
                await client.send_message(entity, line)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        print("\nbye.")
        await client.disconnect()


async def cmd_watch(cfg, args):
    client = make_client(cfg)
    await client.start()
    target = resolve_target(cfg, args.target)
    entity = await client.get_entity(target)
    print(f"Watching messages from {getattr(entity, 'username', target)}. Ctrl-C to stop.")

    @client.on(events.NewMessage(from_users=entity))
    async def on_msg(event):
        print(f"[{event.message.date:%H:%M:%S}] {event.message.message}")

    await client.run_until_disconnected()


async def cmd_whoami(cfg, args):
    client = make_client(cfg)
    await client.start()
    me = await client.get_me()
    print(f"Account : {me.first_name} (@{me.username or me.id})")
    print(f"Target  : {cfg.get('target') or '(not set)'}")
    print(f"Session : {SESSION_PATH}.session")
    await client.disconnect()


def build_parser():
    p = argparse.ArgumentParser(prog="sai-tg",
                                description="Control a Sai AI agent over Telegram.")
    p.add_argument("--target", help="Sai bot @username or chat id (overrides config).")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="Authenticate and create a local session.")
    sub.add_parser("whoami", help="Show logged-in account and target.")
    sub.add_parser("chat", help="Interactive REPL with the agent.")
    sub.add_parser("watch", help="Stream incoming messages from the bot.")

    sp = sub.add_parser("send", help="Send a message and print the reply.")
    sp.add_argument("text")
    sp.add_argument("--timeout", type=float, default=120.0)

    sa = sub.add_parser("ask", help="Alias of send.")
    sa.add_argument("text")
    sa.add_argument("--timeout", type=float, default=120.0)
    return p


HANDLERS = {
    "login": cmd_login,
    "send": cmd_send,
    "ask": cmd_send,
    "chat": cmd_chat,
    "watch": cmd_watch,
    "whoami": cmd_whoami,
}


def main():
    args = build_parser().parse_args()
    cfg = load_config()
    handler = HANDLERS[args.command]
    asyncio.run(handler(cfg, args))


if __name__ == "__main__":
    main()