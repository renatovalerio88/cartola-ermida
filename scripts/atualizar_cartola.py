import json
import os
import urllib.request
from datetime import datetime

SLUG_LIGA = "cartola-de-ermida"
ARQUIVO_HISTORICO = "historico_cartola.json"

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


print("Buscando status do mercado...")
status = buscar_json(URL_STATUS)

rodada_status = int(status.get("rodada_atual", 0) or 0)
mercado_status = int(status.get("status_mercado", 0) or 0)

print(f"Rodada do Cartola/status: {rodada_status}")
print(f"Status do mercado: {mercado_status}")

# status_mercado:
# 1 = mercado aberto
# 2 = mercado fechado / rodada em andamento
# 3 = mercado em manutenção ou outro estado
#
# Se mercado está aberto, normalmente o Cartola já aponta para a próxima rodada.
# Então a última rodada fechada é rodada_atual - 1.
if mercado_status == 1:
    rodada_para_salvar = rodada_status - 1
else:
    rodada_para_salvar = rodada_status

if rodada_para_salvar <= 0:
    raise Exception("Não foi possível determinar a rodada correta para salvar.")

print(f"Rodada que será salva no histórico: {rodada_para_salvar}")

print("Buscando dados da liga...")
dados_liga = buscar_json(URL_LIGA)

historico = carregar_historico()
historico["liga"] = dados_liga.get("liga", {}).get("nome", "Cartola de Ermida")

times = dados_liga.get("times", [])

if not times:
    raise Exception("Nenhum time encontrado na API da liga.")

historico.setdefault("rodadas", {})
historico["rodadas"][str(rodada_para_salvar)] = []

for time_liga in times:
    pontos = time_liga.get("pontos", {}).get("rodada", 0)
    patrimonio = time_liga.get("patrimonio", 0)

    registro = {
        "time_id": time_liga.get("time_id"),
        "time": str(time_liga.get("nome", "")).strip(),
        "cartoleiro": str(time_liga.get("nome_cartola", "")).strip(),
        "rodada": rodada_para_salvar,
        "pontos": round(float(pontos or 0), 2),
        "patrimonio": round(float(patrimonio or 0), 2)
    }

    historico["rodadas"][str(rodada_para_salvar)].append(registro)

    print(f"OK - {registro['time']} : {registro['pontos']}")

# Limpeza de rodadas futuras vazias ou falsas
# Mantém apenas rodadas até a rodada correta.
rodadas_para_apagar = []

for rodada_txt, lista in historico["rodadas"].items():
    try:
        numero = int(rodada_txt)
    except ValueError:
        continue

    if numero > rodada_para_salvar:
        rodadas_para_apagar.append(rodada_txt)

for rodada_txt in rodadas_para_apagar:
    print(f"Removendo rodada futura/falsa: {rodada_txt}")
    del historico["rodadas"][rodada_txt]

salvar_historico(historico)

print("historico_cartola.json atualizado com sucesso!")
print(f"Times atualizados: {len(times)}")
