"""Speech-to-text. Claude doesn't take audio, so voice notes are transcribed first.

Default: Whisper on Cloudflare Workers AI (REST). Swap this one function to use
Deepgram, AssemblyAI, etc. If no provider is configured, the app falls back to
typed notes.
"""

import base64

import httpx

from ..config import get_settings

WHISPER_MODEL = "@cf/openai/whisper-large-v3-turbo"


class SpeechToTextUnavailable(RuntimeError):
    pass


def transcribe(audio: bytes) -> str:
    s = get_settings()
    if not (s.cloudflare_account_id and s.cloudflare_ai_token):
        raise SpeechToTextUnavailable("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN, or type the notes.")
    url = f"https://api.cloudflare.com/client/v4/accounts/{s.cloudflare_account_id}/ai/run/{WHISPER_MODEL}"
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {s.cloudflare_ai_token}"},
        json={"audio": base64.b64encode(audio).decode()},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["result"]["text"].strip()
