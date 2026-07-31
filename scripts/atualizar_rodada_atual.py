import json
import os
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo


ARQUIVO_RODADA_ATUAL = Path("rodada_atual_cartola.json")
ARQUIVO_PARCIAIS = Path("parciais_cartola.json")

URL_STATUS = "https://api.cartola.globo.com/mercado/status"
URL_PONTUADOS = "https://api.cartola.globo.com/atletas/pontuados"
URL_PARTIDAS = "https://api.cartola.globo.com/partidas"
URL_ATLETAS_MERCADO = "https://api.cartola.globo.com/atletas/mercado"

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


def agora_iso():
    """Data/hora atual em ISO 8601, com o fuso de São Paulo."""
    return datetime.now(FUSO).isoformat(timespec="seconds")


def buscar_json(
    url,
    tentativas=3,
    obrigatorio=True,
):
    """Consulta uma URL e devolve o JSON.

    Alguns endpoints do Cartola, especialmente /atletas/pontuados,
    podem responder sem conteúdo entre o fechamento de uma rodada e
    o início das parciais da rodada seguinte. Quando obrigatorio=False,
    essa situação é tratada como "dados ainda indisponíveis" e não como
    falha do workflow.
    """
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
                conteudo = (
                    resposta
                    .read()
                    .decode("utf-8")
                    .strip()
                )

                if not conteudo:
                    raise ValueError(
                        "A API respondeu sem conteúdo."
                    )

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

    if not obrigatorio:
        print(
            f"Dados opcionais indisponíveis em {url}. "
            "A execução continuará com segurança."
        )
        return None

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




def obter_mapa_atletas_mercado(dados):
    atletas = dados.get("atletas", [])
    if not isinstance(atletas, list):
        return {}

    mapa = {}
    for atleta in atletas:
        if not isinstance(atleta, dict):
            continue
        atleta_id = inteiro(atleta.get("atleta_id", 0))
        if atleta_id > 0:
            mapa[atleta_id] = atleta
    return mapa


def obter_mapa_clubes_mercado(dados):
    clubes = dados.get("clubes", {}) if isinstance(dados, dict) else {}
    if not isinstance(clubes, dict):
        return {}
    mapa = {}
    for chave, clube in clubes.items():
        if not isinstance(clube, dict):
            continue
        clube_id = inteiro(clube.get("id", chave))
        sigla = str(clube.get("abreviacao") or clube.get("sigla") or "").strip().upper()
        if clube_id > 0 and sigla:
            mapa[clube_id] = sigla[:3]
    return mapa


def clube_atual_atleta(atleta, mapa_atletas_mercado):
    atleta_id = inteiro(atleta.get("atleta_id", 0))
    mercado = mapa_atletas_mercado.get(atleta_id, {})
    clube_mercado = inteiro(mercado.get("clube_id", 0)) if isinstance(mercado, dict) else 0
    if clube_mercado > 0:
        return clube_mercado
    return inteiro(atleta.get("clube_id", 0))



def montar_mapa_pontuados_do_time(dados_time):
    """
    Reconstrói um mapa compatível com /atletas/pontuados usando os dados
    oficiais devolvidos por /time/id/{id}/{rodada}.

    Isso mantém titulares, reservas, capitão e Reserva de Luxo disponíveis
    na comparação mesmo depois que a rodada deixa o modo de parciais.
    """
    mapa = {}
    listas = [dados_time.get("atletas", []), dados_time.get("reservas", [])]

    for lista in listas:
        if not isinstance(lista, list):
            continue
        for atleta in lista:
            if not isinstance(atleta, dict):
                continue
            atleta_id = inteiro(atleta.get("atleta_id", 0))
            if atleta_id <= 0:
                continue

            chaves_pontos = ("pontuacao", "pontos", "pontos_num")
            tem_pontuacao = any(chave in atleta for chave in chaves_pontos)
            pontos = numero(
                atleta.get(
                    "pontuacao",
                    atleta.get("pontos", atleta.get("pontos_num", 0)),
                )
            )

            entrou_explicito = atleta.get("entrou_em_campo")
            if entrou_explicito is None:
                # Na resposta oficial do time, a presença do campo de pontos
                # identifica que o atleta recebeu uma nota, inclusive 0,00.
                entrou = bool(tem_pontuacao)
            else:
                entrou = bool(entrou_explicito)

            mapa[str(atleta_id)] = {
                "pontuacao": pontos,
                "entrou_em_campo": entrou,
            }

    return mapa

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


def atleta_tem_dados_na_api(
    mapa_pontuados,
    atleta_id,
):
    return str(atleta_id) in mapa_pontuados


def parse_data_cartola(valor):
    if not valor:
        return None

    texto = str(valor).strip()
    formatos = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    )

    for formato in formatos:
        try:
            data = datetime.strptime(texto.replace("Z", "+00:00"), formato)
            if data.tzinfo is None:
                data = data.replace(tzinfo=FUSO)
            return data.astimezone(FUSO)
        except ValueError:
            continue

    try:
        data = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        if data.tzinfo is None:
            data = data.replace(tzinfo=FUSO)
        return data.astimezone(FUSO)
    except ValueError:
        return None


def texto_indica_encerrado(partida):
    termos = []
    for chave, valor in partida.items():
        if isinstance(valor, (str, int, float, bool)):
            termos.append(f"{chave}={valor}".lower())
    texto = " ".join(termos)
    return any(
        termo in texto
        for termo in (
            "encerrad",
            "finalizad",
            "fim de jogo",
            "finalizado",
            "finished",
        )
    )


def montar_mapa_partidas(dados_partidas):
    partidas = dados_partidas.get("partidas", [])
    if not isinstance(partidas, list):
        partidas = []

    agora = datetime.now(FUSO)
    mapa = {}

    for partida in partidas:
        if not isinstance(partida, dict):
            continue

        # Não descartamos partidas com ``valida: false``. A API do Cartola
        # pode marcar como não válida uma partida já encerrada, mas ela ainda
        # é necessária para confirmar que um atleta daquele clube não atuou
        # e permitir a entrada do reserva. Esse é o caso observado na rodada
        # 19: o jogo do Bragantino aparece como encerrado e ``valida: false``.
        valida = partida.get("valida", True)

        data = parse_data_cartola(
            partida.get("partida_data")
            or partida.get("data")
            or partida.get("data_partida")
        )

        encerrada = texto_indica_encerrado(partida)

        # A API pública nem sempre fornece um campo explícito de encerramento.
        # Como proteção, após três horas do horário marcado consideramos a
        # ausência confirmada. Jogos inválidos/adiados não entram neste cálculo.
        if not encerrada and data is not None:
            encerrada = agora >= data + timedelta(hours=3)

        info = {
            "data": data.isoformat() if data else None,
            "encerrada": bool(encerrada),
            "valida": bool(valida),
        }

        for chave in ("clube_casa_id", "clube_visitante_id"):
            clube_id = inteiro(partida.get(chave, 0))
            if clube_id > 0:
                mapa[clube_id] = info

    return mapa


def jogo_do_atleta(mapa_partidas, clube_id):
    return mapa_partidas.get(inteiro(clube_id), {})


def jogo_encerrado_atleta(mapa_partidas, clube_id):
    return bool(jogo_do_atleta(mapa_partidas, clube_id).get("encerrada", False))


def data_jogo_atleta(mapa_partidas, clube_id):
    texto = jogo_do_atleta(mapa_partidas, clube_id).get("data")
    return parse_data_cartola(texto) or datetime.max.replace(tzinfo=FUSO)


def montar_detalhe_atleta(
    atleta,
    mapa_pontuados,
    mapa_partidas,
    mapa_atletas_mercado,
    mapa_clubes_mercado,
    capitao_id=0,
    reserva_luxo_id=0,
):
    atleta_id = inteiro(atleta.get("atleta_id", 0))
    pontos = obter_pontuacao_atleta(mapa_pontuados, atleta_id)
    entrou = atleta_entrou_em_campo(mapa_pontuados, atleta_id)
    tem_dados = atleta_tem_dados_na_api(mapa_pontuados, atleta_id)
    clube_id_original = inteiro(atleta.get("clube_id", 0))
    clube_id = clube_atual_atleta(atleta, mapa_atletas_mercado)
    jogo_encerrado = jogo_encerrado_atleta(mapa_partidas, clube_id)
    data_jogo = data_jogo_atleta(mapa_partidas, clube_id)

    return {
        "atleta_id": atleta_id,
        "apelido": atleta.get("apelido") or str(atleta_id),
        "posicao_id": inteiro(atleta.get("posicao_id", 0)),
        "clube_id": clube_id,
        "clube_id_original": clube_id_original,
        "clube_sigla": mapa_clubes_mercado.get(clube_id, ""),
        "clube_corrigido_pelo_mercado": bool(
            clube_id > 0 and clube_id != clube_id_original
        ),
        "preco_num": round(numero(atleta.get("preco_num", 0)), 2),
        "jogo_encerrado": jogo_encerrado,
        "data_jogo": None if data_jogo.year == datetime.max.year else data_jogo.isoformat(),
        "nao_jogou": bool(jogo_encerrado and not entrou),
        "capitao": atleta_id == capitao_id,
        "reserva_luxo": atleta_id == reserva_luxo_id,
        "entrou_em_campo": entrou,
        "tem_dados_api": tem_dados,
        "pontos": round(pontos, 2),
        "pontos_computados": 0.0,
        "substituicao_aplicada": False,
        "tipo_substituicao": None,
        "entrou_no_lugar_de": None,
        "substituido_por": None,
        "titular_efetivo": False,
    }


def aplicar_pontos_computados(atleta):
    multiplicador = MULTIPLICADOR_CAPITAO if atleta.get("capitao") else 1.0
    atleta["pontos_computados"] = round(
        numero(atleta.get("pontos", 0)) * multiplicador,
        2,
    )
    return atleta["pontos_computados"]


def calcular_parcial(
    dados_time,
    mapa_pontuados,
    mapa_partidas,
    mapa_atletas_mercado,
    mapa_clubes_mercado,
):
    atletas = dados_time.get("atletas", [])
    reservas = dados_time.get("reservas", [])
    capitao_id = inteiro(dados_time.get("capitao_id", 0))
    reserva_luxo_id = inteiro(dados_time.get("reserva_luxo_id", 0))

    if not isinstance(atletas, list):
        raise ValueError("A escalação não contém uma lista de atletas.")
    if not isinstance(reservas, list):
        reservas = []
    if len(atletas) < 11:
        raise ValueError(
            "Escalação incompleta: "
            f"apenas {len(atletas)} atletas."
        )

    titulares_originais = [
        montar_detalhe_atleta(
            atleta,
            mapa_pontuados,
            mapa_partidas,
            mapa_atletas_mercado,
            mapa_clubes_mercado,
            capitao_id=capitao_id,
            reserva_luxo_id=reserva_luxo_id,
        )
        for atleta in atletas
    ]
    reservas_originais = [
        montar_detalhe_atleta(
            atleta,
            mapa_pontuados,
            mapa_partidas,
            mapa_atletas_mercado,
            mapa_clubes_mercado,
            capitao_id=0,
            reserva_luxo_id=reserva_luxo_id,
        )
        for atleta in reservas
    ]

    titulares_efetivos = list(titulares_originais)
    reservas_exibidas = list(reservas_originais)
    substituicoes = []

    # Banco normal: o reserva da posição entra quando sua pontuação é
    # positiva e a ausência de um titular foi confirmada após o fim do jogo.
    # Se mais de um titular da posição não atuar, vale a ordem cronológica;
    # em jogos simultâneos: capitão, maior preço e ordem alfabética.
    for reserva in list(reservas_originais):
        if not reserva.get("entrou_em_campo") or numero(reserva.get("pontos")) <= 0:
            continue

        posicao = inteiro(reserva.get("posicao_id"))
        ausentes = [
            titular
            for titular in titulares_efetivos
            if inteiro(titular.get("posicao_id")) == posicao
            and not titular.get("entrou_em_campo")
            and titular.get("jogo_encerrado")
        ]

        if not ausentes:
            continue

        ausentes.sort(
            key=lambda titular: (
                parse_data_cartola(titular.get("data_jogo"))
                or datetime.max.replace(tzinfo=FUSO),
                0 if titular.get("capitao") else 1,
                -numero(titular.get("preco_num", 0)),
                str(titular.get("apelido", "")).casefold(),
            )
        )
        saiu = ausentes[0]
        indice = titulares_efetivos.index(saiu)
        entrou = dict(reserva)
        saiu_banco = dict(saiu)

        entrou["capitao"] = bool(saiu.get("capitao"))
        entrou["titular_efetivo"] = True
        entrou["substituicao_aplicada"] = True
        entrou["tipo_substituicao"] = "banco_normal"
        entrou["entrou_no_lugar_de"] = saiu.get("apelido")

        saiu_banco["capitao"] = False
        saiu_banco["titular_efetivo"] = False
        saiu_banco["substituicao_aplicada"] = True
        saiu_banco["tipo_substituicao"] = "banco_normal"
        saiu_banco["substituido_por"] = entrou.get("apelido")
        saiu_banco["nao_jogou"] = bool(not saiu.get("entrou_em_campo"))

        titulares_efetivos[indice] = entrou
        reservas_exibidas = [
            item
            for item in reservas_exibidas
            if inteiro(item.get("atleta_id")) != inteiro(reserva.get("atleta_id"))
        ]
        reservas_exibidas.append(saiu_banco)

        substituicoes.append({
            "tipo": "banco_normal",
            "posicao_id": posicao,
            "saiu_atleta_id": inteiro(saiu.get("atleta_id")),
            "saiu": saiu.get("apelido"),
            "entrou_atleta_id": inteiro(entrou.get("atleta_id")),
            "entrou": entrou.get("apelido"),
            "capitao_transferido": bool(saiu.get("capitao")),
            "pontos_adicionados": round(numero(entrou.get("pontos")), 2),
        })

    # Reserva de Luxo: só pode substituir o pior titular da mesma posição
    # quando todos os titulares originais daquela posição entraram em campo.
    luxo = next(
        (
            reserva
            for reserva in reservas_originais
            if reserva.get("reserva_luxo")
        ),
        None,
    )
    if luxo and luxo.get("entrou_em_campo"):
        posicao = inteiro(luxo.get("posicao_id"))
        originais_posicao = [
            titular
            for titular in titulares_originais
            if inteiro(titular.get("posicao_id")) == posicao
        ]
        todos_atuaram = bool(originais_posicao) and all(
            titular.get("entrou_em_campo")
            for titular in originais_posicao
        )
        luxo_ja_usado = any(
            inteiro(t.get("atleta_id")) == inteiro(luxo.get("atleta_id"))
            for t in titulares_efetivos
        )

        if todos_atuaram and not luxo_ja_usado:
            candidatos = [
                titular
                for titular in titulares_efetivos
                if inteiro(titular.get("posicao_id")) == posicao
            ]
            if candidatos:
                pior = min(candidatos, key=lambda item: numero(item.get("pontos")))
                if numero(luxo.get("pontos")) > numero(pior.get("pontos")):
                    indice = titulares_efetivos.index(pior)
                    entrou = dict(luxo)
                    saiu_banco = dict(pior)

                    entrou["capitao"] = bool(pior.get("capitao"))
                    entrou["titular_efetivo"] = True
                    entrou["substituicao_aplicada"] = True
                    entrou["tipo_substituicao"] = "reserva_luxo"
                    entrou["entrou_no_lugar_de"] = pior.get("apelido")

                    saiu_banco["capitao"] = False
                    saiu_banco["titular_efetivo"] = False
                    saiu_banco["substituicao_aplicada"] = True
                    saiu_banco["tipo_substituicao"] = "reserva_luxo"
                    saiu_banco["substituido_por"] = entrou.get("apelido")

                    titulares_efetivos[indice] = entrou
                    reservas_exibidas = [
                        item
                        for item in reservas_exibidas
                        if inteiro(item.get("atleta_id")) != inteiro(luxo.get("atleta_id"))
                    ]
                    reservas_exibidas.append(saiu_banco)

                    substituicoes.append({
                        "tipo": "reserva_luxo",
                        "posicao_id": posicao,
                        "saiu_atleta_id": inteiro(pior.get("atleta_id")),
                        "saiu": pior.get("apelido"),
                        "entrou_atleta_id": inteiro(entrou.get("atleta_id")),
                        "entrou": entrou.get("apelido"),
                        "capitao_transferido": bool(pior.get("capitao")),
                        "pontos_adicionados": round(
                            numero(entrou.get("pontos")) - numero(pior.get("pontos")),
                            2,
                        ),
                    })

    total = 0.0
    atletas_pontuando = 0
    for titular in titulares_efetivos:
        titular["titular_efetivo"] = True
        total += aplicar_pontos_computados(titular)
        if titular.get("entrou_em_campo"):
            atletas_pontuando += 1

    for reserva in reservas_exibidas:
        aplicar_pontos_computados(reserva)

    return (
        round(total, 2),
        atletas_pontuando,
        titulares_efetivos,
        reservas_exibidas,
        substituicoes,
    )

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


print()

# Com o mercado aberto, a rodada indicada pelo status já é a próxima.
# Nesse momento /atletas/pontuados pode ficar vazio. Não precisamos dele:
# os valores definitivos são obtidos pelo endpoint /time/id/{id}/{rodada}.
dados_pontuados = None
mapa_pontuados = {}
mapa_partidas = {}
mapa_atletas_mercado = {}
mapa_clubes_mercado = {}
rodada_pontuados = 0
total_atletas_pontuados = 0
parciais_disponiveis = False

if mercado_aberto:
    print(
        "Mercado aberto: a rodada anterior será "
        "consultada pelos valores definitivos."
    )

else:
    print("Consultando atletas pontuados...")

    dados_pontuados = buscar_json(
        URL_PONTUADOS,
        obrigatorio=False,
    )

    if isinstance(dados_pontuados, dict):
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

    if parciais_disponiveis:
        print("Consultando partidas da rodada...")
        dados_partidas = buscar_json(URL_PARTIDAS)
        mapa_partidas = montar_mapa_partidas(
            dados_partidas
        )
        print(
            "Clubes com partida mapeada: "
            f"{len(mapa_partidas)}"
        )

        print("Consultando cadastro atual de atletas...")
        dados_atletas_mercado = buscar_json(
            URL_ATLETAS_MERCADO
        )
        mapa_atletas_mercado = (
            obter_mapa_atletas_mercado(
                dados_atletas_mercado
            )
        )
        mapa_clubes_mercado = obter_mapa_clubes_mercado(
            dados_atletas_mercado
        )
        print(
            "Atletas atuais mapeados: "
            f"{len(mapa_atletas_mercado)}"
        )

    else:
        print(
            "Ainda não existem parciais válidas para "
            f"a rodada {rodada_status}."
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
                reservas_detalhes,
                substituicoes_aplicadas,
            ) = calcular_parcial(
                dados_time,
                mapa_pontuados,
                mapa_partidas,
                mapa_atletas_mercado,
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

            # Mesmo com o resultado oficial, preservamos a escalação
            # efetiva completa para o comparativo Meu Time x adversário.
            # A pontuação total continua vindo da API oficial do time.
            mapa_oficial_time = montar_mapa_pontuados_do_time(dados_time)
            if len(atletas_escalados) >= 11 and mapa_oficial_time:
                (
                    _pontos_calculados,
                    atletas_pontuando,
                    detalhes,
                    reservas_detalhes,
                    substituicoes_aplicadas,
                ) = calcular_parcial(
                    dados_time,
                    mapa_oficial_time,
                    mapa_partidas,
                    mapa_atletas_mercado,
                    mapa_clubes_mercado,
                )
            else:
                atletas_pontuando = 0
                detalhes = []
                reservas_detalhes = []
                substituicoes_aplicadas = []

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

        if detalhes:
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
            registro["reservas_parcial"] = reservas_detalhes
            registro["substituicoes_aplicadas"] = substituicoes_aplicadas
            registro["criterio_parcial"] = (
                "escalação efetiva com banco normal, reserva de luxo e capitão 1.5"
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


agora_execucao_iso = agora_iso()
anterior_rodada = carregar_json(ARQUIVO_RODADA_ATUAL) or {}
anterior_monitor = anterior_rodada.get("monitoramento", {}) if isinstance(anterior_rodada, dict) else {}

def dados_funcionais(dados):
    if not isinstance(dados, dict):
        return {}
    copia = dict(dados)
    copia.pop("ultima_atualizacao", None)
    copia.pop("monitoramento", None)
    return copia

saida_base_comparacao = {
    "liga": "Cartola de Ermida",
    "rodada_cartola": rodada_status,
    "status_mercado": mercado_status,
    "mercado_aberto": mercado_aberto,
    "bola_rolando": bola_rolando_api,
    "fechamento_mercado": status.get("fechamento"),
    "rodada_em_andamento": rodada_em_andamento,
    "rodada_dados": rodada_dados,
    "rodada_pontuados": rodada_pontuados,
    "total_atletas_pontuados": total_atletas_pontuados,
    "observacao": observacao,
    "fonte": "parciais_cartola.json" if rodada_em_andamento else "rodada_atual_cartola.json",
    "times": novos_times,
}
houve_mudanca_dados = dados_funcionais(anterior_rodada) != dados_funcionais(saida_base_comparacao)
ultima_mudanca_dados = (
    agora_execucao_iso
    if houve_mudanca_dados
    else anterior_monitor.get("ultima_mudanca_dados")
    or anterior_rodada.get("ultima_atualizacao")
    or agora_execucao_iso
)

saida = {
    "liga": "Cartola de Ermida",
    "rodada_cartola": rodada_status,
    "status_mercado": mercado_status,
    "mercado_aberto": mercado_aberto,
    "bola_rolando": bola_rolando_api,
    "fechamento_mercado": status.get("fechamento"),
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
    "monitoramento": {
        "modo": (
            "ao_vivo" if rodada_em_andamento
            else "mercado_aberto" if mercado_aberto
            else "aguardando_parciais"
        ),
        "consulta_programada_minutos": 10,
        "ultima_consulta_api": agora_execucao_iso,
        "ultima_mudanca_dados": ultima_mudanca_dados,
        "resultado_ultima_consulta": (
            "dados_novos" if houve_mudanca_dados else "sem_alteracao"
        ),
        "houve_parciais_validas": bool(parciais_disponiveis),
        "times_processados": len(novos_times),
        "substituicoes_banco": sum(
            1 for time in novos_times
            for item in time.get("substituicoes_aplicadas", [])
            if item.get("tipo") == "banco_normal"
        ),
        "reservas_luxo_acionados": sum(
            1 for time in novos_times
            for item in time.get("substituicoes_aplicadas", [])
            if item.get("tipo") == "reserva_luxo"
        ),
    },
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

elif mercado_aberto and ARQUIVO_PARCIAIS.exists():
    # A abertura do mercado confirma que a rodada anterior terminou.
    # O arquivo ao vivo deixa de ser necessário; rodada_atual_cartola.json
    # passa a conter os pontos definitivos da rodada encerrada.
    ARQUIVO_PARCIAIS.unlink()

    print(
        "parciais_cartola.json removido: "
        "a rodada anterior foi encerrada e consolidada."
    )

elif not mercado_aberto and ARQUIVO_PARCIAIS.exists():
    # Se o endpoint de pontuados oscilar durante uma rodada fechada,
    # preservamos a última parcial válida em vez de apagar dados bons.
    print(
        "Parciais ainda indisponíveis ou temporariamente fora do ar. "
        "O último parciais_cartola.json válido foi preservado."
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
