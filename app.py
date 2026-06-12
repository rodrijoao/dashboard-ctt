import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard de Envios CTT - B. Braun", layout="wide")

st.title("📦 Dashboard de Controlo de Envios CTT")
st.markdown("Análise em tempo real do Relatório Diário de Expedição.")

# Link direto para o CSV exportado da Google Drive (Substitui pelo teu link de exportação real)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1t87M2Y7Z4A_M7Vw3F30bUuV7lC5Z6_L_qUjXf-rSjYg/export?format=csv"

@st.cache_data(ttl=60)
def load_data(url):
    # skiprows=12 faz o Python ignorar as primeiras 12 linhas institucionais e ler a tabela real
    df = pd.read_csv(url, skiprows=12)
    # Limpar espaços em branco dos nomes das colunas
    df.columns = [str(c).strip() for c in df.columns]
    return df

try:
    df = load_data(GOOGLE_SHEET_URL)
    
    # Remover linhas totalmente vazias que possam vir no fim do ficheiro
    df = df.dropna(subset=['Objeto'])
    
    st.success("✅ Dados do Relatório de Expedição carregados com sucesso!")

    # --- PROCESSAMENTO DOS DADOS REAIS CTT ---
    total_envios = len(df)
    
    # Criar uma coluna limpa para analisar o estado (ex: "EMI - Entregue" passa a ser avaliado)
    df['situacao_clean'] = df['Situação do Objeto'].astype(str).str.upper()
    
    # Filtros baseados nos códigos reais dos CTT
    entregues_df = df[df['situacao_clean'].str.contains('ENTREGUE|EMI|ENT', na=False)]
    pendentes_df = df[df['situacao_clean'].str.contains('TRÂNCO|TRÂNSITO|EMF|DISTRIB', na=False)]
    incidencias_df = df[df['situacao_clean'].str.contains('INCID|ALERTA|DEV|RETIDO|FALHA', na=False)]
    
    entregues = len(entregues_df)
    pendentes = len(pendentes_df)
    incidencias = total_envios - (entregues + pendentes) # O resto assume incidência/outros

    # Simulação de tentativas (Como o ficheiro CTT não traz o número, calculamos com base na lógica de eventos)
    # Se a data do 1º evento for igual à do último, assumimos 1ª tentativa. Se mudar, assumimos 2ª.
    df['Data 1º Evento'] = df['Data 1º Evento'].astype(str).str.strip()
    df['Data último evento'] = df['Data último evento'].astype(str).str.strip()
    
    entregues_completo_df = df.loc[entregues_df.index].copy()
    
    # Extrair apenas a data (sem a hora) para comparar o dia do primeiro e do último evento
    def calcular_tentativas(row):
        try:
            d1 = row['Data 1º Evento'].split()[0]
            d2 = row['Data último evento'].split()[0]
            return 1 if d1 == d2 else 2
        except:
            return 1

    if not entregues_completo_df.empty:
        entregues_completo_df['Tentativas_Calculadas'] = entregues_completo_df.apply(calcular_tentativas, axis=1)
        entregues_1a = len(entregues_completo_df[entregues_completo_df['Tentativas_Calculadas'] == 1])
        entregues_2a = len(entregues_completo_df[entregues_completo_df['Tentativas_Calculadas'] == 2])
    else:
        entregues_1a, entregues_2a = 0, 0

    # --- PAINEL DE METRICAS (KPIs) ---
    st.subheader("📊 Resumo Operacional")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric(label="📦 Total de Envios", value=f"{total_envios:,}")
    kpi2.metric(label="✅ Entregues", value=f"{entregues:,}", delta=f"{(entregues/max(total_envios,1))*100:.1f}% do total")
    kpi3.metric(label="⏳ Em Trânsito / Pendentes", value=f"{pendentes:,}", delta=f"{(pendentes/max(total_envios,1))*100:.1f}%", delta_color="inverse")
    kpi4.metric(label="⚠️ Incidências / Outros", value=f"{incidencias:,}", delta=f"{(incidencias/max(total_envios,1))*100:.1f}%", delta_color="inverse")

    st.markdown("---")

    # --- GRÁFICOS ---
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("🎯 Eficácia de Entrega")
        dados_tentativas = pd.DataFrame({
            'Performance': ['À 1ª Tentativa (Mesmo Dia)', 'À 2ª Tentativa+ (Dias Diferentes)'],
            'Quantidade': [entregues_1a, entregues_2a]
        })
        fig_bar = px.bar(dados_tentativas, x='Performance', y='Quantidade', text='Quantidade',
                         color='Performance', color_discrete_sequence=['#2ecc71', '#3498db'])
        fig_bar.update_traces(textposition='inside')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_graf2:
        st.subheader("🔄 Distribuição por Situação Real")
        fig_pie = px.pie(df, names='Situação do Objeto', color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABELA DE DADOS ---
    st.markdown("---")
    st.subheader("🔍 Listagem de Objetos Encontrados")
    
    # Filtro rápido interativo
    filtro_sit = st.selectbox("Filtrar listagem por Situação:", ["Todos"] + list(df['Situação do Objeto'].unique()))
    df_visivel = df if filtro_sit == "Todos" else df[df['Situação do Objeto'] == filtro_sit]
    
    # Mostrar colunas úteis organizadas
    colunas_visiveis = ['Objeto', 'Refª Cliente', 'Situação do Objeto', 'Data 1º Evento', 'Data último evento', 'Nome do Destinatário']
    st.dataframe(df_visivel[colunas_visiveis], use_container_width=True)

except Exception as e:
    st.error(f"Erro ao processar a tabela: {e}")
    st.info("Verifique se o ficheiro na Google Drive mantém a linha 'Cód. Cliente,Cód. Contrato...' na linha 13.")
