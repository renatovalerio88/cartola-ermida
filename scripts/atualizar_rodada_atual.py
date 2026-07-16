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


def agora_texto():
    return datetime.now(FUSO).strftime("%d/%m/%Y %H:%M:%S")


def buscar_json(url, tentativas=3):
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=25) as resposta:
                return json.loads(resposta.read().decode("utf-8"))
        except Exception as erro:
            ultimo_erro = erro
            print(f"Tentativa {tentativa}/{tentativas} falhou em {url}: {erro}")
            if tentativa < tentativas:
                time.sleep(tentativa * 2)
    raise RuntimeError(f"Falha definitiva em {url}: {ultimo_erro}")


def carregar_json(caminho):
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            return dados if isinstance(dados, dict) else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def salvar_atomico(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=caminho.parent, delete=False, suffix=".tmp"
    ) as temporario:
        json.dump(dados, temporario, ensure_ascii=False, indent=2)
        temporario.write("\n")
        nome_temporario = temporario.name
    os.replace(nome_temporario, caminho)


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
    salvar_atomico(caminho, dados)
    print(f"{caminho}: arquivo atualizado.")
    return True


print("Consultando o status do Cartola...")
status = buscar_json(URL_STATUS)

rodada_status = int(status.get("rodada_atual", 0) or 0)
mercado_status = int(status.get("status_mercado", 0) or 0)
mercado_aberto = mercado_status == 1
bola_rolando = bool(status.get("bola_rolando", False))
rodada_em_andamento = bola_rolando
rodada_dados = rodada_status - 1 if mercado_aberto else rodada_status

if rodada_dados <= 0:
    raise RuntimeError("Não foi possível determinar a rodada dos dados.")

print(f"Rodada Cartola: {rodada_status}")
print(f"Status mercado: {mercado_status}")
print(f"Mercado aberto: {mercado_aberto}")
print(f"Bola rolando: {bola_rolando}")
print(f"Rodada usada nos dados: {rodada_dados}")

novos_times = []
erros = []

for indice, (time_id, nome_time, cartoleiro) in enumerate(TIMES, start=1):
    url = f"https://api.cartola.globo.com/time/id/{time_id}"
    try:
        dados = buscar_json(url)
        rodada_retornada = int(
            dados.get("rodada_atual", rodada_dados) or rodada_dados
        )
        if rodada_retornada != rodada_dados:
            raise ValueError(
                f"API retornou rodada {rodada_retornada}; "
                f"esperada {rodada_dados}."
            )

        registro = {
            "time_id": time_id,
            "time": nome_time,
            "cartoleiro": cartoleiro,
            "rodada_dados": rodada_retornada,
            "pontos": round(float(dados.get("pontos", 0) or 0), 2),
            "patrimonio": round(float(dados.get("patrimonio", 0) or 0), 2),
            "pontos_campeonato": round(
                float(dados.get("pontos_campeonato", 0) or 0), 2
            ),
        }
        novos_times.append(registro)
        print(f"[{indice:02d}/{TOTAL_TIMES}] OK - {nome_time}: {registro['pontos']}")
    except Exception as erro:
        mensagem = f"{nome_time}: {erro}"
        erros.append(mensagem)
        print(f"[{indice:02d}/{TOTAL_TIMES}] ERRO - {mensagem}")
    time.sleep(0.12)

if erros or len(novos_times) != TOTAL_TIMES:
    print("\nColeta cancelada para preservar os arquivos anteriores.")
    print(f"Times obtidos: {len(novos_times)}/{TOTAL_TIMES}")
    for mensagem in erros:
        print(f" - {mensagem}")
    raise RuntimeError("Não foi possível obter os 36 times.")

if rodada_em_andamento:
    observacao = "Dados parciais da rodada atual."
elif mercado_aberto:
    observacao = "Mercado aberto: pontos da última rodada fechada."
else:
    observacao = "Mercado fechado, mas sem indicação de bola rolando."

saida = {
    "liga": "Cartola de Ermida",
    "rodada_cartola": rodada_status,
    "status_mercado": mercado_status,
    "mercado_aberto": mercado_aberto,
    "bola_rolando": bola_rolando,
    "rodada_em_andamento": rodada_em_andamento,
    "rodada_dados": rodada_dados,
    "observacao": observacao,
    "times": novos_times,
}

salvar_somente_se_mudou(ARQUIVO_RODADA_ATUAL, dict(saida))

if rodada_em_andamento:
    parciais = dict(saida)
    parciais["fonte"] = "api_time_id"
    salvar_somente_se_mudou(ARQUIVO_PARCIAIS, parciais)
elif ARQUIVO_PARCIAIS.exists():
    ARQUIVO_PARCIAIS.unlink()
    print("parciais_cartola.json removido: não há rodada ao vivo.")

print("\nAtualização da rodada atual concluída com segurança.")
print(f"Times atualizados: {len(novos_times)}")
print(f"Parciais ao vivo: {'sim' if rodada_em_andamento else 'não'}")
