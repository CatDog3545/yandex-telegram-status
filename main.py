
import os
import time
import logging
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.account import UpdateProfileRequest

from yandex_music import Client
from yandex_music.ynison import YnisonClient


# Настройки
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
YANDEX_TOKEN = os.environ["YANDEX_TOKEN"]
TELEGRAM_SESSION = os.environ["TELEGRAM_SESSION"]

PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

log = logging.getLogger(__name__)


# HTTP-сервер для Render
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Music status service is running")

    def log_message(self, *args):
        pass


def start_server():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    log.info("HTTP server started on port %s", PORT)
    server.serve_forever()


# Получение названия трека и исполнителя
def get_track_text(playable, ym_client):
    if not playable:
        return None

    title = getattr(playable, "title", None)
    if not title:
        return None

    artists = []

    # Пробуем получить исполнителей из объекта трека
    track_id = getattr(playable, "playable_id", None)

    if track_id:
        try:
            tracks = ym_client.tracks([str(track_id)])
            if tracks and tracks[0]:
                artists = [
                    artist.name
                    for artist in (tracks[0].artists or [])
                    if artist.name
                ]
        except Exception:
            log.exception("Could not load artist information")

    if artists:
        return f"🎵 {title} — {', '.join(artists)}"

    return f"🎵 {title}"


def main():
    threading.Thread(
        target=start_server,
        daemon=True
    ).start()

    # Подключение Telegram
    tg = TelegramClient(
        StringSession(TELEGRAM_SESSION),
        API_ID,
        API_HASH
    )

    tg.connect()

    if not tg.is_user_authorized():
        raise RuntimeError(
            "Telegram session is not authorized"
        )

    log.info("Telegram connected")

    # Подключение Яндекс Музыки
    ym = Client(YANDEX_TOKEN).init()

    last_bio = None

    with YnisonClient(YANDEX_TOKEN).session() as music:
        log.info("Yandex Music connected")

        while True:
            try:
                playable = music.current_playable
                status = music.state.player_state.status

                if not playable or status.paused:
                    time.sleep(5)
                    continue

                bio = get_track_text(playable, ym)

                if bio and bio != last_bio:
                    # Ограничиваем длину описания
                    bio = bio[:70]

                    tg(UpdateProfileRequest(about=bio))

                    last_bio = bio
                    log.info("Bio updated: %s", bio)

            except Exception:
                log.exception("Track update error")

            time.sleep(5)


if __name__ == "__main__":
    main()
