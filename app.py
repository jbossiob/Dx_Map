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
    if 'Prom_atendidos' in df.columns:
        df['Prom_atendidos'] = df['Prom_atendidos'].astype(str).str.replace(',', '', regex=False)
        df['Prom_atendidos'] = pd.to_numeric(df['Prom_atendidos'], errors='coerce')
        
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
# (Se añadieron sector y categoria_inst)
if 'sector' not in st.session_state: st.session_state.sector = "Todos"
if 'categoria_inst' not in st.session_state: st.session_state.categoria_inst = "Todas"
if 'cat' not in st.session_state: st.session_state.cat = "Todas"
if 'prod' not in st.session_state: st.session_state.prod = "Todos"
if 'diag' not in st.session_state: st.session_state.diag = "Todos"
if 'dep' not in st.session_state: st.session_state.dep = "Todas"
if 'excluir_lima' not in st.session_state: st.session_state.excluir_lima = False

def limpiar_filtros():
    st.session_state.sector = "Todos"
    st.session_state.categoria_inst = "Todas"
    st.session_state.cat = "Todas"
    st.session_state.prod = "Todos"
    st.session_state.diag = "Todos"
    st.session_state.dep = "Todas"
    st.session_state.excluir_lima = False

# 3. FILTROS Y BOTONES DE CONTROL
st.markdown("### 🔍 Panel de Control")

col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    # BOTÓN DINÁMICO PARA LIMA Y CALLAO
    label_lima = "✅ Incluir Lima y Callao" if st.session_state.excluir_lima else "🚫 Excluir Lima y Callao"
    if st.button(label_lima, use_container_width=True):
        st.session_state.excluir_lima = not st.session_state.excluir_lima
        st.rerun()

with col_btn2:
    st.button("🔄 Limpiar Filtros", on_click=limpiar_filtros, use_container_width=True)

# LÓGICA DE FILTRADO EN CASCADA
# (Hemos agregado los pasos "0.1" y "0.2" para Sector y Categoría de institución)

# Nivel 0.1: Sector (Ej. MINSA, EsSalud, Privado)
lista_sectores = ["Todos"] + sorted(df['SECTOR'].dropna().unique().tolist())
sector_sel = st.selectbox("Sector:", lista_sectores, key='sector')
df_sec = df[df['SECTOR'] == sector_sel] if sector_sel != "Todos" else df.copy()

# Nivel 0.2: Categoría de IPRESS (Ej. III-1, II-2)
lista_categorias = ["Todas"] + sorted(df_sec['CATEGORIA'].dropna().unique().tolist())
cat_inst_sel = st.selectbox("Categoría IPRESS:", lista_categorias, key='categoria_inst')
df_cat = df_sec[df_sec['CATEGORIA'] == cat_inst_sel] if cat_inst_sel != "Todas" else df_sec

# Nivel 1: Cat. Terapéutica
lista_cat = ["Todas"] + sorted(df_cat['Cat_terapeutica'].dropna().unique().tolist())
cat_sel = st.selectbox("Cat. Terapéutica:", lista_cat, key='cat')
df_f1 = df_cat[df_cat['Cat_terapeutica'] == cat_sel] if cat_sel != "Todas" else df_cat.copy()

# Nivel 2: Producto
lista_productos = ["Todos"] + sorted(df_f1['Producto'].dropna().unique().tolist())
prod_sel = st.selectbox("Producto:", lista_productos, key='prod')
df_f2 = df_f1[df_f1['Producto'] == prod_sel] if prod_sel != "Todos" else df_f1

# Nivel 3: Diagnóstico
lista_diagnosticos = ["Todos"] + sorted(df_f2['Diagnóstico'].dropna().unique().tolist())
diag_sel = st.selectbox("Diagnóstico:", lista_diagnosticos, key='diag')
df_f3 = df_f2[df_f2['Diagnóstico'] == diag_sel] if diag_sel != "Todos" else df_f2

# APLICAR EXCLUSIÓN DE LIMA Y CALLAO
if st.session_state.excluir_lima:
    df_f3 = df_f3[~df_f3['DEPARTAMENTO_GEO'].isin(['LIMA', 'CALLAO'])]
    st.warning("⚠️ Lima y Callao han sido excluidos del análisis para resaltar las provincias.")

# Nivel 4: Departamento
deps_en_data = sorted(df_f3['DEPARTAMENTO_GEO'].dropna().unique().tolist())
dep_sel = st.selectbox("Región:", ["Todas"] + deps_en_data, key='dep')

if dep_sel != "Todas":
    df_final = df_f3[df_f3['DEPARTAMENTO_GEO'] == dep_sel]
    nivel_zoom = 5.0 
else:
    df_final = df_f3
    nivel_zoom = 3.5 

# 4. PREPARAR DATOS MAPA
df_mapa = df_final.groupby('DEPARTAMENTO_GEO', as_index=False)['Prom_atendidos'].sum()
df_mapa.rename(columns={'Prom_atendidos': 'Prom_Mensual'}, inplace=True)
df_mapa['Prom_Mensual'] = df_mapa['Prom_Mensual'].round(1)

# 5. DIBUJAR EL MAPA
st.markdown("---")
escala_roche = ["#E6EFFF", "#0B41CD"]

fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO_GEO',
    featureidkey='properties.NOMBDEP', 
    color='Prom_Mensual',
    color_continuous_scale=escala_roche, 
    mapbox_style="carto-positron",
    zoom=nivel_zoom, 
    center={"lat": -9.18, "lon": -75.01}, 
    opacity=0.8,
    labels={'Prom_Mensual': 'Promedio Mensual'}
)

fig.update_layout(
    margin={"r":0,"t":0,"l":0,"b":0},
    height=400, 
    coloraxis_colorbar=dict(title="Pac.", thickness=10)
)

st.plotly_chart(fig, use_container_width=True)

# 6. ANÁLISIS DE IPRESS
st.markdown("---")
st.markdown("**🏥 Análisis de Instituciones (IPRESS)**")

if not df_final.empty:
    cols_agrupar = ['DEPARTAMENTO_GEO', 'PROVINCIA', 'SECTOR', 'CATEGORIA', 'IPRESS', 'Diagnóstico']
    df_tabla = df_final.groupby(cols_agrupar, as_index=False)['Prom_atendidos'].sum()
    df_tabla.rename(columns={
        'DEPARTAMENTO_GEO': 'Departamento', 
        'PROVINCIA': 'Provincia',
        'SECTOR': 'Sector',
        'CATEGORIA': 'Categoría',
        'Prom_atendidos': 'Prom_Mensual'
    }, inplace=True)
    df_tabla = df_tabla.sort_values(by='Prom_Mensual', ascending=False)
    
    # 6.1 BLOQUES DESTACADOS
    st.markdown("🏆 **Top Clínicas / Hospitales (Promedio Mensual)**")
    top3 = df_tabla.head(3)
    
    cols = st.columns(len(top3) if len(top3) > 0 else 1)
    for i, (index, row) in enumerate(top3.iterrows()):
        with cols[i]:
            st.info(f"**{row['IPRESS']}**\n\n📌 {row['Sector']} - {row['Categoría']}\n\n🎯 Promedio: **{row['Prom_Mensual']:.1f}**")
            
    # 6.2 GRÁFICO DE BARRAS
    st.markdown("📊 **Ranking: Promedio de pacientes mensual**")
    df_top10 = df_tabla.head(10).sort_values(by='Prom_Mensual', ascending=True) 
    
    fig_bar = px.bar(
        df_top10, 
        x='Prom_Mensual', 
        y='IPRESS', 
        orientation='h',
        color='Prom_Mensual',
        color_continuous_scale=escala_roche,
        labels={'Prom_Mensual': 'Promedio de pacientes mensual', 'IPRESS': ''}
    )
    fig_bar.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        height=350,
        showlegend=False,
        coloraxis_showscale=False
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # 6.3 TABLA COMPLETA
    with st.expander("📋 Ver base de datos completa de IPRESS"):
        st.dataframe(
            df_tabla.style.format({'Prom_Mensual': '{:.1f}'}), 
            use_container_width=True, 
            hide_index=True
        )
else:
    st.info("No hay datos para esta combinación de filtros.")

# 7. PIE DE PÁGINA
st.markdown("---")
st.caption("Fuente: Datos Abiertos - SuSalud")
