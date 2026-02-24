import streamlit as st
import pandas as pd
import plotly.express as px
import base64

# ---------------------------
# CONFIGURAÇÕES INICIAIS
# ---------------------------
st.set_page_config(page_title="Dashboard de Aging - Garantia", layout="wide")

def exibir_logo_sidebar(path_logo, largura=200):
    try:
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
    except FileNotFoundError:
        st.sidebar.warning("⚠️ Logo não encontrada (logo_DFS.png).")

exibir_logo_sidebar("logo_DFS.png")

# ---------------------------
# LEITURA E PREPARO DOS DADOS
# ---------------------------
st.title("🔧 Dashboard de Aging - Garantia Técnica")

caminho_arquivo = "BASE_AGING_2026.xlsx"
try:
    df = pd.read_excel(caminho_arquivo)
except FileNotFoundError:
    st.error(f"Arquivo não encontrado em: {caminho_arquivo}")
    st.stop()

df.columns = df.columns.str.strip()

# Remover chamados ignorados
if 'Ignorar' in df.columns:
    df = df[df['Ignorar'].astype(str).str.strip().str.upper() != 'SIM']

# Aging baseado na coluna Aging1
df['Aging (dias)'] = df['Aging1']

# Processamento de datas
df['Data_Abertura'] = pd.to_datetime(df['Data'], errors='coerce')
df['Ano'] = df['Data_Abertura'].dt.year
df['Mês_Num'] = df['Data_Abertura'].dt.month
meses_dict = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
              5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
              9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
df['Mês'] = df['Mês_Num'].map(meses_dict)

# Limpeza de espaços e exclusão de vazios em EC e Mantenedor
df['EC'] = df['EC'].astype(str).str.strip()
df['Mantenedor'] = df['Mantenedor'].astype(str).str.strip()
df = df[(df['EC'] != "") & (df['Mantenedor'] != "")]
df = df.dropna(subset=['Data_Abertura', 'Aging (dias)'])

# ---------------------------
# SIDEBAR - FILTROS
# ---------------------------
st.sidebar.title("📊 Filtros gerais")

anos_disponiveis = sorted(df['Ano'].dropna().unique())
ano_selecionado = st.sidebar.selectbox("Ano:", anos_disponiveis, index=len(anos_disponiveis)-1)

meses_disponiveis = sorted(df[df['Ano'] == ano_selecionado]['Mês_Num'].dropna().unique())
mes_selecionado = st.sidebar.selectbox("Mês:", meses_disponiveis)

status_opcoes = df['Status'].dropna().unique().tolist()
status_selecionado = st.sidebar.multiselect("Status", status_opcoes, default=status_opcoes)

servico_opcoes = df['Serviço'].dropna().unique().tolist()
servico_selecionado = st.sidebar.multiselect("Serviço", servico_opcoes, default=servico_opcoes)

# Aplicar filtros
df_filtrado = df[
    (df['Ano'] == ano_selecionado) &
    (df['Mês_Num'] == mes_selecionado) &
    (df['Status'].isin(status_selecionado)) &
    (df['Serviço'].isin(servico_selecionado))
]

# Botão de download
st.sidebar.markdown("### 📥 Exportar Dados")
csv_full = df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="📄 Baixar planilha completa",
    data=csv_full,
    file_name='aging_completo.csv',
    mime='text/csv'
)

# ---------------------------
# TABS PRINCIPAIS (3)
# ---------------------------
aba1, aba2, aba3 = st.tabs([
    "📈 Controle Anual",
    "📅 Controle Mensal",
    "🔍 Análise Detalhada"
])

# =========================================================
# 📈 CONTROLE ANUAL (YTD)
# =========================================================
with aba1:
    st.subheader(f"📈 Controle Anual - {ano_selecionado}")

    df_ano = df[df['Ano'] == ano_selecionado]

    if df_ano.empty:
        st.warning("Nenhum dado disponível para o ano selecionado.")
    else:
        # Aging médio geral do ano
        aging_geral = df_ano['Aging (dias)'].mean()
        st.metric("Aging Médio YTD", f"{aging_geral:.1f} dias")

        # Evolução mensal
        media_mensal = df_ano.groupby('Mês_Num')['Aging (dias)'].mean().reset_index()
        media_mensal['Mês'] = media_mensal['Mês_Num'].map(meses_dict)

        fig_geral = px.line(
            media_mensal, x='Mês', y='Aging (dias)', markers=True,
            title="Evolução Mensal do Aging Médio"
        )
        fig_geral.update_traces(texttemplate='%{y:.1f}', textposition='top center')
        fig_geral.add_shape(type="line", x0=-0.5, x1=11.5, y0=2, y1=2,
                            line=dict(color="red", width=2, dash="dash"))
        st.plotly_chart(fig_geral, use_container_width=True)

        # Aging médio YTD por EC
        ec_ytd = df_ano.groupby('EC')['Aging (dias)'].mean().reset_index()
        fig_ec_ytd = px.bar(
            ec_ytd, x='Aging (dias)', y='EC', orientation='h', text_auto='.1f',
            title="Aging Médio YTD por EC"
        )
        fig_ec_ytd.add_shape(type="line", x0=2, x1=2, y0=-0.5, y1=len(ec_ytd)-0.5,
                             line=dict(color="red", width=2, dash="dash"))
        st.plotly_chart(fig_ec_ytd, use_container_width=True)

        # 🔹 Performance dos SAs (Anual)
        st.subheader("📊 Performance dos SAs - Anual")

        meta_aging = 2
        sa_perf = df_ano.groupby('Mantenedor')['Aging (dias)'].mean().reset_index()
        percentual_meta = (sa_perf['Aging (dias)'] <= meta_aging).mean() * 100
        st.metric("✅ % de SAs dentro da meta (≤ 2 dias)", f"{percentual_meta:.1f}%")

        ranking_df = df_ano.groupby('Mantenedor').agg(
            Qtde_Chamados=('Aging (dias)', 'count'),
            Aging_Médio=('Aging (dias)', 'mean')
        ).reset_index()
        ranking_df['Aging_Médio'] = ranking_df['Aging_Médio'].round(1)
        top10_melhores = ranking_df.sort_values(by='Aging_Médio').head(10)
        top10_piores = ranking_df.sort_values(by='Aging_Médio', ascending=False).head(10)

        col1, col2 = st.columns(2)
        col1.markdown("**🔹 Top 10 Melhores (Aging baixo)**")
        col1.dataframe(top10_melhores, use_container_width=True)

        col2.markdown("**🔸 Top 10 Piores (Aging alto)**")
        col2.dataframe(top10_piores, use_container_width=True)

# =========================================================
# 📅 CONTROLE MENSAL
# =========================================================
with aba2:
    st.subheader(f"📅 Controle Mensal - {meses_dict[mes_selecionado]} / {ano_selecionado}")

    if df_filtrado.empty:
        st.warning("Nenhum dado para o período selecionado.")
    else:
        col1, col2 = st.columns(2)
        col1.metric("Aging Médio", f"{df_filtrado['Aging (dias)'].mean():.1f} dias")
        col2.metric("Maior Aging", f"{df_filtrado['Aging (dias)'].max():.1f} dias")

        # 🔹 Aging por EC
        st.subheader("Aging por EC")
        ec_df = df_filtrado.groupby('EC')['Aging (dias)'].mean().reset_index()
        fig_ec = px.bar(ec_df, x='EC', y='Aging (dias)', text_auto='.1f', title="Aging por EC")
        fig_ec.add_shape(type="line", x0=-0.5, x1=len(ec_df)-0.5, y0=2, y1=2,
                         line=dict(color="red", width=2, dash="dash"))
        st.plotly_chart(fig_ec, use_container_width=True)

        # 🔹 Performance dos SAs (Mensal)
        st.subheader("📊 Performance dos SAs - Mensal")

        meta_aging = 2
        sa_perf = df_filtrado.groupby('Mantenedor')['Aging (dias)'].mean().reset_index()
        percentual_meta = (sa_perf['Aging (dias)'] <= meta_aging).mean() * 100
        st.metric("✅ % de SAs dentro da meta (≤ 2 dias)", f"{percentual_meta:.1f}%")

        ranking_df = df_filtrado.groupby('Mantenedor').agg(
            Qtde_Chamados=('Aging (dias)', 'count'),
            Aging_Médio=('Aging (dias)', 'mean')
        ).reset_index()
        ranking_df['Aging_Médio'] = ranking_df['Aging_Médio'].round(1)
        top10_melhores = ranking_df.sort_values(by='Aging_Médio').head(10)
        top10_piores = ranking_df.sort_values(by='Aging_Médio', ascending=False).head(10)

        col1, col2 = st.columns(2)
        col1.markdown("**🔹 Top 10 Melhores (Aging baixo)**")
        col1.dataframe(top10_melhores, use_container_width=True)

        col2.markdown("**🔸 Top 10 Piores (Aging alto)**")
        col2.dataframe(top10_piores, use_container_width=True)

# =========================================================
# 🔍 ANÁLISE DETALHADA
# =========================================================
with aba3:
    st.subheader("📈 Tendência Mensal do Aging por SA")

    sa_tendencia = df[df['Ano'] == ano_selecionado].groupby(['Mantenedor', 'Mês_Num'])['Aging (dias)'].mean().reset_index()
    sa_tendencia['Mês'] = sa_tendencia['Mês_Num'].map(meses_dict)
    sa_tendencia['Aging (dias)'] = sa_tendencia['Aging (dias)'].round(1)

    sa_selecionado = st.selectbox("Selecione um Serviço Autorizado:", sorted(sa_tendencia['Mantenedor'].unique()))
    df_sa = sa_tendencia[sa_tendencia['Mantenedor'] == sa_selecionado]

    if df_sa.empty:
        st.warning("Nenhum dado disponível para o SA selecionado.")
    else:
        fig_sa_tendencia = px.line(df_sa, x='Mês', y='Aging (dias)', markers=True,
                                   title=f"Tendência Mensal - {sa_selecionado}")
        fig_sa_tendencia.add_shape(type="line", x0=-0.5, x1=11.5, y0=2, y1=2,
                                   line=dict(color="red", width=2, dash="dash"))
        st.plotly_chart(fig_sa_tendencia, use_container_width=True)
        st.dataframe(df_sa, use_container_width=True)











