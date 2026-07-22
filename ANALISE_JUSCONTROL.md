# Análise: Integração ControlJus (JusControl) × Sistema de Jurimetria

**Data:** 22/07/2026 · **Contrato:** 044312 (id 197379) · **Processos monitorados:** 796 de 1000 (cota)

---

## 1. O que foi validado na API (acesso real)

- Login com seleção de contrato funciona; token válido por ~12h (renovação automática implementada).
- `pesquisarFormatoLista` paginado retorna o universo completo (796 processos).
- `GET /Processos/{id}` entrega metadados ricos e estruturados.
- `POST /Processos/{id}/movimentacoes` entrega TODO o histórico de andamentos (nome + data), inclusive anteriores ao monitoramento.
- **Recortes DJEN** (`recorte.textoLimpo`): presentes apenas em publicações capturadas APÓS o início do monitoramento. Encontramos íntegras completas de até 25k caracteres (decisões monocráticas, intimações com inteiro teor).
- Endpoints `publicacoes`, `valores`, `ged`, `movimentacoes/automaticas`: retornam 404 neste contrato — fallback via movimentações (conforme manual).
- **API pública do DJEN (comunicaapi.pje.jus.br): bloqueada geograficamente** (CloudFront 403 para IPs fora do Brasil) — não utilizável do Railway. O ControlJus é a fonte primária de textos.

## 2. Mapeamento: coluna da planilha → fonte de dados

| Coluna | Fonte | Método | Cobertura |
|---|---|---|---|
| Número do processo, UF, Comarca, Vara, Tribunal, Classe, Instância, Situação | ControlJus (detalhe) | objetivo | ~100% |
| Partes/Advogados (ativo/passivo), CNPJs, Nome/CPF | ControlJus (detalhe) | objetivo | ~100% |
| Assuntos | ControlJus (assuntosProcessos) | objetivo | alta |
| Justiça gratuita?, Segredo de justiça? | ControlJus (flags) | objetivo | alta |
| Data da distribuição, Data do último movimento | ControlJus | objetivo | alta |
| Data da sentença/acórdão/trânsito/arquivamento/acordo | Movimentações (nomes padronizados PJe) | extração por regex | alta (histórico completo) |
| Desfecho | Movimentações ("Julgado(s) improcedente(s)...", "Homologada a transação"...) + IA sobre íntegras | objetivo + IA | alta |
| Decisões por instância | Extração (Decisao por grau) | objetivo | alta |
| Tipos de recursos (RO, RR, AIRR, ED-PJE...) | Movimentações | regex | alta |
| Indicativo de bloqueio (Sisbajud/BacenJud), revelia | Movimentações + IA | regex + IA | média-alta |
| Fase (Conhecimento/Execução/Liquidação) | Classe + movimentações | heurística | alta |
| **Pedidos + TipoPedido/Valor/Desfecho** | **IA sobre íntegras (recortes DJEN)** | **IA + catálogo canônico** | **crescente**¹ |
| Juízes | IA sobre íntegras (assinatura do ato) | IA | crescente¹ |
| Valor de condenação, valor de acordo | IA sobre íntegras + ControlJus | IA + objetivo | crescente¹ |
| Valor de causa | ControlJus (quando preenchido) + planilha | objetivo | parcial |
| Último salário, Data admissão/demissão, Tipo de cargos | **não disponível na API** | mantido da planilha / IA sobre inicial² | baixa |
| Valor de custas, depósitos, Pagamentos de Recursos | Parcial via IA sobre despachos/guias | IA | baixa-média |

¹ **Limitação estrutural:** decisões proferidas ANTES do início do monitoramento não têm texto na API (só nome+data da movimentação). Os textos se acumulam daqui pra frente — cada sentença/acórdão publicado nos 796 processos chega semanalmente com íntegra e é analisado pela IA. A planilha-base (919 processos) supre o histórico.

² Dados de RH (salário, admissão) vêm da petição inicial/contrato — não expostos pela API. Ficam da planilha; a IA os captura quando aparecem citados em sentenças.

## 3. Arquitetura implementada

```
planilha-base (919 proc., histórico completo)  ──┐
                                                 ├──▶  MySQL (Railway)
ControlJus API (796 proc. monitorados)  ─────────┤     ├─ processos (60+ campos, legado p/ gráficos)
  · metadados objetivos                          │     ├─ movimentacoes (bruta, incremental)
  · movimentações históricas (datas/eventos)     │     ├─ decisoes (atos + íntegras + análise IA)
  · recortes DJEN (íntegras, daqui pra frente)   │     ├─ pedidos_catalogo (288 canônicos + aliases)
                                                 │     ├─ pedidos_processo (normalizado, com desfecho)
Claude API (análise de íntegras)  ───────────────┘     └─ sincronizacao_logs (auditoria)
```

- **Tabelas normalizadas são a fonte da verdade; as colunas legadas do `Processo` são materializadas** a partir delas — todos os gráficos/filtros existentes continuam funcionando sem refatoração.
- **Padronização de pedidos:** todo pedido passa pelo `PedidoCatalogo` (match exato → alias → difuso ≥0.92 → criação marcada para revisão). A IA recebe o catálogo completo no prompt (com cache) e é instruída a NUNCA inventar variações.
- **Merge por CNJ:** o sync casa processos do ControlJus com a planilha pelo CNJ normalizado — enriquece, não duplica (validado: 3/3 processos casaram).

## 4. Comandos

| Comando | Função |
|---|---|
| `seed_catalogo_pedidos` | Semeia o catálogo canônico (roda no boot) |
| `importar_planilha` | Importa/atualiza a baseline de 919 processos (boot, idempotente, ~3s) |
| `cj_sincronizar [--limite N] [--ids a,b]` | Sincroniza ControlJus: metadados + movimentações + eventos/datas |
| `ia_analisar [--limite N] [--simular]` | Analisa íntegras pendentes com a Claude API |
| `sync_semanal` | Orquestrador do cron (sincroniza + analisa) |

## 5. O que a IA extrai de cada íntegra (structured output)

Desfecho do processo (vocabulário fechado da planilha) · pedidos normalizados no catálogo com resultado (DEFERIMENTO/INDEFERIMENTO/PARCIAL), valor e fundamentação · magistrado · revelia · justiça gratuita · valores de condenação/acordo · confiança global. Só sobrescreve campos do processo com confiança ≥ 0,6; análise bruta fica auditável em `decisoes.analise_json`.

## 6. Pendências / próximos passos

1. **`ANTHROPIC_API_KEY` no Railway** — necessária para ativar a análise por IA (variável já prevista; sem ela o cron pula a etapa e loga aviso).
2. **Sincronização inicial completa** dos 796 processos (~40-60 min pelo rate-limit da API) — rodar `cj_sincronizar` uma vez após o deploy.
3. **Curadoria do catálogo:** entradas criadas pela IA ficam com `criado_por_ia=true` para revisão periódica (mesclar como alias se redundante).
4. **Módulos novos possíveis com dados mais ricos** (roadmap): linha do tempo por processo (movimentações completas), audiências futuras (datas embutidas nos nomes), painel de fundamentações por pedido, alertas de nova sentença/acórdão (o cron detecta), busca full-text nas íntegras.
5. Dados de RH (último salário/admissão) permanecem limitados ao que a planilha traz ou ao que a IA encontrar citado nas decisões.
