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
    df = pd.read_csv("datos.csv")
    
    # --- CORRECCIÓN DE TIPO DE DATO ---
    # Forzamos a que Prom_atendidos sea número (quitando posibles comas de miles)
    if 'Prom_atendidos' in df.columns:
        df['Prom_atendidos'] = df['Prom_atendidos'].astype(str).str.replace(',', '', regex=False)
        df['Prom_atendidos'] = pd.to_numeric(df['Prom_atendidos'], errors='coerce')
        
    # Limpieza profunda de nombres geográficos
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
if 'cat' not in st.session_state: st.session_state.cat = "Todas"
if 'prod' not in st.session_state: st.session_state.prod = "Todos"
if 'diag' not in st.session_state: st.session_state.diag = "Todos"
if 'dep' not in st.session_state: st.session_state.dep = "Todas"

def limpiar_filtros():
    st.session_state.cat = "Todas"
    st.session_state.prod = "Todos"
    st.session_state.diag = "Todos"
    st.session_state.dep = "Todas"

# 3. FILTROS EN CASCADA (Pantalla Principal)
col1, col2 = st.columns([0.7, 0.3])
with col1:
    st.markdown("### 🔍 Filtros")
with col2:
    st.button("🔄 Limpiar", on_click=limpiar_filtros, use_container_width=True)

# Nivel 1: Categoría Terapéutica
lista_cat = ["Todas"] + sorted(df['Cat_terapeutica'].dropna().unique().tolist())
cat_sel = st.selectbox("Cat. Terapéutica:", lista_cat, key='cat')
df_f1 = df[df['Cat_terapeutica'] == cat_sel] if cat_sel != "Todas" else df.copy()

# Nivel 2: Producto (Depende de Categoría)
lista_productos = ["Todos"] + sorted(df_f1['Producto'].dropna().unique().tolist())
prod_sel = st.selectbox("Producto:", lista_productos, key='prod')
df_f2 = df_f1[df_f1['Producto'] == prod_sel] if prod_sel != "Todos" else df_f1

# Nivel 3: Diagnóstico (Depende de Producto y Categoría)
lista_diagnosticos = ["Todos"] + sorted(df_f2['Diagnóstico'].dropna().unique().tolist())
diag_sel = st.selectbox("Diagnóstico:", lista_diagnosticos, key='diag')
df_f3 = df_f2[df_f2['Diagnóstico'] == diag_sel] if diag_sel != "Todos" else df_f2

# Nivel 4: Departamento (Depende de todo lo anterior)
deps_en_data = sorted(df_f3['DEPARTAMENTO_GEO'].dropna().unique().tolist())
dep_sel = st.selectbox("Región (Filtra mapa y tabla):", ["Todas"] + deps_en_data, key='dep')

if dep_sel != "Todas":
    df_final = df_f3[df_f3['DEPARTAMENTO_GEO'] == dep_sel]
    nivel_zoom = 5.0 
else:
    df_final = df_f3
    nivel_zoom = 3.5 

# 4. PREPARAR DATOS MAPA (SUMA TOTAL DEL PERIODO)
df_mapa = df_final.groupby('DEPARTAMENTO_GEO', as_index=False)['Prom_atendidos'].sum()
# Renombramos la columna para que tenga sentido visualmente
df_mapa.rename(columns={'Prom_atendidos': 'Total_Atendidos'}, inplace=True)
df_mapa['Total_Atendidos'] = df_mapa['Total_Atendidos'].round(0)

# 5. DIBUJAR EL MAPA DE COROPLETAS
st.markdown("---")
escala_roche = ["#E6EFFF", "#0B41CD"]

fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO_GEO',
    featureidkey='properties.NOMBDEP', 
    color='Total_Atendidos',
    color_continuous_scale=escala_roche, 
    mapbox_style="carto-positron",
    zoom=nivel_zoom, 
    center={"lat": -9.18, "lon": -75.01}, 
    opacity=0.8,
    labels={'Total_Atendidos': 'Volumen Total'}
)

fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    height=400, 
    coloraxis_colorbar=dict(title="Total", thickness=10)
)

st.plotly_chart(fig, use_container_width=True)

# 6. ANÁLISIS DE IPRESS (SUMA TOTAL DEL PERIODO)
st.markdown("---")
st.markdown("**🏥 Análisis de Instituciones (IPRESS)**")

if not df_final.empty:
    cols_agrupar = ['DEPARTAMENTO_GEO', 'PROVINCIA', 'IPRESS', 'Diagnóstico']
    # Aquí está la corrección principal: usamos .sum()
    df_tabla = df_final.groupby(cols_agrupar, as_index=False)['Prom_atendidos'].sum()
    
    # Renombramos columnas para la vista final
    df_tabla.rename(columns={
        'DEPARTAMENTO_GEO': 'Departamento', 
        'PROVINCIA': 'Provincia',
        'Prom_atendidos': 'Total_Atendidos'
    }, inplace=True)
    
    df_tabla = df_tabla.sort_values(by='Total_Atendidos', ascending=False)
    
    # 6.1 BLOQUES DESTACADOS (TOP 3)
    st.markdown("🏆 **Top Clínicas / Hospitales (Volumen Anual)**")
    top3 = df_tabla.head(3)
    
    cols = st.columns(len(top3) if len(top3) > 0 else 1)
    for i, (index, row) in enumerate(top3.iterrows()):
        with cols[i]:
            st.info(f"**{row['IPRESS']}**\n\n🎯 Total Pacientes: **{int(row['Total_Atendidos'])}**")
            
    # 6.2 GRÁFICO DE BARRAS (TOP 10)
    st.markdown("📊 **Ranking de Mayor Demanda**")
    df_top10 = df_tabla.head(10).sort_values(by='Total_Atendidos', ascending=True) 
    
    fig_bar = px.bar(
        df_top10, 
        x='Total_Atendidos', 
        y='IPRESS', 
        orientation='h',
        color='Total_Atendidos',
        color_continuous_scale=escala_roche,
        labels={'Total_Atendidos': 'Total Pacientes', 'IPRESS': ''}
    )
    fig_bar.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        height=350,
        showlegend=False,
        coloraxis_showscale=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # 6.3 LA TABLA COMPLETA (OCULTA EN UN ACORDEÓN)
    with st.expander("📋 Ver base de datos completa de IPRESS"):
        # Mostramos los números enteros sin decimales porque son personas reales
        st.dataframe(
            df_tabla.style.format({'Total_Atendidos': '{:,.0f}'}), 
            use_container_width=True, 
            hide_index=True
        )
else:
    st.info("No hay datos para esta combinación de filtros.")

# 7. PIE DE PÁGINA
st.markdown("---")
st.caption("Fuente: Datos Abiertos - SuSalud")
