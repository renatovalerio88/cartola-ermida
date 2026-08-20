import json
from collections import defaultdict
from pathlib import Path


ARQUIVO_HISTORICO = Path("historico_cartola.json")

TOTAL_TIMES = 36

# Se 3 ou mais times repetirem simultaneamente pontos E patrimônio
# em rodadas consecutivas, a rodada será destacada para investigação.
LIMITE_REPETICOES_SUSPEITAS = 3

# Diferenças maiores que isso entre rodadas serão apenas destacadas.
# Não significam necessariamente erro.
LIMITE_VARIACAO_PONTOS = 100.0
LIMITE_VARIACAO_PATRIMONIO = 40.0


TIMES = [
    (3619967, "Forward F. Club"),
    (40995, "WECAM"),
    (6074454, "SardoGalo 13"),
    (385413, "Mão C.F"),
    (8976743, "MT10M1T0"),
    (50252506, "Branes25"),
    (195382, "CAMARASSO"),
    (60383, "RJ Clube"),
    (19198951, "SANTASTICO GLORIOSO I"),
    (25588958, "JUNA FUTEBOL CLUBE"),
    (654232, "D1OS"),
    (974057, "S.C. Finha Paulista"),
    (2745059, "Epidemia Sport Clube"),
    (91357, "DP-SC"),
    (29565271, "Legione Romanista"),
    (28538913, "Maria Gol De Costas"),
    (178173, "Jack Golden"),
    (21141036, "Ardam Cabubu"),
    (50327258, "Digdigie94"),
    (18434405, "Gabiru cabuloso"),
    (1193651, "CruzeiroKiller"),
    (25565544, "CHARLLOTTTE F.C."),
    (28604976, "Galo de Rio Doce FC"),
    (14705949, "Seu Cuca Futebol"),
    (214265, "Framos F.C"),
    (186377, "JACB FC"),
    (51042838, "A76 FC"),
    (285883, "Kayser Football"),
    (3128927, "Jafeth G.D.F.C."),
    (25937153, "GALOBERA F.C"),
    (1005072, "PELUDÃO13"),
    (49415297, "SemFreio LEFC1988"),
    (103947, "Campista F. C"),
    (24449, "Sport Club Prexeca Bangers"),
    (25889523, "Clube de Regatas Sô"),
    (596168, "Galo Doido BH 93"),
]


IDS_ESPERADOS = {time_id for time_id, _ in TIMES}
NOMES = {time_id: nome for time_id, nome in TIMES}


def inteiro(valor, padrao=0):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def numero(valor, padrao=None):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def formatar_numero(valor):
    if valor is None:
        return "N/D"

    return f"{valor:.2f}".replace(".", ",")


def carregar_historico():
    if not ARQUIVO_HISTORICO.exists():
        raise RuntimeError(
            f"Arquivo não encontrado: {ARQUIVO_HISTORICO}"
        )

    with ARQUIVO_HISTORICO.open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        dados = json.load(arquivo)

    if not isinstance(dados, dict):
        raise RuntimeError(
            "historico_cartola.json não contém um objeto JSON válido."
        )

    rodadas = dados.get("rodadas")

    if not isinstance(rodadas, dict):
        raise RuntimeError(
            "historico_cartola.json não contém o objeto 'rodadas'."
        )

    return dados


def obter_rodadas_ordenadas(historico):
    resultado = []

    for chave in historico.get("rodadas", {}):
        try:
            rodada = int(chave)
        except (TypeError, ValueError):
            continue

        if rodada > 0:
            resultado.append(rodada)

    return sorted(set(resultado))


def registros_da_rodada(historico, rodada):
    registros = historico.get(
        "rodadas",
        {},
    ).get(
        str(rodada),
        [],
    )

    if isinstance(registros, list):
        return registros

    return []


def criar_mapa(registros):
    mapa = {}

    for item in registros:
        if not isinstance(item, dict):
            continue

        time_id = inteiro(
            item.get("time_id"),
            0,
        )

        if time_id > 0 and time_id not in mapa:
            mapa[time_id] = item

    return mapa


def auditar_estrutura_rodada(historico, rodada):
    registros = registros_da_rodada(
        historico,
        rodada,
    )

    problemas = []
    avisos = []

    if len(registros) != TOTAL_TIMES:
        problemas.append(
            f"quantidade de registros = {len(registros)} "
            f"(esperado {TOTAL_TIMES})"
        )

    ids = []
    ids_invalidos = []

    for indice, item in enumerate(registros, start=1):
        if not isinstance(item, dict):
            problemas.append(
                f"registro {indice} não é um objeto JSON"
            )
            continue

        time_id = inteiro(
            item.get("time_id"),
            0,
        )

        if time_id <= 0:
            ids_invalidos.append(indice)
        else:
            ids.append(time_id)

        rodada_registro = inteiro(
            item.get("rodada"),
            rodada,
        )

        if rodada_registro != rodada:
            problemas.append(
                f"registro de {item.get('time', time_id)} "
                f"informa rodada {rodada_registro}"
            )

        pontos = numero(
            item.get("pontos"),
            None,
        )

        patrimonio = numero(
            item.get("patrimonio"),
            None,
        )

        if pontos is None:
            problemas.append(
                f"{item.get('time', time_id)} sem pontuação válida"
            )

        if patrimonio is None:
            avisos.append(
                f"{item.get('time', time_id)} sem patrimônio válido"
            )

    if ids_invalidos:
        problemas.append(
            f"{len(ids_invalidos)} registros com time_id inválido"
        )

    duplicados = sorted(
        time_id
        for time_id in set(ids)
        if ids.count(time_id) > 1
    )

    if duplicados:
        nomes = [
            NOMES.get(time_id, str(time_id))
            for time_id in duplicados
        ]

        problemas.append(
            "times duplicados: " + ", ".join(nomes)
        )

    ids_encontrados = set(ids)

    faltantes = sorted(
        IDS_ESPERADOS - ids_encontrados
    )

    extras = sorted(
        ids_encontrados - IDS_ESPERADOS
    )

    if faltantes:
        problemas.append(
            "times ausentes: "
            + ", ".join(
                NOMES.get(time_id, str(time_id))
                for time_id in faltantes
            )
        )

    if extras:
        problemas.append(
            "times inesperados: "
            + ", ".join(str(time_id) for time_id in extras)
        )

    return {
        "rodada": rodada,
        "registros": len(registros),
        "problemas": problemas,
        "avisos": avisos,
        "mapa": criar_mapa(registros),
    }


def auditar_repeticoes(
    rodada_anterior,
    mapa_anterior,
    rodada_atual,
    mapa_atual,
):
    repeticao_completa = []
    repeticao_pontos = []
    repeticao_patrimonio = []

    for time_id in sorted(
        IDS_ESPERADOS
        & set(mapa_anterior)
        & set(mapa_atual)
    ):
        anterior = mapa_anterior[time_id]
        atual = mapa_atual[time_id]

        pontos_anterior = numero(
            anterior.get("pontos"),
            None,
        )

        pontos_atual = numero(
            atual.get("pontos"),
            None,
        )

        patrimonio_anterior = numero(
            anterior.get("patrimonio"),
            None,
        )

        patrimonio_atual = numero(
            atual.get("patrimonio"),
            None,
        )

        mesmos_pontos = (
            pontos_anterior is not None
            and pontos_atual is not None
            and round(pontos_anterior, 2)
            == round(pontos_atual, 2)
        )

        mesmo_patrimonio = (
            patrimonio_anterior is not None
            and patrimonio_atual is not None
            and round(patrimonio_anterior, 2)
            == round(patrimonio_atual, 2)
        )

        if mesmos_pontos:
            repeticao_pontos.append(time_id)

        if mesmo_patrimonio:
            repeticao_patrimonio.append(time_id)

        if mesmos_pontos and mesmo_patrimonio:
            repeticao_completa.append(time_id)

    return {
        "rodada_anterior": rodada_anterior,
        "rodada_atual": rodada_atual,
        "repeticao_completa": repeticao_completa,
        "repeticao_pontos": repeticao_pontos,
        "repeticao_patrimonio": repeticao_patrimonio,
    }


def auditar_variacoes(
    rodada_anterior,
    mapa_anterior,
    rodada_atual,
    mapa_atual,
):
    alertas = []

    for time_id in sorted(
        IDS_ESPERADOS
        & set(mapa_anterior)
        & set(mapa_atual)
    ):
        anterior = mapa_anterior[time_id]
        atual = mapa_atual[time_id]

        pontos_anterior = numero(
            anterior.get("pontos"),
            None,
        )

        pontos_atual = numero(
            atual.get("pontos"),
            None,
        )

        patrimonio_anterior = numero(
            anterior.get("patrimonio"),
            None,
        )

        patrimonio_atual = numero(
            atual.get("patrimonio"),
            None,
        )

        variacao_pontos = None
        variacao_patrimonio = None

        if (
            pontos_anterior is not None
            and pontos_atual is not None
        ):
            variacao_pontos = (
                pontos_atual - pontos_anterior
            )

        if (
            patrimonio_anterior is not None
            and patrimonio_atual is not None
        ):
            variacao_patrimonio = (
                patrimonio_atual - patrimonio_anterior
            )

        pontos_extremos = (
            variacao_pontos is not None
            and abs(variacao_pontos)
            > LIMITE_VARIACAO_PONTOS
        )

        patrimonio_extremo = (
            variacao_patrimonio is not None
            and abs(variacao_patrimonio)
            > LIMITE_VARIACAO_PATRIMONIO
        )

        if pontos_extremos or patrimonio_extremo:
            alertas.append(
                {
                    "time_id": time_id,
                    "time": NOMES.get(
                        time_id,
                        str(time_id),
                    ),
                    "rodada_anterior": rodada_anterior,
                    "rodada_atual": rodada_atual,
                    "pontos_anterior": pontos_anterior,
                    "pontos_atual": pontos_atual,
                    "variacao_pontos": variacao_pontos,
                    "patrimonio_anterior": patrimonio_anterior,
                    "patrimonio_atual": patrimonio_atual,
                    "variacao_patrimonio": variacao_patrimonio,
                }
            )

    return alertas


def auditar_repeticoes_internas(historico, rodadas):
    """
    Procura assinaturas completas repetidas para o mesmo time
    em quaisquer rodadas, não apenas rodadas consecutivas.

    Isso é apenas informativo. Pontuação e patrimônio iguais
    podem ocorrer legitimamente.
    """

    assinaturas = defaultdict(list)

    for rodada in rodadas:
        mapa = criar_mapa(
            registros_da_rodada(
                historico,
                rodada,
            )
        )

        for time_id, item in mapa.items():
            pontos = numero(
                item.get("pontos"),
                None,
            )

            patrimonio = numero(
                item.get("patrimonio"),
                None,
            )

            if pontos is None or patrimonio is None:
                continue

            assinatura = (
                time_id,
                round(pontos, 2),
                round(patrimonio, 2),
            )

            assinaturas[assinatura].append(
                rodada
            )

    repeticoes = []

    for (
        time_id,
        pontos,
        patrimonio,
    ), lista_rodadas in assinaturas.items():
        if len(lista_rodadas) <= 1:
            continue

        repeticoes.append(
            {
                "time_id": time_id,
                "time": NOMES.get(
                    time_id,
                    str(time_id),
                ),
                "pontos": pontos,
                "patrimonio": patrimonio,
                "rodadas": lista_rodadas,
            }
        )

    return repeticoes


def imprimir_titulo(texto):
    print()
    print("=" * 72)
    print(texto)
    print("=" * 72)


historico = carregar_historico()
rodadas = obter_rodadas_ordenadas(
    historico
)

if not rodadas:
    raise RuntimeError(
        "Nenhuma rodada encontrada no histórico."
    )


print("=" * 72)
print("AUDITORIA DO HISTÓRICO - CARTOLA DE ERMIDA")
print("=" * 72)

print(
    f"Liga: {historico.get('liga', 'N/D')}"
)

print(
    f"Rodadas encontradas: "
    f"{rodadas[0]} a {rodadas[-1]}"
)

print(
    f"Quantidade de rodadas: {len(rodadas)}"
)

print(
    f"Times esperados por rodada: {TOTAL_TIMES}"
)

print()
print(
    "IMPORTANTE: esta auditoria é SOMENTE LEITURA."
)

print(
    "Nenhum arquivo será modificado."
)


resultados_estrutura = {}
rodadas_com_problema = []
rodadas_com_aviso = []


imprimir_titulo(
    "1. INTEGRIDADE ESTRUTURAL DAS RODADAS"
)


for rodada in rodadas:
    resultado = auditar_estrutura_rodada(
        historico,
        rodada,
    )

    resultados_estrutura[rodada] = resultado

    if resultado["problemas"]:
        rodadas_com_problema.append(
            rodada
        )

        print(
            f"R{rodada:02d}: REPROVADA"
        )

        for problema in resultado["problemas"]:
            print(
                f"  ERRO: {problema}"
            )

    elif resultado["avisos"]:
        rodadas_com_aviso.append(
            rodada
        )

        print(
            f"R{rodada:02d}: APROVADA COM AVISOS"
        )

        for aviso in resultado["avisos"]:
            print(
                f"  AVISO: {aviso}"
            )

    else:
        print(
            f"R{rodada:02d}: OK "
            f"({resultado['registros']}/{TOTAL_TIMES})"
        )


imprimir_titulo(
    "2. REPETIÇÕES ENTRE RODADAS CONSECUTIVAS"
)


comparacoes = []
rodadas_suspeitas = []


for indice in range(1, len(rodadas)):
    rodada_anterior = rodadas[indice - 1]
    rodada_atual = rodadas[indice]

    # Só tratamos como consecutivas se realmente forem N e N+1.
    if rodada_atual != rodada_anterior + 1:
        print(
            f"R{rodada_anterior:02d} -> "
            f"R{rodada_atual:02d}: "
            "rodadas não consecutivas; comparação ignorada."
        )
        continue

    mapa_anterior = resultados_estrutura[
        rodada_anterior
    ]["mapa"]

    mapa_atual = resultados_estrutura[
        rodada_atual
    ]["mapa"]

    resultado = auditar_repeticoes(
        rodada_anterior,
        mapa_anterior,
        rodada_atual,
        mapa_atual,
    )

    comparacoes.append(
        resultado
    )

    quantidade = len(
        resultado["repeticao_completa"]
    )

    if quantidade >= LIMITE_REPETICOES_SUSPEITAS:
        rodadas_suspeitas.append(
            rodada_atual
        )

        print()
        print(
            f"R{rodada_anterior:02d} -> "
            f"R{rodada_atual:02d}: "
            f"ALERTA ({quantidade} repetições completas)"
        )

        for time_id in resultado[
            "repeticao_completa"
        ]:
            atual = mapa_atual[time_id]

            print(
                "  "
                + NOMES.get(
                    time_id,
                    str(time_id),
                )
                + " | "
                + formatar_numero(
                    numero(
                        atual.get("pontos"),
                        None,
                    )
                )
                + " pts | C$ "
                + formatar_numero(
                    numero(
                        atual.get("patrimonio"),
                        None,
                    )
                )
            )

    elif quantidade > 0:
        print(
            f"R{rodada_anterior:02d} -> "
            f"R{rodada_atual:02d}: "
            f"{quantidade} repetição(ões) completa(s), "
            "abaixo do limite de alerta."
        )

    else:
        print(
            f"R{rodada_anterior:02d} -> "
            f"R{rodada_atual:02d}: OK"
        )


imprimir_titulo(
    "3. VARIAÇÕES EXTREMAS ENTRE RODADAS"
)


todos_alertas_variacao = []


for indice in range(1, len(rodadas)):
    rodada_anterior = rodadas[indice - 1]
    rodada_atual = rodadas[indice]

    if rodada_atual != rodada_anterior + 1:
        continue

    mapa_anterior = resultados_estrutura[
        rodada_anterior
    ]["mapa"]

    mapa_atual = resultados_estrutura[
        rodada_atual
    ]["mapa"]

    alertas = auditar_variacoes(
        rodada_anterior,
        mapa_anterior,
        rodada_atual,
        mapa_atual,
    )

    todos_alertas_variacao.extend(
        alertas
    )


if not todos_alertas_variacao:
    print(
        "Nenhuma variação extrema encontrada."
    )

else:
    for alerta in todos_alertas_variacao:
        print()
        print(
            f"{alerta['time']} | "
            f"R{alerta['rodada_anterior']:02d} -> "
            f"R{alerta['rodada_atual']:02d}"
        )

        if alerta["variacao_pontos"] is not None:
            print(
                "  Pontos: "
                f"{formatar_numero(alerta['pontos_anterior'])} -> "
                f"{formatar_numero(alerta['pontos_atual'])} "
                f"(variação "
                f"{formatar_numero(alerta['variacao_pontos'])})"
            )

        if alerta["variacao_patrimonio"] is not None:
            print(
                "  Patrimônio: "
                f"{formatar_numero(alerta['patrimonio_anterior'])} -> "
                f"{formatar_numero(alerta['patrimonio_atual'])} "
                f"(variação "
                f"{formatar_numero(alerta['variacao_patrimonio'])})"
            )


imprimir_titulo(
    "4. ASSINATURAS REPETIDAS NO HISTÓRICO"
)


repeticoes_historicas = (
    auditar_repeticoes_internas(
        historico,
        rodadas,
    )
)


if not repeticoes_historicas:
    print(
        "Nenhuma combinação exata de pontos + patrimônio "
        "foi repetida pelo mesmo time."
    )

else:
    print(
        f"Foram encontradas "
        f"{len(repeticoes_historicas)} "
        "assinaturas repetidas."
    )

    print(
        "Isso não significa automaticamente erro; "
        "serve apenas para investigação."
    )

    for item in repeticoes_historicas:
        rodadas_texto = ", ".join(
            f"R{rodada:02d}"
            for rodada in item["rodadas"]
        )

        print(
            f"  {item['time']} | "
            f"{formatar_numero(item['pontos'])} pts | "
            f"C$ {formatar_numero(item['patrimonio'])} | "
            f"{rodadas_texto}"
        )


imprimir_titulo(
    "5. RESUMO FINAL"
)


print(
    f"Rodadas auditadas: {len(rodadas)}"
)

print(
    f"Times esperados por rodada: {TOTAL_TIMES}"
)

print(
    f"Registros esperados no total: "
    f"{len(rodadas) * TOTAL_TIMES}"
)

print(
    f"Rodadas com problema estrutural: "
    f"{len(rodadas_com_problema)}"
)

if rodadas_com_problema:
    print(
        "  "
        + ", ".join(
            f"R{rodada:02d}"
            for rodada in rodadas_com_problema
        )
    )


print(
    f"Rodadas com avisos estruturais: "
    f"{len(rodadas_com_aviso)}"
)

if rodadas_com_aviso:
    print(
        "  "
        + ", ".join(
            f"R{rodada:02d}"
            for rodada in rodadas_com_aviso
        )
    )


rodadas_suspeitas = sorted(
    set(rodadas_suspeitas)
)

print(
    f"Rodadas com padrão forte de repetição: "
    f"{len(rodadas_suspeitas)}"
)

if rodadas_suspeitas:
    print(
        "  "
        + ", ".join(
            f"R{rodada:02d}"
            for rodada in rodadas_suspeitas
        )
    )


print(
    f"Variações extremas para revisão: "
    f"{len(todos_alertas_variacao)}"
)

print(
    f"Assinaturas históricas repetidas: "
    f"{len(repeticoes_historicas)}"
)


print()
print("-" * 72)


if rodadas_com_problema:
    print(
        "RESULTADO: ATENÇÃO - existem problemas "
        "estruturais no histórico."
    )

elif rodadas_suspeitas:
    print(
        "RESULTADO: ATENÇÃO - existem rodadas com "
        "padrão semelhante a possível dado defasado."
    )

else:
    print(
        "RESULTADO: APROVADO - nenhuma evidência forte "
        "de contaminação foi encontrada."
    )


print("-" * 72)

print()
print(
    "Auditoria concluída."
)

print(
    "Nenhum arquivo foi alterado."
)
