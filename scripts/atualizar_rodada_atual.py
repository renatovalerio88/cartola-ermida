import json
import urllib.request
import time
from datetime import datetime

ARQUIVO_RODADA_ATUAL = "rodada_atual_cartola.json"
URL_STATUS = "https://api.cartola.globo.com/mercado/status"

TIMES = [
    {"time_id": 3619967, "time": "Forward F. Club", "cartoleiro": "Valcard"},
    {"time_id": 40995, "time": "WECAM", "cartoleiro": "Renato Valerio"},
    {"time_id": 6074454, "time": "SardoGalo 13", "cartoleiro": "Álvaro Firmino"},
    {"time_id": 385413, "time": "Mão C.F", "cartoleiro": "Lucas Mão"},
    {"time_id": 8976743, "time": "MT10M1T0", "cartoleiro": "Marco Tulio"},
    {"time_id": 50252506, "time": "Branes25", "cartoleiro": "Roger Nunes"},
    {"time_id": 195382, "time": "CAMARASSO", "cartoleiro": "André Camarasso"},
    {"time_id": 60383, "time": "RJ Clube", "cartoleiro": "Ricardo Júdice"},
    {"time_id": 19198951, "time": "SANTASTICO GLORIOSO I", "cartoleiro": "Renato Do SANTOS"},
    {"time_id": 25588958, "time": "JUNA FUTEBOL CLUBE", "cartoleiro": "AMARILO JUNIOR"},
    {"time_id": 654232, "time": "D1OS", "cartoleiro": "10inho"},
    {"time_id": 974057, "time": "S.C. Finha Paulista", "cartoleiro": "Lucas Guedes"},
    {"time_id": 2745059, "time": "Epidemia Sport Clube", "cartoleiro": "Jorge Queiroz"},
    {"time_id": 91357, "time": "DP-SC", "cartoleiro": "D Pedro"},
    {"time_id": 29565271, "time": "Legione Romanista", "cartoleiro": "Arthur Godioso"},
    {"time_id": 28538913, "time": "Maria Gol De Costas", "cartoleiro": "Rafa Palhares"},
    {"time_id": 178173, "time": "Jack Golden", "cartoleiro": "Dourado"},
    {"time_id": 21141036, "time": "Ardam Cabubu", "cartoleiro": "Guizoba"},
    {"time_id": 50327258, "time": "Digdigie94", "cartoleiro": "DigdigieCabuloso"},
    {"time_id": 18434405, "time": "Gabiru cabuloso", "cartoleiro": "Wendell Costa"},
    {"time_id": 1193651, "time": "CruzeiroKiller", "cartoleiro": "André Pitanga"},
    {"time_id": 25565544, "time": "CHARLLOTTTE F.C.", "cartoleiro": "Charles Duek"},
    {"time_id": 28604976, "time": "Galo de Rio Doce FC", "cartoleiro": "Pedro Natali"},
    {"time_id": 14705949, "time": "Seu Cuca Futebol", "cartoleiro": "Xande Costa"},
    {"time_id": 214265, "time": "Framos F.C", "cartoleiro": "Fernando Ramos"},
    {"time_id": 186377, "time": "JACB FC", "cartoleiro": "Juca Barros"},
    {"time_id": 51042838, "time": "A76 FC", "cartoleiro": "Alan Guimarães"},
    {"time_id": 285883, "time": "Kayser Football", "cartoleiro": "Pedro Kayser"},
    {"time_id": 3128927, "time": "Jafeth G.D.F.C.", "cartoleiro": "Henrique Jafeth"},
    {"time_id": 25937153, "time": "GALOBERA F.C", "cartoleiro": "Gabriel Carvalho"},
    {"time_id": 1005072, "time": "PELUDÃO13", "cartoleiro": "WAGNER"},
    {"time_id": 49415297, "time": "SemFreio LEFC1988", "cartoleiro": "LEANDRO CAMPOS GIANI"},
    {"time_id": 103947, "time": "Campista F. C", "cartoleiro": "Rafael Abrantes"},
    {"time_id": 24449, "time": "Sport Club Prexeca Bangers", "cartoleiro": "Giovanni Guedes"},
    {"time_id": 25889523, "time": "Clube de Regatas Sô", "cartoleiro": "Betinho Valerio"},
    {"time_id": 596168, "time": "Galo Doido BH 93", "cartoleiro": "Lucas Real"},
]


def buscar_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
    )
    with urllib.request.urlopen(req) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


print("Buscando status do mercado...")
status = buscar_json(URL_STATUS)

rodada_status = int(status.get("rodada_atual", 0) or 0)
mercado_status = int(status.get("status_mercado", 0) or 0)

mercado_aberto = mercado_status == 1
rodada_em_andamento = mercado_status != 1

if mercado_aberto:
    rodada_dados = rodada_status - 1
else:
    rodada_dados = rodada_status

print(f"Rodada do Cartola/status: {rodada_status}")
print(f"Status do mercado: {mercado_status}")
print(f"Rodada usada para dados: {rodada_dados}")

times_rodada = []

for t in TIMES:
    url = f"https://api.cartola.globo.com/time/id/{t['time_id']}"

    try:
        dados = buscar_json(url)

        pontos = round(float(dados.get("pontos", 0) or 0), 2)
        patrimonio = round(float(dados.get("patrimonio", 0) or 0), 2)
        pontos_campeonato = round(float(dados.get("pontos_campeonato", 0) or 0), 2)

        times_rodada.append({
            "time_id": t["time_id"],
            "time": t["time"],
            "cartoleiro": t["cartoleiro"],
            "rodada_dados": int(dados.get("rodada_atual", rodada_dados) or rodada_dados),
            "pontos": pontos,
            "patrimonio": patrimonio,
            "pontos_campeonato": pontos_campeonato
        })

        print(f"OK - {t['time']} : {pontos}")
        time.sleep(0.1)

    except Exception as e:
        print(f"ERRO - {t['time']} : {e}")

saida = {
    "liga": "Cartola de Ermida",
    "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "rodada_cartola": rodada_status,
    "status_mercado": mercado_status,
    "mercado_aberto": mercado_aberto,
    "rodada_em_andamento": rodada_em_andamento,
    "rodada_dados": rodada_dados,
    "observacao": "Sem token. Se mercado_aberto=true, os pontos normalmente representam a última rodada fechada.",
    "times": times_rodada
}

with open(ARQUIVO_RODADA_ATUAL, "w", encoding="utf-8") as arquivo:
    json.dump(saida, arquivo, ensure_ascii=False, indent=2)

print("rodada_atual_cartola.json atualizado com sucesso!")
print(f"Times atualizados: {len(times_rodada)}")
