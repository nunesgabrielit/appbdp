# Deploy no Railway

Este projeto sobe o backend FastAPI com:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Arquivos adicionados para o deploy

- `main.py`: ponto de entrada na raiz para a autodetecção do Railway
- `Procfile`: fallback de start command
- `nixpacks.toml`: start command explícito para Nixpacks/Railpack
- `railway.toml`: configuração em código do serviço Railway

## Variáveis obrigatórias

```env
DATABASE_URL=postgresql+asyncpg://usuario:senha@host:5432/banco
```

## Variáveis recomendadas

```env
ADMIN_ACCESS_KEY=uma_chave_forte
```

## Se ainda falhar

1. Confirme que o serviço está apontando para a raiz deste repositório.
2. Em `Settings > Build`, deixe o builder como `Railpack`.
3. Em `Settings > Deploy`, confira se o Start Command não está sobrescrito com um valor antigo.
4. Redeploy depois de subir estes arquivos para o GitHub.
