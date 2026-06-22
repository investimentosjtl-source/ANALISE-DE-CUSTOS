import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="Analytics Protheus")

st.title("📊 Painel de Análise de Custos e Estoque (Protheus)")
st.markdown("Suba o arquivo consolidado contendo os dois períodos nas colunas.")

# --- SEÇÃO DE UPLOAD ---
st.sidebar.header("📂 Carga de Dados")
uploaded_file = st.sidebar.file_uploader("Suba a planilha com os dois períodos", type=["xlsx", "csv"])

if uploaded_file:
    # Lendo o arquivo único
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    
    # 1. Identificar as datas/períodos disponíveis olhando os colchetes nas colunas
    datas_detectadas = []
    for col in df.columns:
        match = re.search(r'\[Data:(.*?)\]', col)
        if match:
            datas_detectadas.append(match.group(1))
            
    # Remove duplicadas mantendo a ordem
    datas_unicas = sorted(list(set(datas_detectadas)))
    
    if len(datas_unicas) < 2:
        st.error("⚠️ Não encontramos dois períodos distintos nas colunas dessa planilha.")
        st.info("Garanta que suas colunas tenham o formato de data do Protheus, ex: `[Data:31/05/2026] Valor Unitario`")
        st.write("Colunas encontradas:", list(df.columns))
    else:
        # --- SELEÇÃO DE PERÍODOS NA SIDEBAR ---
        st.sidebar.header("🗓️ Seleção de Períodos")
        periodo_1 = st.sidebar.selectbox("Período 1 (Base/Antigo)", options=datas_unicas, index=0)
        periodo_2 = st.sidebar.selectbox("Período 2 (Comparativo/Atual)", options=datas_unicas, index=len(datas_unicas)-1)
        
        # --- FILTROS GLOBAIS ---
        st.sidebar.header("🔍 Filtros")
        
        # Identificando colunas fixas (que não mudam por período)
        col_armazem = [c for c in df.columns if 'ARMAZ' in c.upper() or 'LOCAL' in c.upper()][0]
        col_tipo = [c for c in df.columns if 'TIPO' in c.upper()][0]
        col_produto = [c for c in df.columns if 'PROD' in c.upper() or 'COD' in c.upper()][0]
        col_desc = [c for c in df.columns if 'DESC' in c.upper()][0]
        
        lista_armazem = sorted(df[col_armazem].dropna().unique())
        lista_tipo = sorted(df[col_tipo].dropna().unique())
        
        armazem_sel = st.sidebar.multiselect("Armazém", options=lista_armazem)
        tipo_sel = st.sidebar.multiselect("Tipo de Produto", options=tipo_sel)
        
        # Aplicando filtros dinâmicos
        df_filtrado = df.copy()
        if armazem_sel:
            df_filtrado = df_filtrado[df_filtrado[col_armazem].isin(armazem_sel)]
        if tipo_sel:
            df_filtrado = df_filtrado[df_filtrado[col_tipo].isin(tipo_sel)]
            
        # Mapeando colunas dinâmicas de valores para os períodos selecionados
        # Ex: procura por "[Data:31/05/2026] TOTAL"
        col_total_p1 = [c for c in df.columns if periodo_1 in c and 'TOTAL' in c.upper()][0]
        col_total_p2 = [c for c in df.columns if periodo_2 in c and 'TOTAL' in c.upper()][0]
        
        col_vlr_p1 = [c for c in df.columns if periodo_1 in c and ('VALOR UNIT' in c.upper() or 'VLR UNIT' in c.upper())][0]
        col_vlr_p2 = [c for c in df.columns if periodo_2 in c and ('VALOR UNIT' in c.upper() or 'VLR UNIT' in c.upper())][0]
        
        col_qtd_p2 = [c for c in df.columns if periodo_2 in c and ('QUANT' in c.upper() or 'QTD' in c.upper())][0]

        # --- CÁLCULO DOS KPIS ---
        custo_total_p1 = df_filtrado[col_total_p1].sum()
        custo_total_p2 = df_filtrado[col_total_p2].sum()
        var_custo = ((custo_total_p2 - custo_total_p1) / custo_total_p1 * 100) if custo_total_p1 > 0 else 0
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label=f"Custo Total em Estoque ({periodo_2})", 
                value=f"R$ {custo_total_p2:,.2f}", 
                delta=f"{var_custo:.2f}% vs {periodo_1}",
                delta_color="inverse"
            )
        with col2:
            st.metric(
                label=f"Quantidade Total em Estoque ({periodo_2})", 
                value=f"{df_filtrado[col_qtd_p2].sum():,.0f} un"
            )
            
        st.divider()
        
        # --- TABELA DE ANÁLISE ---
        st.subheader("📋 Análise de Variação por Item")
        
        # Criando a tabela final limpa
        df_analise = pd.DataFrame({
            'Produto': df_filtrado[col_produto],
            'Descrição': df_filtrado[col_desc],
            'Tipo': df_filtrado[col_tipo],
            'Armazém': df_filtrado[col_armazem],
            f'Custo Unit. ({periodo_1})': df_filtrado[col_vlr_p1],
            f'Custo Unit. ({periodo_2})': df_filtrado[col_vlr_p2],
            'Diferença R$': df_filtrado[col_vlr_p2] - df_filtrado[col_vlr_p1],
            'Variação (%)': (((df_filtrado[col_vlr_p2] - df_filtrado[col_vlr_p1]) / df_filtrado[col_vlr_p1]) * 100).fillna(0)
        }).sort_values(by='Variação (%)', ascending=False)
        
        st.dataframe(
            df_analise.style.format({
                f'Custo Unit. ({periodo_1})': 'R$ {:,.2f}',
                f'Custo Unit. ({periodo_2})': 'R$ {:,.2f}',
                'Diferença R$': 'R$ {:,.2f}',
                'Variação (%)': '{:.2f}%'
            }),
            use_container_width=True
        )
        
        # --- GRÁFICO ---
        st.subheader(f"🔥 Top 10 Produtos com Maior Alta no Custo Unitário")
        top_ofensores = df_analise[df_analise['Variação (%)'] > 0].head(10)
        
        if not top_ofensores.empty:
            fig = px.bar(
                top_ofensores,
                x='Variação (%)',
                y='Descrição',
                orientation='h',
                color='Variação (%)',
                color_continuous_scale='Reds'
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 Pronto para rodar! Suba o arquivo unificado do Protheus na barra lateral.")