import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path

class Expense:
    def __init__(self, id, establishment, category, value, date):
        self.id = id
        self.establishment = establishment
        self.category = category
        self.value = float(value)
        self.date = date

class MonthlySavings:
    def __init__(self, id, saving_type, value, date):
        self.id = id
        self.saving_type = saving_type
        self.value = float(value)
        self.date = date

class FinanceManager:
    def __init__(self):
        self.expenses = []
        self.monthly_savings = []
        self.next_expense_id = 1
        self.next_savings_id = 1
        self.sheets_manager = GoogleSheetsManager()
        self.sheets_manager.authenticate()

    def add_expense(self, establishment, category, value, date):
        expense = Expense(self.next_expense_id, establishment, category, value, date)
        self.expenses.append(expense)
        self.next_expense_id += 1
        return f"Despesa adicionada: {expense.establishment} - R${expense.value:.2f}"

    def edit_expense(self, id, establishment, value, date):
        for expense in self.expenses:
            if expense.id == id:
                expense.establishment = establishment
                expense.category = category
                expense.value = float(value)
                expense.date = date
                return f"Despesa atualizada: {expense.establishment} - R${expense.value:.2f}"
        return "Despesa não encontrada"

    def add_monthly_savings(self, saving_type, value, date):
        savings = MonthlySavings(self.next_savings_id, saving_type, value, date)
        self.monthly_savings.append(savings)
        self.next_savings_id += 1
        return f"Economia mensal adicionada: R${savings.value:.2f} para {savings.date}"

    def edit_monthly_savings(self, id, saving_type, value, date):
        for savings in self.monthly_savings:
            if savings.id == id:
                savings.category = saving_type
                savings.value = float(value)
                savings.date = date
                return f"Economia mensal atualizada: R${savings.value:.2f} para {savings.date}"
        return "Economia mensal não encontrada"

    def get_total_expenses(self):
        return sum(expense.value for expense in self.expenses)

    def get_total_savings(self):
        return sum(savings.value for savings in self.monthly_savings)

    def get_expenses_df(self):
        return pd.DataFrame([
            {
                "ID": expense.id,
                "Data": expense.date,
                "Estabelecimento": expense.establishment,
                "Categoria": expense.category,
                "Valor": expense.value
            } for expense in self.expenses
        ])

    def get_savings_df(self):
        return pd.DataFrame([
            {
                "ID": savings.id,
                "Tipo Entrada": savings.saving_type,
                "Data": savings.date,
                "Valor": savings.value
            } for savings in self.monthly_savings
        ])
    
    def add_expenses_from_csv(self, csv_content):
        try:
            df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
            required_columns = ["Estabelecimento", "Valor da Despesa", "Data", "Categoria"]
            if not all(col in df.columns for col in required_columns):
                return "Erro: O arquivo CSV não contém todas as colunas necessárias."

            added_count = 0
            for _, row in df.iterrows():
                try:
                    establishment = row["Estabelecimento"]
                    value = float(row["Valor da Despesa"])
                    date = pd.to_datetime(row["Data"]).date()
                    category = row["Categoria"]
                    self.add_expense(establishment, category, value, date)
                    added_count += 1
                except Exception as e:
                    st.error(f"Erro ao adicionar despesa: {e}")

            return f"{added_count} despesas adicionadas com sucesso."
        except Exception as e:
            return f"Erro ao processar o arquivo CSV: {e}"
        
    def save_expenses_to_sheets(self):
        expenses_df = self.get_expenses_df()
        expenses_df['Data'] = expenses_df['Data'].astype(str)
        return self.sheets_manager.save_to_sheets(expenses_df, 'Expenses')

    def save_savings_to_sheets(self):
        savings_df = self.get_savings_df()
        savings_df['Data'] = savings_df['Data'].astype(str)
        return self.sheets_manager.save_to_sheets(savings_df, 'Savings')

class GoogleSheetsManager:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.SPREADSHEET_ID = '1HTHu4syxtJBOiPpCBFgBI_fVF2I3-JVHVwP1lXi12mQ'  # Replace with your actual spreadsheet ID
        self.creds = None

    def authenticate(self):
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    './streamlit_env/credenciais/credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=8080)
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def save_to_sheets(self, data, sheet_name):
        service = build('sheets', 'v4', credentials=self.creds)
        sheet = service.spreadsheets()
        
        # Clear existing data
        sheet.values().clear(spreadsheetId=self.SPREADSHEET_ID, range=sheet_name).execute()
        
        # Prepare data for insertion
        values = [data.columns.tolist()] + data.values.tolist()
        
        body = {
            'values': values
        }
        
        # Insert new data
        result = sheet.values().update(
            spreadsheetId=self.SPREADSHEET_ID, range=sheet_name,
            valueInputOption='USER_ENTERED', body=body).execute()
        
        return result
     
# Configuração da página
st.set_page_config(page_title="Gestão Financeira", page_icon="💰", layout="wide")

# Inicialização do tema e do FinanceManager
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'
if 'finance_manager' not in st.session_state:
    st.session_state.finance_manager = FinanceManager()
if 'csv_processed' not in st.session_state:
    st.session_state.csv_processed = False

fm = st.session_state.finance_manager

# Sidebar para configurações e adição de despesas
st.sidebar.title("Cadastro financeiro")

# Expander para "Adicionar Nova Despesa"
with st.sidebar.expander("Adicionar Nova Despesa", expanded=False):
    st.subheader("Adicionar Nova Despesa")
    establishment = st.text_input("Estabelecimento")
    category = st.selectbox("Categoria", ["Alimentação", "Transporte", "Custo Fixo", "Saúde", "Educação", "Lazer", "Restaurante", "Outros"])
    value = st.number_input("Valor da Despesa", min_value=0.0, step=0.1, format="%.1f")
    date = st.date_input("Data da Despesa")

    if st.button("Adicionar Despesa"):
        message = fm.add_expense(establishment, category, value, date)
        st.success(message)

# Expander para "Upload de Despesas via CSV"
with st.sidebar.expander("Upload de Despesas via CSV", expanded=False):
    st.subheader("Upload de Despesas via CSV")
    uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if uploaded_file is not None and not st.session_state.get('csv_processed', False):
        csv_content = uploaded_file.read()
        message = fm.add_expenses_from_csv(csv_content)
        if "Erro" in message:
            st.error(message)
        else:
            st.success(message)
            st.session_state.csv_processed = True
    elif uploaded_file is not None and st.session_state.get('csv_processed', False):
        st.info("O arquivo CSV já foi processado. Para adicionar novas despesas, faça um novo upload.")

    # Botão para resetar o processamento do CSV
    if st.button("Permitir novo upload de CSV"):
        st.session_state.csv_processed = False
        st.success("Você pode fazer um novo upload de CSV agora.")
        
# Expander para "Adicionar Entrada Mensal"
with st.sidebar.expander("Adicionar Entrada Mensal", expanded=False):
    st.subheader("Entrada Mensal")
    savings_type = st.selectbox("Tipo Entrada", ["Salário", "Bônus", "Extra", "Décimo Terceiro", "FGTS"])
    savings_value = st.number_input("Valor da Entrada", min_value=0.0, step=10.0, format="%.2f")
    savings_date = st.date_input("Data da Entrada")
    if st.button("Adicionar Entrada"):
        message = fm.add_monthly_savings(savings_type, savings_value, savings_date)
        st.success(message)

# Conteúdo principal
st.title("Minha gestão financeira 💰")

# Resumo financeiro
st.header("Resumo Financeiro")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total de Gastos", f"R$ {fm.get_total_expenses():.2f}")
with col2:
    st.metric("Total de Entradas", f"R$ {fm.get_total_savings():.2f}")
with col3:
    st.metric("Saldo", f"R$ {fm.get_total_savings() - fm.get_total_expenses():.2f}")

# Exibição e edição das despesas
col3, col4 = st.columns(2)
with col3:
    st.header("Lista de Despesas")
    expenses_df = fm.get_expenses_df()
    if not expenses_df.empty:
        edited_expenses_df = st.data_editor(expenses_df, num_rows="dynamic", key="expense_editor")

        # Verificar se houve alterações e atualizar as despesas
        if not edited_expenses_df.equals(expenses_df):
            for index, row in edited_expenses_df.iterrows():
                fm.edit_expense(row['ID'], row['Estabelecimento'], row['Categoria'], row['Valor'], row['Data'])
            st.success("Despesas atualizadas com sucesso!")
    else:
        st.info("Nenhuma despesa registrada ainda.")

    # Exportar dados
    if not expenses_df.empty:
        col3_1, col3_2 = st.columns(2)
        with col3_1:
            st.download_button(
                label="Exportar despesas como CSV",
                data=expenses_df.to_csv(index=False).encode('utf-8'),
                file_name="despesas.csv",
                mime="text/csv",
            )
            
        with col3_2:
            if st.button("Salvar Despesas no Google Sheets"):
                result = fm.save_expenses_to_sheets()
                st.success(f"Despesas salvas no Google Sheets. {result.get('updatedCells')} células atualizadas.")
                    
with col4:
    # Exibição e edição das economias mensais
    st.header("Lista de Entradas Mensais")
    savings_df = fm.get_savings_df()
    if not savings_df.empty:
        edited_savings_df = st.data_editor(savings_df, num_rows="dynamic", key="savings_editor")

        # Verificar se houve alterações e atualizar as economias mensais
        if not edited_savings_df.equals(savings_df):
            for index, row in edited_savings_df.iterrows():
                fm.edit_monthly_savings(row['ID'], row['Valor'], row['Data'])
            st.success("Entradas mensais atualizadas com sucesso!")
    else:
        st.info("Nenhuma entrada registrada ainda.")

    if not savings_df.empty:
        col4_1, col4_2 = st.columns(2)
        with col4_1:
            st.download_button(
                label="Exportar entradas mensais como CSV",
                data=savings_df.to_csv(index=False).encode('utf-8'),
                file_name="entradas_mensais.csv",
                mime="text/csv",
            )
        with col4_2:
            if st.button("Salvar Entradas no Google Sheets"):
                result = fm.save_savings_to_sheets()
                st.success(f"Entradas salvas no Google Sheets. {result.get('updatedCells')} células atualizadas.")
            
    
# Gráficos interativos
st.header("Análise de Gastos")

if not expenses_df.empty:
    # Preparar dados
    expenses_df['Data'] = pd.to_datetime(expenses_df['Data'])
    expenses_df['Ano'] = expenses_df['Data'].dt.year
    expenses_df['Mês'] = expenses_df['Data'].dt.strftime('%B')

    # Seleção do tipo de gráfico
    chart_type = st.selectbox("Selecione o tipo de análise:", 
                              ["Gastos por Categoria", "Gastos por Estabelecimento", "Gastos Mensais"])

    if chart_type == "Gastos por Categoria":
        data = expenses_df.groupby('Categoria')['Valor'].sum().reset_index()
        #fig = px.pie(data, values='Valor', names='Categoria', title='Gastos por Categoria')
        fig = px.bar(data, x='Valor', y='Categoria', orientation='h', text='Valor', title='Gastos por Categoria')
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    
    elif chart_type == "Gastos por Estabelecimento":
        data = expenses_df.groupby('Estabelecimento')['Valor'].sum().reset_index().sort_values('Valor', ascending=False)
        fig = px.bar(data, x='Estabelecimento', y='Valor', title='Gastos por Estabelecimento')
    
    else: 
        data = expenses_df.groupby('Mês')['Valor'].sum().reset_index()
        fig = px.bar(data, x='Mês', y='Valor', text='Valor', title='Gastos Mensais')
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    # Ajustar o tema do gráfico
    fig.update_layout(
        template='plotly_dark' if st.session_state.theme == 'dark' else 'plotly_white',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Adicione despesas para ver os gráficos.")

# Aplicar o tema
if st.session_state.theme == 'dark':
    st.markdown("""
        <style>
        .stApp {
            background-color: #1E1E1E;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stApp {
            background-color: white;
            color: black;
        }
        </style>
    """, unsafe_allow_html=True)
