import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo


# ============================================================
# CARTOLA DE ERMIDA
# Recuperação segura de rodada histórica
#
# Fonte imutável:
# parciais_cartola.json do commit 992d5f4
#
# Objetivo:
# recuperar a rodada 23 do historico_cartola.json usando
# exclusivamente o último snapshot válido conhecido antes
# da contaminação causada pela abertura do mercado seguinte.
# ============================================================


ARQUIVO_HISTORICO = Path("historico_cartola.json")

TOTAL_TIMES = 36
RODADA_RECUPERACAO = 23

COMMIT_SNAPSHOT = "992d5f4"

URL_SNAPSHOT = (
    "https://raw.githubusercontent.com/"
    "renatovalerio88/cartola-ermida/"
    f"{COMMIT_SNAPSHOT}/parciais_cartola.json"
)

FUSO = ZoneInfo("America/Sao_Paulo")

FONTES_ACEITAS = {
    "atletas_pontuados",
}


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


def carregar_json_local(caminho):
    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho}"
        )

    with caminho.open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        dados = json.load(arquivo)

    if not isinstance(dados, dict):
        raise ValueError(
            f"{caminho} não contém um objeto JSON válido."
        )

    return dados


def buscar_json(url, tentativas=3):
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            print(
                f"Tentativa {tentativa}/{tentativas} "
                "de baixar o snapshot..."
            )

            requisicao = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                    "Cache-Control": "no-cache",
                },
            )

            with urllib.request.urlopen(
                requisicao,
                timeout=30,
            ) as resposta:
                conteudo = resposta.read().decode("utf-8")

            dados = json.loads(conteudo)

            if not isinstance(dados, dict):
                raise ValueError(
                    "O snapshot baixado não contém "
                    "um objeto JSON."
                )

            return dados

        except Exception as erro:
            ultimo_erro = erro

            print(
                f"Falha na tentativa {tentativa}: {erro}"
            )

            if tentativa < tentativas:
                time.sleep(tentativa * 2)

    raise RuntimeError(
        "Não foi possível baixar o snapshot histórico "
        f"do commit {COMMIT_SNAPSHOT}: {ultimo_erro}"
    )


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


def somar_detalhes(item):
    detalhes = item.get(
        "detalhes_parcial",
        [],
    )

    if not isinstance(detalhes, list) or not detalhes:
        raise ValueError(
            f"{item.get('time', 'Time desconhecido')}: "
            "detalhes_parcial ausente ou vazio."
        )

    total = 0.0

    for atleta in detalhes:
        if not isinstance(atleta, dict):
            continue

        total += numero(
            atleta.get(
                "pontos_computados",
                0,
            )
        )

    return round(total, 2)


def validar_snapshot(fonte):
    print()
    print("=" * 70)
    print("VALIDANDO SNAPSHOT HISTÓRICO")
    print("=" * 70)

    rodada_cartola = inteiro(
        fonte.get(
            "rodada_cartola",
            0,
        )
    )

    rodada_dados = inteiro(
        fonte.get(
            "rodada_dados",
            0,
        )
    )

    rodada_pontuados = inteiro(
        fonte.get(
            "rodada_pontuados",
            0,
        )
    )

    print(
        f"Commit fonte: {COMMIT_SNAPSHOT}"
    )

    print(
        f"Rodada Cartola no snapshot: {rodada_cartola}"
    )

    print(
        f"Rodada dos dados: {rodada_dados}"
    )

    print(
        f"Rodada dos pontuados: {rodada_pontuados}"
    )

    if rodada_cartola != RODADA_RECUPERACAO:
        raise RuntimeError(
            "Snapshot rejeitado: rodada_cartola incorreta. "
            f"Esperada={RODADA_RECUPERACAO}; "
            f"encontrada={rodada_cartola}."
        )

    if rodada_dados != RODADA_RECUPERACAO:
        raise RuntimeError(
            "Snapshot rejeitado: rodada_dados incorreta. "
            f"Esperada={RODADA_RECUPERACAO}; "
            f"encontrada={rodada_dados}."
        )

    if rodada_pontuados != RODADA_RECUPERACAO:
        raise RuntimeError(
            "Snapshot rejeitado: rodada_pontuados incorreta. "
            f"Esperada={RODADA_RECUPERACAO}; "
            f"encontrada={rodada_pontuados}."
        )

    if not bool(
        fonte.get(
            "rodada_em_andamento",
            False,
        )
    ):
        raise RuntimeError(
            "Snapshot rejeitado: rodada_em_andamento "
            "não está marcada como true."
        )

    total_atletas = inteiro(
        fonte.get(
            "total_atletas_pontuados",
            0,
        )
    )

    if total_atletas <= 0:
        raise RuntimeError(
            "Snapshot rejeitado: nenhum atleta pontuado."
        )

    monitoramento = fonte.get(
        "monitoramento",
        {},
    )

    if not isinstance(monitoramento, dict):
        raise RuntimeError(
            "Snapshot rejeitado: monitoramento inválido."
        )

    houve_parciais_validas = bool(
        monitoramento.get(
            "houve_parciais_validas",
            False,
        )
    )

    if not houve_parciais_validas:
        raise RuntimeError(
            "Snapshot rejeitado: não havia "
            "parciais válidas."
        )

    times_processados = inteiro(
        monitoramento.get(
            "times_processados",
            0,
        )
    )

    if times_processados != TOTAL_TIMES:
        raise RuntimeError(
            "Snapshot rejeitado: quantidade incorreta "
            "de times processados. "
            f"{times_processados}/{TOTAL_TIMES}."
        )

    times = fonte.get(
        "times",
        [],
    )

    if not isinstance(times, list):
        raise RuntimeError(
            "Snapshot rejeitado: bloco times inválido."
        )

    if len(times) != TOTAL_TIMES:
        raise RuntimeError(
            "Snapshot rejeitado: quantidade incorreta "
            f"de times. {len(times)}/{TOTAL_TIMES}."
        )

    ids_esperados = {
        time_id
        for time_id, _, _ in TIMES
    }

    mapa = {}
    erros = []

    for item in times:
        if not isinstance(item, dict):
            erros.append(
                "Registro de time inválido."
            )
            continue

        time_id = inteiro(
            item.get(
                "time_id",
                0,
            )
        )

        nome_time = str(
            item.get(
                "time",
                f"time_id={time_id}",
            )
        )

        if time_id <= 0:
            erros.append(
                f"{nome_time}: time_id inválido."
            )
            continue

        if time_id in mapa:
            erros.append(
                f"{nome_time}: time_id duplicado."
            )
            continue

        rodada_item = inteiro(
            item.get(
                "rodada_dados",
                0,
            )
        )

        if rodada_item != RODADA_RECUPERACAO:
            erros.append(
                f"{nome_time}: rodada_dados "
                f"{rodada_item}, esperada "
                f"{RODADA_RECUPERACAO}."
            )
            continue

        fonte_pontos = str(
            item.get(
                "fonte_pontos",
                "",
            )
        ).strip()

        if fonte_pontos not in FONTES_ACEITAS:
            erros.append(
                f"{nome_time}: fonte_pontos "
                f"não confiável: "
                f"{fonte_pontos or 'vazia'}."
            )
            continue

        pontos_time = round(
            numero(
                item.get(
                    "pontos",
                    0,
                )
            ),
            2,
        )

        try:
            pontos_atletas = somar_detalhes(
                item
            )
        except Exception as erro:
            erros.append(
                str(erro)
            )
            continue

        diferenca = round(
            pontos_time - pontos_atletas,
            2,
        )

        if abs(diferenca) > 0.11:
            erros.append(
                f"{nome_time}: total do time "
                f"{pontos_time:.2f} não bate com "
                f"a soma atleta a atleta "
                f"{pontos_atletas:.2f}. "
                f"Diferença={diferenca:.2f}."
            )
            continue

        mapa[time_id] = item

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

    if faltantes:
        erros.append(
            "Times esperados ausentes: "
            + ", ".join(
                str(time_id)
                for time_id in sorted(faltantes)
            )
        )

    if extras:
        erros.append(
            "Times inesperados no snapshot: "
            + ", ".join(
                str(time_id)
                for time_id in sorted(extras)
            )
        )

    if erros:
        print()
        print("SNAPSHOT REPROVADO")

        for erro in erros:
            print(
                f" - {erro}"
            )

        raise RuntimeError(
            "Recuperação cancelada. "
            "historico_cartola.json NÃO foi alterado."
        )

    print()
    print("SNAPSHOT APROVADO")
    print(
        f"Times validados: {len(mapa)}/{TOTAL_TIMES}"
    )
    print(
        f"Atletas pontuados: {total_atletas}"
    )
    print(
        "Fonte dos pontos: atletas_pontuados"
    )
    print(
        "Soma atleta a atleta: validada para os 36 times"
    )

    return mapa


def mapa_historico(registros):
    mapa = {}

    if not isinstance(registros, list):
        return mapa

    for item in registros:
        if not isinstance(item, dict):
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


def validar_rodada_existente(registros):
    if not isinstance(registros, list):
        raise RuntimeError(
            f"A rodada {RODADA_RECUPERACAO} "
            "não existe no histórico."
        )

    if len(registros) != TOTAL_TIMES:
        raise RuntimeError(
            f"A rodada {RODADA_RECUPERACAO} "
            "existente não possui os "
            f"{TOTAL_TIMES} registros esperados."
        )

    mapa = mapa_historico(
        registros
    )

    if len(mapa) != TOTAL_TIMES:
        raise RuntimeError(
            f"A rodada {RODADA_RECUPERACAO} "
            "possui IDs ausentes ou duplicados."
        )

    ids_esperados = {
        time_id
        for time_id, _, _ in TIMES
    }

    if set(mapa.keys()) != ids_esperados:
        raise RuntimeError(
            f"A rodada {RODADA_RECUPERACAO} "
            "não contém exatamente os 36 times "
            "esperados da liga."
        )

    return mapa


def montar_rodada_recuperada(mapa_fonte):
    novos_registros = []

    for (
        time_id,
        nome_time,
        cartoleiro,
    ) in TIMES:
        origem = mapa_fonte[
            time_id
        ]

        registro = {
            "time_id": time_id,
            "time": nome_time,
            "cartoleiro": cartoleiro,
            "rodada": RODADA_RECUPERACAO,
            "pontos": round(
                numero(
                    origem.get(
                        "pontos",
                        0,
                    )
                ),
                2,
            ),
            "patrimonio": round(
                numero(
                    origem.get(
                        "patrimonio",
                        0,
                    )
                ),
                2,
            ),
            "fonte_pontos": (
                "atletas_pontuados_recuperado"
            ),
        }

        novos_registros.append(
            registro
        )

    return novos_registros


def comparar_rodadas(
    registros_antigos,
    registros_novos,
):
    mapa_antigo = validar_rodada_existente(
        registros_antigos
    )

    mapa_novo = mapa_historico(
        registros_novos
    )

    diferencas_pontos = []
    diferencas_patrimonio = []

    print()
    print("=" * 70)
    print("COMPARAÇÃO")
    print("=" * 70)

    for (
        time_id,
        nome_time,
        _cartoleiro,
    ) in TIMES:
        antigo = mapa_antigo[
            time_id
        ]

        novo = mapa_novo[
            time_id
        ]

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

        mudou_pontos = (
            pontos_antigos
            != pontos_novos
        )

        mudou_patrimonio = (
            patrimonio_antigo
            != patrimonio_novo
        )

        if mudou_pontos:
            diferencas_pontos.append(
                nome_time
            )

        if mudou_patrimonio:
            diferencas_patrimonio.append(
                nome_time
            )

        if mudou_pontos or mudou_patrimonio:
            print(
                f"{nome_time}: "
                f"{pontos_antigos:.2f} -> "
                f"{pontos_novos:.2f} pts | "
                f"C$ {patrimonio_antigo:.2f} -> "
                f"C$ {patrimonio_novo:.2f}"
            )

    print()
    print(
        "Times com diferença de pontuação: "
        f"{len(diferencas_pontos)}/{TOTAL_TIMES}"
    )

    print(
        "Times com diferença de patrimônio: "
        f"{len(diferencas_patrimonio)}/{TOTAL_TIMES}"
    )

    return (
        diferencas_pontos,
        diferencas_patrimonio,
    )


def validar_resultado_final(
    historico,
    registros_esperados,
):
    rodadas = historico.get(
        "rodadas",
        {},
    )

    registros = rodadas.get(
        str(RODADA_RECUPERACAO),
        [],
    )

    if not isinstance(registros, list):
        raise RuntimeError(
            "Falha na validação final: "
            "rodada recuperada ausente."
        )

    if len(registros) != TOTAL_TIMES:
        raise RuntimeError(
            "Falha na validação final: "
            "rodada recuperada incompleta."
        )

    mapa_atual = mapa_historico(
        registros
    )

    mapa_esperado = mapa_historico(
        registros_esperados
    )

    if set(mapa_atual.keys()) != set(
        mapa_esperado.keys()
    ):
        raise RuntimeError(
            "Falha na validação final: "
            "IDs dos times divergentes."
        )

    for time_id in mapa_esperado:
        atual = mapa_atual[
            time_id
        ]

        esperado = mapa_esperado[
            time_id
        ]

        pontos_atual = round(
            numero(
                atual.get(
                    "pontos",
                    0,
                )
            ),
            2,
        )

        pontos_esperado = round(
            numero(
                esperado.get(
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

        patrimonio_esperado = round(
            numero(
                esperado.get(
                    "patrimonio",
                    0,
                )
            ),
            2,
        )

        if pontos_atual != pontos_esperado:
            raise RuntimeError(
                "Falha na validação final de pontos "
                f"para time_id={time_id}."
            )

        if patrimonio_atual != patrimonio_esperado:
            raise RuntimeError(
                "Falha na validação final de patrimônio "
                f"para time_id={time_id}."
            )


def main():
    print("=" * 70)
    print("CARTOLA DE ERMIDA")
    print("RECUPERAÇÃO SEGURA DO HISTÓRICO")
    print("=" * 70)

    print()
    print(
        f"Rodada a recuperar: {RODADA_RECUPERACAO}"
    )

    print(
        f"Commit imutável da fonte: {COMMIT_SNAPSHOT}"
    )

    print()
    print(
        "Baixando parciais_cartola.json "
        "diretamente do histórico do GitHub..."
    )

    snapshot = buscar_json(
        URL_SNAPSHOT
    )

    mapa_snapshot = validar_snapshot(
        snapshot
    )

    print()
    print(
        "Carregando historico_cartola.json atual..."
    )

    historico = carregar_json_local(
        ARQUIVO_HISTORICO
    )

    rodadas = historico.get(
        "rodadas",
        {}
    )

    if not isinstance(rodadas, dict):
        raise RuntimeError(
            "historico_cartola.json não possui "
            "um bloco rodadas válido."
        )

    chave_rodada = str(
        RODADA_RECUPERACAO
    )

    registros_antigos = rodadas.get(
        chave_rodada
    )

    validar_rodada_existente(
        registros_antigos
    )

    registros_novos = montar_rodada_recuperada(
        mapa_snapshot
    )

    (
        diferencas_pontos,
        diferencas_patrimonio,
    ) = comparar_rodadas(
        registros_antigos,
        registros_novos,
    )

    if not diferencas_pontos and not diferencas_patrimonio:
        print()
        print("=" * 70)
        print("NENHUMA RECUPERAÇÃO NECESSÁRIA")
        print("=" * 70)

        print(
            "A rodada 23 do histórico já corresponde "
            "integralmente ao snapshot validado."
        )

        return

    print()
    print("=" * 70)
    print("RECUPERANDO RODADA")
    print("=" * 70)

    print(
        "A rodada inteira será substituída por "
        "uma única fonte homogênea e validada."
    )

    historico[
        "rodadas"
    ][
        chave_rodada
    ] = registros_novos

    historico[
        "ultima_atualizacao"
    ] = agora_texto()

    historico[
        "ultima_recuperacao_historica"
    ] = {
        "rodada": RODADA_RECUPERACAO,
        "data": agora_texto(),
        "commit_snapshot": COMMIT_SNAPSHOT,
        "arquivo_snapshot": "parciais_cartola.json",
        "fonte_pontos": "atletas_pontuados",
        "times_validados": TOTAL_TIMES,
        "times_com_pontos_corrigidos": len(
            diferencas_pontos
        ),
        "times_com_patrimonio_corrigido": len(
            diferencas_patrimonio
        ),
    }

    validar_resultado_final(
        historico,
        registros_novos,
    )

    salvar_atomico(
        ARQUIVO_HISTORICO,
        historico,
    )

    print()
    print("=" * 70)
    print("RECUPERAÇÃO CONCLUÍDA COM SUCESSO")
    print("=" * 70)

    print(
        f"Rodada recuperada: {RODADA_RECUPERACAO}"
    )

    print(
        f"Times validados: {TOTAL_TIMES}/{TOTAL_TIMES}"
    )

    print(
        "Times com pontuação corrigida: "
        f"{len(diferencas_pontos)}"
    )

    print(
        "Times com patrimônio corrigido: "
        f"{len(diferencas_patrimonio)}"
    )

    print(
        f"Snapshot utilizado: commit {COMMIT_SNAPSHOT}"
    )

    print(
        "Fonte utilizada: atletas_pontuados"
    )

    print(
        "Rodadas anteriores não foram modificadas."
    )

    print(
        "historico_cartola.json salvo atomicamente."
    )


if __name__ == "__main__":
    main()
