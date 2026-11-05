
import os
import time
import logging

from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from yandex_music.ynison import YnisonClient

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
YANDEX_TOKEN = os.getenv("YANDEX_TOKEN")
PHONE = os.getenv("PHONE")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def get_track_info(track):
    if not track:
        return None

    title = getattr(track, "title", None)
    artists = getattr(track, "artists", [])

    artist_names = [
        artist.name for artist in artists
        if getattr(artist, "name", None)
    ]

    if not title:
        return None

    artist_text = ", ".join(artist_names)

    if artist_text:
        return f"🎵 {title} — {artist_text}"

    return f"🎵 {title}"


def main():
    tg = TelegramClient(
        "telegram_session",
        API_ID,
        API_HASH
    )

    tg.start(phone=PHONE)

    log.info("Telegram подключен")

    last_bio = None

    with YnisonClient(YANDEX_TOKEN).session() as music:
        log.info("Яндекс Музыка подключена")

        while True:
            try:
                track = music.current_playable
                status = music.state.player_state.status

                # Не обновляем профиль на паузе
                if status.paused or not track:
                    time.sleep(5)
                    continue

                new_bio = get_track_info(track)

                if new_bio and new_bio != last_bio:

                    # Ограничение длины описания
                    new_bio = new_bio[:70]

                    tg(UpdateProfileRequest(
                        about=new_bio
                    ))

                    last_bio = new_bio

                    log.info(f"Описание обновлено: {new_bio}")

            except Exception:
                log.exception("Ошибка обновления")

            time.sleep(5)


if __name__ == "__main__":
    main()
