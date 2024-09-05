# Finance Manager App

O **Finance Manager App** é uma aplicação de gerenciamento financeiro construída usando **Streamlit** e conectada ao **Firebase** para armazenamento de dados. O aplicativo permite que usuários registrem e gerenciem suas despesas, com salvamento automático dos dados no Firebase.

## Funcionalidades

- Adicionar e editar despesas
- Salvar despesas automaticamente no Firebase
- Interface interativa com Streamlit
- Integração com o Firebase para autenticação e armazenamento de dados
- Cadastro de novos usuários com e-mail e senha

## Tecnologias Utilizadas

- [Streamlit](https://streamlit.io/) - Framework para criação de interfaces web interativas em Python.
- [Firebase](https://firebase.google.com/) - Plataforma para autenticação e armazenamento de dados na nuvem.
- [Python](https://www.python.org/) - Linguagem de programação usada no desenvolvimento.

## Como Instalar e Executar o Projeto

1. Clone este repositório:

    ```bash
    git clone https://github.com/seu-usuario/finance-manager-app.git
    ```

2. Entre no diretório do projeto:

    ```bash
    cd finance-manager-app
    ```

3. Crie e ative um ambiente virtual (opcional, mas recomendado):

    ```bash
    python -m venv venv
    source venv/bin/activate  # Para Linux/MacOS
    venv\Scripts\activate  # Para Windows
    ```

4. Instale as dependências:

    ```bash
    pip install -r requirements.txt
    ```

5. Configure as variáveis de ambiente sensíveis:

    No arquivo `.streamlit/secrets.toml`, configure suas chaves do Firebase:

    ```toml
    [firebase]
    api_key = "SUA_API_KEY"
    auth_domain = "SEU_AUTH_DOMAIN"
    database_url = "SEU_DATABASE_URL"
    project_id = "SEU_PROJECT_ID"
    storage_bucket = "SEU_STORAGE_BUCKET"
    messaging_sender_id = "SEU_MESSAGING_SENDER_ID"
    app_id = "SEU_APP_ID"
    ```

6. Execute o aplicativo Streamlit:

    ```bash
    streamlit run app.py
    ```

## Como Funciona

### Salvamento Automático no Firebase

Ao adicionar ou editar uma despesa, os dados são automaticamente salvos no Firebase, sem a necessidade de clicar em um botão de salvar. Isso é implementado através da função `save_expenses_to_firebase`, que é chamada sempre que uma nova despesa é adicionada ou editada.

### Firebase

Este projeto utiliza o Firebase tanto para autenticação de usuários quanto para o armazenamento de dados financeiros. Os dados são armazenados em uma estrutura hierárquica organizada por usuário.

### Estrutura de Dados

Cada despesa contém as seguintes informações:
- **ID**: Identificador único da despesa.
- **Estabelecimento**: Nome do local onde a despesa foi realizada.
- **Categoria**: Categoria da despesa (e.g., alimentação, transporte).
- **Valor**: Valor da despesa.
- **Data**: Data em que a despesa foi feita.

## Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir um pull request ou relatar um problema.

