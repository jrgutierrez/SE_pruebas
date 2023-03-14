import streamlit as st
import pandas as pd
import plotly.express as px

from google.oauth2 import service_account
from gsheetsdb import connect

st.set_page_config(layout="wide")

# Create a connection object.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
    ],
)
conn = connect(credentials=credentials)

# Perform SQL query on the Google Sheet.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
#@st.cache_data(ttl=600)
def run_query(query):
    data = conn.execute(query, headers=1)
    data = data.fetchall()
    return pd.DataFrame(data)


sheet_url = st.secrets["private_gsheets_url"]
data = run_query(f'SELECT * FROM "{sheet_url}"')

# Filtrar proveedores
data = data[data['Nombre_de_Grupo_de_Proveedor'] == 'Proveedores']
data = data[['Fecha_de_documento', 'Nombre_de_cliente_proveedor', 'Descripción_de_artículo_servicio', 'Precio']]
data = data[~data['Descripción_de_artículo_servicio'].str.startswith('TICKET')]
data = data[~data['Descripción_de_artículo_servicio'].str.startswith('MOBILIARIO')]
data = data.drop_duplicates().reset_index()

# Fecha a datetime
data['Fecha_de_documento'] =  pd.to_datetime(data['Fecha_de_documento'], format='%d/%m/%y')
# Precio a numerico
data['Precio'] = data['Precio'].str.replace('.', '').str.replace(',', '.').astype(float)

initial_date = st.sidebar.date_input(
    "Selecciona fecha inicio",
    min(data['Fecha_de_documento']))

final_date = st.sidebar.date_input(
    "Selecciona fecha fin",
    max(data['Fecha_de_documento']))



data = data[(data['Fecha_de_documento'] > str(initial_date)) & (data['Fecha_de_documento'] < str(final_date))]
top_5 = data.groupby(['Nombre_de_cliente_proveedor', 'Descripción_de_artículo_servicio'], as_index=False)\
            .agg({'Precio': lambda x: max(x) - min(x)})\
            .sort_values(by=['Precio'], ascending=False)\
            .head(5)\
            .drop(columns = 'Precio')

data = data[data['Nombre_de_cliente_proveedor'].isin(top_5['Nombre_de_cliente_proveedor']) & data['Descripción_de_artículo_servicio'].isin(top_5['Descripción_de_artículo_servicio'])]
data = data.sort_values('Fecha_de_documento')

fig = px.line(data, x = 'Fecha_de_documento', y = 'Precio', color = 'Descripción_de_artículo_servicio', markers = True)
fig.update_layout(legend=dict(
    yanchor="top",
    y=1.5,
    xanchor="left",
    x=0.01
))

st.plotly_chart(fig, use_container_width=True)