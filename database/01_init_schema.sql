-- =====================================================================
-- BDP - Banco de Dados PostgreSQL (Reservas de Mesas)
-- =====================================================================

-- Limpa tabelas antigas caso voce precise rodar o script novamente
DROP TABLE IF EXISTS reservas CASCADE;
DROP TABLE IF EXISTS configuracao_horarios CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- Extensoes necessarias
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- =====================================================================
-- ENUMs
-- =====================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usuario_role') THEN
    CREATE TYPE usuario_role AS ENUM ('Cliente', 'Admin');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reserva_status') THEN
    CREATE TYPE reserva_status AS ENUM (
      'Pendente',
      'Aguardando_Confirmacao',
      'Confirmado',
      'Cancelado',
      'Concluido',
      'No_Show'
    );
  END IF;
END $$;

-- =====================================================================
-- TABELA: Usuarios
-- =====================================================================

CREATE TABLE IF NOT EXISTS usuarios (
  id               uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  nome             text          NOT NULL CHECK (length(trim(nome)) >= 2),
  email            citext        NOT NULL,
  telefonewhatsapp text          NOT NULL CHECK (length(trim(telefonewhatsapp)) >= 8),
  role             usuario_role  NOT NULL DEFAULT 'Cliente',
  datacriacao      timestamptz   NOT NULL DEFAULT now(),

  CONSTRAINT usuarios_email_uk UNIQUE (email)
);

-- =====================================================================
-- TABELA: Configuracao_Horarios
-- Padrao unificado: 1=segunda ... 7=domingo
-- =====================================================================

CREATE TABLE IF NOT EXISTS configuracao_horarios (
  id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  diadasemana             smallint    NOT NULL CHECK (diadasemana BETWEEN 1 AND 7),
  horaabertura            time        NOT NULL,
  horafechamento          time        NOT NULL,
  capacidademaximapessoas integer     NOT NULL CHECK (capacidademaximapessoas > 0),

  CONSTRAINT configuracao_horarios_intervalo_ck CHECK (horafechamento > horaabertura)
);

CREATE INDEX IF NOT EXISTS configuracao_horarios_dia_idx
  ON configuracao_horarios (diadasemana, horaabertura, horafechamento);

-- =====================================================================
-- TABELA: Reservas
-- =====================================================================

CREATE TABLE IF NOT EXISTS reservas (
  id                 uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
  usuarioid          uuid           NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
  datareserva        date           NOT NULL,
  horareserva        timestamptz    NOT NULL,
  quantidadepessoas  integer        NOT NULL CHECK (quantidadepessoas > 0),
  status             reserva_status NOT NULL DEFAULT 'Pendente',
  datacriacao        timestamptz    NOT NULL DEFAULT now(),
  dataatualizacao    timestamptz    NOT NULL DEFAULT now(),

  CONSTRAINT reservas_data_hora_consistencia_ck
    CHECK (datareserva = (horareserva AT TIME ZONE 'America/Rio_Branco')::date)
);

-- Indice para rotina diaria (datareserva + status)
CREATE INDEX IF NOT EXISTS reservas_data_status_idx
  ON reservas (datareserva, status);

-- Regra de negocio: impedir 2 reservas ATIVAS no mesmo dia por usuario
CREATE UNIQUE INDEX IF NOT EXISTS reservas_uk_usuario_data_ativa
  ON reservas (usuarioid, datareserva)
  WHERE status IN ('Pendente','Aguardando_Confirmacao','Confirmado');

-- =====================================================================
-- Gatilhos
-- =====================================================================

CREATE OR REPLACE FUNCTION reservas_set_dataatualizacao()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.dataatualizacao := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reservas_set_dataatualizacao ON reservas;
CREATE TRIGGER trg_reservas_set_dataatualizacao
BEFORE UPDATE ON reservas
FOR EACH ROW
EXECUTE FUNCTION reservas_set_dataatualizacao();

-- Garante consistencia do horario em relacao ao fuso de Rio Branco
CREATE OR REPLACE FUNCTION reservas_validar_data_hora()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.datareserva <> (NEW.horareserva AT TIME ZONE 'America/Rio_Branco')::date THEN
    RAISE EXCEPTION
      'datareserva (%) deve bater com a data de horareserva no fuso local (%)',
      NEW.datareserva,
      (NEW.horareserva AT TIME ZONE 'America/Rio_Branco')::date;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reservas_validar_data_hora ON reservas;
CREATE TRIGGER trg_reservas_validar_data_hora
BEFORE INSERT OR UPDATE ON reservas
FOR EACH ROW
EXECUTE FUNCTION reservas_validar_data_hora();

-- =====================================================================
-- Funcao para checar capacidade por faixa
-- Padrao: ISODOW => 1=segunda ... 7=domingo
-- =====================================================================

CREATE OR REPLACE FUNCTION bdp_checar_capacidade_reserva(
  p_datareserva date,
  p_horareserva timestamptz,
  p_quantidadepessoas integer
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  v_dia smallint;
  v_hora_local time;
  v_capacidade integer;
  v_total_ativos integer;
BEGIN
  v_dia := EXTRACT(ISODOW FROM p_datareserva)::smallint;
  v_hora_local := (p_horareserva AT TIME ZONE 'America/Rio_Branco')::time;

  SELECT ch.capacidademaximapessoas
    INTO v_capacidade
  FROM configuracao_horarios ch
  WHERE ch.diadasemana = v_dia
    AND v_hora_local >= ch.horaabertura
    AND v_hora_local < ch.horafechamento
  ORDER BY ch.horaabertura DESC
  LIMIT 1;

  IF v_capacidade IS NULL THEN
    RAISE EXCEPTION
      'Nao existe configuracao de horario para a data/horario informados (dia %, hora %)',
      v_dia, v_hora_local;
  END IF;

  SELECT COALESCE(SUM(r.quantidadepessoas), 0)
    INTO v_total_ativos
  FROM reservas r
  WHERE r.datareserva = p_datareserva
    AND (r.horareserva AT TIME ZONE 'America/Rio_Branco')::time = v_hora_local
    AND r.status IN ('Pendente','Aguardando_Confirmacao','Confirmado');

  RETURN (v_total_ativos + p_quantidadepessoas) <= v_capacidade;
END;
$$;

-- =====================================================================
-- MOCK DATA
-- =====================================================================

INSERT INTO usuarios (id, nome, email, telefonewhatsapp, role)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'Admin BDP', 'admin@bdp.com', '+55999990000', 'Admin'),
  ('22222222-2222-2222-2222-222222222222', 'Cliente Um', 'cliente1@bdp.com', '+55999990001', 'Cliente'),
  ('33333333-3333-3333-3333-333333333333', 'Cliente Dois', 'cliente2@bdp.com', '+55999990002', 'Cliente')
ON CONFLICT (email) DO NOTHING;

-- 1=segunda ... 7=domingo
INSERT INTO configuracao_horarios (diadasemana, horaabertura, horafechamento, capacidademaximapessoas)
VALUES
  (1, '18:00', '23:00', 50),
  (2, '18:00', '23:00', 50),
  (3, '18:00', '23:00', 50),
  (4, '18:00', '23:00', 50),
  (5, '18:00', '23:00', 50),
  (6, '18:00', '23:59', 60),
  (7, '18:00', '23:59', 60)
ON CONFLICT DO NOTHING;

INSERT INTO reservas (usuarioid, datareserva, horareserva, quantidadepessoas, status)
VALUES
  ('22222222-2222-2222-2222-222222222222', DATE '2026-03-22', TIMESTAMPTZ '2026-03-22 20:00:00-05', 2, 'Pendente'),
  ('33333333-3333-3333-3333-333333333333', DATE '2026-03-22', TIMESTAMPTZ '2026-03-22 21:00:00-05', 4, 'Confirmado'),
  ('22222222-2222-2222-2222-222222222222', DATE '2026-03-23', TIMESTAMPTZ '2026-03-23 19:00:00-05', 2, 'Cancelado');
