import os
import secrets
import time
from urllib.parse import urlencode, quote

import aiohttp
from aiohttp import web

RSO_CLIENT_ID = os.getenv("RSO_CLIENT_ID")
RSO_CLIENT_SECRET = os.getenv("RSO_CLIENT_SECRET")
RSO_REDIRECT_URI = os.getenv("RSO_REDIRECT_URI")
WEBSITE_URL = os.getenv("WEBSITE_URL", "")

_RIOT_AUTH_URL = "https://auth.riotgames.com/authorize"
_RIOT_TOKEN_URL = "https://auth.riotgames.com/token"
_RIOT_ACCOUNT_URL = "https://americas.api.riotgames.com/riot/account/v1/accounts/me"

# state -> timestamp; descartados após 10 minutos
_estados_pendentes: dict[str, float] = {}


def _url_erro() -> str:
    return f"{WEBSITE_URL}/autorizar.html?error=1"


async def handle_login(request: web.Request) -> web.Response:
    state = secrets.token_urlsafe(16)
    agora = time.time()
    _estados_pendentes[state] = agora

    # limpa estados expirados
    expirados = [k for k, v in _estados_pendentes.items() if agora - v > 600]
    for k in expirados:
        del _estados_pendentes[k]

    params = {
        "client_id": RSO_CLIENT_ID,
        "redirect_uri": RSO_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid offline_access",
        "state": state,
    }
    raise web.HTTPFound(f"{_RIOT_AUTH_URL}?{urlencode(params)}")


async def handle_callback(request: web.Request) -> web.Response:
    codigo = request.rel_url.query.get("code")
    state = request.rel_url.query.get("state")
    erro = request.rel_url.query.get("error")

    if erro or not codigo or not state:
        raise web.HTTPFound(_url_erro())

    if state not in _estados_pendentes:
        raise web.HTTPFound(_url_erro())

    del _estados_pendentes[state]

    try:
        async with aiohttp.ClientSession() as session:
            # troca o code pelos tokens
            auth = aiohttp.BasicAuth(RSO_CLIENT_ID, RSO_CLIENT_SECRET)
            async with session.post(
                _RIOT_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": codigo,
                    "redirect_uri": RSO_REDIRECT_URI,
                },
                auth=auth,
            ) as resp:
                if resp.status != 200:
                    print(f"[RSO] Falha ao trocar code: {resp.status} {await resp.text()}")
                    raise web.HTTPFound(_url_erro())
                tokens = await resp.json()

            access_token = tokens["access_token"]
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)

            # busca dados da conta Riot do jogador
            async with session.get(
                _RIOT_ACCOUNT_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as resp:
                if resp.status != 200:
                    print(f"[RSO] Falha ao buscar conta: {resp.status} {await resp.text()}")
                    raise web.HTTPFound(_url_erro())
                conta = await resp.json()

    except web.HTTPFound:
        raise
    except Exception as exc:
        print(f"[RSO] Erro inesperado no callback: {exc}")
        raise web.HTTPFound(_url_erro())

    puuid = conta["puuid"]
    game_name = conta["gameName"]
    tag_line = conta["tagLine"]

    from database import registrar_autorizacao_rso
    await registrar_autorizacao_rso(puuid, game_name, tag_line, access_token, refresh_token, expires_in)

    print(f"[RSO] Jogador autorizado: {game_name}#{tag_line}")
    raise web.HTTPFound(f"{WEBSITE_URL}/sucesso.html?player={quote(game_name)}%23{quote(tag_line)}")


def criar_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/auth/riot", handle_login)
    app.router.add_get("/auth/riot/callback", handle_callback)
    return app


async def iniciar_servidor_web() -> web.AppRunner:
    porta = int(os.getenv("WEB_PORT", "8080"))
    app = criar_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", porta)
    await site.start()
    print(f"[RSO] Servidor web OAuth rodando na porta {porta}")
    return runner
