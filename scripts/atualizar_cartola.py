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
# Consolidação segura do histórico de rodadas fechadas
#
# OBJETIVOS:
# - nunca sobrescrever automaticamente uma rodada consolidada;
# - nunca gravar rodada incompleta;
# - nunca aceitar resposta de /time/id de outra rodada;
# - validar os 36 times antes de alterar o histórico;
# - usar rodada_atual_cartola.json somente quando o snapshot
#   estiver completo, consistente e corresponder à rodada;
# - permitir /time/id apenas como fonte validada;
# - salvar o histórico de forma atômica;
# - preservar todo o histórico anterior.
# ============================================================


ARQUIVO_HISTORICO = Path("historico_cartola.json")
ARQUIVO_RODADA_ATUAL = Path("rodada_atual_cartola.json")

URL_STATUS = "https://api.cartola.globo.com/mercado/status"

TOTAL_TIMES = 36

FUSO = ZoneInfo("America/Sao_Paulo")


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


IDS_ESPERADOS = {time_id for time_id, _, _ in TIMES}


def agora_texto():
    return datetime.now(FUSO).strftime("%d/%m/%Y %H:%M:%S")


def numero(valor, padrao=None):
    try:
        numero_convertido = float(valor)

        if numero_convertido != numero_convertido:
            return padrao

        if numero_convertido in (float("inf"), float("-inf")):
            return padrao

        return numero_convertido

    except (TypeError, ValueError):
        return padrao


def inteiro(valor, padrao=0):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def buscar_json(url, tentativas=3):
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
            )

            with urllib.request.urlopen(
                req,
                timeout=25,
            ) as resposta:
                conteudo = resposta.read().decode("utf-8")
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

    except FileNotFoundError:
        return {
            "liga": "Cartola de Ermida",
            "rodadas": {},
        }

    except json.JSONDecodeError as erro:
        raise RuntimeError(
            f"{ARQUIVO_HISTORICO} contém JSON inválido: {erro}"
        )

    if not isinstance(dados, dict):
        raise RuntimeError(
            "historico_cartola.json não contém "
            "um objeto JSON válido."
        )

    rodadas = dados.get("rodadas")

    if rodadas is None:
        dados["rodadas"] = {}

    elif not isinstance(rodadas, dict):
        raise RuntimeError(
            "O campo 'rodadas' do histórico não é um objeto."
        )

    dados.setdefault(
        "liga",
        "Cartola de Ermida",
    )

    return dados


def carregar_rodada_atual():
    try:
        with ARQUIVO_RODADA_ATUAL.open(
            "r",
            encoding="utf-8",
        ) as arquivo:
            dados = json.load(arquivo)

    except FileNotFoundError:
        return {}

    except json.JSONDecodeError:
        return {}

    return dados if isinstance(dados, dict) else {}


def salvar_atomico(caminho, dados):
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    nome_temporario = None

    try:
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

    except Exception:
        if (
            nome_temporario
            and os.path.exists(nome_temporario)
        ):
            os.unlink(nome_temporario)

        raise


def validar_registros_rodada(
    registros,
    rodada,
    origem,
):
    """
    Validação estrutural antes de qualquer consolidação.

    Retorna:
        (True, []) quando tudo estiver correto
        (False, [erros]) quando houver qualquer inconsistência
    """

    erros = []

    if not isinstance(registros, list):
        return False, [
            f"{origem}: lista de times inválida."
        ]

    if len(registros) != TOTAL_TIMES:
        erros.append(
            f"{origem}: encontrados {len(registros)} times; "
            f"esperados {TOTAL_TIMES}."
        )

    ids_encontrados = []
    ids_duplicados = set()

    for indice, item in enumerate(
        registros,
        start=1,
    ):
        if not isinstance(item, dict):
            erros.append(
                f"{origem}: registro {indice} "
                "não é um objeto JSON."
            )
            continue

        time_id = inteiro(
            item.get("time_id"),
            0,
        )

        if time_id <= 0:
            erros.append(
                f"{origem}: registro {indice} "
                "sem time_id válido."
            )
            continue

        if time_id in ids_encontrados:
            ids_duplicados.add(time_id)

        ids_encontrados.append(time_id)

        rodada_item = inteiro(
            item.get(
                "rodada",
                item.get(
                    "rodada_dados",
                    rodada,
                ),
            ),
            rodada,
        )

        if rodada_item != rodada:
            erros.append(
                f"{origem}: time {time_id} "
                f"pertence à rodada {rodada_item}; "
                f"esperada {rodada}."
            )

        pontos = numero(
            item.get("pontos"),
            None,
        )

        if pontos is None:
            erros.append(
                f"{origem}: time {time_id} "
                "sem pontuação válida."
            )

        patrimonio = numero(
            item.get("patrimonio"),
            None,
        )

        if patrimonio is None:
            erros.append(
                f"{origem}: time {time_id} "
                "sem patrimônio válido."
            )

    ids_encontrados_set = set(
        ids_encontrados
    )

    faltantes = sorted(
        IDS_ESPERADOS - ids_encontrados_set
    )

    extras = sorted(
        ids_encontrados_set - IDS_ESPERADOS
    )

    if ids_duplicados:
        erros.append(
            f"{origem}: IDs duplicados: "
            + ", ".join(
                str(time_id)
                for time_id in sorted(ids_duplicados)
            )
        )

    if faltantes:
        erros.append(
            f"{origem}: IDs ausentes: "
            + ", ".join(
                str(time_id)
                for time_id in faltantes
            )
        )

    if extras:
        erros.append(
            f"{origem}: IDs inesperados: "
            + ", ".join(
                str(time_id)
                for time_id in extras
            )
        )

    return len(erros) == 0, erros


def mapa_snapshot_validado(rodada):
    """
    Tenta usar rodada_atual_cartola.json como fonte.

    O snapshot só será aceito se:
    - corresponder exatamente à rodada desejada;
    - possuir os 36 times;
    - possuir exatamente os IDs esperados;
    - todos tiverem pontuação válida;
    - todos tiverem patrimônio válido.
    """

    dados = carregar_rodada_atual()

    if not dados:
        return {}

    rodada_dados = inteiro(
        dados.get("rodada_dados"),
        0,
    )

    if rodada_dados != rodada:
        print(
            "Snapshot ignorado: "
            f"rodada_dados={rodada_dados}; "
            f"esperada={rodada}."
        )

        return {}

    times = dados.get("times")

    valido, erros = validar_registros_rodada(
        times,
        rodada,
        "rodada_atual_cartola.json",
    )

    if not valido:
        print(
            "Snapshot ignorado por inconsistência:"
        )

        for erro in erros:
            print(f" - {erro}")

        return {}

    mapa = {}

    for item in times:
        time_id = inteiro(
            item.get("time_id"),
            0,
        )

        mapa[time_id] = item

    if set(mapa) != IDS_ESPERADOS:
        return {}

    return mapa


def validar_resposta_time_id(
    dados,
    time_id,
    rodada_esperada,
):
    """
    Validação rigorosa da resposta de /time/id.

    O principal problema que originou esta correção era
    aceitar dados potencialmente defasados como se fossem
    da rodada solicitada.

    Portanto, quando a API informar explicitamente a rodada
    dos dados, ela precisa corresponder à rodada esperada.
    """

    if not isinstance(dados, dict):
        return False, "resposta não é um objeto JSON"

    time_api = dados.get("time")

    if isinstance(time_api, dict):
        time_id_api = inteiro(
            time_api.get("time_id"),
            0,
        )

        if (
            time_id_api > 0
            and time_id_api != time_id
        ):
            return (
                False,
                f"time_id retornado {time_id_api}; "
                f"esperado {time_id}",
            )

    campos_rodada = [
        "rodada_atual",
        "rodada_dados",
        "rodada",
    ]

    rodadas_informadas = []

    for campo in campos_rodada:
        if campo not in dados:
            continue

        valor = inteiro(
            dados.get(campo),
            0,
        )

        if valor > 0:
            rodadas_informadas.append(
                (campo, valor)
            )

    for campo, rodada_api in rodadas_informadas:
        if rodada_api != rodada_esperada:
            return (
                False,
                f"{campo}={rodada_api}; "
                f"esperada {rodada_esperada}",
            )

    pontos = numero(
        dados.get("pontos"),
        None,
    )

    if pontos is None:
        return (
            False,
            "pontuação ausente ou inválida",
        )

    patrimonio = numero(
        dados.get("patrimonio"),
        None,
    )

    if patrimonio is None:
        return (
            False,
            "patrimônio ausente ou inválido",
        )

    return True, "OK"


def registro_do_snapshot(
    snapshot,
    time_id,
    nome_time,
    cartoleiro,
    rodada,
):
    pontos = numero(
        snapshot.get("pontos"),
        None,
    )

    patrimonio = numero(
        snapshot.get("patrimonio"),
        None,
    )

    if pontos is None:
        raise ValueError(
            "snapshot sem pontuação válida"
        )

    if patrimonio is None:
        raise ValueError(
            "snapshot sem patrimônio válido"
        )

    return {
        "time_id": time_id,
        "time": nome_time,
        "cartoleiro": cartoleiro,
        "rodada": rodada,
        "pontos": round(pontos, 2),
        "patrimonio": round(
            patrimonio,
            2,
        ),
        "fonte_pontos": (
            "rodada_atual_cartola_validado"
        ),
    }


def registro_da_api(
    dados,
    time_id,
    nome_time,
    cartoleiro,
    rodada,
):
    valido, motivo = validar_resposta_time_id(
        dados,
        time_id,
        rodada,
    )

    if not valido:
        raise ValueError(
            f"resposta /time/id rejeitada: {motivo}"
        )

    pontos = numero(
        dados.get("pontos"),
        None,
    )

    patrimonio = numero(
        dados.get("patrimonio"),
        None,
    )

    return {
        "time_id": time_id,
        "time": nome_time,
        "cartoleiro": cartoleiro,
        "rodada": rodada,
        "pontos": round(
            pontos,
            2,
        ),
        "patrimonio": round(
            patrimonio,
            2,
        ),
        "fonte_pontos": (
            "api_time_id_validado"
        ),
    }


def rodada_ja_consolidada(
    historico,
    rodada,
):
    registros = historico.get(
        "rodadas",
        {},
    ).get(
        str(rodada)
    )

    if registros is None:
        return False

    valido, erros = validar_registros_rodada(
        registros,
        rodada,
        (
            f"historico_cartola.json "
            f"rodada {rodada}"
        ),
    )

    if valido:
        return True

    print()
    print(
        "ATENÇÃO: a rodada já existe no histórico, "
        "mas não passou na validação estrutural."
    )

    for erro in erros:
        print(f" - {erro}")

    print()
    print(
        "PROTEÇÃO DO HISTÓRICO: a rodada NÃO será "
        "sobrescrita automaticamente."
    )

    print(
        "Use o processo de recuperação controlada "
        "para qualquer correção histórica."
    )

    raise RuntimeError(
        f"Rodada {rodada} existente, porém inconsistente."
    )


# ============================================================
# INÍCIO
# ============================================================


print("=" * 72)
print("CARTOLA DE ERMIDA - CONSOLIDAÇÃO SEGURA DO HISTÓRICO")
print("=" * 72)

print()
print("Consultando o status do Cartola...")


status = buscar_json(
    URL_STATUS
)


rodada_status = inteiro(
    status.get("rodada_atual"),
    0,
)

mercado_status = inteiro(
    status.get("status_mercado"),
    0,
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
        "A API não informou uma rodada atual válida."
    )


if not mercado_aberto:
    print()
    print(
        "Mercado ainda não está aberto."
    )

    print(
        "Nenhuma rodada será consolidada neste momento."
    )

    print(
        "Isso evita gravar uma parcial como "
        "resultado definitivo."
    )

    raise SystemExit(0)


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
    f"Verificando a rodada fechada "
    f"{rodada_para_salvar}..."
)


historico = carregar_historico()


# ============================================================
# PROTEÇÃO 1
# RODADAS CONSOLIDADAS SÃO IMUTÁVEIS
# ============================================================


if rodada_ja_consolidada(
    historico,
    rodada_para_salvar,
):
    registros_existentes = (
        historico["rodadas"][
            str(rodada_para_salvar)
        ]
    )

    print()
    print(
        f"Rodada {rodada_para_salvar} "
        "já consolidada no histórico."
    )

    print(
        f"Registros encontrados: "
        f"{len(registros_existentes)}/{TOTAL_TIMES}."
    )

    print()
    print(
        "PROTEÇÃO DO HISTÓRICO: ATIVA."
    )

    print(
        "A rodada existente é imutável "
        "e NÃO será sobrescrita."
    )

    print(
        "Para corrigir uma rodada histórica, "
        "utilize recuperação controlada."
    )

    print()
    print(
        "Nenhuma alteração realizada "
        "em historico_cartola.json."
    )

    raise SystemExit(0)


# ============================================================
# PROTEÇÃO 2
# TENTAR SNAPSHOT JÁ VALIDADO
# ============================================================


print()
print(
    "Procurando snapshot validado da rodada..."
)


mapa_snapshot = (
    mapa_snapshot_validado(
        rodada_para_salvar
    )
)


if mapa_snapshot:
    print(
        "Snapshot completo e consistente encontrado."
    )

    print(
        "Fonte preferencial: "
        "rodada_atual_cartola.json validado."
    )

else:
    print(
        "Snapshot validado não disponível."
    )

    print(
        "Será utilizada a API /time/id "
        "com validação rigorosa."
    )


# ============================================================
# MONTAGEM DA NOVA RODADA
# ============================================================


novos_registros = []
erros = []


print()
print(
    f"Preparando os {TOTAL_TIMES} registros "
    f"da rodada {rodada_para_salvar}..."
)


for indice, (
    time_id,
    nome_time,
    cartoleiro,
) in enumerate(
    TIMES,
    start=1,
):
    try:
        # ----------------------------------------------------
        # FONTE 1: SNAPSHOT VALIDADO
        # ----------------------------------------------------

        if time_id in mapa_snapshot:
            snapshot = (
                mapa_snapshot[time_id]
            )

            registro = registro_do_snapshot(
                snapshot,
                time_id,
                nome_time,
                cartoleiro,
                rodada_para_salvar,
            )

        # ----------------------------------------------------
        # FONTE 2: /time/id VALIDADO
        # ----------------------------------------------------

        else:
            url = (
                "https://api.cartola.globo.com"
                f"/time/id/{time_id}/"
                f"{rodada_para_salvar}"
            )

            dados = buscar_json(
                url
            )

            registro = registro_da_api(
                dados,
                time_id,
                nome_time,
                cartoleiro,
                rodada_para_salvar,
            )

            time.sleep(0.12)

        novos_registros.append(
            registro
        )

        print(
            f"[{indice:02d}/{TOTAL_TIMES}] "
            f"OK - {nome_time}: "
            f"{registro['pontos']:.2f} "
            f"[{registro['fonte_pontos']}]"
        )

    except Exception as erro:
        mensagem = (
            f"{nome_time}: {erro}"
        )

        erros.append(
            mensagem
        )

        print(
            f"[{indice:02d}/{TOTAL_TIMES}] "
            f"ERRO - {mensagem}"
        )


# ============================================================
# PROTEÇÃO 3
# NADA É GRAVADO SE UM ÚNICO TIME FALHAR
# ============================================================


if erros:
    print()
    print("=" * 72)
    print("CONSOLIDAÇÃO CANCELADA")
    print("=" * 72)

    print()
    print(
        f"Falhas encontradas: {len(erros)}"
    )

    for mensagem in erros:
        print(
            f" - {mensagem}"
        )

    print()
    print(
        "Nenhum dado foi gravado."
    )

    print(
        "O histórico anterior permanece intacto."
    )

    raise RuntimeError(
        "A rodada não passou na validação "
        "dos 36 times."
    )


# ============================================================
# PROTEÇÃO 4
# AUDITORIA FINAL DO BLOCO ANTES DE GRAVAR
# ============================================================


valido, erros_validacao = (
    validar_registros_rodada(
        novos_registros,
        rodada_para_salvar,
        (
            f"nova rodada "
            f"{rodada_para_salvar}"
        ),
    )
)


if not valido:
    print()
    print("=" * 72)
    print("CONSOLIDAÇÃO BLOQUEADA")
    print("=" * 72)

    print()

    for erro in erros_validacao:
        print(
            f" - {erro}"
        )

    print()
    print(
        "Nenhum dado foi gravado."
    )

    raise RuntimeError(
        "A rodada montada não passou "
        "na validação final."
    )


if len(novos_registros) != TOTAL_TIMES:
    raise RuntimeError(
        f"Validação interna falhou: "
        f"{len(novos_registros)}/"
        f"{TOTAL_TIMES} registros."
    )


ids_novos = {
    inteiro(
        item.get("time_id"),
        0,
    )
    for item in novos_registros
}


if ids_novos != IDS_ESPERADOS:
    raise RuntimeError(
        "Validação interna falhou: "
        "a relação de times não corresponde "
        "aos 36 participantes oficiais."
    )


# ============================================================
# PROTEÇÃO 5
# NUNCA APAGAR OU REESCREVER RODADAS ANTIGAS
# ============================================================


historico.setdefault(
    "rodadas",
    {},
)


if str(rodada_para_salvar) in historico["rodadas"]:
    raise RuntimeError(
        "Proteção final acionada: "
        "a rodada apareceu no histórico "
        "durante a execução."
    )


historico["rodadas"][
    str(rodada_para_salvar)
] = novos_registros


# Não removemos rodadas anteriores.
# Não reescrevemos rodadas anteriores.
# Não fazemos limpeza automática de histórico.


rodadas_validas = []


for chave in historico["rodadas"]:
    try:
        numero_rodada = int(chave)

        if numero_rodada > 0:
            rodadas_validas.append(
                numero_rodada
            )

    except (TypeError, ValueError):
        continue


if rodadas_validas:
    historico[
        "ultima_rodada_fechada"
    ] = max(rodadas_validas)

else:
    historico[
        "ultima_rodada_fechada"
    ] = rodada_para_salvar


historico[
    "ultima_atualizacao"
] = agora_texto()


# ============================================================
# GRAVAÇÃO ATÔMICA
# ============================================================


print()
print(
    "Todas as validações foram aprovadas."
)

print(
    "Gravando historico_cartola.json "
    "de forma atômica..."
)


salvar_atomico(
    ARQUIVO_HISTORICO,
    historico,
)


# ============================================================
# CONFIRMAÇÃO PÓS-GRAVAÇÃO
# ============================================================


historico_confirmacao = (
    carregar_historico()
)


registros_confirmacao = (
    historico_confirmacao
    .get("rodadas", {})
    .get(
        str(rodada_para_salvar),
        [],
    )
)


confirmacao_valida, erros_confirmacao = (
    validar_registros_rodada(
        registros_confirmacao,
        rodada_para_salvar,
        "verificação pós-gravação",
    )
)


if not confirmacao_valida:
    print()
    print(
        "ATENÇÃO CRÍTICA:"
    )

    print(
        "O arquivo foi salvo, mas falhou "
        "na leitura de confirmação."
    )

    for erro in erros_confirmacao:
        print(
            f" - {erro}"
        )

    raise RuntimeError(
        "Falha na confirmação pós-gravação."
    )


print()
print("=" * 72)
print("HISTÓRICO CONSOLIDADO COM SEGURANÇA")
print("=" * 72)

print()
print(
    f"Rodada consolidada: "
    f"{rodada_para_salvar}"
)

print(
    f"Times: "
    f"{len(registros_confirmacao)}/"
    f"{TOTAL_TIMES}"
)

if mapa_snapshot:
    print(
        "Fonte: snapshot previamente validado "
        "da rodada fechada."
    )

else:
    print(
        "Fonte: /time/id com validação "
        "individual da rodada."
    )

print()
print(
    "PROTEÇÕES ATIVAS:"
)

print(
    " - rodada histórica existente "
    "não pode ser sobrescrita"
)

print(
    " - rodada incompleta não pode "
    "ser consolidada"
)

print(
    " - IDs ausentes, extras ou duplicados "
    "bloqueiam a gravação"
)

print(
    " - pontuação ou patrimônio inválidos "
    "bloqueiam a gravação"
)

print(
    " - respostas incompatíveis de /time/id "
    "são rejeitadas"
)

print(
    " - gravação é realizada de forma atômica"
)

print(
    " - histórico anterior é preservado"
)

print()
print(
    "Consolidação concluída."
)
