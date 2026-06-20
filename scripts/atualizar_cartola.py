import json
import urllib.request
import time
from datetime import datetime

SLUG_LIGA = "cartola-de-ermida"
ARQUIVO_HISTORICO = "historico_cartola.json"

URL_LIGA = f"https://api.cartola.globo.com/auth/liga/{SLUG_LIGA}?orderBy=campeonato"


def buscar_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "x-glb-app": "cartola_web",
            "x-glb-auth": "oidc",
        }
    )

    with urllib.request.urlopen(req) as resposta:
        return json.loads(resposta.read().decode("utf-8"))


def carregar_historico():
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        return {
            "liga": "Cartola de Ermida",
            "rodadas": {}
        }


def salvar_historico(historico):
    historico["ultima_atualizacao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as arquivo:
        json.dump(historico, arquivo, ensure_ascii=False, indent=2)


print("Buscando dados da liga...")

dados_liga = buscar_json(URL_LIGA)

historico = carregar_historico()

historico["liga"] = dados_liga.get("liga", {}).get("nome", "Cartola de Ermida")

times = dados_liga.get("times", [])

if not times:
    raise Exception("Nenhum time encontrado na API da liga.")

# Pega a rodada mais comum entre os times.
# Normalmente é a rodada atual/última rodada processada.
rodadas_detectadas = []

for time_liga in times:
    rodada_time_id = time_liga.get("rodada_time_id")
    if rodada_time_id:
        rodadas_detectadas.append(int(rodada_time_id))

if not rodadas_detectadas:
    raise Exception("Não foi possível detectar a rodada.")

rodada_atual = max(set(rodadas_detectadas), key=rodadas_detectadas.count)

print(f"Rodada detectada: {rodada_atual}")

historico["rodadas"][str(rodada_atual)] = []

for time_liga in times:
    pontos = time_liga.get("pontos", {}).get("rodada", 0)
    patrimonio = time_liga.get("patrimonio", 0)

    historico["rodadas"][str(rodada_atual)].append({
        "time_id": time_liga.get("time_id"),
        "time": str(time_liga.get("nome", "")).strip(),
        "cartoleiro": str(time_liga.get("nome_cartola", "")).strip(),
        "rodada": rodada_atual,
        "pontos": round(float(pontos or 0), 2),
        "patrimonio": round(float(patrimonio or 0), 2)
    })

    print(f"OK - {time_liga.get('nome')} : {round(float(pontos or 0), 2)}")

salvar_historico(historico)

print("historico_cartola.json atualizado com sucesso!")
print(f"Times atualizados: {len(times)}")
