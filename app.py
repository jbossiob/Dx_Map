import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. CONFIGURACIÓN MOBILE-FIRST
# Usamos layout="centered" para que en celulares se apile perfectamente
st.set_page_config(page_title="Roche Market Monitor", layout="centered")

# Encabezado limpio
st.title("📊 BI Roche - Panorama")

# 2. CARGAR DATOS
@st.cache_data
def load_data():
    df = pd.read_csv("datos.csv")
    
    # --- LA MAGIA PARA QUE SE PINTE EL MAPA ---
    # Limpiamos "AMAZONAS, PERU" para que quede solo "AMAZONAS" y haga match con el mapa
    if 'DEPARTAMENTO' in df.columns:
        df['DEPARTAMENTO_GEO'] = df['DEPARTAMENTO'].str.replace(', PERU', '', regex=False).str.strip().str.upper()
    return df

@st.cache_data
def load_geojson():
    # GeoJSON con la silueta de los departamentos
    url_geo = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_departamental_simple.geojson"
    return requests.get(url_geo).json()

df = load_data()
peru_geo = load_geojson()

# 3. FILTROS EN PANTALLA PRINCIPAL (Ideal para celular)
st.markdown("### 🔍 Filtros")
lista_diagnosticos = df['Diagnóstico'].dropna().unique().tolist()
diagnostico_seleccionado = st.selectbox("Seleccione Diagnóstico:", lista_diagnosticos)

# Filtrar datos
df_filtrado = df[df['Diagnóstico'] == diagnostico_seleccionado]

# 4. PREPARAR DATOS MAPA (Coropletas por Promedio)
df_mapa = df_filtrado.groupby('DEPARTAMENTO_GEO', as_index=False)['Prom_atendidos'].mean()
df_mapa['Prom_atendidos'] = df_mapa['Prom_atendidos'].round(1)

# 5. DIBUJAR EL MAPA DE COROPLETAS (Siluetas rellenas)
st.markdown("---")
st.markdown(f"**📍 Promedio de Atención: {diagnostico_seleccionado}**")

fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO_GEO',
    featureidkey='properties.NOMBDEP', 
    color='Prom_atendidos',
    color_continuous_scale="Reds", # Escala de calor (Coropletas)
    mapbox_style="carto-positron",
    zoom=3.8, # Zoom optimizado para celular
    center={"lat": -9.18, "lon": -75.01}, 
    opacity=0.75,
    labels={'Prom_atendidos': 'Promedio'}
)

# Ajustar márgenes y altura para mobile
fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    height=450, # Altura fija para que no ocupe toda la pantalla
    coloraxis_colorbar=dict(title="", thickness=15, len=0.8) # Barra de color más delgada
)

st.plotly_chart(fig, use_container_width=True)

# 6. TABLA DE DETALLE (Optimizada para no desbordar)
st.markdown("---")
st.markdown("**🏥 Detalle de Clínicas**")

departamentos_disponibles = ["Todos"] + df_filtrado['DEPARTAMENTO'].unique().tolist()
dep_seleccionado = st.selectbox("Filtrar por Departamento:", departamentos_disponibles)

if dep_seleccionado != "Todos":
    df_tabla = df_filtrado[df_filtrado['DEPARTAMENTO'] == dep_seleccionado]
else:
    df_tabla = df_filtrado

# Seleccionamos menos columnas para que en el celular no haya que hacer scroll infinito
columnas_tabla = ['PROVINCIA', 'Producto', 'Cat_terapeutica', 'Prom_atendidos']
df_tabla = df_tabla[columnas_tabla].sort_values(by='Prom_atendidos', ascending=False)

st.dataframe(df_tabla.style.format({'Prom_atendidos': '{:.1f}'}), use_container_width=True, hide_index=True)
