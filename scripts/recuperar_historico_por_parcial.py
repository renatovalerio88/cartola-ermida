import json
import os
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo


ARQUIVO_HISTORICO = Path("historico_cartola.json")
ARQUIVO_FONTE = Path("parciais_cartola.json")

TOTAL_TIMES = 36
FUSO = ZoneInfo("America/Sao_Paulo")

FONTES_ACEITAS = {
    "atletas_pontuados",
    "snapshot_ao_vivo_validado",
    "parciais_finais_validadas",
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


def carregar_json(caminho):
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

    if not isinstance(
        detalhes,
        list,
    ) or not detalhes:
        raise ValueError(
            f"{item.get('time', 'Time desconhecido')}: "
            "não possui detalhes_parcial."
        )

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


def validar_fonte(fonte):
    print()
    print("Validando snapshot de recuperação...")

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

    if rodada_dados <= 0:
        raise ValueError(
            "rodada_dados inválida."
        )

    if rodada_pontuados != rodada_dados:
        raise ValueError(
            "A rodada da API de pontuados não corresponde "
            "à rodada do snapshot. "
            f"rodada_dados={rodada_dados}; "
            f"rodada_pontuados={rodada_pontuados}."
        )

    if rodada_cartola != rodada_dados:
        raise ValueError(
            "O snapshot não foi capturado enquanto a própria "
            "rodada ainda estava ativa. "
            f"rodada_cartola={rodada_cartola}; "
            f"rodada_dados={rodada_dados}."
        )

    if not bool(
        fonte.get(
            "rodada_em_andamento",
            False,
        )
    ):
        raise ValueError(
            "O snapshot não está marcado como rodada_em_andamento."
        )

    monitoramento = fonte.get(
        "monitoramento",
        {},
    )

    if not isinstance(
        monitoramento,
        dict,
    ):
        raise ValueError(
            "Bloco monitoramento inválido."
        )

    if not bool(
        monitoramento.get(
            "houve_parciais_validas",
            False,
        )
    ):
        raise ValueError(
            "O snapshot informa que não havia parciais válidas."
        )

    times_processados = inteiro(
        monitoramento.get(
            "times_processados",
            0,
        )
    )

    if times_processados != TOTAL_TIMES:
        raise ValueError(
            "O snapshot não processou todos os times. "
            f"Encontrado: {times_processados}/{TOTAL_TIMES}."
        )

    total_atletas = inteiro(
        fonte.get(
            "total_atletas_pontuados",
            0,
        )
    )

    if total_atletas <= 0:
        raise ValueError(
            "O snapshot não possui atletas pontuados."
        )

    times = fonte.get(
        "times",
        [],
    )

    if not isinstance(
        times,
        list,
    ):
        raise ValueError(
            "O snapshot não contém uma lista válida de times."
        )

    if len(times) != TOTAL_TIMES:
        raise ValueError(
            "Quantidade incorreta de times no snapshot. "
            f"Encontrados: {len(times)}/{TOTAL_TIMES}."
        )

    ids_esperados = {
        time_id
        for time_id, _, _ in TIMES
    }

    mapa = {}
    erros = []

    for item in times:
        if not isinstance(
            item,
            dict,
        ):
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
                time_id,
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

        if rodada_item != rodada_dados:
            erros.append(
                f"{nome_time}: rodada_dados={rodada_item}, "
                f"esperada={rodada_dados}."
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
                f"{nome_time}: fonte_pontos não confiável: "
                f"{fonte_pontos or 'vazia'}."
            )
            continue

        pontos = round(
            numero(
                item.get(
                    "pontos",
                    0,
                )
            ),
            2,
        )

        try:
            soma = somar_detalhes(
                item
            )
        except Exception as erro:
            erros.append(
                str(erro)
            )
            continue

        if abs(
            soma - pontos
        ) > 0.11:
            erros.append(
                f"{nome_time}: pontos do time {pontos:.2f} "
                f"não batem com soma dos atletas {soma:.2f}."
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
            "Times ausentes: "
            + ", ".join(
                str(item)
                for item in sorted(
                    faltantes
                )
            )
        )

    if extras:
        erros.append(
            "Times inesperados: "
            + ", ".join(
                str(item)
                for item in sorted(
                    extras
                )
            )
        )

    if erros:
        print()
        print("SNAPSHOT REPROVADO:")

        for erro in erros:
            print(
                f" - {erro}"
            )

        raise RuntimeError(
            "A recuperação foi cancelada. "
            "Nenhum dado foi alterado."
        )

    print(
        f"Rodada validada: {rodada_dados}"
    )

    print(
        f"Times validados: {len(mapa)}/{TOTAL_TIMES}"
    )

    print(
        f"Atletas pontuados na API: {total_atletas}"
    )

    print(
        "Fonte atleta a atleta: APROVADA"
    )

    return (
        rodada_dados,
        mapa,
    )


def mapa_historico(registros):
    mapa = {}

    if not isinstance(
        registros,
        list,
    ):
        return mapa

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


def montar_rodada_recuperada(
    rodada,
    mapa_fonte,
):
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
            "rodada": rodada,
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
            "fonte_pontos": "atletas_pontuados_recuperado",
        }

        novos_registros.append(
            registro
        )

    return novos_registros


def mostrar_comparacao(
    registros_antigos,
    registros_novos,
):
    antigos = mapa_historico(
        registros_antigos
    )

    novos = mapa_historico(
        registros_novos
    )

    diferencas = []

    print()
    print(
        "Comparação entre histórico atual "
        "e snapshot validado:"
    )

    for (
        time_id,
        nome_time,
        _cartoleiro,
    ) in TIMES:
        antigo = antigos.get(
            time_id
        )

        novo = novos.get(
            time_id
        )

        if not antigo or not novo:
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

        mudou_pontos = (
            pontos_antigos
            != pontos_novos
        )

        mudou_patrimonio = (
            patrimonio_antigo
            != patrimonio_novo
        )

        if (
            mudou_pontos
            or mudou_patrimonio
        ):
            diferencas.append(
                nome_time
            )

            print(
                f" - {nome_time}: "
                f"{pontos_antigos:.2f} -> "
                f"{pontos_novos:.2f} pts | "
                f"C$ {patrimonio_antigo:.2f} -> "
                f"C$ {patrimonio_novo:.2f}"
            )

    print()
    print(
        f"Registros diferentes: "
        f"{len(diferencas)}/{TOTAL_TIMES}"
    )

    return diferencas


def validar_historico_apos_recuperacao(
    historico,
    rodada,
    registros_esperados,
):
    registros = historico.get(
        "rodadas",
        {},
    ).get(
        str(rodada),
        [],
    )

    if not isinstance(
        registros,
        list,
    ):
        raise RuntimeError(
            "A rodada recuperada não existe "
            "no histórico após a substituição."
        )

    if len(registros) != TOTAL_TIMES:
        raise RuntimeError(
            "A rodada recuperada ficou incompleta."
        )

    mapa_atual = mapa_historico(
        registros
    )

    mapa_esperado = mapa_historico(
        registros_esperados
    )

    if set(
        mapa_atual.keys()
    ) != set(
        mapa_esperado.keys()
    ):
        raise RuntimeError(
            "Os IDs da rodada recuperada "
            "não correspondem aos esperados."
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

        if (
            pontos_atual
            != pontos_esperado
            or patrimonio_atual
            != patrimonio_esperado
        ):
            raise RuntimeError(
                "Falha na validação final do histórico "
                f"para time_id {time_id}."
            )


def main():
    print("=" * 70)
    print("CARTOLA DE ERMIDA")
    print("RECUPERAÇÃO SEGURA DE RODADA HISTÓRICA")
    print("=" * 70)

    fonte = carregar_json(
        ARQUIVO_FONTE
    )

    historico = carregar_json(
        ARQUIVO_HISTORICO
    )

    if not isinstance(
        historico.get(
            "rodadas",
            {},
        ),
        dict,
    ):
        raise RuntimeError(
            "historico_cartola.json não possui "
            "o bloco rodadas corretamente."
        )

    rodada, mapa_fonte = (
        validar_fonte(
            fonte
        )
    )

    chave_rodada = str(
        rodada
    )

    registros_antigos = (
        historico[
            "rodadas"
        ].get(
            chave_rodada
        )
    )

    if not isinstance(
        registros_antigos,
        list,
    ):
        raise RuntimeError(
            f"A rodada {rodada} não existe "
            "no histórico atual."
        )

    if len(
        registros_antigos
    ) != TOTAL_TIMES:
        raise RuntimeError(
            f"A rodada {rodada} existente "
            "não possui os 36 registros esperados."
        )

    registros_novos = (
        montar_rodada_recuperada(
            rodada,
            mapa_fonte,
        )
    )

    diferencas = mostrar_comparacao(
        registros_antigos,
        registros_novos,
    )

    if not diferencas:
        print()
        print(
            "Nenhuma diferença encontrada."
        )

        print(
            "O histórico já corresponde "
            "ao snapshot validado."
        )

        return

    print()
    print(
        "Substituindo a rodada inteira "
        f"{rodada} por uma única fonte "
        "homogênea e validada..."
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
        "rodada": rodada,
        "data": agora_texto(),
        "fonte": "parciais_cartola.json",
        "fonte_pontos": "atletas_pontuados",
        "times_validados": TOTAL_TIMES,
        "registros_alterados": len(
            diferencas
        ),
    }

    validar_historico_apos_recuperacao(
        historico,
        rodada,
        registros_novos,
    )

    salvar_atomico(
        ARQUIVO_HISTORICO,
        historico,
    )

    print()
    print("=" * 70)
    print("RECUPERAÇÃO CONCLUÍDA")
    print("=" * 70)

    print(
        f"Rodada recuperada: {rodada}"
    )

    print(
        f"Times validados: {TOTAL_TIMES}"
    )

    print(
        f"Registros que divergiam: "
        f"{len(diferencas)}"
    )

    print(
        "Fonte utilizada: atletas_pontuados"
    )

    print(
        "historico_cartola.json atualizado."
    )

    print(
        "Nenhuma outra rodada foi modificada."
    )


if __name__ == "__main__":
    main()
