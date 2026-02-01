# 🏠 Casa Split

Aplicação Streamlit para gerenciar despesas compartilhadas entre duas pessoas.

## 📋 Requisitos

- Python 3.9+
- PostgreSQL (local ou remoto)
- venv (virtual environment)

## 🚀 Como Rodar Localmente

### 1. Clonar o repositório
```bash
git clone https://github.com/kmonthiago/casa-split.git
cd casa-split
```

### 2. Criar e ativar venv
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# ou
.venv\Scripts\activate  # Windows
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar banco de dados

#### Opção A: PostgreSQL Local
```bash
# Criar banco de dados local
createdb casa_split

# Configurar variável de ambiente
export DATABASE_URL="postgresql://seu_usuario:sua_senha@localhost:5432/casa_split"
```

#### Opção B: Usar Neon (PostgreSQL hospedado)
1. Criar conta em https://neon.tech
2. Criar um novo projeto
3. Copiar a connection string
4. Configurar variável:
```bash
export DATABASE_URL="postgresql://seu_usuario:sua_senha@ep-xxx.neon.tech/casa_split"
```

### 5. Rodar a aplicação
```bash
streamlit run app.py
```

A aplicação abrirá em `http://localhost:8501`

## 🎯 Funcionalidades

- ➕ **Adicionar Gasto**: Com suporte a categorias personalizáveis e divisão customizável
- 📊 **Resumo do Mês**: Visualize gastos totais e saldo de cada pessoa
- 🔐 **Fechamento**: Registre acertos mensais
- ⚙️ **Configurações**: Gerencie categorias personalizadas

## 📝 Variáveis de Ambiente

- `DATABASE_URL`: String de conexão PostgreSQL (obrigatória)

## 🗄️ Estrutura do Projeto

```
casa-split/
├── app.py           # Aplicação principal
├── db.py            # Funções de banco de dados
├── logic.py         # Lógica de cálculos
├── parser.py        # Parser de categorias
├── categorias.json  # Categorias personalizadas
└── requirements.txt # Dependências
```

## 📦 Dependências

- `streamlit==1.41.1` - Framework web
- `psycopg[binary]==3.2.13` - Driver PostgreSQL
