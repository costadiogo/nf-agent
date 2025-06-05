from typing import Dict, Any
from utils import build_sql_agent
from database import sanitize_table_name, quote_table_name, get_database_overview
from database import process_zip_to_sqlite, process_csv_to_sqlite

import streamlit as st
import pandas as pd
import os
import tempfile
import time

class InvoiceApp:
    def __init__(self):
        self.db_path = None
        self.agent = None
        self.tables_info = {}
        
        
    def create_sql_agent(self, api_key: str):
        
        try:
            self.agent = build_sql_agent(
                openai_api_key=api_key,
                db_path=self.db_path,
                tables_info=self.tables_info
            )
            
            return True
        
        except Exception as e:
            st.error(f"❌ Erro ao criar agente SQL: {str(e)}")
            return False
    
    def query_database(self, question: str) -> str:
        try:
            if not self.agent:
                return "❌ Agente não configurado. Configure primeiro sua API key."
            response = self.agent.invoke(question)
            return response
        except Exception as e:
            return f"❌ Erro na consulta: {str(e)}"

    def sanitize_table_name(self, name: str) -> str:
        return sanitize_table_name(name)

    def quote_table_name(self, table_name: str) -> str:
        return quote_table_name(table_name)

    def get_database_overview(self) -> Dict[str, Any]:
        if not self.db_path:
            return {}
        try:
            return get_database_overview(self.db_path, self.tables_info)
        except Exception as e:
            st.error(str(e))
            return {}
        
    def setup_database(self, uploaded_file):
        try:
            db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
            os.close(db_fd)
            self.tables_info = {}

            if uploaded_file.name.endswith('.zip'):
                return process_zip_to_sqlite(uploaded_file, self.db_path, self.tables_info)
            elif uploaded_file.name.endswith('.csv'):
                return process_csv_to_sqlite(uploaded_file, self.db_path, self.tables_info)
            else:
                st.error("❌ Formato de arquivo não suportado.")
                return False
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")
            return False

def main():
    st.set_page_config(
        page_title="📊 Análise de Notas Fiscais",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Sistema de Análise de Notas Fiscais")
    st.markdown("*Upload seu arquivo ZIP com aquivos CSV ou CSV e faça perguntas sobre seus dados*")

    if 'app' not in st.session_state:
        st.session_state.app = InvoiceApp()
    
    app = st.session_state.app
 
    with st.sidebar:
        st.header("⚙️ Configuração")

        api_key = st.text_input(
            "OpenAI API Key", 
            type="password",
            help="Sua chave da API OpenAI"
        )
        
        if api_key:
            st.success("✅ API Key configurada")
        
        st.markdown("---")

        st.header("📁 Upload de Dados")
        uploaded_file = st.file_uploader(
            "Faça upload de de arquivos .ZIP, ou CSV",
            type=['zip', 'csv'],
            help="Arquivo ZIP contendo planilhas CSV das notas fiscais, arquivos CSV individuais com dados de notas fiscais."
        )
            
        process = st.button("🔄 Processar Arquivo")
        status_placeholder = st.empty()

        if uploaded_file and process:
            status_placeholder.info("⏳ Processando arquivo, aguarde...")
            time.sleep(1) 

            success = app.setup_database(uploaded_file)

            if success:
                status_placeholder.success("✅ Arquivo processado com sucesso!")
            else:
                status_placeholder.error("❌ Erro ao process o arquivo.")
                
            if api_key and app.create_sql_agent(api_key):
                st.success("✅ Agente configurado!")
                st.session_state.ready = True

    if hasattr(st.session_state, 'ready') and st.session_state.ready:
        
        tab1, tab2, tab3 = st.tabs(["💬 Consultas", "📋 Visão Geral", "📖 Exemplos"])
        
        with tab1:
            st.header("💬 Faça suas perguntas")
            
            question = st.text_input(
                "Digite sua pergunta sobre as notas fiscais:",
                placeholder="Ex: Qual o valor total das vendas em janeiro?",
                key="question_input"
            )
            
            col1, col2 = st.columns([1, 4])
            
            with col1:
                if st.button("🔍 Consultar", disabled=not question):
                    with st.spinner(""):
                        response = app.query_database(question)
                    
                    st.session_state.last_response = response
                    
            with col2:
                if st.button("🧹 Limpar"):
                    if 'last_response' in st.session_state:
                        del st.session_state.last_response
                    st.rerun()

            if 'last_response' in st.session_state:
                
                result = st.session_state.last_response
                
                st.markdown("### 📊 Resultado:")
                
                response_placeholder = st.empty()
            
                full_response = ""
                output = result['output']

                for char in output:
                    full_response += char
                    formatted_response = full_response.replace("\n", "<br>")
                    response_placeholder.markdown(formatted_response, unsafe_allow_html=True)
                    time.sleep(0.01)
        
        with tab2:
            st.header("📋 Visão Geral dos Dados")
            
            overview = app.get_database_overview()
            
            if overview:
                for table_name, info in overview.items():
                    with st.expander(f"📊 Tabela: {table_name.upper()}"):
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("Total de Registros", info['total_registros'])
                            st.write("**Colunas:**")
                            for col in info['colunas']:
                                st.write(f"• {col}")
                        
                        with col2:
                            st.write("**Valores Nulos:**")
                            nulls_df = pd.DataFrame(list(info['valores_nulos'].items()), 
                                                  columns=['Coluna', 'Nulos'])
                            st.dataframe(nulls_df, use_container_width=True)
                        
                        st.write("**Amostra dos Dados:**")
                        st.dataframe(info['amostra'], use_container_width=True)
        
        with tab3:
            st.header("📖 Exemplos de Consultas")
            
            examples = [
                {
                    "category": "💰 Análises Financeiras",
                    "questions": [
                        "Qual o valor total de todas as notas fiscais?",
                        "Qual cliente tem o maior volume de compras?",
                        "Quais notas têm valor acima de R$ 10.000?",
                        "Qual a média de valor por nota fiscal?"
                    ]
                },
                {
                    "category": "📅 Análises Temporais", 
                    "questions": [
                        "Quantas notas foram emitidas em cada mês?",
                        "Qual mês teve maior faturamento?",
                        "Quais notas foram emitidas nos últimos 30 dias?",
                        "Compare as vendas de janeiro com fevereiro"
                    ]
                },
                {
                    "category": "🛍️ Análise de Produtos",
                    "questions": [
                        "Quais são os 10 produtos mais vendidos?",
                        "Qual produto tem maior valor unitário?",
                        "Quantos itens diferentes foram vendidos?",
                        "Qual categoria de produto vende mais?"
                    ]
                },
                {
                    "category": "👥 Análise de Clientes",
                    "questions": [
                        "Quais são os 5 melhores clientes por volume?",
                        "Quantos clientes únicos temos?",
                        "Qual cliente compra mais frequentemente?",
                        "Liste clientes com mais de 5 notas"
                    ]
                }
            ]
            
            for ex in examples:
                with st.expander(ex["category"]):
                    for q in ex["questions"]:
                        st.info(f"💬 {q}")
    
    else:
        st.info("""
        👋 **Como usar:**
        
        1. **Configure sua OpenAI API Key** na barra lateral
        2. **Faça upload do arquivo ZIP** contendo seus CSVs de notas fiscais
        3. **Clique em "Processar Arquivo"** para carregar os dados
        4. **Faça perguntas** sobre seus dados em linguagem natural!
        
        📁 **Formato esperado:** Arquivo ZIP com planilhas CSV (ex: cabecalho.csv, itens.csv)
        """)

        with st.expander("📋 Ver exemplo de estrutura dos dados"):
            st.markdown("""
            **cabecalho.csv:**
            ```
            numero_nota,data_emissao,cliente,valor_total
            123456,2024-01-15,Cliente A,1500.00
            123457,2024-01-16,Cliente B,2300.50
            ```
            
            **itens.csv:**
            ```
            numero_nota,descricao,quantidade,valor_unitario,valor_total
            123456,Produto X,2,750.00,1500.00
            123457,Produto Y,1,2300.50,2300.50
            ```
            """)

if __name__ == "__main__":
    main()