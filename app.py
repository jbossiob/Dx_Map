import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# 1. CONFIGURACIÓN MOBILE-FIRST
st.set_page_config(page_title="Roche BI", layout="centered")

# Nuevo título
st.title("📊 Demanda según diagnósticos - Perú")

# 2. CARGAR DATOS
@st.cache_data
def load_data():
    df = pd.read_csv("datos.csv")
    
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

# 3. FILTROS EN PANTALLA PRINCIPAL
st.markdown("### 🔍 Filtros")

# Filtro 1: Diagnóstico (Obligatorio)
lista_diagnosticos = df['Diagnóstico'].dropna().unique().tolist()
diag_sel = st.selectbox("Diagnóstico:", lista_diagnosticos)

df_filtrado = df[df['Diagnóstico'] == diag_sel]

# Filtro 2: Producto
lista_productos = ["Todos"] + sorted(df_filtrado['Producto'].dropna().unique().tolist())
prod_sel = st.selectbox("Producto:", lista_productos)
if prod_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado['Producto'] == prod_sel]

# Filtro 3: Categoría Terapéutica
lista_cat = ["Todas"] + sorted(df_filtrado['Cat_terapeutica'].dropna().unique().tolist())
cat_sel = st.selectbox("Cat. Terapéutica:", lista_cat)
if cat_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Cat_terapeutica'] == cat_sel]

# Filtro 4: Departamento (Controlador del Zoom y la Tabla)
deps_en_data = sorted(df_filtrado['DEPARTAMENTO_GEO'].unique().tolist())
dep_sel = st.selectbox("Región (Filtra mapa y tabla):", ["Todas"] + deps_en_data)

# Aplicar el filtro de departamento a los datos finales
if dep_sel != "Todas":
    df_final = df_filtrado[df_filtrado['DEPARTAMENTO_GEO'] == dep_sel]
    nivel_zoom = 5.0  # Zoom más cercano si hay un departamento seleccionado
else:
    df_final = df_filtrado
    nivel_zoom = 3.5  # Zoom general de todo el Perú

# 4. PREPARAR DATOS MAPA
df_mapa = df_final.groupby('DEPARTAMENTO_GEO', as_index=False)['Prom_atendidos'].mean()
df_mapa['Prom_atendidos'] = df_mapa['Prom_atendidos'].round(1)

# 5. DIBUJAR EL MAPA DE COROPLETAS
st.markdown("---")

# Escala de colores personalizada (Blanco azulado -> Azul Roche -> Azul Oscuro)
escala_roche = ["#E6EFFF", "#0B41CD"]

fig = px.choropleth_mapbox(
    df_mapa,
    geojson=peru_geo,
    locations='DEPARTAMENTO_GEO',
    featureidkey='properties.NOMBDEP', 
    color='Prom_atendidos',
    color_continuous_scale=escala_roche, 
    mapbox_style="carto-positron",
    zoom=nivel_zoom, # Aquí aplicamos el zoom dinámico
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

# Mostramos la tabla si hay datos
if not df_final.empty:
    cols_ver = ['PROVINCIA', 'Producto', 'Cat_terapeutica', 'Prom_atendidos']
    df_tabla = df_final[cols_ver].sort_values(by='Prom_atendidos', ascending=False)
    
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
