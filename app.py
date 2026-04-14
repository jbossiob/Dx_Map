import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. CONFIGURACIÓN MOBILE-FIRST
st.set_page_config(page_title="Roche BI", layout="centered")

st.title("📊 BI Roche - Panorama")

# 2. CARGAR DATOS
@st.cache_data
def load_data():
    df = pd.read_csv("datos.csv")
    
    # --- LIMPIEZA PROFUNDA DE NOMBRES ---
    # Pasamos a mayúsculas, quitamos ", PERU" y borramos espacios fantasmas
    if 'DEPARTAMENTO' in df.columns:
        df['DEPARTAMENTO_GEO'] = df['DEPARTAMENTO'].astype(str).str.upper()
        df['DEPARTAMENTO_GEO'] = df['DEPARTAMENTO_GEO'].str.replace(', PERU', '', regex=False).str.strip()
        
        # Correcciones específicas de tildes que suelen fallar en GeoJSON
        dic_acentos = {'ÁN': 'AN', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'JUNÍN': 'JUNIN'}
        for con, sin in dic_acentos.items():
            df['DEPARTAMENTO_GEO'] = df['DEPARTAMENTO_GEO'].str.replace(con, sin)
            
    return df

@st.cache_data
def load_geojson():
    # GeoJSON estándar de departamentos de Perú
    url_geo = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_departamental_simple.geojson"
    return requests.get(url_geo).json()

df = load_data()
peru_geo = load_geojson()

# 3. FILTROS EN PANTALLA PRINCIPAL
st.markdown("### 🔍 Selección de Diagnóstico")
lista_diagnosticos = df['Diagnóstico'].dropna().unique().tolist()
diag_sel = st.selectbox("Busque o seleccione:", lista_diagnosticos)

# Filtrar datos
df_filtrado = df[df['Diagnóstico'] == diag_sel]

# 4. PREPARAR DATOS MAPA (Agrupamos Provincias -> Departamento)
df_mapa = df_filtrado.groupby('DEPARTAMENTO_GEO', as_index=False)['Prom_atendidos'].mean()
df_mapa['Prom_atendidos'] = df_mapa['Prom_atendidos'].round(1)

# 5. DIBUJAR EL MAPA DE COROPLETAS
st.markdown("---")
st.markdown(f"**📍 Promedio Regional: {diag_sel}**")

# IMPORTANTE: featureidkey='properties.NOMBDEP' debe coincidir con el nombre en mayúsculas
fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO_GEO',
    featureidkey='properties.NOMBDEP', 
    color='Prom_atendidos',
    color_continuous_scale="Reds", 
    mapbox_style="carto-positron",
    zoom=3.5, 
    center={"lat": -9.18, "lon": -75.01}, 
    opacity=0.8,
    labels={'Prom_atendidos': 'Promedio'}
)

fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    height=400, 
    coloraxis_colorbar=dict(title="Prom", thickness=10)
)

st.plotly_chart(fig, use_container_width=True)

# 6. TABLA DE DETALLE (PROVINCIAS)
st.markdown("---")
st.markdown("**🏥 Detalle por Provincia**")

# Seleccionamos un departamento para ver sus provincias
deps_en_data = sorted(df_filtrado['DEPARTAMENTO_GEO'].unique().tolist())
dep_sel = st.selectbox("Toque una región para ver detalle:", ["Ver todas"] + deps_en_data)

if dep_sel != "Ver todas":
    df_tabla = df_filtrado[df_filtrado['DEPARTAMENTO_GEO'] == dep_sel]
else:
    df_tabla = df_filtrado

# Mostramos Provincias y Productos
cols_ver = ['PROVINCIA', 'Producto', 'Cat_terapeutica', 'Prom_atendidos']
df_tabla = df_tabla[cols_ver].sort_values(by='Prom_atendidos', ascending=False)

st.dataframe(
    df_tabla.style.format({'Prom_atendidos': '{:.1f}'}), 
    use_container_width=True, 
    hide_index=True
)
