#!/usr/bin/env python3

import csv
import json
import urllib.request
from pathlib import Path


# ------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------

URL = (
    "https://raw.githubusercontent.com/"
    "hsn2000/Spotify-Recommendation-System/"
    "master/mpd.slice.0-999.json"
)

# Descobre automaticamente a raiz do repositório.
RAIZ = Path(__file__).resolve().parent.parent

PASTA_DATA = RAIZ / "data"
ARQUIVO_JSON = PASTA_DATA / "dataset_temp.json"
ARQUIVO_CSV = PASTA_DATA / "dataset.csv"


# ------------------------------------------------------------
# DOWNLOAD
# ------------------------------------------------------------

def baixar_dataset():
    PASTA_DATA.mkdir(parents=True, exist_ok=True)

    print("Baixando dataset...")
    print(f"Fonte: {URL}")

    urllib.request.urlretrieve(URL, ARQUIVO_JSON)

    print("Download concluído.")


# ------------------------------------------------------------
# CONVERSÃO JSON -> CSV
# ------------------------------------------------------------

def converter_para_csv():
    print("Convertendo JSON para CSV...")

    with open(ARQUIVO_JSON, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    playlists = dados["playlists"]

    cabecalho = [
        "playlist_id",
        "playlist_nome",
        "playlist_modificada_em",
        "playlist_num_albums",
        "playlist_num_tracks",
        "playlist_num_followers",
        "playlist_num_edits",
        "playlist_duracao_ms",
        "playlist_num_artists",
        "playlist_collaborative",
        "posicao",
        "track_id",
        "track_nome",
        "track_duracao_ms",
        "artist_id",
        "artist_nome",
        "album_id",
        "album_nome",
    ]

    quantidade_linhas = 0

    with open(
        ARQUIVO_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as arquivo_csv:

        writer = csv.writer(arquivo_csv)

        writer.writerow(cabecalho)

        for playlist in playlists:

            for track in playlist.get("tracks", []):

                writer.writerow([
                    playlist.get("pid", ""),
                    playlist.get("name", ""),
                    playlist.get("modified_at", ""),
                    playlist.get("num_albums", ""),
                    playlist.get("num_tracks", ""),
                    playlist.get("num_followers", ""),
                    playlist.get("num_edits", ""),
                    playlist.get("duration_ms", ""),
                    playlist.get("num_artists", ""),
                    playlist.get("collaborative", ""),

                    track.get("pos", ""),
                    track.get("track_uri", ""),
                    track.get("track_name", ""),
                    track.get("duration_ms", ""),
                    track.get("artist_uri", ""),
                    track.get("artist_name", ""),
                    track.get("album_uri", ""),
                    track.get("album_name", ""),
                ])

                quantidade_linhas += 1

    print(f"{len(playlists)} playlists processadas.")
    print(f"{quantidade_linhas} registros gerados.")


# ------------------------------------------------------------
# LIMPEZA
# ------------------------------------------------------------

def limpar_temporarios():
    if ARQUIVO_JSON.exists():
        ARQUIVO_JSON.unlink()


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    try:
        baixar_dataset()
        converter_para_csv()
        limpar_temporarios()

        print()
        print("========================================")
        print("Dataset criado com sucesso!")
        print("========================================")
        print()
        print(f"Arquivo: {ARQUIVO_CSV}")

    except Exception as erro:
        print()
        print("Erro durante a geração do dataset:")
        print(erro)

        raise


if __name__ == "__main__":
    main()
