import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import hashlib
import os

# Firebase imports
import firebase_admin
from firebase_admin import credentials, auth, db

# Acessar variáveis do TOML
firebase_secrets = st.secrets["firebase"]

# Configuração do Firebase
cred = credentials.Certificate({
    "type": firebase_secrets["type"],
    "project_id": firebase_secrets["project_id"],
    "private_key_id": firebase_secrets["private_key_id"],
    "private_key": firebase_secrets["private_key"].replace('\\n', '\n'),
    "client_email": firebase_secrets["client_email"],
    "client_id": firebase_secrets["client_id"],
    "auth_uri": firebase_secrets["auth_uri"],
    "token_uri": firebase_secrets["token_uri"],
    "auth_provider_x509_cert_url": firebase_secrets["auth_provider_x509_cert_url"],
    "client_x509_cert_url": firebase_secrets["client_x509_cert_url"],
    "universe_domain": firebase_secrets["universe_domain"]
})

# Inicialização do Firebase
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': firebase_secrets["databaseURL"]
    })

# Configuração da página Streamlit (primeiro comando do Streamlit)
st.set_page_config(page_title="Gestão Financeira", page_icon="💰", layout="wide")

# Função para registrar um novo usuário
def register_user(email, password):
    try:
        user = auth.create_user(
            email=email,
            password=password
        )
        st.success(f"Usuário {user.email} registrado com sucesso!")
        return user
    except Exception as e:
        st.error(f"Erro ao registrar usuário: {e}")
        return None

# Função para autenticar usuário
def authenticate_user(email, password):
    user = firebase.authenticate(email, password)
    if user:
        st.session_state.logged_in = True
        st.session_state.user_id = user['id']
        load_user_data(user['id'])
    else:
        st.error("Falha na autenticação.")

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
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.expenses = []
        self.monthly_savings = []
        self.next_expense_id = 1
        self.next_savings_id = 1

    def add_expense(self, establishment, category, value, date):
        expense = Expense(self.next_expense_id, establishment, category, value, date)
        self.expenses.append(expense)
        self.next_expense_id += 1

        # Salva automaticamente no Firebase após adicionar despesa
        self.save_expenses_to_firebase()

        return f"Despesa adicionada: {expense.establishment} - R${expense.value:.2f}"

    def edit_expense(self, id, establishment, category, value, date):
        for expense in self.expenses:
            if expense.id == id:
                expense.establishment = establishment
                expense.category = category
                expense.value = float(value)
                expense.date = date

                # Salva automaticamente no Firebase após editar despesa
                self.save_expenses_to_firebase()

                return f"Despesa atualizada: {expense.establishment} - R${expense.value:.2f}"
        return "Despesa não encontrada"
    
    # Função que salva automaticamente as despesas
    def save_expenses_to_firebase(self):
        expenses_df = self.get_expenses_df()
        save_expenses_to_firebase(self.user_id, expenses_df)

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

            # Salva automaticamente no Firebase após adicionar despesas do CSV
            self.save_expenses_to_firebase()

            return f"{added_count} despesas adicionadas com sucesso."
        except Exception as e:
            return f"Erro ao processar o arquivo CSV: {e}"

# Função para salvar os dados no firebase
def save_expenses_to_firebase(user_id, expenses_df):
    try:
        expenses_ref = db.reference(f'users/{user_id}/expenses')
        expenses_df['Data'] = expenses_df['Data'].astype(str)
        expenses_data = expenses_df.to_dict('records')
        expenses_ref.set(expenses_data)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados no Firebase: {e}")
        return False
        
# Função para carregar as despesas e economias do Firebase
def load_expenses_from_firebase(user_id):
    try:
        expenses_ref = db.reference(f'users/{user_id}/expenses')
        expenses_data = expenses_ref.get()
        if expenses_data:
            expenses_df = pd.DataFrame(expenses_data)
            return expenses_df
        else:
            return pd.DataFrame()  # Retorna um DataFrame vazio se não houver despesas
    except Exception as e:
        st.error(f"Erro ao carregar despesas do Firebase: {e}")
        return pd.DataFrame()
        
# Função de login
def login():
    st.title("Acesse agora seu Gestor Financeiro Pessoal")
    
    # Inicializa variáveis de estado
    if 'is_registering' not in st.session_state:
        st.session_state.is_registering = False

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Verifica se o usuário já está logado
    if st.session_state.logged_in and 'user_id' in st.session_state:
        st.success(f"Bem-vindo novamente, {st.session_state.user_display_name}!")
        return
    
    # Botões para alternar entre Login e Registrar
    col1, col2 = st.columns([1, 20])
    with col1:
        if st.button("Login"):
            st.session_state.is_registering = False
    with col2:
        if st.button("Registrar"):
            st.session_state.is_registering = True
            
    # Formulário de Login ou Registro baseado no estado
    if st.session_state.is_registering:
        st.subheader("Registrar Novo Usuário")
        email = st.text_input("Email", key="register_email_unique")
        password = st.text_input("Senha", type="password", key="register_password_unique")
        if st.button("Registrar", key="register_button_unique"):
            user = register_user(email, password)
            if user:
                st.success("Registro realizado com sucesso! Faça o login.")
    
    else:
        st.subheader("Login")
        # Cria um formulário com o nome 'login_form'
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email_unique")
            password = st.text_input("Senha", type="password", key="login_password_unique")

            # O botão de submissão do formulário
            submit_button = st.form_submit_button("Login")

        # Verifica se o login foi bem-sucedido e carrega os dados
        if submit_button:
            user = authenticate_user(email, password)
            if user:
                st.success(f"Bem-vindo, {user.display_name or user.email}! Aguarde enquanto carregamos os seus dados.")
                st.session_state.logged_in = True
                st.session_state.user_id = user.uid  # Atribui o user_id corretamente

                # Carregar as despesas e economias do Firebase após o login
                expenses_df = load_expenses_from_firebase(st.session_state.user_id)
                if not expenses_df.empty:
                    st.session_state.expenses_df = expenses_df

                # Inicializa o FinanceManager se ainda não existir
                if st.session_state.finance_manager is None:
                    st.session_state.finance_manager = FinanceManager(st.session_state.user_id)

                    # Preencher o FinanceManager com as despesas carregadas do Firebase
                    for _, row in st.session_state.expenses_df.iterrows():
                        st.session_state.finance_manager.add_expense(
                            row['Estabelecimento'], row['Categoria'], row['Valor'], pd.to_datetime(row['Data']).date()
                        )
                st.rerun()  # Recarrega a página para atualizar o estado
            else:
                st.error("Credenciais inválidas.")

def load_user_data(user_id):
    # Função para carregar dados específicos do usuário
    user_data = firebase.get_user_data(user_id)
    st.session_state.user_data = user_data
                
# Função de logout                
def logout():
    # Limpar o estado do usuário
    st.session_state.clear()
    st.session_state.logged_in = False
    st.session_state.user_data = None
    st.write("Você foi desconectado.")
        
            ##################################################################
            ##################### Configuração da página #####################
            ##################################################################
        
def main():   
    # Inicialização do tema e do FinanceManager
    if 'theme' not in st.session_state:
        st.session_state.theme = 'dark'
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'finance_manager' not in st.session_state:
        st.session_state.finance_manager = None
    if 'csv_processed' not in st.session_state:
        st.session_state.csv_processed = False

    if not st.session_state.logged_in:
        login()
    else:
        user_id = st.session_state.user_id
        # Verificar se os dados são consistentes
        if 'user_data' in st.session_state and st.session_state.user_data['user_id'] != user_id:
            st.session_state.user_data = None
        # Carregar dados do usuário
        load_user_data(user_id) 

    # Certifique-se de que o FinanceManager está inicializado
    if st.session_state.finance_manager is None:
        st.session_state.finance_manager = FinanceManager(st.session_state.user_id)
        
    if st.session_state.logged_in:
        if st.session_state.finance_manager is None:
            st.session_state.finance_manager = FinanceManager(st.session_state.user_id)
            if 'expenses_df' in st.session_state and not st.session_state.expenses_df.empty:
                for _, row in st.session_state.expenses_df.iterrows():
                    st.session_state.finance_manager.add_expense(
                        row['Estabelecimento'], row['Categoria'], row['Valor'], pd.to_datetime(row['Data']).date()
                    )
    
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
        st.metric("Total de Gastos", f"R$ {fm.get_total_expenses():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with col2:
        st.metric("Total de Entradas", f"R$ {fm.get_total_savings():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    with col3:
        st.metric("Saldo", f"R$ {(fm.get_total_savings() - fm.get_total_expenses()):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

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
            st.download_button(
                label="Exportar despesas como CSV",
                data=expenses_df.to_csv(index=False).encode('utf-8'),
                file_name="despesas.csv",
                mime="text/csv",
            )

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
            st.download_button(
                label="Exportar entradas mensais como CSV",
                data=savings_df.to_csv(index=False).encode('utf-8'),
                file_name="entradas_mensais.csv",
                mime="text/csv",
            )           

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
        
    # Add a logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.finance_manager = None
        st.rerun()


        
# Run the app
if __name__ == "__main__":
    main()