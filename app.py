import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Roche Market Monitor", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Panorama Competitivo - Roche Perú")

# 2. CARGAR DATOS (Caché para que sea rapidísimo)
@st.cache_data
def load_data():
    # Ahora lee el archivo CSV local en lugar de internet
    df = pd.read_csv("datos.csv")
    return df

@st.cache_data
def load_geojson():
    # GeoJSON público con la silueta de los departamentos de Perú
    url_geo = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_departamental_simple.geojson"
    return requests.get(url_geo).json()

df = load_data()
peru_geo = load_geojson()

# 3. BARRA LATERAL: FILTROS
st.sidebar.header("Filtros Estratégicos")
lista_diagnosticos = df['Des_CIE10'].dropna().unique().tolist()
diagnostico_seleccionado = st.sidebar.selectbox("Seleccione Diagnóstico (CIE10):", lista_diagnosticos)

# Filtrar el dataframe general
df_filtrado = df[df['Des_CIE10'] == diagnostico_seleccionado]

# 4. PREPARAR DATOS PARA EL MAPA (Agrupar por Departamento)
# Sumamos los pacientes por departamento para pintar el mapa
df_mapa = df_filtrado.groupby('DEPARTAMENTO', as_index=False)['TOTAL_ATENDIDOS'].sum()

# 5. DIBUJAR EL MAPA DE COROPLETAS
st.subheader(f"📍 Mapa de Calor: {diagnostico_seleccionado}")

# Crear el mapa interactivo con Plotly
fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO',
    featureidkey='properties.NOMBDEP', # Llave del GeoJSON que hace match con tu Excel
    color='TOTAL_ATENDIDOS',
    color_continuous_scale="Reds", # Escala de calor de Roche (puedes cambiar a 'Blues', 'Viridis', etc.)
    mapbox_style="carto-positron",
    zoom=4,
    center={"lat": -9.18, "lon": -75.01}, # Centro geográfico de Perú
    opacity=0.7,
    labels={'TOTAL_ATENDIDOS': 'Pacientes Atendidos'}
)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# Mostrar el mapa en Streamlit
st.plotly_chart(fig, use_container_width=True)

# 6. TABLA DE DETALLE POR CLÍNICA
st.markdown("---")
st.subheader("🏥 Top Clínicas / Hospitales")

# Selector de Departamento para ver el detalle de clínicas
departamentos_disponibles = ["Todos"] + df_filtrado['DEPARTAMENTO'].unique().tolist()
dep_seleccionado = st.selectbox("Filtrar detalle por Departamento:", departamentos_disponibles)

# Lógica de la tabla
if dep_seleccionado != "Todos":
    df_tabla = df_filtrado[df_filtrado['DEPARTAMENTO'] == dep_seleccionado]
else:
    df_tabla = df_filtrado

# Ordenar para mostrar los que tienen más pacientes arriba
df_tabla = df_tabla[['DEPARTAMENTO', 'PROVINCIA', 'RAZON_SOC', 'Producto', 'TOTAL_ATENDIDOS']]
df_tabla = df_tabla.sort_values(by='TOTAL_ATENDIDOS', ascending=False)

st.dataframe(df_tabla, use_container_width=True, hide_index=True)
