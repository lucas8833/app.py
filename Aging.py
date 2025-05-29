import streamlit as st
import pandas as pd
import plotly.express as px
import base64

st.set_page_config(page_title="Dashboard de Aging - Garantia", layout="wide")

# ✅ Exibir logo na sidebar
def exibir_logo_sidebar(path_logo, largura=200):
    with open(path_logo, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.sidebar.markdown(
        f"""
        <div style="display: flex; justify-content: center;">
            <img src="data:image/png;base64,{encoded}" width="{largura}">
        </div>
        """,
        unsafe_allow_html=True
    )

exibir_logo_sidebar("logo_DFS.png")

# 🔗 Navegação
st.sidebar.title("📊 Navegação")
pagina = st.sidebar.radio("Escolha a página:", ["Controle Mensal", "Controle Anual"])

st.title("🔧 Dashboard de Aging - Garantia Técnica")

# 📂 Leitura do arquivo local
caminho_arquivo = "BASE_AGING_2025.xlsx"
try:
    df = pd.read_excel(caminho_arquivo)
except FileNotFoundError:
    st.error(f"Arquivo não encontrado em: {caminho_arquivo}")
    st.stop()

# 🔧 Limpeza dos nomes das colunas
df.columns = df.columns.str.strip()

# 🔍 Remover chamados ignorados
if 'Ignorar' in df.columns:
    df = df[df['Ignorar'].astype(str).str.strip().str.upper() != 'SIM']

# ✅ Aging baseado na coluna Aging1
df['Aging (dias)'] = df['Aging1']

# 📅 Processamento de datas
df['Data_Abertura'] = pd.to_datetime(df['Data'], errors='coerce')
df['Ano'] = df['Data_Abertura'].dt.year
df['Mês_Num'] = df['Data_Abertura'].dt.month
meses_dict = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
              5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
              9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
df['Mês'] = df['Mês_Num'].map(meses_dict)

# ✔️ Filtrar dados válidos
df = df.dropna(subset=['Data_Abertura', 'Aging (dias)', 'EC', 'Mantenedor'])

# 🔧 Sidebar - Filtros gerais
st.sidebar.subheader("Filtros gerais")
status_opcoes = df['Status'].dropna().unique().tolist()
status_selecionado = st.sidebar.multiselect("Status", status_opcoes, default=status_opcoes)

servico_opcoes = df['Serviço'].dropna().unique().tolist()
servico_selecionado = st.sidebar.multiselect("Serviço", servico_opcoes, default=servico_opcoes)

# 🔍 Aplicar filtros
df_filtrado = df[
    (df['Status'].isin(status_selecionado)) &
    (df['Serviço'].isin(servico_selecionado))
]

# 🗓️ Controle Mensal
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

        # 🔥 Aging por EC (com linha da meta)
        st.subheader("Aging por EC")
        ec_df = df_mensal.groupby('EC')['Aging (dias)'].mean().reset_index()

        fig_ec = px.bar(
            ec_df, x='EC', y='Aging (dias)',
            title="Aging por EC",
            text_auto=True
        )

        # ✔️ Linha da meta (2 dias)
        fig_ec.add_shape(
            type="line",
            x0=-0.5, x1=len(ec_df)-0.5,
            y0=2, y1=2,
            line=dict(color="red", width=2, dash="dash"),
            xref='x', yref='y'
        )

        st.plotly_chart(fig_ec, use_container_width=True)

        # 🔥 Tabela de Serviços Autorizados com Aging > 2 (incluindo EC)
        st.subheader("Serviços Autorizados com Aging > 2")

        sa_df = df_mensal.groupby(['Mantenedor', 'EC']).agg(
            Qtde_Chamados=('Aging (dias)', 'count'),
            Aging_Médio=('Aging (dias)', 'mean')
        ).reset_index()

        sa_acima2 = sa_df[sa_df['Aging_Médio'] > 2]

        if sa_acima2.empty:
            st.success("Nenhum SA com Aging acima de 2 dias!")
        else:
            st.dataframe(sa_acima2.sort_values(by='Aging_Médio', ascending=False))

# 📊 Controle Anual
elif pagina == "Controle Anual":
    st.subheader("📈 Aging Médio YTD")

    # 🔥 Cards do Aging YTD Geral
    aging_ytd_geral = df_filtrado.groupby(['Ano'])['Aging (dias)'].mean().reset_index()

    colunas = st.columns(len(aging_ytd_geral))

    for idx, row in aging_ytd_geral.iterrows():
        colunas[idx].metric(
            label=f"Ano {int(row['Ano'])}",
            value=f"{row['Aging (dias)']:.2f} dias"
        )

    # 🔥 Gráfico de Evolução Mensal (Geral)
    st.subheader("📆 Evolução Mensal do Aging Médio")

    media_mensal = df_filtrado.groupby(['Ano', 'Mês_Num'])['Aging (dias)'].mean().reset_index()
    media_mensal['Mês'] = media_mensal['Mês_Num'].map(meses_dict)

    fig_geral = px.line(media_mensal, x='Mês', y='Aging (dias)', color='Ano', markers=True,
                         title="Evolução Mensal do Aging Médio - Geral")

    # ✔️ Linha da Meta (2 dias)
    fig_geral.add_shape(
        type="line",
        x0=-0.5, x1=11.5,  # de Jan a Dez
        y0=2, y1=2,
        line=dict(color="red", width=2, dash="dash"),
        xref='x', yref='y'
    )

    fig_geral.update_layout(
        xaxis={'categoryorder': 'array', 'categoryarray': list(meses_dict.values())}
    )

    st.plotly_chart(fig_geral, use_container_width=True)

    # 🔥 Aging por EC - Evolução Mensal
    st.subheader("📆 Evolução Mensal do Aging por EC")

    ec_ano = df_filtrado.groupby(['Ano', 'Mês_Num', 'EC'])['Aging (dias)'].mean().reset_index()
    ec_ano['Mês'] = ec_ano['Mês_Num'].map(meses_dict)

    fig_ec_ano = px.line(ec_ano, x='Mês', y='Aging (dias)', color='EC', line_group='Ano', markers=True,
                          title="Evolução Mensal do Aging por EC")

    # ✔️ Linha da Meta
    fig_ec_ano.add_shape(
        type="line",
        x0=-0.5, x1=11.5,
        y0=2, y1=2,
        line=dict(color="red", width=2, dash="dash"),
        xref='x', yref='y'
    )

    fig_ec_ano.update_layout(
        xaxis={'categoryorder': 'array', 'categoryarray': list(meses_dict.values())}
    )

    st.plotly_chart(fig_ec_ano, use_container_width=True)

    # 🔥 Aging YTD por EC (Gráfico de Barras Horizontal)
    st.subheader("📊 Aging Médio YTD por EC")

    ec_ytd = df_filtrado.groupby('EC')['Aging (dias)'].mean().reset_index()

    fig = px.bar(
        ec_ytd,
        x='Aging (dias)',
        y='EC',
        orientation='h',
        title="Aging Médio YTD por EC",
        text_auto=True
    )

    # ✔️ Linha da Meta
    fig.add_shape(
        type="line",
        x0=2, x1=2,
        y0=-0.5, y1=len(ec_ytd)-0.5,
        line=dict(color="red", width=2, dash="dash"),
        xref='x', yref='y'
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # 🏆 Ranking SA Anual com EC responsável
    st.subheader("Ranking de Serviços Autorizados")

    ranking_sa = df_filtrado.groupby(['Ano', 'Mantenedor', 'EC']).agg(
        Qtde_Chamados=('Aging (dias)', 'count'),
        Aging_Médio=('Aging (dias)', 'mean')
    ).reset_index()

    ranking_sa = ranking_sa.sort_values(by=['Ano', 'Aging_Médio'], ascending=[True, False])

    st.dataframe(ranking_sa)

else:
    st.info("⬆️ Coloque o arquivo BASE_AGING_2025.xlsx na mesma pasta do app para iniciar.")






