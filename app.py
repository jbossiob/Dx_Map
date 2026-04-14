import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Roche Market Monitor", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Panorama Competitivo - Roche Perú")

# 2. CARGAR DATOS
@st.cache_data
def load_data():
    # Lee el archivo CSV local desde el repositorio
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
lista_diagnosticos = df['Diagnóstico'].dropna().unique().tolist()
diagnostico_seleccionado = st.sidebar.selectbox("Seleccione Diagnóstico:", lista_diagnosticos)

# Filtrar el dataframe general
df_filtrado = df[df['Diagnóstico'] == diagnostico_seleccionado]

# 4. PREPARAR DATOS PARA EL MAPA (Agrupar por Departamento y sacar PROMEDIO)
df_mapa = df_filtrado.groupby('DEPARTAMENTO', as_index=False)['Prom_atendidos'].mean()
# Redondear a 1 decimal para que el mapa se vea más limpio
df_mapa['Prom_atendidos'] = df_mapa['Prom_atendidos'].round(1)

# 5. DIBUJAR EL MAPA DE COROPLETAS
st.subheader(f"📍 Mapa de Calor: {diagnostico_seleccionado}")

# Crear el mapa interactivo con Plotly
fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO',
    featureidkey='properties.NOMBDEP', # Llave del GeoJSON que hace match con tu Excel
    color='Prom_atendidos',
    color_continuous_scale="Reds", 
    mapbox_style="carto-positron",
    zoom=4,
    center={"lat": -9.18, "lon": -75.01}, # Centro geográfico de Perú
    opacity=0.7,
    labels={'Prom_atendidos': 'Promedio Atendidos'}
)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

# Mostrar el mapa en Streamlit
st.plotly_chart(fig, use_container_width=True)

# 6. TABLA DE DETALLE
st.markdown("---")
st.subheader("🏥 Detalle de Atención")

# Selector de Departamento para ver el detalle
departamentos_disponibles = ["Todos"] + df_filtrado['DEPARTAMENTO'].unique().tolist()
dep_seleccionado = st.selectbox("Filtrar detalle por Departamento:", departamentos_disponibles)

# Lógica de la tabla
if dep_seleccionado != "Todos":
    df_tabla = df_filtrado[df_filtrado['DEPARTAMENTO'] == dep_seleccionado]
else:
    df_tabla = df_filtrado

# Seleccionar columnas y ordenar de mayor a menor promedio
columnas_tabla = ['DEPARTAMENTO', 'PROVINCIA', 'Diagnóstico', 'Producto', 'Cat_terapeutica', 'Prom_atendidos']
df_tabla = df_tabla[columnas_tabla]
df_tabla = df_tabla.sort_values(by='Prom_atendidos', ascending=False)

# Mostrar tabla (redondeando visualmente el promedio para no tener demasiados decimales)
st.dataframe(df_tabla.style.format({'Prom_atendidos': '{:.1f}'}), use_container_width=True, hide_index=True)
