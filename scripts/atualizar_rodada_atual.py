import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo


ARQUIVO_RODADA_ATUAL = Path("rodada_atual_cartola.json")
ARQUIVO_PARCIAIS = Path("parciais_cartola.json")

URL_STATUS = "https://api.cartola.globo.com/mercado/status"
URL_PONTUADOS = "https://api.cartola.globo.com/atletas/pontuados"

TOTAL_TIMES = 36
MULTIPLICADOR_CAPITAO = 1.5
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


def agora_texto():
    return datetime.now(FUSO).strftime("%d/%m/%Y %H:%M:%S")


def buscar_json(url, tentativas=3):
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
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
                return json.loads(
                    resposta.read().decode("utf-8")
                )

        except Exception as erro:
            ultimo_erro = erro

            print(
                f"Tentativa {tentativa}/{tentativas} "
                f"falhou em {url}: {erro}"
            )

            if tentativa < tentativas:
                time.sleep(tentativa * 2)

    raise RuntimeError(
        f"Falha definitiva ao consultar {url}: {ultimo_erro}"
    )


def carregar_json(caminho):
    try:
        with caminho.open(
            "r",
            encoding="utf-8",
        ) as arquivo:
            dados = json.load(arquivo)

            if isinstance(dados, dict):
                return dados

            return None

    except (
        FileNotFoundError,
        json.JSONDecodeError,
    ):
        return None


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


def sem_data(dados):
    if dados is None:
        return None

    copia = dict(dados)
    copia.pop("ultima_atualizacao", None)

    return copia


def salvar_somente_se_mudou(caminho, dados):
    anterior = carregar_json(caminho)

    if sem_data(anterior) == sem_data(dados):
        print(f"{caminho}: dados sem alteração.")
        return False

    dados["ultima_atualizacao"] = agora_texto()

    salvar_atomico(
        caminho,
        dados,
    )

    print(f"{caminho}: arquivo atualizado.")

    return True


def numero(valor, padrao=0.0):
    try:
        return float(valor)

    except (
        TypeError,
        ValueError,
    ):
        return float(padrao)


def inteiro(valor, padrao=0):
    try:
        return int(valor)

    except (
        TypeError,
        ValueError,
    ):
        return int(padrao)


def obter_mapa_pontuados(dados):
    atletas = dados.get("atletas", {})

    if not isinstance(atletas, dict):
        raise ValueError(
            "A API de pontuados não retornou "
            "um mapa de atletas."
        )

    return atletas


def obter_dados_atleta(
    mapa_pontuados,
    atleta_id,
):
    dados = mapa_pontuados.get(
        str(atleta_id),
        {},
    )

    if not isinstance(dados, dict):
        return {}

    return dados


def obter_pontuacao_atleta(
    mapa_pontuados,
    atleta_id,
):
    dados = obter_dados_atleta(
        mapa_pontuados,
        atleta_id,
    )

    return numero(
        dados.get(
            "pontuacao",
            dados.get(
                "pontos",
                dados.get(
                    "pontos_num",
                    0,
                ),
            ),
        )
    )


def atleta_entrou_em_campo(
    mapa_pontuados,
    atleta_id,
):
    dados = obter_dados_atleta(
        mapa_pontuados,
        atleta_id,
    )

    return bool(
        dados.get(
            "entrou_em_campo",
            False,
        )
    )


def calcular_parcial(
    dados_time,
    mapa_pontuados,
):
    atletas = dados_time.get(
        "atletas",
        [],
    )

    capitao_id = inteiro(
        dados_time.get(
            "capitao_id",
            0,
        )
    )

    if not isinstance(atletas, list):
        raise ValueError(
            "A escalação não contém "
            "uma lista de atletas."
        )

    if len(atletas) < 11:
        raise ValueError(
            "Escalação incompleta: "
            f"apenas {len(atletas)} atletas."
        )

    total = 0.0
    detalhes = []
    atletas_pontuando = 0

    ids_pontuados = {
        inteiro(chave)
        for chave in mapa_pontuados
        if str(chave).isdigit()
    }

    for atleta in atletas:
        atleta_id = inteiro(
            atleta.get(
                "atleta_id",
                0,
            )
        )

        apelido = (
            atleta.get("apelido")
            or str(atleta_id)
        )

        pontuacao_normal = obter_pontuacao_atleta(
            mapa_pontuados,
            atleta_id,
        )

        entrou_em_campo = atleta_entrou_em_campo(
            mapa_pontuados,
            atleta_id,
        )

        eh_capitao = (
            atleta_id == capitao_id
        )

        if eh_capitao:
            pontuacao_computada = (
                pontuacao_normal
                * MULTIPLICADOR_CAPITAO
            )
        else:
            pontuacao_computada = (
                pontuacao_normal
            )

        if atleta_id in ids_pontuados:
            atletas_pontuando += 1

        total += pontuacao_computada

        detalhes.append(
            {
                "atleta_id": atleta_id,
                "apelido": apelido,
                "posicao_id": inteiro(
                    atleta.get(
                        "posicao_id",
                        0,
                    )
                ),
                "capitao": eh_capitao,
                "entrou_em_campo": entrou_em_campo,
                "pontos": round(
                    pontuacao_normal,
                    2,
                ),
                "pontos_computados": round(
                    pontuacao_computada,
                    2,
                ),
            }
        )

    return (
        round(total, 2),
        atletas_pontuando,
        detalhes,
    )


def montar_detalhes_reservas(dados_time, mapa_pontuados):
    reservas = dados_time.get("reservas", [])
    if not isinstance(reservas, list):
        reservas = []
    reserva_luxo_id = inteiro(dados_time.get("reserva_luxo_id", 0))
    detalhes = []
    for atleta in reservas:
        atleta_id = inteiro(atleta.get("atleta_id", 0))
        pontos = obter_pontuacao_atleta(mapa_pontuados, atleta_id)
        detalhes.append({
            "atleta_id": atleta_id,
            "apelido": atleta.get("apelido") or str(atleta_id),
            "posicao_id": inteiro(atleta.get("posicao_id", 0)),
            "reserva_luxo": atleta_id == reserva_luxo_id,
            "entrou_em_campo": atleta_entrou_em_campo(mapa_pontuados, atleta_id),
            "pontos": round(pontos, 2),
            "substituicao_aplicada": False,
        })
    return detalhes


def rodada_da_escalacao(dados_time):
    informacoes_time = dados_time.get(
        "time",
        {},
    )

    if not isinstance(
        informacoes_time,
        dict,
    ):
        informacoes_time = {}

    return inteiro(
        informacoes_time.get(
            "rodada_time_id",
            dados_time.get(
                "rodada_atual",
                0,
            ),
        )
    )


print("Consultando o status do Cartola...")

status = buscar_json(URL_STATUS)

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

bola_rolando_api = bool(
    status.get(
        "bola_rolando",
        False,
    )
)

if rodada_status <= 0:
    raise RuntimeError(
        "Não foi possível determinar "
        "a rodada atual do Cartola."
    )

print(f"Rodada Cartola: {rodada_status}")
print(f"Status mercado: {mercado_status}")
print(f"Mercado aberto: {mercado_aberto}")
print(
    "Bola rolando informada pela API: "
    f"{bola_rolando_api}"
)


print("\nConsultando atletas pontuados...")

dados_pontuados = buscar_json(
    URL_PONTUADOS
)

rodada_pontuados = inteiro(
    dados_pontuados.get(
        "rodada",
        0,
    )
)

mapa_pontuados = obter_mapa_pontuados(
    dados_pontuados
)

total_atletas_pontuados = inteiro(
    dados_pontuados.get(
        "total_atletas",
        len(mapa_pontuados),
    )
)

if total_atletas_pontuados <= 0:
    total_atletas_pontuados = len(
        mapa_pontuados
    )

parciais_disponiveis = (
    rodada_pontuados == rodada_status
    and total_atletas_pontuados > 0
    and len(mapa_pontuados) > 0
)

rodada_em_andamento = (
    not mercado_aberto
    and parciais_disponiveis
)

print(
    "Rodada da API de pontuados: "
    f"{rodada_pontuados}"
)

print(
    "Atletas pontuados: "
    f"{total_atletas_pontuados}"
)

print(
    "Parciais disponíveis: "
    f"{parciais_disponiveis}"
)

print(
    "Rodada em andamento calculada: "
    f"{rodada_em_andamento}"
)


if rodada_em_andamento:
    rodada_dados = rodada_status
else:
    rodada_dados = rodada_status - 1

if rodada_dados <= 0:
    raise RuntimeError(
        "Não foi possível determinar "
        "a rodada dos dados."
    )


novos_times = []
erros = []

print()

if rodada_em_andamento:
    print("Calculando parciais ao vivo...")
else:
    print(
        "Buscando dados fechados "
        f"da rodada {rodada_dados}..."
    )


for indice, (
    time_id,
    nome_time,
    cartoleiro,
) in enumerate(
    TIMES,
    start=1,
):
    url = (
        "https://api.cartola.globo.com/"
        f"time/id/{time_id}/{rodada_dados}"
    )

    try:
        dados_time = buscar_json(url)

        rodada_escalacao = rodada_da_escalacao(
            dados_time
        )

        atletas_escalados = dados_time.get(
            "atletas",
            [],
        )

        if not isinstance(
            atletas_escalados,
            list,
        ):
            atletas_escalados = []

        if rodada_em_andamento:
            if rodada_escalacao != rodada_status:
                print(
                    f"[{indice:02d}/{TOTAL_TIMES}] "
                    f"AVISO - {nome_time}: "
                    "a última escalação salva é da "
                    f"rodada {rodada_escalacao}. "
                    "Ela será utilizada na rodada "
                    f"{rodada_status}."
                )

            if len(atletas_escalados) < 11:
                raise ValueError(
                    "Nenhuma escalação válida "
                    "foi encontrada."
                )

            (
                pontos,
                atletas_pontuando,
                detalhes,
            ) = calcular_parcial(
                dados_time,
                mapa_pontuados,
            )

            pontos_anteriores = numero(
                dados_time.get(
                    "pontos_campeonato",
                    0,
                )
            )

            pontos_campeonato = round(
                pontos_anteriores + pontos,
                2,
            )

            fonte_pontos = (
                "atletas_pontuados"
            )

        else:
            pontos = round(
                numero(
                    dados_time.get(
                        "pontos",
                        0,
                    )
                ),
                2,
            )

            pontos_campeonato = round(
                numero(
                    dados_time.get(
                        "pontos_campeonato",
                        0,
                    )
                ),
                2,
            )

            atletas_pontuando = 0
            detalhes = []
            fonte_pontos = "api_time_id"

        registro = {
            "time_id": time_id,
            "time": nome_time,
            "cartoleiro": cartoleiro,
            "rodada_dados": rodada_dados,
            "rodada_escalacao": rodada_escalacao,
            "pontos": pontos,
            "patrimonio": round(
                numero(
                    dados_time.get(
                        "patrimonio",
                        0,
                    )
                ),
                2,
            ),
            "pontos_campeonato": pontos_campeonato,
            "fonte_pontos": fonte_pontos,
            "atletas_pontuando": atletas_pontuando,
        }

        if rodada_em_andamento:
            registro["capitao_id"] = inteiro(
                dados_time.get(
                    "capitao_id",
                    0,
                )
            )

            registro[
                "detalhes_parcial"
            ] = detalhes
            registro["reserva_luxo_id"] = inteiro(
                dados_time.get("reserva_luxo_id", 0)
            )
            registro["reservas_parcial"] = montar_detalhes_reservas(
                dados_time, mapa_pontuados
            )
            registro["substituicoes_aplicadas"] = []
            registro["criterio_parcial"] = (
                "titulares + capitao 1.5; reservas apenas para diagnóstico"
            )

        novos_times.append(registro)

        print(
            f"[{indice:02d}/{TOTAL_TIMES}] "
            f"OK - {nome_time}: "
            f"{pontos:.2f}"
        )

    except Exception as erro:
        mensagem = (
            f"{nome_time}: {erro}"
        )

        erros.append(mensagem)

        print(
            f"[{indice:02d}/{TOTAL_TIMES}] "
            f"ERRO - {mensagem}"
        )

    time.sleep(0.12)


if erros or len(novos_times) != TOTAL_TIMES:
    print()

    print(
        "Coleta cancelada para preservar "
        "os arquivos anteriores."
    )

    print(
        f"Times obtidos: "
        f"{len(novos_times)}/{TOTAL_TIMES}"
    )

    for mensagem in erros:
        print(f" - {mensagem}")

    raise RuntimeError(
        "Não foi possível calcular "
        "os 36 times."
    )


if rodada_em_andamento:
    observacao = (
        "Parciais calculadas pelas escalações "
        "dos times e pela API oficial de "
        "atletas pontuados."
    )

elif mercado_aberto:
    observacao = (
        "Mercado aberto: exibindo os pontos "
        "da última rodada fechada."
    )

else:
    observacao = (
        "Mercado fechado, aguardando os "
        "primeiros atletas pontuados."
    )


saida = {
    "liga": "Cartola de Ermida",
    "rodada_cartola": rodada_status,
    "status_mercado": mercado_status,
    "mercado_aberto": mercado_aberto,
    "bola_rolando": bola_rolando_api,
    "rodada_em_andamento": rodada_em_andamento,
    "rodada_dados": rodada_dados,
    "rodada_pontuados": rodada_pontuados,
    "total_atletas_pontuados": (
        total_atletas_pontuados
    ),
    "observacao": observacao,
    "fonte": (
        "parciais_cartola.json"
        if rodada_em_andamento
        else "rodada_atual_cartola.json"
    ),
    "times": novos_times,
}


salvar_somente_se_mudou(
    ARQUIVO_RODADA_ATUAL,
    dict(saida),
)


if rodada_em_andamento:
    parciais = dict(saida)
    parciais["fonte"] = (
        "parciais_cartola.json"
    )

    salvar_somente_se_mudou(
        ARQUIVO_PARCIAIS,
        parciais,
    )

elif ARQUIVO_PARCIAIS.exists():
    ARQUIVO_PARCIAIS.unlink()

    print(
        "parciais_cartola.json removido: "
        "não há parciais atuais disponíveis."
    )


print()

print(
    "Atualização da rodada atual "
    "concluída com segurança."
)

print(
    f"Times atualizados: "
    f"{len(novos_times)}"
)

print(
    "Parciais ao vivo: "
    f"{'sim' if rodada_em_andamento else 'não'}"
)


if rodada_em_andamento:
    wecam = next(
        (
            time
            for time in novos_times
            if time["time"] == "WECAM"
        ),
        None,
    )

    if wecam:
        print(
            "Verificação WECAM: "
            f"{wecam['pontos']:.2f} pontos"
        )
