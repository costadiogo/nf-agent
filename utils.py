from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.base import create_sql_agent

def get_custom_prefix(tables_info: dict) -> str:
    """Prompt customizado para notas fiscais"""
    tables_desc = "\n".join([
        f"- {table}: {info['rows']} registros, colunas: {', '.join(info['columns'])}"
        for table, info in tables_info.items()
    ])

    return f"""
        Você é um especialista em análise de notas fiscais com acesso a um banco de dados SQLite.

        TABELAS DISPONÍVEIS:
        {tables_desc}

        INSTRUÇÕES IMPORTANTES:
        1. Sempre use SQL para responder perguntas sobre os dados
        2. Para valores monetários, formate como R$ X,XX
        3. Para datas, use formato brasileiro DD/MM/AAAA
        4. Sempre explique o que encontrou de forma clara
        5. Se não encontrar dados, informe claramente
        6. Para consultas complexas, quebre em etapas
        7 . Use a coluna CPF/CNPJ Emitente como chave primária para identificar 
        clientes nas consultas em multiplas tabelas

        EXEMPLOS DE PERGUNTAS COMUNS:
        - "Qual o valor total das notas do cliente X?"
        - "Quantas notas foram emitidas em janeiro?"
        - "Quais os produtos mais vendidos?"
        - "Qual cliente tem maior volume de compras?"

        Sempre seja preciso e didático nas respostas.
"""

def build_sql_agent(openai_api_key: str, db_path: str, tables_info: dict):
    
    # Configurar LLM
    llm = ChatOpenAI(
        temperature=0,
        openai_api_key=openai_api_key,
        model_name="gpt-4o"
    )

    # Conectar ao banco
    db = SQLDatabase.from_uri(f"sqlite:///{db_path}")

    # Criar toolkit
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)

    # Gerar prefixo customizado
    prefix = get_custom_prefix(tables_info)

    # Criar agente
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type="openai-tools",
        prefix=prefix
    )

    return agent