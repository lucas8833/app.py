import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Aging - Garantia", layout="wide")

st.sidebar.title("📊 Navegação")
pagina = st.sidebar.radio("Escolha a página:", ["Controle Mensal", "Controle Anual"])

st.title("🔧 Dashboard de Aging - Garantia Técnica")

# Leitura direta do arquivo local
caminho_arquivo = "BASE_AGING_2025.xlsx"
try:
    df = pd.read_excel(caminho_arquivo)
except FileNotFoundError:
    st.error(f"Arquivo não encontrado em: {caminho_arquivo}")
    st.stop()

# Limpeza dos nomes das colunas
df.columns = df.columns.str.strip()

# Remover chamados ignorados
if 'Ignorar' in df.columns:
    df = df[df['Ignorar'].astype(str).str.strip().str.upper() != 'SIM']

# Usa a coluna Aging1
df['Aging (dias)'] = df['Aging1']

# Processar datas
df['Data_Abertura'] = pd.to_datetime(df['Data'], errors='coerce')
df['Ano'] = df['Data_Abertura'].dt.year
df['Mês_Num'] = df['Data_Abertura'].dt.month
meses_dict = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
              5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
              9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
df['Mês'] = df['Mês_Num'].map(meses_dict)

# Filtros obrigatórios
df = df.dropna(subset=['Data_Abertura', 'Aging (dias)', 'EC', 'Mantenedor'])

# Sidebar: Filtros adicionais
st.sidebar.subheader("Filtros gerais")
status_opcoes = df['Status'].dropna().unique().tolist()
status_selecionado = st.sidebar.multiselect("Status", status_opcoes, default=status_opcoes)

servico_opcoes = df['Serviço'].dropna().unique().tolist()
servico_selecionado = st.sidebar.multiselect("Serviço", servico_opcoes, default=servico_opcoes)

df_filtrado = df[
    (df['Status'].isin(status_selecionado)) &
    (df['Serviço'].isin(servico_selecionado))
]

if pagina == "Controle Mensal":
    st.subheader("📅 Controle Mensal")
    ano = st.sidebar.selectbox("Ano:", sorted(df_filtrado['Ano'].unique()))
    mes = st.sidebar.selectbox("Mês:", sorted(df_filtrado['Mês_Num'].unique()))
    df_mensal = df_filtrado[(df_filtrado['Ano'] == ano) & (df_filtrado['Mês_Num'] == mes)]

    if df_mensal.empty:
        st.warning("Nenhum dado para o período selecionado.")
    else:
        col1, col2 = st.columns(2)
        col1.metric("Aging Médio", f"{df_mensal['Aging (dias)'].mean():.2f} dias")
        col2.metric("Maior Aging", f"{df_mensal['Aging (dias)'].max()} dias")

        st.subheader("Aging por EC")
        lider_df = df_mensal.groupby('EC')['Aging (dias)'].mean().reset_index()
        fig_lider = px.bar(lider_df, x='EC', y='Aging (dias)', title="Aging por EC", text_auto=True)
        st.plotly_chart(fig_lider, use_container_width=True)

        st.subheader("Serviços Autorizados com Aging > 2")
        sa_df = df_mensal.groupby('Mantenedor')['Aging (dias)'].mean().reset_index()
        sa_acima2 = sa_df[sa_df['Aging (dias)'] > 2]
        if sa_acima2.empty:
            st.success("Nenhum SA com Aging acima de 2 dias!")
        else:
            st.dataframe(sa_acima2.sort_values(by='Aging (dias)', ascending=False))
            fig_sa = px.bar(sa_acima2, x='Mantenedor', y='Aging (dias)', title='SA com Aging > 2 dias', text_auto=True)
            st.plotly_chart(fig_sa, use_container_width=True)

        st.subheader("Base detalhada")
        st.dataframe(df_mensal)

elif pagina == "Controle Anual":
    st.subheader("Evolução Anual do Aging")

    media_mensal = df_filtrado.groupby(['Ano', 'Mês_Num'])['Aging (dias)'].mean().reset_index()
    media_mensal['Mês'] = media_mensal['Mês_Num'].map(meses_dict)
    fig_geral = px.line(media_mensal, x='Mês', y='Aging (dias)', color='Ano', markers=True)
    st.plotly_chart(fig_geral, use_container_width=True)

    # Aging YTD Geral
    st.subheader("📈 Aging Médio YTD (Geral)")
    aging_ytd_geral = df_filtrado.groupby(['Ano'])['Aging (dias)'].mean().reset_index()
    st.dataframe(aging_ytd_geral)

    st.subheader("Aging por EC - Anual")
    lider_ano = df_filtrado.groupby(['Ano', 'Mês_Num', 'EC'])['Aging (dias)'].mean().reset_index()
    lider_ano['Mês'] = lider_ano['Mês_Num'].map(meses_dict)
    fig_lider = px.line(lider_ano, x='Mês', y='Aging (dias)', color='EC', line_group='Ano', markers=True)
    st.plotly_chart(fig_lider, use_container_width=True)

    # Aging YTD por EC
    st.subheader("📊 Aging Médio YTD por EC")
    ec_ytd = df_filtrado.groupby(['Ano', 'EC'])['Aging (dias)'].mean().reset_index()
    st.dataframe(ec_ytd.sort_values(by=['Ano', 'Aging (dias)'], ascending=[True, False]))

else:
    st.info("⬆️ Coloque o arquivo BASE_AGING_2025.xlsx na mesma pasta do app para iniciar.")




