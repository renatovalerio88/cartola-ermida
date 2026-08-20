import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo


ARQUIVO_HISTORICO = Path("historico_cartola.json")
ARQUIVO_RODADA_ATUAL = Path("rodada_atual_cartola.json")

URL_STATUS = "https://api.cartola.globo.com/mercado/status"

TOTAL_TIMES = 36
FUSO = ZoneInfo("America/Sao_Paulo")

# Quantidade mínima de repetições exatas de pontos + patrimônio
# entre duas rodadas consecutivas para bloquear a consolidação.
#
# Uma coincidência isolada pode acontecer.
# Várias coincidências simultâneas são assinatura de dado defasado.
LIMITE_REPETICOES_SUSPEITAS = 3


TIMES = [
    (3619967, "Forward F. Club", "Valcard"),
    (40995, "WECAM", "Renato Valerio"),
    (6074454, "SardoGalo 13", "Álvaro Firmino"),
    (385413, "Mão C.F", "Lucas Mão"),
    (8976743, "MT10M1T0", "Marco Tulio"),
    (50252506, "Branes25", "Roger Nunes"),
    (195382, "CAMARASSO", "André Camarasso"),
    (60383, "RJ Clube", "Ricardo Júdice"),
    (19198951, "SANTASTICO GLORIOSO I", "Renato Do SANTOS"),
    (25588958, "JUNA FUTEBOL CLUBE", "AMARILO JUNIOR"),
    (654232, "D1OS", "10inho"),
    (974057, "S.C. Finha Paulista", "Lucas Guedes"),
    (2745059, "Epidemia Sport Clube", "Jorge Queiroz"),
    (91357, "DP-SC", "D Pedro"),
    (29565271, "Legione Romanista", "Arthur Godioso"),
    (28538913, "Maria Gol De Costas", "Rafa Palhares"),
    (178173, "Jack Golden", "Dourado"),
    (21141036, "Ardam Cabubu", "Guizoba"),
    (50327258, "Digdigie94", "DigdigieCabuloso"),
    (18434405, "Gabiru cabuloso", "Wendell Costa"),
    (1193651, "CruzeiroKiller", "André Pitanga"),
    (25565544, "CHARLLOTTTE F.C.", "Charles Duek"),
    (28604976, "Galo de Rio Doce FC", "Pedro Natali"),
    (14705949, "Seu Cuca Futebol", "Xande Costa"),
    (214265, "Framos F.C", "Fernando Ramos"),
    (186377, "JACB FC", "Juca Barros"),
    (51042838, "A76 FC", "Alan Guimarães"),
    (285883, "Kayser Football", "Pedro Kayser"),
    (3128927, "Jafeth G.D.F.C.", "Henrique Jafeth"),
    (25937153, "GALOBERA F.C", "Gabriel Carvalho"),
    (1005072, "PELUDÃO13", "WAGNER"),
    (49415297, "SemFreio LEFC1988", "LEANDRO CAMPOS GIANI"),
    (103947, "Campista F. C", "Rafael Abrantes"),
    (24449, "Sport Club Prexeca Bangers", "Giovanni Guedes"),
    (25889523, "Clube de Regatas Sô", "Betinho Valerio"),
    (596168, "Galo Doido BH 93", "Lucas Real"),
]


def agora_texto():
    return datetime.now(FUSO).strftime("%d/%m/%Y %H:%M:%S")


def numero(valor, padrao=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


def inteiro(valor, padrao=0):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return int(padrao)


def buscar_json(url, tentativas=3):
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                    "Cache-Control": "no-cache",
                },
            )

            with urllib.request.urlopen(req, timeout=25) as resposta:
                conteudo = resposta.read().decode("utf-8").strip()

                if not conteudo:
                    raise ValueError("A API respondeu sem conteúdo.")

                dados = json.loads(conteudo)

                if not isinstance(dados, dict):
                    raise ValueError(
                        "A API não retornou um objeto JSON."
                    )

                return dados

        except Exception as erro:
            ultimo_erro = erro

            print(
                f"Tentativa {tentativa}/{tentativas} "
                f"falhou em {url}: {erro}"
            )

            if tentativa < tentativas:
                import time
                time.sleep(tentativa * 2)

    raise RuntimeError(
        f"Falha definitiva em {url}: {ultimo_erro}"
    )


def carregar_historico():
    try:
        with ARQUIVO_HISTORICO.open(
            "r",
            encoding="utf-8",
        ) as arquivo:
            dados = json.load(arquivo)

            if not isinstance(dados, dict):
                raise ValueError(
                    "O histórico não contém um objeto JSON."
                )

            dados.setdefault(
                "liga",
                "Cartola de Ermida",
            )

            dados.setdefault(
                "rodadas",
                {},
            )

            return dados

    except FileNotFoundError:
        return {
            "liga": "Cartola de Ermida",
            "rodadas": {},
        }


def carregar_rodada_atual():
    try:
        with ARQUIVO_RODADA_ATUAL.open(
            "r",
            encoding="utf-8",
        ) as arquivo:
            dados = json.load(arquivo)

            if isinstance(dados, dict):
                return dados

            return {}

    except (
        FileNotFoundError,
        json.JSONDecodeError,
    ):
        return {}


def salvar_atomico(caminho, dados):
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=caminho.parent,
        delete=False,
        suffix=".tmp",
    ) as temporario:
        json.dump(
            dados,
            temporario,
            ensure_ascii=False,
            indent=2,
        )

        temporario.write("\n")
        nome_temporario = temporario.name

    os.replace(
        nome_temporario,
        caminho,
    )


def soma_detalhes(item):
    detalhes = item.get(
        "detalhes_parcial",
        [],
    )

    if not isinstance(
        detalhes,
        list,
    ) or not detalhes:
        return None

    total = 0.0

    for atleta in detalhes:
        if not isinstance(
            atleta,
            dict,
        ):
            continue

        total += numero(
            atleta.get(
                "pontos_computados",
                0,
            )
        )

    return round(
        total,
        2,
    )


def validar_registro_snapshot(
    item,
    rodada,
):
    """
    Valida individualmente um time antes de permitir
    que ele seja promovido ao histórico definitivo.

    A falha identificada na rodada 23 tinha a seguinte
    assinatura:

    - pontos agregados > 0;
    - patrimônio reaproveitado da rodada anterior;
    - atletas da suposta rodada fechada todos zerados.

    Por isso, quando existe detalhamento, a soma dos
    pontos computados precisa ser compatível com o
    total informado para o time.
    """

    if not isinstance(
        item,
        dict,
    ):
        return (
            False,
            "registro inválido",
        )

    rodada_item = inteiro(
        item.get(
            "rodada_dados",
            0,
        )
    )

    if rodada_item != inteiro(rodada):
        return (
            False,
            (
                f"rodada_dados={rodada_item}; "
                f"esperada={rodada}"
            ),
        )

    time_id = inteiro(
        item.get(
            "time_id",
            0,
        )
    )

    if time_id <= 0:
        return (
            False,
            "time_id inválido",
        )

    pontos = round(
        numero(
            item.get(
                "pontos",
                0,
            )
        ),
        2,
    )

    soma = soma_detalhes(item)

    if soma is None:
        return (
            False,
            "registro sem detalhamento verificável",
        )

    if abs(soma - pontos) > 0.11:
        return (
            False,
            (
                f"total do time {pontos:.2f} "
                f"incompatível com soma dos atletas "
                f"{soma:.2f}"
            ),
        )

    fonte = str(
        item.get(
            "fonte_pontos",
            "",
        )
    ).strip()

    fontes_aceitas = {
        "api_time_id_validado",
        "snapshot_ao_vivo_validado",
        "parciais_finais_validadas",
        "atletas_pontuados",
    }

    if fonte not in fontes_aceitas:
        return (
            False,
            (
                "fonte não validada para consolidação: "
                f"{fonte or 'vazia'}"
            ),
        )

    return (
        True,
        "ok",
    )


def mapa_rodada_atual_validado(
    rodada,
):
    dados = carregar_rodada_atual()

    rodada_snapshot = inteiro(
        dados.get(
            "rodada_dados",
            0,
        )
    )

    if rodada_snapshot != inteiro(rodada):
        raise RuntimeError(
            "rodada_atual_cartola.json não corresponde "
            "à rodada que precisa ser consolidada. "
            f"Snapshot={rodada_snapshot}; "
            f"esperada={rodada}."
        )

    times = dados.get(
        "times",
        [],
    )

    if not isinstance(
        times,
        list,
    ):
        raise RuntimeError(
            "rodada_atual_cartola.json não contém "
            "uma lista válida de times."
        )

    if len(times) != TOTAL_TIMES:
        raise RuntimeError(
            "rodada_atual_cartola.json está incompleto. "
            f"Times encontrados: {len(times)}/{TOTAL_TIMES}."
        )

    mapa = {}
    erros = []

    for item in times:
        time_id = inteiro(
            item.get(
                "time_id",
                0,
            )
        ) if isinstance(item, dict) else 0

        valido, motivo = validar_registro_snapshot(
            item,
            rodada,
        )

        if not valido:
            nome = (
                item.get(
                    "time",
                    str(time_id),
                )
                if isinstance(item, dict)
                else "registro desconhecido"
            )

            erros.append(
                f"{nome}: {motivo}"
            )

            continue

        if time_id in mapa:
            erros.append(
                f"time_id duplicado: {time_id}"
            )

            continue

        mapa[time_id] = item

    if erros:
        print()
        print(
            "SNAPSHOT REPROVADO. "
            "Nenhum dado será gravado no histórico."
        )

        for erro in erros:
            print(
                f" - {erro}"
            )

        raise RuntimeError(
            "rodada_atual_cartola.json contém "
            "dados inconsistentes."
        )

    if len(mapa) != TOTAL_TIMES:
        raise RuntimeError(
            "O snapshot não possui os 36 times "
            "válidos e únicos."
        )

    ids_esperados = {
        time_id
        for time_id, _, _ in TIMES
    }

    ids_snapshot = set(
        mapa.keys()
    )

    faltantes = (
        ids_esperados
        - ids_snapshot
    )

    extras = (
        ids_snapshot
        - ids_esperados
    )

    if faltantes or extras:
        if faltantes:
            print(
                "Times ausentes no snapshot:",
                sorted(faltantes),
            )

        if extras:
            print(
                "Times inesperados no snapshot:",
                sorted(extras),
            )

        raise RuntimeError(
            "A composição da liga no snapshot "
            "não corresponde aos 36 times esperados."
        )

    return mapa


def mapa_historico_rodada(
    historico,
    rodada,
):
    rodadas = historico.get(
        "rodadas",
        {},
    )

    if not isinstance(
        rodadas,
        dict,
    ):
        return {}

    registros = rodadas.get(
        str(rodada),
        [],
    )

    if not isinstance(
        registros,
        list,
    ):
        return {}

    mapa = {}

    for item in registros:
        if not isinstance(
            item,
            dict,
        ):
            continue

        time_id = inteiro(
            item.get(
                "time_id",
                0,
            )
        )

        if time_id > 0:
            mapa[time_id] = item

    return mapa


def auditar_repeticoes_rodada_anterior(
    mapa_snapshot,
    historico,
    rodada,
):
    """
    Segunda barreira de segurança.

    Se vários times repetirem exatamente pontos E
    patrimônio da rodada anterior, interrompemos a
    consolidação.

    Foi exatamente esse padrão que revelou os
    14 registros contaminados da rodada 23.
    """

    rodada_anterior = inteiro(
        rodada
    ) - 1

    if rodada_anterior <= 0:
        return

    mapa_anterior = mapa_historico_rodada(
        historico,
        rodada_anterior,
    )

    if len(mapa_anterior) != TOTAL_TIMES:
        print(
            "Auditoria de repetição ignorada: "
            "a rodada anterior não possui os "
            "36 registros completos."
        )

        return

    repetidos = []

    for (
        time_id,
        nome_time,
        _cartoleiro,
    ) in TIMES:
        atual = mapa_snapshot.get(
            time_id,
            {},
        )

        anterior = mapa_anterior.get(
            time_id,
            {},
        )

        if not atual or not anterior:
            continue

        pontos_atual = round(
            numero(
                atual.get(
                    "pontos",
                    0,
                )
            ),
            2,
        )

        pontos_anterior = round(
            numero(
                anterior.get(
                    "pontos",
                    0,
                )
            ),
            2,
        )

        patrimonio_atual = round(
            numero(
                atual.get(
                    "patrimonio",
                    0,
                )
            ),
            2,
        )

        patrimonio_anterior = round(
            numero(
                anterior.get(
                    "patrimonio",
                    0,
                )
            ),
            2,
        )

        if (
            pontos_atual
            == pontos_anterior
            and patrimonio_atual
            == patrimonio_anterior
        ):
            repetidos.append(
                {
                    "time_id": time_id,
                    "time": nome_time,
                    "pontos": pontos_atual,
                    "patrimonio": patrimonio_atual,
                }
            )

    if repetidos:
        print()
        print(
            "Auditoria de repetição entre rodadas:"
        )

        for item in repetidos:
            print(
                f" - {item['time']}: "
                f"{item['pontos']:.2f} pts / "
                f"C$ {item['patrimonio']:.2f}"
            )

    if (
        len(repetidos)
        >= LIMITE_REPETICOES_SUSPEITAS
    ):
        raise RuntimeError(
            "CONSOLIDAÇÃO BLOQUEADA: "
            f"{len(repetidos)} times repetiram "
            "simultaneamente pontos e patrimônio "
            "da rodada anterior. "
            "O padrão é compatível com resposta "
            "defasada da API."
        )


def montar_registros_historico(
    mapa_snapshot,
    rodada,
):
    registros = []

    for (
        time_id,
        nome_time,
        cartoleiro,
    ) in TIMES:
        snapshot = mapa_snapshot.get(
            time_id,
        )

        if not snapshot:
            raise RuntimeError(
                f"Snapshot ausente para {nome_time}."
            )

        registro = {
            "time_id": time_id,
            "time": nome_time,
            "cartoleiro": cartoleiro,
            "rodada": rodada,
            "pontos": round(
                numero(
                    snapshot.get(
                        "pontos",
                        0,
                    )
                ),
                2,
            ),
            "patrimonio": round(
                numero(
                    snapshot.get(
                        "patrimonio",
                        0,
                    )
                ),
                2,
            ),
            "fonte_pontos": str(
                snapshot.get(
                    "fonte_pontos",
                    "snapshot_validado",
                )
            ),
        }

        registros.append(
            registro
        )

    return registros


print(
    "Consultando o status do Cartola..."
)

status = buscar_json(
    URL_STATUS
)

rodada_status = inteiro(
    status.get(
        "rodada_atual",
        0,
    )
)

mercado_status = inteiro(
    status.get(
        "status_mercado",
        0,
    )
)

mercado_aberto = (
    mercado_status == 1
)

print(
    f"Rodada Cartola: {rodada_status}"
)

print(
    f"Status mercado: {mercado_status}"
)

print(
    f"Mercado aberto: {mercado_aberto}"
)


if rodada_status <= 0:
    raise RuntimeError(
        "Não foi possível determinar "
        "a rodada atual."
    )


if not mercado_aberto:
    raise RuntimeError(
        "O mercado não está aberto. "
        "Nenhuma parcial será gravada "
        "como resultado definitivo."
    )


rodada_para_salvar = (
    rodada_status - 1
)

if rodada_para_salvar <= 0:
    raise RuntimeError(
        "Não foi possível determinar "
        "a última rodada fechada."
    )


print()

print(
    "Consolidando a rodada fechada "
    f"{rodada_para_salvar}..."
)

print(
    "A consolidação usará somente "
    "rodada_atual_cartola.json previamente "
    "validado. /time/id não será usado como "
    "fallback para o histórico."
)


historico = carregar_historico()

historico["liga"] = (
    "Cartola de Ermida"
)

historico.setdefault(
    "rodadas",
    {},
)


mapa_snapshot = (
    mapa_rodada_atual_validado(
        rodada_para_salvar
    )
)

print(
    "Snapshot aprovado: "
    f"{len(mapa_snapshot)}/{TOTAL_TIMES} "
    "times validados."
)


auditar_repeticoes_rodada_anterior(
    mapa_snapshot,
    historico,
    rodada_para_salvar,
)

print(
    "Auditoria contra a rodada anterior: "
    "APROVADA."
)


novos_registros = (
    montar_registros_historico(
        mapa_snapshot,
        rodada_para_salvar,
    )
)


if len(novos_registros) != TOTAL_TIMES:
    raise RuntimeError(
        "A consolidação não produziu "
        "os 36 registros esperados."
    )


rodada_existente = (
    historico["rodadas"].get(
        str(rodada_para_salvar),
        [],
    )
)


if (
    isinstance(
        rodada_existente,
        list,
    )
    and rodada_existente
):
    mapa_existente = {}

    for item in rodada_existente:
        if not isinstance(
            item,
            dict,
        ):
            continue

        time_id = inteiro(
            item.get(
                "time_id",
                0,
            )
        )

        if time_id > 0:
            mapa_existente[
                time_id
            ] = item

    diferencas = []

    for novo in novos_registros:
        time_id = novo[
            "time_id"
        ]

        antigo = mapa_existente.get(
            time_id
        )

        if not antigo:
            diferencas.append(
                (
                    novo["time"],
                    "registro inexistente",
                )
            )

            continue

        pontos_antigos = round(
            numero(
                antigo.get(
                    "pontos",
                    0,
                )
            ),
            2,
        )

        pontos_novos = round(
            numero(
                novo.get(
                    "pontos",
                    0,
                )
            ),
            2,
        )

        patrimonio_antigo = round(
            numero(
                antigo.get(
                    "patrimonio",
                    0,
                )
            ),
            2,
        )

        patrimonio_novo = round(
            numero(
                novo.get(
                    "patrimonio",
                    0,
                )
            ),
            2,
        )

        if (
            pontos_antigos
            != pontos_novos
            or patrimonio_antigo
            != patrimonio_novo
        ):
            diferencas.append(
                (
                    novo["time"],
                    (
                        f"{pontos_antigos:.2f} -> "
                        f"{pontos_novos:.2f} pts | "
                        f"C$ {patrimonio_antigo:.2f} -> "
                        f"C$ {patrimonio_novo:.2f}"
                    ),
                )
            )

    if diferencas:
        print()
        print(
            "A rodada já existia no histórico, "
            "mas o novo snapshot validado possui "
            "diferenças:"
        )

        for (
            nome,
            descricao,
        ) in diferencas:
            print(
                f" - {nome}: {descricao}"
            )

        print(
            "Como a nova fonte passou por todas "
            "as validações, ela poderá corrigir "
            "um registro histórico anteriormente "
            "contaminado."
        )

    else:
        print(
            "A rodada já existe e os valores "
            "validados são idênticos."
        )


historico[
    "rodadas"
][
    str(rodada_para_salvar)
] = novos_registros


for rodada_texto in list(
    historico["rodadas"]
):
    try:
        numero_rodada = int(
            rodada_texto
        )

    except ValueError:
        continue

    if (
        numero_rodada
        > rodada_para_salvar
    ):
        print(
            "Removendo rodada futura inválida: "
            f"{rodada_texto}"
        )

        del historico[
            "rodadas"
        ][
            rodada_texto
        ]


historico[
    "ultima_rodada_fechada"
] = rodada_para_salvar

historico[
    "ultima_atualizacao"
] = agora_texto()


salvar_atomico(
    ARQUIVO_HISTORICO,
    historico,
)


print()

print(
    "historico_cartola.json "
    "atualizado com segurança."
)

print(
    "Rodada consolidada: "
    f"{rodada_para_salvar}"
)

print(
    "Times atualizados: "
    f"{len(novos_registros)}"
)

print(
    "Fonte: snapshot previamente validado."
)

print(
    "Proteção contra respostas defasadas: ATIVA."
)
