import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de Envios CTT", layout="wide")

st.title("📦 Dashboard de Controlo de Envios (Google Drive)")
st.markdown("""
Esta aplicação lê automaticamente os dados atualizados diretamente da sua Google Drive Premium.
Basta substituir o ficheiro na sua pasta partilhada para que os gráficos se atualizem!
""")

# Link direto para o CSV exportado da Google Drive (Substituir ID_DO_SEU_FICHEIRO)
# IMPORTANTE: O utilizador terá de colar o ID real do ficheiro dele aqui
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Nd9fxXR4CwlA-t7DJgPYaOfwbKcHekjGwzOxvofwwo0/edit?gid=1823527833#gid=1823527833"

@st.cache_data(ttl=300)  # Faz cache por 5 minutos para ser rápido, depois atualiza
def load_data(url):
    return pd.read_csv(url)

try:
    df = load_data(GOOGLE_SHEET_URL)
    st.success("✅ Dados carregados com sucesso a partir da Google Drive!")
    
    # Mapeamento dinâmico de colunas comuns para facilitar a vida ao utilizador
    colunas_disponiveis = [str(c).strip().lower() for c in df.columns]
    
    # Tenta adivinhar a coluna de Estado
    col_estado = df.columns[0]
    for c in df.columns:
        if 'est' in str(c).lower() or 'sit' in str(c).lower() or 'status' in str(c).lower():
            col_estado = c
            break
            
    # Tenta adivinhar a coluna de Tentativas
    col_tentativas = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    for c in df.columns:
        if 'tent' in str(c).lower() or 'num' in str(c).lower() or 'vez' in str(c).lower():
            col_tentativas = c
            break

    # Seletor caso a app falhe a adivinhar
    st.sidebar.header("⚙️ Configurações de Colunas")
    col_estado_selecionada = st.sidebar.selectbox("Coluna de Estado/Situação:", df.columns, index=list(df.columns).index(col_estado))
    col_tentativas_selecionada = st.sidebar.selectbox("Coluna de Tentativas:", df.columns, index=list(df.columns).index(col_tentativas))

    # --- PROCESSAMENTO ---
    total_envios = len(df)
    
    # Tratamento de dados para evitar erros de texto
    df['estado_clean'] = df[col_estado_selecionada].astype(str).str.strip().str.lower()
    
    # Contagens Inteligentes baseadas em termos comuns
    entregues_df = df[df['estado_clean'].str.contains('entreg|conclu|sucess|ok', na=False)]
    pendentes_df = df[df['estado_clean'].str.contains('pend|caminh|transit|distrib', na=False)]
    incidencias_df = df[df['estado_clean'].str.contains('incid|alerta|problem|erro|falh|devolv', na=False)]
    
    entregues = len(entregues_df)
    pendentes = len(pendentes_df)
    incidencias = len(incidencias_df)
    
    # Garantir que o número de tentativas é tratado como número
    df[col_tentativas_selecionada] = pd.to_numeric(df[col_tentativas_selecionada], errors='coerce').fillna(1)
    
    # Filtrar tentativas dentro dos já entregues
    entregues_completo_df = df.loc[entregues_df.index]
    entregues_1a = len(entregues_completo_df[entregues_completo_df[col_tentativas_selecionada] == 1])
    entregues_2a = len(entregues_completo_df[entregues_completo_df[col_tentativas_selecionada] == 2])
    outras_tentativas = entregues - (entregues_1a + entregues_2a)

    # --- KPIs ---
    st.subheader("📊 Métricas Principais")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric(label="📦 Total de Envios", value=f"{total_envios:,}")
    kpi2.metric(label="✅ Entregues", value=f"{entregues:,}", delta=f"{(entregues/max(total_envios,1))*100:.1f}% do total")
    kpi3.metric(label="⏳ Pendentes / Em Trânsito", value=f"{pendentes:,}", delta=f"{(pendentes/max(total_envios,1))*100:.1f}%", delta_color="inverse")
    kpi4.metric(label="⚠️ Com Incidência", value=f"{incidencias:,}", delta=f"{(incidencias/max(total_envios,1))*100:.1f}%", delta_color="inverse")

    st.markdown("---")

    # --- GRÁFICOS ---
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("🎯 Eficácia à Cabeceira (Tentativas)")
        dados_tentativas = pd.DataFrame({
            'Tentativa': ['1ª Tentativa', '2ª Tentativa', '3+ Tentativas'],
            'Quantidade': [entregues_1a, entregues_2a, max(0, outras_tentativas)]
        })
        fig_bar = px.bar(dados_tentativas, x='Tentativa', y='Quantidade', text='Quantidade',
                         color='Tentativa', color_discrete_sequence=['#2ecc71', '#3498db', '#e74c3c'])
        fig_bar.update_traces(textposition='inside')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_graf2:
        st.subheader("🔄 Estado Geral da Operação")
        fig_pie = px.pie(df, names=col_estado_selecionada, color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABELA DE DADOS ---
    st.markdown("---")
    st.subheader("🔍 Base de Dados Completa (Sincronizada)")
    st.dataframe(df.drop(columns=['estado_clean'], errors='ignore'), use_container_width=True)

except Exception as e:
    st.error("A carregar base de dados de demonstração... (Configure o link da sua Drive na barra lateral para ver os seus dados reais)")
    st.info("Para testar, a app precisa que o ficheiro na sua Google Drive esteja partilhado como 'Qualquer pessoa com o link'.")
