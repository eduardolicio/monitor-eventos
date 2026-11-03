"""Avisa no WhatsApp e/ou Telegram quando surge um evento novo na página de uma casa de shows."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

URL = os.environ["PAGE_URL"]
# Texto que precisa existir na página. Sem ele, assumimos bloqueio ou erro,
# e não uma casa sem eventos.
PAGE_MARKER = os.environ["PAGE_MARKER"]
EVENT_SELECTOR = os.getenv("EVENT_SELECTOR", "a.eventoCard")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STATE_FILE = Path(os.getenv("STATE_FILE", "seen.json"))
TELEGRAM_API = os.getenv("TELEGRAM_API", "https://api.telegram.org")
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "")  # ex.: +5548999999999
WHATSAPP_APIKEY = os.getenv("WHATSAPP_APIKEY", "")
CALLMEBOT_API = os.getenv("CALLMEBOT_API", "https://api.callmebot.com")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    )
}


def clean(text: str) -> str:
    """Junta os espaços. O site usa espaço não separável em alguns nomes."""
    return " ".join(text.split())


def normalize(url: str) -> str:
    """Remove query e fragmento para parâmetros de rastreio não virarem evento novo."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def describe(card) -> str:
    """Monta o texto do aviso a partir de um cartão de evento."""
    title = card.select_one(".eventoCard__title")
    content = card.select_one(".eventoCard__content")
    date = content.find("div") if content else None

    lines = [clean(tag.get_text(" ")) for tag in (title, date) if tag]
    return "\n".join(line for line in lines if line) or clean(card.get_text(" "))


def fetch_events() -> dict[str, str]:
    """Retorna {url_do_evento: descrição}. Uma casa sem eventos retorna dict vazio."""
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")

    if clean(PAGE_MARKER) not in clean(soup.get_text(" ")):
        raise RuntimeError(f'A página não contém "{PAGE_MARKER}". Possível bloqueio.')

    return {
        normalize(urljoin(URL, card["href"])): describe(card)
        for card in soup.select(EVENT_SELECTOR)
        if card.get("href")
    }


def load_seen() -> set[str] | None:
    """Retorna None na primeira execução, quando ainda não existe estado salvo."""
    if not STATE_FILE.exists():
        return None
    return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))


def save_seen(seen: set[str]) -> None:
    STATE_FILE.write_text(
        json.dumps(sorted(seen), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def send_telegram(text: str) -> None:
    response = requests.post(
        f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )
    response.raise_for_status()


def send_whatsapp(text: str) -> None:
    response = requests.get(
        f"{CALLMEBOT_API}/whatsapp.php",
        params={"phone": WHATSAPP_PHONE, "text": text, "apikey": WHATSAPP_APIKEY},
        timeout=60,
    )
    # O CallMeBot pode responder 203 em caso de erro, que raise_for_status não pega.
    if response.status_code != 200:
        raise RuntimeError(f"CallMeBot respondeu {response.status_code}")


def notify(text: str) -> None:
    channels = []
    if WHATSAPP_PHONE and WHATSAPP_APIKEY:
        channels.append(send_whatsapp)
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        channels.append(send_telegram)

    if not channels:
        print(f"[nenhum canal configurado]\n{text}")
        return

    errors = []
    for send in channels:
        try:
            send(text)
        except (requests.RequestException, RuntimeError) as error:
            # Não exibe a exceção: a URL dela contém o token ou a API key.
            errors.append(f"{send.__name__}: {type(error).__name__}")

    if errors:
        print(f"Falha parcial no envio: {errors}", file=sys.stderr)

    # Só repete o aviso se nenhum canal entregou, para não duplicar no que funcionou.
    if len(errors) == len(channels):
        raise RuntimeError("Nenhum canal conseguiu enviar o aviso.")


def main() -> int:
    events = fetch_events()
    seen = load_seen()

    # A linha de base pode ser vazia: assim o primeiro evento da temporada gera aviso.
    if seen is None:
        save_seen(set(events))
        print(f"Primeira execução: {len(events)} evento(s) salvos, sem notificar.")
        return 0

    new_links = [link for link in events if link not in seen]

    if not new_links:
        print(f"Nenhum evento novo ({len(events)} na página).")
        return 0

    for link in new_links:
        notify(f"🎟️ {events[link]}\n{link}")
        # Salva a cada envio: se um falhar, só os pendentes são reenviados.
        seen.add(link)
        save_seen(seen)

    print(f"{len(new_links)} evento(s) novo(s) notificado(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
