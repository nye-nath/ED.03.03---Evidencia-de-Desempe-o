import os
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(
    page_title="Dashboard TMDB - Evidencia",
    page_icon="🎬",
    layout="wide"
)

COLOR_GRIS = "#B9C3D1"
COLOR_AZUL = "#1C4C9A"

plt.rcParams.update({
    "font.sans-serif": "DejaVu Sans",
    "axes.edgecolor": COLOR_GRIS,
    "axes.linewidth": 0.8,
    "grid.color": COLOR_GRIS,
    "grid.alpha": 0.3
})

@st.cache_data
def cargar_datos():
    cache_file = "respuesta.json"
    
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            datos_raw = json.load(f)
        origen = "Caché local (respuesta.json)"
    else:
        token = None
        if os.path.exists("token.txt"):
            with open("token.txt", "r", encoding="utf-8") as f:
                token = f.read().strip()

        if not token or len(token) < 20:
            st.error("No se encontró 'respuesta.json' ni un token válido en 'token.txt'.")
            st.stop()

        todas_las_peliculas = []
        base_url = "https://api.themoviedb.org/3/discover/movie"
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        for page in range(1, 13):
            params = {"language": "en-US", "sort_by": "vote_count.desc", "page": page}
            respuesta = requests.get(base_url, headers=headers, params=params)

            if respuesta.status_code != 200:
                st.error(f"Error HTTP {respuesta.status_code} al consultar TMDB.")
                st.stop()
            if "json" not in (respuesta.headers.get("Content-Type") or ""):
                st.error("La respuesta de la API no es JSON válido.")
                st.stop()

            todas_las_peliculas.extend(respuesta.json().get("results", []))

        datos_raw = {"results": todas_las_peliculas}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(datos_raw, f, ensure_ascii=False, indent=2)
        origen = "API de TMDB (en vivo)"

    df = pd.DataFrame(datos_raw.get("results", []))
    columnas = ["title", "vote_average", "vote_count", "popularity", "release_date", "original_language"]
    df = df[columnas].copy()

    total_inicial = len(df)
    df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce")
    df["vote_count"] = pd.to_numeric(df["vote_count"], errors="coerce")
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")

    df_clean = df.dropna(subset=["vote_average", "vote_count", "popularity", "release_date", "original_language"]).copy()
    df_clean["año"] = df_clean["release_date"].dt.year

    top_idiomas = df_clean["original_language"].value_counts().nlargest(4).index
    df_clean["idioma_grupo"] = df_clean["original_language"].apply(
        lambda x: x.upper() if x in top_idiomas else "OTROS"
    )

    stats_limpieza = {
        "inicial": total_inicial,
        "final": len(df_clean),
        "perdidos": total_inicial - len(df_clean),
        "origen": origen
    }
    return df_clean, stats_limpieza

df, stats = cargar_datos()

st.sidebar.header("Filtros de Exploración")
st.sidebar.caption(f"Fuente: {stats['origen']}")

min_anio, max_anio = int(df["año"].min()), int(df["año"].max())
rango_anios = st.sidebar.slider(
    "Rango de año de estreno",
    min_value=min_anio,
    max_value=max_anio,
    value=(2000, max_anio)
)

idiomas_disponibles = sorted(df["idioma_grupo"].unique().tolist())
idiomas_seleccionados = st.sidebar.multiselect(
    "Idioma original",
    options=idiomas_disponibles,
    default=idiomas_disponibles
)

df_filtrado = df[
    (df["año"] >= rango_anios[0]) &
    (df["año"] <= rango_anios[1]) &
    (df["idioma_grupo"].isin(idiomas_seleccionados))
]

st.title("🎬 Análisis de Películas Populares (TMDB API)")
st.markdown("Dashboard interactivo construido a partir del consumo y limpieza de datos de **The Movie Database**.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Películas filtradas", f"{len(df_filtrado)} / {stats['final']}")
col2.metric("Calificación promedio", f"{df_filtrado['vote_average'].mean():.2f} / 10" if len(df_filtrado) else "N/A")
col3.metric("Votos promedio", f"{int(df_filtrado['vote_count'].mean()):,}" if len(df_filtrado) else "0")
col4.metric("Popularidad máxima", f"{df_filtrado['popularity'].max():.1f}" if len(df_filtrado) else "0")

st.divider()

if df_filtrado.empty:
    st.warning("No hay películas que coincidan con los filtros seleccionados.")
    st.stop()

fila1_col1, fila1_col2 = st.columns(2)

with fila1_col1:
    st.subheader("1. Distribución de Calificaciones")
    fig1, ax1 = plt.subplots(figsize=(7, 4.5))
    n, bins, patches = ax1.hist(df_filtrado["vote_average"], bins=10, color=COLOR_GRIS, edgecolor="white")
    if len(patches) > 0:
        patches[n.argmax()].set_facecolor(COLOR_AZUL)
    ax1.set_title("Concentración de calificaciones de usuarios", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Calificación promedio (0 a 10 puntos)")
    ax1.set_ylabel("Cantidad de películas")
    ax1.grid(axis="y", linestyle="--")
    st.pyplot(fig1)

with fila1_col2:
    st.subheader("2. Comparación por Idioma")
    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    comp = df_filtrado.groupby("idioma_grupo")["vote_average"].mean().reset_index().sort_values(by="vote_average", ascending=True)
    colores = [COLOR_AZUL if v == comp["vote_average"].max() else COLOR_GRIS for v in comp["vote_average"]]
    ax2.barh(comp["idioma_grupo"], comp["vote_average"], color=colores, height=0.55)
    ax2.set_title("Calificación promedio según idioma original", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Calificación promedio (0 a 10 puntos)")
    ax2.set_ylabel("Idioma original")
    ax2.set_xlim(0, 10)
    ax2.grid(axis="x", linestyle="--")
    st.pyplot(fig2)

fila2_col1, fila2_col2 = st.columns(2)

with fila2_col1:
    st.subheader("3. Relación Votos vs. Popularidad")
    fig3, ax3 = plt.subplots(figsize=(7, 4.5))
    ax3.scatter(df_filtrado["vote_count"], df_filtrado["popularity"], color=COLOR_AZUL, alpha=0.65, s=45)
    ax3.set_title("Votos acumulados frente a popularidad actual", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Cantidad total de votos")
    ax3.set_ylabel("Índice de popularidad (puntos TMDB)")
    ax3.grid(True, linestyle="--")
    st.pyplot(fig3)

with fila2_col2:
    st.subheader("4. Evolución Temporal")
    fig4, ax4 = plt.subplots(figsize=(7, 4.5))
    evol = df_filtrado.groupby("año")["vote_average"].mean().reset_index()
    ax4.plot(evol["año"], evol["vote_average"], marker="o", color=COLOR_AZUL, linewidth=2)
    ax4.set_title("Tendencia de calificación promedio por año de estreno", fontsize=11, fontweight="bold")
    ax4.set_xlabel("Año de estreno")
    ax4.set_ylabel("Calificación promedio anual (0 a 10 puntos)")
    ax4.set_ylim(5, 9.5)
    ax4.grid(True, linestyle="--")
    st.pyplot(fig4)

with st.expander("Ver reporte de limpieza y tabla de datos"):
    st.write(f"**Registros iniciales:** {stats['inicial']} | **Descartados:** {stats['perdidos']} | **Utilizables:** {stats['final']}")
    st.dataframe(df_filtrado[["title", "año", "idioma_grupo", "vote_average", "vote_count", "popularity"]], use_container_width=True)
