# 📦 BratzCORE – O núcleo do seu mercado

API desenvolvida para a disciplina de Desenvolvimento Web III; O coração do seu mercado está conosco. Use já o sistema Bratz e automatize seu serviço.

## 🧱 Estrutura do projeto:
```bash
BratzCORE/
├── migrations/             # Contém os scripts de migração do banco de dados (Alembic)
├── models/                 # Define os modelos de dados (tabelas) com SQLAlchemy
│   ├── init.py
│   ├── client.py
│   ├── finances.py
│   ├── product.py
│   ├── stock.py
│   ├── supplier.py
│   └── user.py
├── routes/                 # Define os endpoints da API (Blueprints)
│   ├── init.py
│   ├── accounts.py
│   ├── auth.py
│   ├── clients.py
│   ├── finance.py
│   ├── products.py
│   ├── stocks.py
│   └── suppliers.py
├── utils/                  # Módulos de utilidade (autenticação, respostas, etc.)
│   ├── init.py
│   ├── accounts.py
│   ├── auth.py
│   ├── error_handling.py
│   ├── extensions.py
│   ├── jwt_manager.py
│   └── responses.py
├── .env                    # Arquivo para variáveis de ambiente (NÃO VERSIONADO)
├── .gitignore              # Arquivos e pastas a serem ignorados pelo Git
├── app.py                  # Ponto de entrada da aplicação (Application Factory)
├── config.py               # Carrega as configurações da aplicação
├── requirements.txt        # Lista de dependências Python do projeto
└── seeder.py               # Script para popular o banco de dados com dados de teste
```

## 🛠️ Instalação
1. Clone o repositório

```bash
https://github.com/4Before/BratzCORE.git
cd BratzCORE

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
É importante que você tenha em mente que a produção está sendo desenvolvida usando um banco de dados serverless da NeonDB. Aqui está a forma de configurar o sistema para que você possa conectar sua database:
- Crie um arquivo `.env` contendo chaves secretas e sua string de conexão do banco de dados (NeonDB ou PostgreSQL local).
```env
SECRET_KEY="sua-chave-secreta-aqui"
JWT_SECRET_KEY="sua-outra-chave-secreta-aqui"
DATABASE_URL="postgresql+psycopg://user:password@host:port/dbname"
```
- Realize a migração de update do sistema do banco de dados usando o comando migrate
```bash
flask db upgrade
```
- O seu sistema então possui as tabelas constituintes da aplicação. Agora, simplesmente popule o banco de dados para teste (opcional).
```bash
python seeder.py
```

## 🎮 Executando o projeto
Apenas inicie o projeto inicial 

```bash
python app.py
```

## 🗺️ Mapa de requisições

Todas as rotas são prefixadas com `/bratz`.

### Autenticação (`/auth`)
- `POST - /bratz/auth/register`: Registra um novo usuário básico.
- `POST - /bratz/auth/login`: Realiza login e obtém um token JWT.

### Contas de Usuário (`/accounts`)
- `GET    - /bratz/accounts`: Lista todas as contas de usuário.
- `POST   - /bratz/accounts`: Cria uma nova conta de usuário (requer privilégio).
- `GET    - /bratz/accounts/<id>`: Busca os dados de uma conta específica.
- `PATCH  - /bratz/accounts/<id>/profile`: Atualiza o perfil de uma conta.
- `PATCH  - /bratz/accounts/<id>/privileges`: Atualiza privilégios de uma conta do tipo `CUSTOM`.
- `DELETE - /bratz/accounts/<id>`: Deleta uma conta.

### Clientes (`/clients`)
- `GET    - /bratz/clients`: Lista ou busca por clientes.
- `POST   - /bratz/clients`: Cria um novo cliente.
- `GET    - /bratz/clients/<id>`: Busca um cliente específico.
- `PUT    - /bratz/clients/<id>`: Atualiza os dados de um cliente.
- `DELETE - /bratz/clients/<id>`: Deleta um cliente.
- `GET    - /bratz/clients/<id>/discounts`: Lista os descontos de um cliente.
- `POST   - /bratz/clients/<id>/discounts`: Adiciona ou atualiza um desconto para um cliente.
- `DELETE - /bratz/clients/<id>/discounts/<category>`: Remove um desconto específico de um cliente.

### Produtos (`/products`)
- `GET    - /bratz/products`: Lista ou busca produtos (com estoque e paginação).
- `POST   - /bratz/products`: Cria um novo produto.
- `GET    - /bratz/products/<id>`: Busca um produto específico (com estoque).
- `PUT    - /bratz/products/<id>`: Atualiza os dados de um produto.
- `DELETE - /bratz/products/<id>`: Deleta um produto.
- `GET    - /bratz/products/reports/low-stock`: Gera relatório de produtos com estoque baixo.
- `GET    - /bratz/products/reports/expiring`: Gera relatório de produtos próximos do vencimento.

### Fornecedores (`/suppliers`)
- `GET    - /bratz/suppliers`: Lista todos os fornecedores.
- `POST   - /bratz/suppliers`: Cria um novo fornecedor.
- `GET    - /bratz/suppliers/<id>`: Busca um fornecedor específico.
- `PUT    - /bratz/suppliers/<id>`: Atualiza os dados de um fornecedor.
- `DELETE - /bratz/suppliers/<id>`: Deleta um fornecedor.
- `GET    - /bratz/suppliers/<id>/products`: Lista todos os produtos de um fornecedor.

### Estoques (`/stocks`)
- `GET    - /bratz/stocks`: Lista todos os locais de armazenamento.
- `POST   - /bratz/stocks`: Cria um novo local de armazenamento.
- `GET    - /bratz/stocks/<id>`: Busca um local de armazenamento específico.
- `PUT    - /bratz/stocks/<id>`: Atualiza os dados de um local de armazenamento.
- `DELETE - /bratz/stocks/<id>`: Deleta um local de armazenamento.
- `GET    - /bratz/stocks/<id>/products`: Lista os produtos e suas quantidades em um estoque.
- `POST   - /bratz/stocks/<id>/products/<product_id>`: Adiciona ou incrementa um produto em um estoque.
- `PATCH  - /bratz/stocks/<id>/products/<product_id>/quantity`: Define a quantidade exata de um produto em um estoque.

### Finanças (`/finances`)
- `POST   - /bratz/finances/register-sell`: Registra uma nova venda.
- `GET    - /bratz/finances/sells`: Lista o histórico de todas as vendas (admin).
- `GET    - /bratz/finances/specific/<cashier_id>/sells`: Lista o histórico de vendas de um caixa.
- `GET    - /bratz/finances/summary/daily`: Retorna um resumo financeiro consolidado para um dia.
- `GET    - /bratz/finances/summary/monthly`: Retorna um resumo financeiro consolidado para um mês.
- `GET    - /bratz/finances/reports/profit-margin`: Gera um relatório de margem de lucro em um período.
- `GET    - /bratz/finances/reports/sales-flow`: Retorna o faturamento diário em um período (para gráficos).
- `GET    - /bratz/finances/reports/payment-methods`: Agrupa o faturamento por método de pagamento.
- `GET    - /bratz/finances/reports/sales-by-category`: *(A Fazer)* Rankeia as categorias de produtos por faturamento.
- `GET    - /bratz/finances/reports/sales-by-operator`: *(A Fazer)* Mostra o desempenho de vendas por operador.
- `GET    - /bratz/finances/reports/top-clients`: *(A Fazer)* Lista os clientes que mais compraram.
- `POST   - /bratz/finances/entries`: *(A Fazer)* Registra uma nova despesa ou outra receita.

---