"""
Cliente da API ControlJus (JusControl).

Implementa o fluxo validado no manual operacional:
- login com seleção de contrato (CONTROLJUS_CONTRATO_ID);
- cache de token com folga de 5 minutos;
- renovação automática em HTTP 401 (uma tentativa);
- rate-limit amigável (~300 ms entre páginas);
- paginação profunda de processos e movimentações.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE_URL = "https://api.controljus.com.br/api"
DELAY_ENTRE_PAGINAS = 0.3  # segundos


class ControlJusError(Exception):
    pass


class ControlJusClient:
    def __init__(self, email=None, senha=None, contrato_id=None):
        self.email = email or os.environ.get("CONTROLJUS_EMAIL")
        self.senha = senha or os.environ.get("CONTROLJUS_PASSWORD")
        contrato = contrato_id or os.environ.get("CONTROLJUS_CONTRATO_ID")
        self.contrato_id = int(contrato) if contrato else None
        if not self.email or not self.senha:
            raise ControlJusError(
                "Credenciais ausentes: defina CONTROLJUS_EMAIL e CONTROLJUS_PASSWORD."
            )
        self._token = None
        self._token_expira = None

    # ------------------------------------------------------------------ HTTP
    def _http(self, method, path, body=None, token=None, timeout=25):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            texto = resp.read().decode()
            if not texto:
                return {"success": True}
            try:
                return json.loads(texto)
            except json.JSONDecodeError:
                return {"raw": texto}

    # ----------------------------------------------------------------- token
    def _login(self):
        corpo = {"login": self.email, "senha": self.senha}
        if self.contrato_id:
            corpo["contratoId"] = self.contrato_id
        resp = self._http("POST", "/login", corpo, timeout=15)

        # Conta com múltiplos contratos devolve um array (seletor)
        if isinstance(resp, list):
            escolhido = None
            if self.contrato_id:
                escolhido = next((c for c in resp if c.get("id") == self.contrato_id), None)
            if not escolhido:
                escolhido = next((c for c in resp if not c.get("contratoPai")), resp[0])
            corpo["contratoId"] = escolhido["id"]
            resp = self._http("POST", "/login", corpo, timeout=15)

        token = resp.get("token")
        if not token:
            raise ControlJusError(f"Login falhou: {str(resp)[:200]}")

        expira = None
        if resp.get("expiracao"):
            try:
                expira = datetime.strptime(resp["expiracao"], "%d/%m/%Y %H:%M:%S")
            except ValueError:
                pass
        if not expira and resp.get("expiration"):
            try:
                expira = datetime.fromisoformat(resp["expiration"].replace("Z", ""))
            except ValueError:
                pass
        if not expira:
            expira = datetime.now() + timedelta(hours=12)

        self._token = token
        self._token_expira = expira - timedelta(minutes=5)  # folga
        logger.info("ControlJus: login OK, token válido até %s", expira)

    def _garantir_token(self):
        if not self._token or datetime.now() >= self._token_expira:
            self._login()
        return self._token

    def _chamar(self, method, path, body=None):
        token = self._garantir_token()
        try:
            return self._http(method, path, body, token=token)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # token expirado — refaz login uma vez
                self._token = None
                token = self._garantir_token()
                return self._http(method, path, body, token=token)
            if e.code == 404:
                return None
            raise

    # ------------------------------------------------------------- endpoints
    def listar_todos_processos(self, quantidade=50, max_paginas=None):
        """Itera por TODOS os processos do contrato (formato lista)."""
        pagina = 1
        total = None
        while True:
            resp = self._chamar(
                "POST",
                "/Processos/pesquisarFormatoLista",
                {"termo": None, "numeroProcesso": None, "pagina": pagina, "quantidade": quantidade},
            )
            if not resp:
                break
            resultado = resp.get("resultado") or []
            if total is None:
                total = (resp.get("totalizador") or {}).get("totalGeral")
            for item in resultado:
                yield item
            if not resultado or (total and pagina * quantidade >= total):
                break
            if max_paginas and pagina >= max_paginas:
                break
            pagina += 1
            time.sleep(DELAY_ENTRE_PAGINAS)

    def total_processos(self):
        resp = self._chamar(
            "POST",
            "/Processos/pesquisarFormatoLista",
            {"termo": None, "numeroProcesso": None, "pagina": 1, "quantidade": 1},
        )
        return ((resp or {}).get("totalizador") or {}).get("totalGeral") or 0

    def detalhe_processo(self, pasta_id):
        return self._chamar("GET", f"/Processos/{pasta_id}")

    def movimentacoes(self, pasta_id, quantidade=50, max_itens=1000):
        """Baixa movimentações em profundidade (paginação até esgotar/teto)."""
        pagina = 1
        colhidas = 0
        while colhidas < max_itens:
            resp = self._chamar(
                "POST",
                f"/Processos/{pasta_id}/movimentacoes",
                {"pagina": pagina, "quantidade": quantidade},
            )
            resultado = (resp or {}).get("resultado") or []
            if not resultado:
                break
            for mov in resultado:
                yield mov
                colhidas += 1
                if colhidas >= max_itens:
                    break
            if len(resultado) < quantidade:
                break
            pagina += 1
            time.sleep(DELAY_ENTRE_PAGINAS)

    def cotas_monitoramento(self):
        return self._chamar("GET", "/Processos/ObterTotalProcessosParaMonitoramento")
