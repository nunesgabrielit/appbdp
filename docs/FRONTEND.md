# Frontend BDP

O frontend da fase 3 foi criado em [web/](C:/Users/gabri/OneDrive/Documentos/appbdp/web) com:

- React
- Vite
- TypeScript

## Como rodar

Na pasta `web`, instale as dependencias:

```powershell
npm install
```

Crie um `.env` em `web/` com base no arquivo `.env.example`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Depois execute:

```powershell
npm run dev
```

O frontend abre em:

```text
http://127.0.0.1:5173
```

## Fluxo inicial

1. Cadastre um usuario.
2. O UUID retornado ja fica pronto para ser usado na reserva.
3. Crie a reserva com `horaReserva` no formato ISO com `-05:00`.
4. Consulte, confirme ou cancele reservas do dia na mesma tela.

## Observacao importante

O backend recebeu liberacao de CORS para:

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://localhost:4173`
- `http://127.0.0.1:4173`
