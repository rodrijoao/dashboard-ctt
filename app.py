import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página para formato profissional
st.set_page_config(page_title="Dashboard CTT - B. Braun", layout="wide", page_icon="📦")

st.title("📦 Dashboard de Controlo de Envios CTT - B. Braun")
st.markdown("---")

# ==============================================================================
# 🔗 CONFIGURAÇÃO DIRETA DO LINK DO GOOGLE SHEETS
# ==============================================================================
# Este link já aponta diretamente para a exportação limpa do teu ficheiro da Drive
LINK_DIRETO_GOOGLE = https://docs.google.com/spreadsheets/d/e/2PACX-1vR84h1yg_J4CmyKkZ49XCC7rG4NJhSdnLUotwoWKpU4Ebpq2D2QN0ptsxOOUnHy375RykhNP2bD-2DP/pub?output=csv

@st.cache_data(ttl=10) # Atualiza quase em tempo real
def load_data(url):
    try:
        # Pula as 12 linhas institucionais e lê os dados reais
        df = pd.read_csv(url, skiprows=12)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro técnico ao aceder ao Google Sheets: {e}")
        return None

df_raw = load_data(LINK_DIRETO_GOOGLE)

if df_raw is not None and 'Objeto' in df_raw.columns:
    # Limpeza de linhas em branco do final do relatório
    df = df_raw.dropna(subset=['Objeto']).copy()
    
    # 1. PROCESSAMENTO INTELIGENTE DE ESTADOS (SIGLAS CTT)
    df['Situação_Clean'] = df['Situação do Objeto'].astype(str).str.strip().str.upper()
    
    # Classificação exata com base no padrão CTT
    entregues_mask = df['Situação_Clean'].str.startswith('EMI') | df['Situação_Clean'].str.contains('ENTREGUE')
    em_transito_mask = df['Situação_Clean'].str.startswith('EMF') | df['Situação_Clean'].str.contains('TRÂN') | df['Situação_Clean'].str.contains('DISTRIB')
    
    df_entregues = df[entregues_mask]
    df_transito = df[em_transito_mask]
    df_incidencias = df[~(entregues_mask | em_transito_mask)]
    
    total_envios = len(df)
    qtd_entregues = len(df_entregues)
    qtd_transito = len(df_transito)
    qtd_incidencias = len(df_incidencias)

    # 2. CÁLCULO DE TENTATIVAS DE ENTREGA (LÓGICA DE DATAS CTT)
    entregues_1a = 0
    entregues_2a = 0
    
    if qtd_entregues > 0:
        def verificar_tentativa(row):
            try:
                d1 = str(row['Data 1º Evento']).split()[0]
                d2 = str(row['Data último evento']).split()[0]
                return 1 if d1 == d2 else 2
            except:
                return 1
                
        df_entregues_calc = df_entregues.copy()
        df_entregues_calc['Tentativas'] = df_entregues_calc.apply(verificar_tentativa, axis=1)
        entregues_1a = len(df_entregues_calc[df_entregues_calc['Tentativas'] == 1])
        entregues_2a = len(df_entregues_calc[df_entregues_calc['Tentativas'] == 2])

    # 3. PAINEL DE MÉTRICAS (KPIs VISUAIS)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric(label="📦 Total de Envios", value=f"{total_envios:,}")
    with kpi2:
        perc_ent = (qtd_entregues / max(total_envios, 1)) * 100
        st.metric(label="✅ Total Entregues", value=f"{qtd_entregues:,}", delta=f"{perc_ent:.1f}% do volume")
    with kpi3:
        perc_tra = (qtd_transito / max(total_envios, 1)) * 100
        st.metric(label="⏳ Em Trânsito / Pendentes", value=f"{qtd_transito:,}", delta=f"{perc_tra:.1f}%", delta_color="normal")
    with kpi4:
        perc_inc = (qtd_incidencias / max(total_envios, 1)) * 100
        st.metric(label="⚠️ Incidências / Alertas", value=f"{qtd_incidencias:,}", delta=f"{perc_inc:.1f}%", delta_color="inverse")

    st.markdown("---")

    # 4. ÁREA DOS GRÁFICOS INTERATIVOS
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("🎯 Eficácia Operacional (Tentativas)")
        dados_tentativas = pd.DataFrame({
            'Desempenho': ['À 1ª Tentativa', 'À 2ª Tentativa ou Mais'],
            'Encomendas': [entregues_1a, entregues_2a]
        })
        fig_bar = px.bar(dados_tentativas, x='Desempenho', y='Encomendas', text='Encomendas',
                         color='Desempenho', color_discrete_sequence=['#2ecc71', '#e67e22'])
        fig_bar.update_traces(textposition='inside', textfont_size=14)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_graf2:
        st.subheader("🔄 Repartição por Situação CTT")
        fig_pie = px.pie(df, names='Situação do Objeto', 
                         color_discrete_sequence=px.colors.qualitative.Bold,
                         hole=0.4)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    # 5. TABELA DE PESQUISA AVANÇADA
    st.markdown("---")
    st.subheader("🔍 Filtro e Consulta de Objetos")
    
    estados_unicos = ["Todos"] + list(df['Situação do Objeto'].unique())
    filtro = st.selectbox("Escolha uma situação para isolar os dados:", estados_unicos)
    
    df_filtrado = df if filtro == "Todos" else df[df['Situação do Objeto'] == filtro]
    
    colunas_comerciais = ['Objeto', 'Refª Cliente', 'Situação do Objeto', 'Data 1º Evento', 'Data último evento', 'Nome do Destinatário', 'Código Postal']
    st.dataframe(df_filtrado[colunas_comerciais], use_container_width=True, hide_index=True)

else:
    st.error("❌ Link ou permissões do Google Sheets inválidos.")
    st.info("Por favor, garanta que no Google Sheets clicou em 'Partilhar' e mudou para 'Qualquer pessoa com o link'.")
