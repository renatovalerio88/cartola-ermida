import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

ARQUIVO_HISTORICO = Path("historico_cartola.json")
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


def carregar_historico():
    try:
        with ARQUIVO_HISTORICO.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            if not isinstance(dados, dict):
                raise ValueError("O histórico não contém um objeto JSON.")
            dados.setdefault("liga", "Cartola de Ermida")
            dados.setdefault("rodadas", {})
            return dados
    except FileNotFoundError:
        return {"liga": "Cartola de Ermida", "rodadas": {}}


def salvar_atomico(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", encoding="utf-8", dir=caminho.parent, delete=False, suffix=".tmp"
    ) as temporario:
        json.dump(dados, temporario, ensure_ascii=False, indent=2)
        temporario.write("\n")
        nome_temporario = temporario.name
    os.replace(nome_temporario, caminho)


print("Consultando o status do Cartola...")
status = buscar_json(URL_STATUS)

rodada_status = int(status.get("rodada_atual", 0) or 0)
mercado_status = int(status.get("status_mercado", 0) or 0)
mercado_aberto = mercado_status == 1

print(f"Rodada Cartola: {rodada_status}")
print(f"Status mercado: {mercado_status}")
print(f"Mercado aberto: {mercado_aberto}")

if not mercado_aberto:
    raise RuntimeError(
        "O mercado não está aberto. Nenhuma parcial será gravada "
        "como resultado definitivo."
    )

rodada_para_salvar = rodada_status - 1
if rodada_para_salvar <= 0:
    raise RuntimeError("Não foi possível determinar a última rodada fechada.")

print(f"Consolidando a rodada fechada {rodada_para_salvar}...")

novos_registros = []
erros = []

for indice, (time_id, nome_time, cartoleiro) in enumerate(TIMES, start=1):
    url = f"https://api.cartola.globo.com/time/id/{time_id}/{rodada_para_salvar}"
    try:
        dados = buscar_json(url)
        rodada_retornada = int(
            dados.get("rodada_atual", rodada_para_salvar) or rodada_para_salvar
        )
        if rodada_retornada != rodada_para_salvar:
            raise ValueError(
                f"API retornou rodada {rodada_retornada}; "
                f"esperada {rodada_para_salvar}."
            )

        registro = {
            "time_id": time_id,
            "time": nome_time,
            "cartoleiro": cartoleiro,
            "rodada": rodada_para_salvar,
            "pontos": round(float(dados.get("pontos", 0) or 0), 2),
            "patrimonio": round(float(dados.get("patrimonio", 0) or 0), 2),
        }
        novos_registros.append(registro)
        print(f"[{indice:02d}/{TOTAL_TIMES}] OK - {nome_time}: {registro['pontos']}")
    except Exception as erro:
        mensagem = f"{nome_time}: {erro}"
        erros.append(mensagem)
        print(f"[{indice:02d}/{TOTAL_TIMES}] ERRO - {mensagem}")
    time.sleep(0.12)

if erros or len(novos_registros) != TOTAL_TIMES:
    print("\nAtualização cancelada para preservar o histórico anterior.")
    print(f"Times obtidos: {len(novos_registros)}/{TOTAL_TIMES}")
    for mensagem in erros:
        print(f" - {mensagem}")
    raise RuntimeError("Não foi possível obter os 36 times.")

historico = carregar_historico()
historico["liga"] = "Cartola de Ermida"
historico.setdefault("rodadas", {})
historico["rodadas"][str(rodada_para_salvar)] = novos_registros

for rodada_texto in list(historico["rodadas"]):
    try:
        numero = int(rodada_texto)
    except ValueError:
        continue
    if numero > rodada_para_salvar:
        print(f"Removendo rodada futura inválida: {rodada_texto}")
        del historico["rodadas"][rodada_texto]

historico["ultima_rodada_fechada"] = rodada_para_salvar
historico["ultima_atualizacao"] = agora_texto()
salvar_atomico(ARQUIVO_HISTORICO, historico)

print("\nhistorico_cartola.json atualizado com segurança.")
print(f"Rodada consolidada: {rodada_para_salvar}")
print(f"Times atualizados: {len(novos_registros)}")
