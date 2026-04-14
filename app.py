import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. CONFIGURACIÓN MOBILE-FIRST
st.set_page_config(page_title="Roche BI", layout="centered")

st.title("📊 Demanda según diagnósticos - Perú")

# 2. CARGAR DATOS
@st.cache_data
def load_data():
    # Lee el archivo datos.csv que ahora incluye la columna IPRESS
    df = pd.read_csv("datos.csv")
    
    # Limpieza profunda de nombres geográficos para el match con el GeoJSON
    if 'DEPARTAMENTO' in df.columns:
        df['DEPARTAMENTO_GEO'] = df['DEPARTAMENTO'].astype(str).str.upper()
        df['DEPARTAMENTO_GEO'] = df['DEPARTAMENTO_GEO'].str.replace(', PERU', '', regex=False).str.strip()
        
        dic_acentos = {'ÁN': 'AN', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'JUNÍN': 'JUNIN'}
        for con, sin in dic_acentos.items():
            df['DEPARTAMENTO_GEO'] = df['DEPARTAMENTO_GEO'].str.replace(con, sin)
            
    return df

@st.cache_data
def load_geojson():
    url_geo = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_departamental_simple.geojson"
    return requests.get(url_geo).json()

df = load_data()
peru_geo = load_geojson()

# --- INICIALIZAR MEMORIA DE FILTROS ---
if 'diag' not in st.session_state: st.session_state.diag = "Todos"
if 'prod' not in st.session_state: st.session_state.prod = "Todos"
if 'cat' not in st.session_state: st.session_state.cat = "Todas"
if 'dep' not in st.session_state: st.session_state.dep = "Todas"

def limpiar_filtros():
    st.session_state.diag = "Todos"
    st.session_state.prod = "Todos"
    st.session_state.cat = "Todas"
    st.session_state.dep = "Todas"

# 3. FILTROS EN PANTALLA PRINCIPAL
col1, col2 = st.columns([0.7, 0.3])
with col1:
    st.markdown("### 🔍 Filtros")
with col2:
    st.button("🔄 Limpiar", on_click=limpiar_filtros, use_container_width=True)

# Filtro 1: Diagnóstico
lista_diagnosticos = ["Todos"] + sorted(df['Diagnóstico'].dropna().unique().tolist())
diag_sel = st.selectbox("Diagnóstico:", lista_diagnosticos, key='diag')

if diag_sel != "Todos":
    df_filtrado = df[df['Diagnóstico'] == diag_sel]
else:
    df_filtrado = df.copy()

# Filtro 2: Producto
lista_productos = ["Todos"] + sorted(df_filtrado['Producto'].dropna().unique().tolist())
prod_sel = st.selectbox("Producto:", lista_productos, key='prod')
if prod_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Producto'] == prod_sel]

# Filtro 3: Categoría Terapéutica
lista_cat = ["Todas"] + sorted(df_filtrado['Cat_terapeutica'].dropna().unique().tolist())
cat_sel = st.selectbox("Cat. Terapéutica:", lista_cat, key='cat')
if cat_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Cat_terapeutica'] == cat_sel]

# Filtro 4: Departamento (Controlador del Zoom y Filtro de Tabla)
deps_en_data = sorted(df_filtrado['DEPARTAMENTO_GEO'].unique().tolist())
dep_sel = st.selectbox("Región (Filtra mapa y tabla):", ["Todas"] + deps_en_data, key='dep')

# Aplicar el filtro de departamento a los datos finales
if dep_sel != "Todas":
    df_final = df_filtrado[df_filtrado['DEPARTAMENTO_GEO'] == dep_sel]
    nivel_zoom = 5.0 
else:
    df_final = df_filtrado
    nivel_zoom = 3.5 

# 4. PREPARAR DATOS MAPA (PROMEDIO POR DEPARTAMENTO)
df_mapa = df_final.groupby('DEPARTAMENTO_GEO', as_index=False)['Prom_atendidos'].mean()
df_mapa['Prom_atendidos'] = df_mapa['Prom_atendidos'].round(1)

# 5. DIBUJAR EL MAPA DE COROPLETAS
st.markdown("---")
escala_roche = ["#E6EFFF", "#0B41CD"]

fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO_GEO',
    featureidkey='properties.NOMBDEP', 
    color='Prom_atendidos',
    color_continuous_scale=escala_roche, 
    mapbox_style="carto-positron",
    zoom=nivel_zoom, 
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

# 6. TABLA DE DETALLE POR IPRESS (GRANULARIDAD MÁXIMA)
st.markdown("---")
st.markdown("**🏥 Detalle de Atención por IPRESS**")

if not df_final.empty:
    # Agrupamos para asegurar que 'Prom_atendidos' sea el promedio si hay filas repetidas
    # Columnas solicitadas: Departamento | Provincia | IPRESS | Diagnóstico | Prom_atendidos
    cols_agrupar = ['DEPARTAMENTO_GEO', 'PROVINCIA', 'IPRESS', 'Diagnóstico']
    
    df_tabla = df_final.groupby(cols_agrupar, as_index=False)['Prom_atendidos'].mean()
    df_tabla = df_tabla.sort_values(by='Prom_atendidos', ascending=False)
    
    # Renombrar para que se vea estético en la tabla
    df_tabla.columns = ['Departamento', 'Provincia', 'IPRESS', 'Diagnóstico', 'Prom_atendidos']
    
    st.dataframe(
        df_tabla.style.format({'Prom_atendidos': '{:.1f}'}), 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("No hay datos para esta combinación de filtros.")

# 7. PIE DE PÁGINA
st.markdown("---")
st.caption("Fuente: Datos Abiertos - SuSalud")
