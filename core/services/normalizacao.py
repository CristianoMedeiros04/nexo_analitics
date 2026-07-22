"""
Normalização de pedidos contra o catálogo canônico (PedidoCatalogo).

Regras, na ordem:
1. match exato (case-insensitive, espaços colapsados);
2. match por alias registrado;
3. match difuso conservador (difflib >= 0.92) — evita duplicar catálogo
   por variações triviais de grafia;
4. sem match → cria entrada nova marcada como ``criado_por_ia`` para
   revisão posterior (mantém rastreabilidade, nunca perde dado).
"""

import difflib
import unicodedata

from core.models import PedidoCatalogo


def _chave(texto):
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())


class NormalizadorPedidos:
    def __init__(self):
        self._indice = {}
        self._chaves = []
        self.recarregar()

    def recarregar(self):
        self._indice = {}
        for cat in PedidoCatalogo.objects.filter(ativo=True):
            self._indice[_chave(cat.nome)] = cat
            for alias in cat.aliases or []:
                self._indice.setdefault(_chave(alias), cat)
        self._chaves = list(self._indice.keys())

    def normalizar(self, nome_pedido, criar_se_ausente=True):
        """Retorna (PedidoCatalogo, criado_novo: bool) ou (None, False)."""
        chave = _chave(nome_pedido)
        if not chave:
            return None, False

        cat = self._indice.get(chave)
        if cat:
            return cat, False

        proximos = difflib.get_close_matches(chave, self._chaves, n=1, cutoff=0.92)
        if proximos:
            cat = self._indice[proximos[0]]
            # registra a grafia nova como alias para acelerar futuros matches
            if nome_pedido not in (cat.aliases or []):
                cat.aliases = (cat.aliases or []) + [nome_pedido]
                cat.save(update_fields=["aliases"])
                self._indice[chave] = cat
                self._chaves.append(chave)
            return cat, False

        if not criar_se_ausente:
            return None, False

        cat = PedidoCatalogo.objects.create(
            nome=" ".join((nome_pedido or "").split()),
            criado_por_ia=True,
        )
        self._indice[chave] = cat
        self._chaves.append(chave)
        return cat, True
