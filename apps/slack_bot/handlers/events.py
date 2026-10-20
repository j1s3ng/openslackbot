from slack_bolt import App


THINKING_TEXT = "🧠 Thinking..."


def register_event_handlers(app: App) -> None:
    @app.event("message")
    def handle_message(event, say):
        if event.get("subtype") == "bot_message" or event.get("bot_id"):
            return
        text = (event.get("text") or "").strip()
        if not text:
            return

        thread_ts = event.get("thread_ts") or event.get("ts")
        say(text=THINKING_TEXT, thread_ts=thread_ts)

    @app.event("app_mention")
    def handle_app_mention(event, say):
        text = (event.get("text") or "").strip()
        if not text:
            return
        thread_ts = event.get("thread_ts") or event.get("ts")
        say(text=THINKING_TEXT, thread_ts=thread_ts)
