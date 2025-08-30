# 📦 BratzCORE – O núcleo do seu mercado

API (em teste) desenvolvida para a disciplina de Desenvolvimento Web III; Aqui está sendo criada a API responsável por criar contas, organizar todos os sistemas e servir como núcleo do seu mercado.
- BratzCORE - Núcleo
- BratzCAIXA - App desktop
- BratzADM - Web App
- BratzSTOCK - App Mobile


## 🧱 Estrutura do projeto:
```bash
BratzApi/
│
├── app.py                # Arquivo principal do app Flask
├── config.py             # Configurações do Flask e banco de dados
├── models/
│   └── __init__.py       # Inicializador
│   └── user_model.py     # Modelo de usuário
│   └── product_model.py  # Modelo de produto
├── routes/
│   └── __init__.py       # Inicializador
│   └── accounts.py       # Rota de contas
│   └── auth.py           # Rota de autenticação
│   └── clients.py        # Rota de clientes
│   └── finance.py        # Rota de finança
│   └── products.py       # Rota de produtos
│   └── stocks.py         # Rota de estoques
├── routes/
│   └── __init__.py       # Inicializador
│   └── auth.py           # Utilitário de autenticação (para token e autoridade)
│   └── extensions.py     # Extnsões de banco de dados
│   └── jwt_manager.py    # Suporte ao JWT de segurança
│   └── responses.py      # Utilitário de respostas (para padronização)
├── seeder.py             # Script de teste de conexão
├── requirements.txt      # Dependências do projeto
├── migrations/           # Diretório de migrações do banco de dados
└── README.md             # Este arquivo
```

## 🛠️ Instalação
1. Clone o repositório

```bash
https://github.com/vichsort/BratzCORE.git
cd bratzcore

```

2. Crie e ative o venv
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS
```

3. Faça a instalação de dependências
```bash
pip install -r requirements.txt
```

Caso enfrente problemas, instale o `psycopg[binary]` desta forma:
```bash
pip install "psycopg[binary]"
```

## ⚙️ Configuração
Estamos usando uma configuração local de banco de dados. Por isso, ao instalar, dite sua instância dentro do arquivo `config.py`
```python
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg://usuario:senha@localhost:5432/seubanco"
```
Então, rode o script de iniciação de banco de dados:
```python
python seeder.py
```


## 🎮 Executando o projeto
Apenas inicie o projeto inicial 

```bash
python app.py
```

## 🗺️ Mapa de requisições
### Contas
`/bratz/auth/login` POST - Login <br>
`/bratz/accounts` GET - Vê as contas<br>
`/bratz/accounts/{id}` GET - Vê uma conta específica<br>
`/bratz/accounts/{id}/profile` PATCH - Muda informações de um perfil<br>
`/bratz/accounts/{id}/privileges` PATCH - Muda previlégios de um perfil<br>
`/bratz/accounts` POST - Criação de contas<br>
`/bratz/accounts/{id}` DELETE - Deleta uma conta<br>

### Clientes
`/bratz/clients` GET - Vê todos os clientes<br>
`/bratz/clients/{id}` GET - Vê um cliente específico<br>
`/bratz/clients/{id}` PATCH - Muda dados de um cliente específico<br>
`/bratz/clients` POST - Adiciona um cliente<br>

### Estoques
`/bratz/stock` GET - Vê todos os estoques (a fazer) <br>
`/bratz/stock/{id}` GET - Vê um estoque esoecífico (e sua movimentação) (a fazer) <br>
`/bratz/stock` POST - Cria um estoque (a fazer) <br>
`/bratz/stock/{id}` PATCH - Modifica um estoque específico (a fazer) <br>

### Produtos
`/bratz/products` GET - Vê a lista de itens<br>
`/bratz/products/{id}` GET - Vê um item específico<br>
`/bratz/products/{id}` PATCH - Modifica o item<br>
`/bratz/products` POST - Cria um item <br>

### Armazenamento
`/bratz/stock/{id}/storage/{item}` GET - Vê quantidade de tal item dentro do armazenamento do estoque (a fazer) <br>
`/bratz/stock/{id}/storage/{item}` POST - Adiciona um produto ao armazenamento. {item} é o id do item (a fazer) <br>
`/bratz/stock/{id}/storage/{item}/item` PATCH - Muda dados do item específico (a fazer) <br>
`/bratz/stock/{id}/storage/{item}/quantity` PATCH - Muda quantidade do item específico. (a fazer) <br>

### ADMIN
`/bratz/stats/overview` GET - Vê estatísticas
`/bratz/finance` GET - Vê dados financeiros. 

---

## CRIANDO UMA CONTA
Usando o token que você conseguiu como Bearer Token, você manda esse corpo (`http://127.0.0.1:5000/bratz/accounts`)
```
{
  "email": "new.subowner@market.com",
  "password": "StrongPass123!",
  "confirm_password": "StrongPass123!",
  "account_type": "FULL_MANAGEMENT"
}
```

retorno
```
{
    "data": {
        "account_type": "FULL_MANAGEMENT",
        "email": "new.subowner@market.com",
        "id": 2,
        "privileges": {
            "ACCOUNT_CREATOR": false,
            "ADMIN": true,
            "BINDING": false,
            "CLIENT_CREATOR": true,
            "DOWN_STORAGE": false,
            "FINANCE": false,
            "MICRO_ACCOUNT_CREATOR": true,
            "NF": true,
            "PANEL_MODIFIER": false,
            "REDO": true,
            "STAT_VIEWER": false,
            "STOCK_MODIFIER": true,
            "STORAGE_MODIFIER": true,
            "UNDO": true
        }
    },
    "message": "Account created successfully",
    "status": "success"
}
```


