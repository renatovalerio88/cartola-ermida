import json
import os
import urllib.request
from datetime import datetime

SLUG_LIGA = "cartola-de-ermida"
ARQUIVO_RODADA_ATUAL = "rodada_atual_cartola.json"

URL_LIGA = f"https://api.cartola.globo.com/auth/liga/{SLUG_LIGA}?orderBy=campeonato"
URL_STATUS = "https://api.cartola.globo.com/mercado/status"


def buscar_json(url):
    token = os.environ.get("CARTOLA_TOKEN")

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "x-glb-app": "cartola_web",
        "x-glb-auth": "oidc",
    }

    if token:
        headers["Authorization"] = token

    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


print("Buscando status do mercado...")
status = buscar_json(URL_STATUS)

rodada_status = int(status.get("rodada_atual", 0) or 0)
mercado_status = int(status.get("status_mercado", 0) or 0)

# 1 = mercado aberto
# 2 = mercado fechado / rodada em andamento
# outros = manutenção/outros estados
mercado_aberto = mercado_status == 1
rodada_em_andamento = mercado_status != 1

print(f"Rodada do Cartola/status: {rodada_status}")
print(f"Status do mercado: {mercado_status}")
print(f"Rodada em andamento: {rodada_em_andamento}")

print("Buscando dados da liga...")
dados_liga = buscar_json(URL_LIGA)

times = dados_liga.get("times", [])

if not times:
    raise Exception("Nenhum time encontrado na API da liga.")

times_rodada = []

for time_liga in times:
    pontos = time_liga.get("pontos", {}).get("rodada", 0)
    patrimonio = time_liga.get("patrimonio", 0)

    registro = {
        "time_id": time_liga.get("time_id"),
        "time": str(time_liga.get("nome", "")).strip(),
        "cartoleiro": str(time_liga.get("nome_cartola", "")).strip(),
        "pontos": round(float(pontos or 0), 2),
        "patrimonio": round(float(patrimonio or 0), 2),
        "ranking_rodada": time_liga.get("ranking", {}).get("rodada"),
        "ranking_campeonato": time_liga.get("ranking", {}).get("campeonato")
    }

    times_rodada.append(registro)

    print(f"OK - {registro['time']} : {registro['pontos']}")

saida = {
    "liga": dados_liga.get("liga", {}).get("nome", "Cartola de Ermida"),
    "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "rodada_cartola": rodada_status,
    "status_mercado": mercado_status,
    "mercado_aberto": mercado_aberto,
    "rodada_em_andamento": rodada_em_andamento,
    "observacao": "Se mercado_aberto=true, estes pontos podem representar a última rodada fechada, não parcial ao vivo.",
    "times": times_rodada
}

with open(ARQUIVO_RODADA_ATUAL, "w", encoding="utf-8") as arquivo:
    json.dump(saida, arquivo, ensure_ascii=False, indent=2)

print("rodada_atual_cartola.json atualizado com sucesso!")
print(f"Times atualizados: {len(times_rodada)}")
