# BDP — Dias da Semana (Padrão 1–7)

## Objetivo
Padronizar dias da semana em todas as camadas (API e PostgreSQL) usando o mesmo sistema numérico:

| Número | Dia |
|---:|---|
| 1 | Segunda-feira |
| 2 | Terça-feira |
| 3 | Quarta-feira |
| 4 | Quinta-feira |
| 5 | Sexta-feira |
| 6 | Sábado |
| 7 | Domingo |

Esse padrão é equivalente ao ISO-8601 e ao `EXTRACT(ISODOW ...)` no PostgreSQL.

## Banco de Dados (PostgreSQL)
O script [01_init_schema.sql](file:///c:/Users/Jur%C3%ADdico/Documents/appbdp/database/01_init_schema.sql) implementa:

- `DOMAIN dia_semana_1_7` com validação `1..7`
- `configuracao_horarios.diadasemana` como `dia_semana_1_7`
- Funções utilitárias:
  - `bdp_dia_semana_nome(int)` → `text`
  - `bdp_dia_semana_num(text)` → `int` validado
- Capacidade por faixa usando `EXTRACT(ISODOW FROM p_datareserva)`

### Exemplos SQL

Inserir configuração para domingo:

```sql
INSERT INTO configuracao_horarios (diadasemana, horaabertura, horafechamento, capacidademaximapessoas)
VALUES (7, '18:00', '23:59', 60);
```

Converter número para texto:

```sql
SELECT bdp_dia_semana_nome(7); -- Domingo
```

Converter texto para número:

```sql
SELECT bdp_dia_semana_num('segunda-feira'); -- 1
SELECT bdp_dia_semana_num('sábado');        -- 6
```

## API (Python/FastAPI)
O módulo [weekdays.py](file:///c:/Users/Jur%C3%ADdico/Documents/appbdp/app/weekdays.py) define:

- `WEEKDAY_INT_TO_NAME_PT` e `WEEKDAY_NAME_TO_INT_PT`
- `weekday_int_to_name(day)` e `weekday_name_to_int(name)`
- `validate_weekday_int(day)`

O cálculo de dia da semana para consultas de capacidade usa `date.isoweekday()` (1..7), alinhado ao banco.

## Testes
Os testes estão em `tests/`:

- Unitários: [test_weekdays.py](file:///c:/Users/Jur%C3%ADdico/Documents/appbdp/tests/test_weekdays.py)
- Integração (PostgreSQL): [test_integration_reservas_domingo.py](file:///c:/Users/Jur%C3%ADdico/Documents/appbdp/tests/test_integration_reservas_domingo.py)

Rodar unitários:

```bash
python -m pytest -q
```

Rodar integração (necessário banco PostgreSQL dedicado de teste):

```bash
export DATABASE_URL_TEST="postgresql+asyncpg://usuario:senha@localhost:5432/bdp_test"
python -m pytest -q
```

O teste de integração executa o script `database/01_init_schema.sql` no banco configurado em `DATABASE_URL_TEST`.
