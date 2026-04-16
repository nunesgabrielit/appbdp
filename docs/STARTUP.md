# Inicialização automática (um comando)

## Requisitos
- Python 3.11+
- PostgreSQL rodando localmente
- Banco já criado (ex.: `bdp_app`)

## Configuração única
Crie um arquivo `.env` na raiz do projeto (mesma pasta do `requirements.txt`) com:

```env
DATABASE_URL=postgresql+asyncpg://usuario:senha@localhost:5432/bdp_app
```

## Executar (um comando)
Opções equivalentes:

```powershell
.\start.ps1
```

ou (duplo clique no Windows):
- `start.cmd`

ou:

```powershell
python .\start_bdp.py
```

O processo faz:
1) Instala somente dependências faltantes (a partir do `requirements.txt`)
2) Valida conexão com PostgreSQL via `SELECT 1`
3) Inicia `uvicorn app.main:app --reload`

Logs são gravados em `bdp_startup.log`.

## Erros comuns
- `DATABASE_URL não está configurada`  
  Crie/ajuste o `.env` na raiz do projeto.

- `Falha ao conectar no PostgreSQL usando DATABASE_URL`  
  Verifique se o serviço do Postgres está rodando, se o banco existe, e se usuário/senha estão corretos.

- `Falha ao instalar dependências`  
  Rode manualmente:

```powershell
python -m pip install -r requirements.txt
```
