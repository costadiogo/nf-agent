from typing import Dict, Any, Union
from pathlib import Path

import os
import zipfile
import pandas as pd
import re
import sqlite3
import pandas as pd
import tempfile
import streamlit as st

def sanitize_table_name(name: str) -> str:
    
    name = re.sub(r'[^\w]', '_', name)
    if name and name[0].isdigit():
        name = f"table_{name}"
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name if name else "unnamed_table"

def quote_table_name(table_name: str) -> str:

    if not table_name.replace('_', '').isalnum() or table_name[0].isdigit():
        return f'"{table_name}"'
    return table_name

def get_database_overview(db_path: str, tables_info: Dict[str, Any]) -> Dict[str, Any]:

    overview = {}
    try:
        conn = sqlite3.connect(db_path)
        for table_name, info in tables_info.items():
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            overview[table_name] = {
                'total_registros': len(df),
                'colunas': list(df.columns),
                'tipos_dados': df.dtypes.to_dict(),
                'valores_nulos': df.isnull().sum().to_dict(),
                'amostra': df.head(3)
            }
        conn.close()
    except Exception as e:
        raise RuntimeError(f"Erro ao gerar overview: {str(e)}")
    return overview

def process_uploaded_file(uploaded_file) -> Dict[str, Any]:

    result = {}
    file_name = uploaded_file.name.lower()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # .zip
        if file_name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
                zip_ref.extractall(tmp_path)

            for file in tmp_path.glob("*.csv"):
                df = pd.read_csv(file, sep=None, engine='python')  # tenta detectar separador
                result[file.stem] = df

        # .csv
        elif file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
            name = Path(file_name).stem
            result[name] = df

    return result

def save_df_to_sqlite(df, table_name, db_path):
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()

def process_zip_to_sqlite(zip_file, db_path, tables_info):
    try:
        conn = sqlite3.connect(db_path)
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.endswith('.csv'):
                    with zip_ref.open(file_name) as csv_file:
                        df = pd.read_csv(csv_file)
                    table_name = os.path.splitext(file_name)[0].lower()
                    table_name = sanitize_table_name(table_name)
                    table_name = quote_table_name(table_name)
                    save_df_to_sqlite(df, table_name, db_path)
                    
                    tables_info[table_name] = {
                        'rows': len(df),
                        'columns': list(df.columns),
                        'sample': df.head(2).to_dict('records')
                    }
                    st.success(f"✅ Tabela '{table_name}' criada com {len(df)} registros")
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao processar arquivo ZIP: {str(e)}")
        return False

def process_csv_to_sqlite(csv_file, db_path, tables_info):
    try:
        df = pd.read_csv(csv_file)
        table_name = os.path.splitext(csv_file.name)[0].lower()
        table_name = sanitize_table_name(table_name)
        table_name = quote_table_name(table_name)
        save_df_to_sqlite(df, table_name, db_path)
        tables_info[table_name] = {
            'rows': len(df),
            'columns': list(df.columns),
            'sample': df.head(2).to_dict('records')
        }
        st.success(f"✅ Tabela '{table_name}' criada com {len(df)} registros")
        return True
    except Exception as e:
        st.error(f"❌ Erro ao processar arquivo CSV: {str(e)}")
        return False