import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Fisio Performance", layout="wide")

# --- FUNÇÃO PARA CARREGAR E TRATAR DADOS ---
@st.cache_data
def carregar_e_tratar_dados(caminho_arquivo):
    df = pd.read_excel(caminho_arquivo)

    # Tratamento de Datas
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df = df.dropna(subset=['Data'])
    df = df.sort_values(by='Data')
    
    # Limpeza de nomes e colunas
    df.columns = df.columns.str.strip()
    df['Nome'] = df['Nome'].astype(str).str.strip()

    # Cálculos de Assimetria
    testes_quantitativos = ['WBLT', 'Prancha', 'Ponte', 'Hop', 'Quadri', 'Isquios']
    for teste in testes_quantitativos:
        col_d = f'{teste} D'
        col_e = f'{teste} E'
        
        df[col_d] = pd.to_numeric(df[col_d], errors='coerce')
        df[col_e] = pd.to_numeric(df[col_e], errors='coerce')
        
        max_val = df[[col_d, col_e]].max(axis=1)
        df[f'Assimetria_{teste}'] = (abs(df[col_d] - df[col_e]) / max_val.replace(0, np.nan)) * 100
        df[f'Assimetria_{teste}'] = df[f'Assimetria_{teste}'].fillna(0)
        
    return df

# --- CARREGAMENTO INICIAL ---
nome_do_arquivo = "planilha_fisioterapia.xlsx" 
try:
    df = carregar_e_tratar_dados(nome_do_arquivo)
except Exception as e:
    st.error(f"❌ Erro ao carregar arquivo: {e}")
    st.stop()

# --- SIDEBAR / FILTROS ---
st.sidebar.header("Filtros de Avaliação")
nomes_ordenados = sorted(df['Nome'].unique())
atleta_sel = st.sidebar.selectbox("Selecione a Atleta", nomes_ordenados)

# Filtro de fases dinâmico por atleta
fases_atleta = df[df['Nome'] == atleta_sel].sort_values(by='Data')['Fase'].unique()
fase_sel = st.sidebar.selectbox("Fase da Avaliação", fases_atleta)

# --- DEFINIÇÃO DOS DADOS SELECIONADOS ---
# Pegamos os dados da atleta na fase escolhida
dados_atleta = df[(df['Nome'] == atleta_sel) & (df['Fase'] == fase_sel)].iloc[0]

# Calculamos a média da posição (Benchmarks)
df_posicao = df[df['Posição'] == dados_atleta['Posição']]
medias_referencia = df_posicao.select_dtypes(include=[np.number]).mean()

# --- FUNÇÕES DE INTERFACE (Definidas após os dados estarem prontos) ---

def plotar_comparativo(nome_teste):
    d = dados_atleta[f'{nome_teste} D']
    e = dados_atleta[f'{nome_teste} E']
    asim = dados_atleta[f'Assimetria_{nome_teste}']

    # Busca a média da posição para este teste específico
    m_d = medias_referencia.get(f'{nome_teste} D', 0)
    m_e = medias_referencia.get(f'{nome_teste} E', 0)
    media_final = (m_d + m_e) / 2
    
    fig = go.Figure(data=[
        go.Bar(name='Direito', x=[nome_teste], y=[d], marker_color='#00CC96'),
        go.Bar(name='Esquerdo', x=[nome_teste], y=[e], marker_color='#EF553B')
    ])
    
    fig.add_hline(y=media_final, line_dash="dot", line_color="white", 
                  annotation_text=f"Média {dados_atleta['Posição']}",
                  annotation_position="bottom right")

    cor_asim = "red" if asim > 15 else "green"
    fig.update_layout(
        title=f"{nome_teste} (Assimetria: <span style='color:{cor_asim}'>{asim:.1f}%</span>)",
        barmode='group', height=350, margin=dict(l=20, r=20, t=60, b=20),
        showlegend=True,
        template="plotly_dark" # Deixa o gráfico mais moderno
    )
    return fig

def exibir_qualitativo(teste, lado_d, lado_e):
    st.markdown(f"**{teste}**")
    cd, ce = st.columns(2)
    for col, val, lab in zip([cd, ce], [lado_d, lado_e], ["D", "E"]):
        with col:
            if "ok" in str(val).lower():
                st.success(f"{lab}: {val}")
            else:
                st.warning(f"{lab}: {val}")

# --- CONSTRUÇÃO DO DASHBOARD ---
data_formatada = dados_atleta['Data'].strftime('%d/%m/%Y')
st.title(f"⚽ Avaliação Física: {atleta_sel}")
st.subheader(f"Data: {data_formatada} | Fase: {fase_sel}")

# Métricas Biométricas
c1, c2, c3, c4 = st.columns(4)
c1.metric("Idade", f"{dados_atleta['Idade']} anos")
c2.metric("Peso", f"{dados_atleta['Peso']} kg")
c3.metric("Altura", f"{dados_atleta['Altura']} m")
c4.metric("M. Dominante", f"{dados_atleta['M. Dominante']}")

st.info(f"**Histórico/Lesões:** {dados_atleta['lesões/cirurgias']}")
st.divider()

# Avaliação Qualitativa
st.subheader("📋 Observações Clínicas e Qualitativas")
exibir_qualitativo("Flexibilidade (Teste de Thomas)", dados_atleta['Thomas D'], dados_atleta['Thomas E'])
st.write("") 
exibir_qualitativo("Padrão de Movimento (Agachamento)", dados_atleta['Agach D'], dados_atleta['Agach E'])

st.divider()

# Gráficos de Assimetria
st.subheader("📊 Análise de Desempenho Muscular (vs Média da Posição)")
testes_grafico = ['WBLT', 'Prancha', 'Ponte', 'Hop', 'Quadri', 'Isquios']
col_esq, col_dir = st.columns(2)

for i, teste in enumerate(testes_grafico):
    if i % 2 == 0:
        with col_esq:
            st.plotly_chart(plotar_comparativo(teste), use_container_width=True)
    else:
        with col_dir:
            st.plotly_chart(plotar_comparativo(teste), use_container_width=True)

# Alertas Críticos
st.divider()
st.subheader("⚠️ Resumo de Alertas de Assimetria Crítica (> 15%)")
alertas = [f"O teste **{t}** apresenta assimetria de **{dados_atleta[f'Assimetria_{t}']:.1f}%**." 
           for t in testes_grafico if dados_atleta[f'Assimetria_{t}'] > 15]

if alertas:
    for a in alertas: st.error(a)
else:
    st.success("Nenhuma assimetria crítica detectada.")

# Gráfico de Evolução
st.divider()
st.subheader(f"📈 Evolução de Assimetria - Histórico de {atleta_sel}")
df_evolucao = df[df['Nome'] == atleta_sel]

if len(df_evolucao) > 1:
    testes_evol = ['WBLT', 'Prancha', 'Hop', 'Isquios']
    tabs = st.tabs(testes_evol)
    for i, teste in enumerate(testes_evol):
        with tabs[i]:
            fig_evol = px.line(df_evolucao, x='Data', y=f'Assimetria_{teste}', text='Fase', markers=True, 
                               title=f"Evolução: {teste}", template="plotly_dark")
            fig_evol.update_traces(textposition="top center")
            fig_evol.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Limite 15%")
            st.plotly_chart(fig_evol, use_container_width=True)
else:
    st.info("Histórico insuficiente para gerar gráficos de evolução.")
    
#streamlit run app.py