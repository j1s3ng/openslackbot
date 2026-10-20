from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from apps.slack_bot.handlers.events import register_event_handlers
from packages.common.config import get_settings


def create_app() -> App:
    settings = get_settings()
    if not settings.slack_bot_token:
        raise RuntimeError("SLACK_BOT_TOKEN is required to start the Slack bot")
    app = App(token=settings.slack_bot_token)
    register_event_handlers(app)
    return app


def main() -> None:
    settings = get_settings()
    if not settings.slack_app_token:
        raise RuntimeError("SLACK_APP_TOKEN is required for Slack Socket Mode")
    SocketModeHandler(create_app(), settings.slack_app_token).start()


if __name__ == "__main__":
    main()
