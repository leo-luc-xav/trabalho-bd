import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


ARQUIVO_JSON = "openalex_cs_brasil_amostra.json"
PASTA_SAIDA = Path("csv")

TAMANHO_LOTE = 100
MAX_THREADS = 8

# Se você tiver uma API key gratuita do OpenAlex, coloque aqui.
# Exemplo:
# API_KEY = "sua_chave_aqui"
API_KEY = None

PASTA_SAIDA.mkdir(exist_ok=True)


def id_curto(openalex_id):
    if not openalex_id:
        return ""
    return openalex_id.rstrip("/").split("/")[-1]


def texto(valor):
    return "" if valor is None else str(valor)


def lista_texto(valores):
    if not valores:
        return ""
    return " | ".join(str(v) for v in valores if v is not None)


def dividir_lotes(lista, tamanho=100):
    lista = list(lista)

    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]


def requisicao_json(url, tentativas=4):
    for tentativa in range(tentativas):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "OpenAlex-Student-Project"
                }
            )

            with urllib.request.urlopen(req, timeout=20) as response:
                return json.load(response)

        except Exception as erro:
            if tentativa == tentativas - 1:
                raise

            espera = 2 ** tentativa
            print(
                f"Falha temporária: {erro}. "
                f"Tentando novamente em {espera}s..."
            )

            time.sleep(espera)


def montar_url(endpoint, lote, select):
    filtro = "|".join(lote)

    parametros = {
        "filter": f"id:{filtro}",
        "per_page": 100,
        "select": select
    }

    if API_KEY:
        parametros["api_key"] = API_KEY

    query = urllib.parse.urlencode(
        parametros,
        safe="|:,"
    )

    return f"https://api.openalex.org/{endpoint}?{query}"


def buscar_lote(endpoint, lote, select):
    url = montar_url(endpoint, lote, select)

    dados = requisicao_json(url)

    return dados.get("results", [])


def buscar_entidades_parallel(ids, endpoint, select):
    ids = sorted({
        id_curto(i)
        for i in ids
        if i
    })

    lotes = list(dividir_lotes(ids, TAMANHO_LOTE))

    print()
    print(
        f"{endpoint}: {len(ids)} registros "
        f"em {len(lotes)} lote(s)"
    )

    resultados = []

    if not lotes:
        return resultados

    workers = min(MAX_THREADS, len(lotes))

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:

        futuros = {
            executor.submit(
                buscar_lote,
                endpoint,
                lote,
                select
            ): numero
            for numero, lote in enumerate(lotes, start=1)
        }

        concluidos = 0

        for futuro in as_completed(futuros):
            numero = futuros[futuro]

            try:
                dados = futuro.result()
                resultados.extend(dados)

                concluidos += 1

                print(
                    f"{endpoint}: "
                    f"{concluidos}/{len(lotes)} lotes concluídos"
                )

            except Exception as erro:
                print(
                    f"Erro no lote {numero} de {endpoint}: {erro}"
                )

    return resultados


# ============================================================
# CARREGAR WORKS
# ============================================================

with open(
    ARQUIVO_JSON,
    encoding="utf-8"
) as arquivo:

    dados = json.load(arquivo)

trabalhos = dados["results"]

print(f"{len(trabalhos)} trabalhos encontrados.")


# ============================================================
# COLETAR IDS
# ============================================================

autor_ids = set()
instituicao_ids = set()
fonte_ids = set()

for trabalho in trabalhos:

    for autoria in trabalho.get("authorships", []):

        autor = autoria.get("author") or {}

        if autor.get("id"):
            autor_ids.add(autor["id"])

        for instituicao in autoria.get("institutions", []):
            if instituicao.get("id"):
                instituicao_ids.add(
                    instituicao["id"]
                )

    for local in trabalho.get("locations", []):

        fonte = local.get("source")

        if fonte and fonte.get("id"):
            fonte_ids.add(fonte["id"])


print(f"{len(autor_ids)} autores únicos.")
print(f"{len(instituicao_ids)} instituições únicas.")
print(f"{len(fonte_ids)} fontes únicas.")


# ============================================================
# CAMPOS QUE REALMENTE PRECISAMOS
# ============================================================

SELECT_AUTORES = ",".join([
    "id",
    "display_name",
    "orcid",
    "works_count",
    "cited_by_count",
    "summary_stats"
])

SELECT_INSTITUICOES = ",".join([
    "id",
    "display_name",
    "ids",
    "country_code",
    "geo",
    "type",
    "status",
    "works_count",
    "cited_by_count",
    "summary_stats"
])

SELECT_FONTES = ",".join([
    "id",
    "display_name",
    "type",
    "issn_l",
    "issn",
    "host_organization",
    "host_organization_name",
    "country_code",
    "is_oa",
    "is_in_doaj",
    "works_count",
    "cited_by_count",
    "summary_stats"
])


# ============================================================
# BUSCAR AS 3 CATEGORIAS TAMBÉM EM PARALELO
# ============================================================

inicio = time.time()

with ThreadPoolExecutor(max_workers=3) as executor:

    f_autores = executor.submit(
        buscar_entidades_parallel,
        autor_ids,
        "authors",
        SELECT_AUTORES
    )

    f_instituicoes = executor.submit(
        buscar_entidades_parallel,
        instituicao_ids,
        "institutions",
        SELECT_INSTITUICOES
    )

    f_fontes = executor.submit(
        buscar_entidades_parallel,
        fonte_ids,
        "sources",
        SELECT_FONTES
    )

    autores = f_autores.result()
    instituicoes = f_instituicoes.result()
    fontes = f_fontes.result()


# ============================================================
# TRABALHOS.CSV
# ============================================================

with open(
    PASTA_SAIDA / "trabalhos.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as arquivo:

    writer = csv.writer(arquivo)

    writer.writerow([
        "openalex_id",
        "doi",
        "titulo",
        "ano_publicacao",
        "data_publicacao",
        "tipo",
        "idioma",
        "numero_citacoes",
        "quantidade_autores",
        "open_access",
        "topico_principal"
    ])

    for trabalho in trabalhos:

        oa = trabalho.get("open_access") or {}
        topico = trabalho.get("primary_topic") or {}

        writer.writerow([
            id_curto(trabalho.get("id")),
            texto(trabalho.get("doi")),
            texto(trabalho.get("title")),
            texto(trabalho.get("publication_year")),
            texto(trabalho.get("publication_date")),
            texto(trabalho.get("type")),
            texto(trabalho.get("language")),
            texto(trabalho.get("cited_by_count")),
            len(trabalho.get("authorships", [])),
            texto(oa.get("is_oa")),
            texto(topico.get("display_name"))
        ])


# ============================================================
# AUTORES.CSV
# ============================================================

with open(
    PASTA_SAIDA / "autores.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as arquivo:

    writer = csv.writer(arquivo)

    writer.writerow([
        "openalex_id",
        "nome",
        "orcid",
        "quantidade_trabalhos",
        "numero_citacoes",
        "h_index",
        "i10_index",
        "media_citacoes_2_anos"
    ])

    for autor in autores:

        stats = autor.get("summary_stats") or {}

        writer.writerow([
            id_curto(autor.get("id")),
            texto(autor.get("display_name")),
            texto(autor.get("orcid")),
            texto(autor.get("works_count")),
            texto(autor.get("cited_by_count")),
            texto(stats.get("h_index")),
            texto(stats.get("i10_index")),
            texto(stats.get("2yr_mean_citedness"))
        ])


# ============================================================
# INSTITUICOES.CSV
# ============================================================

with open(
    PASTA_SAIDA / "instituicoes.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as arquivo:

    writer = csv.writer(arquivo)

    writer.writerow([
        "openalex_id",
        "nome",
        "ror",
        "pais",
        "codigo_pais",
        "cidade",
        "regiao",
        "tipo",
        "status",
        "quantidade_trabalhos",
        "numero_citacoes",
        "h_index",
        "i10_index",
        "media_citacoes_2_anos"
    ])

    for instituicao in instituicoes:

        ids = instituicao.get("ids") or {}
        geo = instituicao.get("geo") or {}
        stats = instituicao.get("summary_stats") or {}

        writer.writerow([
            id_curto(instituicao.get("id")),
            texto(instituicao.get("display_name")),
            texto(ids.get("ror")),
            texto(geo.get("country")),
            texto(instituicao.get("country_code")),
            texto(geo.get("city")),
            texto(geo.get("region")),
            texto(instituicao.get("type")),
            texto(instituicao.get("status")),
            texto(instituicao.get("works_count")),
            texto(instituicao.get("cited_by_count")),
            texto(stats.get("h_index")),
            texto(stats.get("i10_index")),
            texto(stats.get("2yr_mean_citedness"))
        ])


# ============================================================
# FONTES.CSV
# ============================================================

with open(
    PASTA_SAIDA / "fontes.csv",
    "w",
    newline="",
    encoding="utf-8-sig"
) as arquivo:

    writer = csv.writer(arquivo)

    writer.writerow([
        "openalex_id",
        "nome",
        "tipo",
        "issn_l",
        "issns",
        "organizacao_hospedeira",
        "organizacao_hospedeira_nome",
        "pais",
        "open_access",
        "doaj",
        "quantidade_trabalhos",
        "numero_citacoes",
        "h_index",
        "i10_index",
        "media_citacoes_2_anos"
    ])

    for fonte in fontes:

        stats = fonte.get("summary_stats") or {}

        writer.writerow([
            id_curto(fonte.get("id")),
            texto(fonte.get("display_name")),
            texto(fonte.get("type")),
            texto(fonte.get("issn_l")),
            lista_texto(fonte.get("issn")),
            texto(fonte.get("host_organization")),
            texto(fonte.get("host_organization_name")),
            texto(fonte.get("country_code")),
            texto(fonte.get("is_oa")),
            texto(fonte.get("is_in_doaj")),
            texto(fonte.get("works_count")),
            texto(fonte.get("cited_by_count")),
            texto(stats.get("h_index")),
            texto(stats.get("i10_index")),
            texto(stats.get("2yr_mean_citedness"))
        ])


tempo = time.time() - inicio

print()
print("==============================")
print("FINALIZADO")
print("==============================")
print(f"Trabalhos:    {len(trabalhos)}")
print(f"Autores:      {len(autores)}")
print(f"Instituições: {len(instituicoes)}")
print(f"Fontes:       {len(fontes)}")
print(f"Tempo total:  {tempo:.2f} segundos")
