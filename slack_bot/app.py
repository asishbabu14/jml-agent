"""Slack Bolt adapter. Idle, and successful, when the tokens are unset.

Button clicks call apply_decision with the Slack user's email. The model does
not choose the approver.
"""

from __future__ import annotations

import os
import sys

from mcp_server.config import ConfigError, Settings
from mcp_server.factory import build_service

from slack_bot.intents import apply_decision, handle_message


def main(argv: list[str] | None = None) -> int:
    del argv
    bot = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    app_token = os.environ.get("SLACK_APP_TOKEN", "").strip()
    if not bot or not app_token:
        print(
            "Slack adapter idle: set SLACK_BOT_TOKEN and SLACK_APP_TOKEN to connect. "
            "The MCP server and demo run without Slack.",
            file=sys.stderr,
        )
        return 0
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(exc.message, file=sys.stderr)
        return 2
    service = build_service(settings)
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=bot, signing_secret=os.environ.get("SLACK_SIGNING_SECRET", "").strip() or None)

    @app.event("app_mention")
    def on_mention(event, say):  # type: ignore[no-untyped-def]
        requester = _email_for(app.client, event.get("user", ""))
        if requester is None:
            say("I could not map your Slack user to an email, so I did not open a request.")
            return
        outcome = handle_message(service, event.get("text", ""), requester)
        say(outcome["reply"])

    @app.event("message")
    def on_message(event, say):  # type: ignore[no-untyped-def]
        if event.get("channel_type") != "im" or event.get("bot_id"):
            return
        requester = _email_for(app.client, event.get("user", ""))
        if requester is None:
            say("I could not map your Slack user to an email, so I did not open a request.")
            return
        outcome = handle_message(service, event.get("text", ""), requester)
        say(outcome["reply"])

    @app.action("jml_decide")
    def on_decide(ack, body, say):  # type: ignore[no-untyped-def]
        ack()
        clicker = _email_for(app.client, body.get("user", {}).get("id", ""))
        value = (body.get("actions") or [{}])[0].get("value", "")
        parts = value.split("|")
        if clicker is None or len(parts) < 3:
            say("Approval click was missing an authenticated email or payload.")
            return
        approval_id, role, decision = parts[0], parts[1], parts[2]
        method = parts[3] if len(parts) > 3 else ""
        outcome = apply_decision(
            service,
            approval_id,
            clicker,
            role,
            decision,
            identity_verified=bool(method),
            verification_method=method,
        )
        say(outcome["decision"].get("message", "Decision recorded."))

    print(f"Slack adapter connecting. identity={service.backend_summary()['identity']}", file=sys.stderr)
    SocketModeHandler(app, app_token).start()
    return 0


def _email_for(client, slack_user_id: str) -> str | None:  # type: ignore[no-untyped-def]
    if not slack_user_id:
        return None
    info = client.users_info(user=slack_user_id)
    email = ((info.get("user") or {}).get("profile") or {}).get("email")
    if not email:
        return None
    return str(email).strip().lower()


if __name__ == "__main__":
    sys.exit(main())
