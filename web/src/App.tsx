import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  cancelarReserva,
  confirmarReserva,
  createReserva,
  createUsuario,
  getConfiguracoesHorarios,
  getReservasByDate,
  getReservasHoje,
  getUsuarios,
} from "./api";
import type { ConfiguracaoHorario, Reserva, ReservaInput, Usuario, UsuarioInput } from "./types";

const apiUrl = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const RIO_BRANCO_OFFSET = "-05:00";
const ADMIN_STORAGE_KEY = "bdp_admin_key";

type ViewMode = "reserva" | "admin";

const weekdayLabels: Record<number, string> = {
  1: "Segunda-feira",
  2: "Terca-feira",
  3: "Quarta-feira",
  4: "Quinta-feira",
  5: "Sexta-feira",
  6: "Sabado",
  7: "Domingo",
};

const rioBrancoPartsNow = () => {
  const formatter = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "America/Rio_Branco",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  const parts = formatter.formatToParts(new Date());
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));

  return {
    date: `${map.year}-${map.month}-${map.day}`,
    time: `${map.hour}:${map.minute}`,
  };
};

const buildReservaIso = (date: string, time: string) => `${date}T${time}:00${RIO_BRANCO_OFFSET}`;

const formatReservaHora = (isoString: string) => {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Rio_Branco",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

const getIsoWeekday = (dateString: string) => {
  if (!dateString) {
    return null;
  }

  const [year, month, day] = dateString.split("-").map(Number);
  const utcDate = new Date(Date.UTC(year, month - 1, day));
  const dow = utcDate.getUTCDay();
  return dow === 0 ? 7 : dow;
};

const toMinutes = (hhmmss: string) => {
  const [hour, minute] = hhmmss.split(":").map(Number);
  return hour * 60 + minute;
};

const toHourLabel = (minutes: number) => {
  const hour = String(Math.floor(minutes / 60)).padStart(2, "0");
  const minute = String(minutes % 60).padStart(2, "0");
  return `${hour}:${minute}`;
};

const generateTimeOptions = (configuracoes: ConfiguracaoHorario[]) => {
  const seen = new Set<string>();
  const options: string[] = [];

  for (const configuracao of configuracoes) {
    let cursor = toMinutes(configuracao.horaAbertura);
    const end = toMinutes(configuracao.horaFechamento);

    while (cursor < end) {
      const label = toHourLabel(cursor);
      if (!seen.has(label)) {
        seen.add(label);
        options.push(label);
      }
      cursor += 30;
    }
  }

  return options.sort();
};

const getUsuarioNome = (usuarios: Usuario[], usuarioId: string) =>
  usuarios.find((usuario) => usuario.id === usuarioId)?.nome ?? `${usuarioId.slice(0, 8)}...`;

function App() {
  const now = rioBrancoPartsNow();

  const [view, setView] = useState<ViewMode>("reserva");
  const [usuarioForm, setUsuarioForm] = useState<UsuarioInput>({
    nome: "",
    email: "",
    telefoneWhatsApp: "",
    role: "Cliente",
  });
  const [reservaData, setReservaData] = useState(now.date);
  const [reservaHoraLocal, setReservaHoraLocal] = useState(now.time);
  const [reservaUsuarioId, setReservaUsuarioId] = useState("");
  const [reservaQuantidade, setReservaQuantidade] = useState(1);
  const [historicoData, setHistoricoData] = useState(now.date);
  const [configuracoes, setConfiguracoes] = useState<ConfiguracaoHorario[]>([]);
  const [usuariosAdmin, setUsuariosAdmin] = useState<Usuario[]>([]);
  const [ultimoUsuario, setUltimoUsuario] = useState<Usuario | null>(null);
  const [reservasHoje, setReservasHoje] = useState<Reserva[]>([]);
  const [reservasHistorico, setReservasHistorico] = useState<Reserva[]>([]);
  const [adminKeyInput, setAdminKeyInput] = useState("");
  const [adminKey, setAdminKey] = useState("");
  const [adminUnlocked, setAdminUnlocked] = useState(false);
  const [loadingPublicData, setLoadingPublicData] = useState(false);
  const [loadingAdminData, setLoadingAdminData] = useState(false);
  const [loadingHistorico, setLoadingHistorico] = useState(false);
  const [submittingUsuario, setSubmittingUsuario] = useState(false);
  const [submittingReserva, setSubmittingReserva] = useState(false);
  const [submittingAdminLogin, setSubmittingAdminLogin] = useState(false);
  const [feedback, setFeedback] = useState<string>("Area publica pronta para novas reservas.");
  const [error, setError] = useState<string>("");

  const horaReservaMontada = buildReservaIso(reservaData, reservaHoraLocal);
  const weekday = getIsoWeekday(reservaData);

  const configuracoesDoDia = useMemo(() => {
    if (!weekday) {
      return [];
    }
    return configuracoes.filter((configuracao) => configuracao.diaDaSemana === weekday);
  }, [configuracoes, weekday]);

  const horariosSugeridos = useMemo(() => generateTimeOptions(configuracoesDoDia), [configuracoesDoDia]);

  const metricasAdmin = useMemo(() => {
    const reservasAtivas = reservasHoje.filter((reserva) =>
      ["Pendente", "Aguardando_Confirmacao", "Confirmado"].includes(reserva.status),
    );
    return {
      usuarios: usuariosAdmin.length,
      reservasHoje: reservasHoje.length,
      reservasAtivas: reservasAtivas.length,
      totalPessoasHoje: reservasHoje.reduce((total, reserva) => total + reserva.quantidadePessoas, 0),
    };
  }, [reservasHoje, usuariosAdmin]);

  const carregarConfiguracoes = async () => {
    setLoadingPublicData(true);
    setError("");
    try {
      const configuracoesData = await getConfiguracoesHorarios();
      setConfiguracoes(configuracoesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar os horarios disponiveis.");
    } finally {
      setLoadingPublicData(false);
    }
  };

  const carregarHistoricoAdmin = async (data: string, accessKey: string) => {
    setLoadingHistorico(true);
    try {
      const reservas = await getReservasByDate(data, accessKey);
      setReservasHistorico(reservas);
    } finally {
      setLoadingHistorico(false);
    }
  };

  const carregarAdmin = async (accessKey: string) => {
    setLoadingAdminData(true);
    setError("");
    try {
      const [usuarios, reservasHojeData, historico] = await Promise.all([
        getUsuarios(accessKey),
        getReservasHoje(accessKey),
        getReservasByDate(historicoData, accessKey),
      ]);
      setUsuariosAdmin(usuarios);
      setReservasHoje(reservasHojeData);
      setReservasHistorico(historico);
      setAdminKey(accessKey);
      setAdminUnlocked(true);
      setFeedback("Acesso administrativo liberado.");
      window.localStorage.setItem(ADMIN_STORAGE_KEY, accessKey);
    } catch (err) {
      setAdminUnlocked(false);
      setAdminKey("");
      window.localStorage.removeItem(ADMIN_STORAGE_KEY);
      setError(err instanceof Error ? err.message : "Nao foi possivel entrar no admin.");
      throw err;
    } finally {
      setLoadingAdminData(false);
    }
  };

  useEffect(() => {
    void carregarConfiguracoes();

    const savedAdminKey = window.localStorage.getItem(ADMIN_STORAGE_KEY);
    if (savedAdminKey) {
      setAdminKeyInput(savedAdminKey);
      void carregarAdmin(savedAdminKey).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (horariosSugeridos.length === 0) {
      return;
    }

    if (!horariosSugeridos.includes(reservaHoraLocal)) {
      setReservaHoraLocal(horariosSugeridos[0]);
    }
  }, [horariosSugeridos, reservaHoraLocal]);

  const handleUsuarioSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmittingUsuario(true);
    setError("");

    try {
      const usuario = await createUsuario(usuarioForm);
      setUltimoUsuario(usuario);
      setReservaUsuarioId(usuario.id);
      setFeedback(`Cadastro concluido para ${usuario.nome}. Agora voce pode fazer a reserva.`);
      setUsuarioForm({
        nome: "",
        email: "",
        telefoneWhatsApp: "",
        role: "Cliente",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel cadastrar o usuario.");
    } finally {
      setSubmittingUsuario(false);
    }
  };

  const handleReservaSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmittingReserva(true);
    setError("");

    const payload: ReservaInput = {
      usuarioId: reservaUsuarioId,
      dataReserva: reservaData,
      horaReserva: horaReservaMontada,
      quantidadePessoas: reservaQuantidade,
    };

    try {
      const reserva = await createReserva(payload);
      const freshNow = rioBrancoPartsNow();
      setFeedback(`Reserva criada com sucesso para ${reserva.dataReserva}.`);
      setReservaData(freshNow.date);
      setReservaHoraLocal(freshNow.time);
      setReservaQuantidade(1);

      if (adminUnlocked && adminKey) {
        await carregarAdmin(adminKey);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel criar a reserva.");
    } finally {
      setSubmittingReserva(false);
    }
  };

  const handleAdminSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmittingAdminLogin(true);
    try {
      await carregarAdmin(adminKeyInput);
      setView("admin");
    } catch {
      // handled in carregarAdmin
    } finally {
      setSubmittingAdminLogin(false);
    }
  };

  const atualizarStatus = async (reservaId: string, action: "confirmar" | "cancelar") => {
    if (!adminKey) {
      setError("Entre no admin para atualizar reservas.");
      return;
    }

    setError("");
    try {
      if (action === "confirmar") {
        await confirmarReserva(reservaId, adminKey);
        setFeedback("Reserva confirmada.");
      } else {
        await cancelarReserva(reservaId, adminKey);
        setFeedback("Reserva cancelada.");
      }
      await carregarAdmin(adminKey);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel atualizar a reserva.");
    }
  };

  const buscarHistorico = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!adminKey) {
      setError("Entre no admin para consultar o historico.");
      return;
    }

    setError("");
    try {
      await carregarHistoricoAdmin(historicoData, adminKey);
      setFeedback(`Historico carregado para ${historicoData}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar o historico.");
    }
  };

  const sairDoAdmin = () => {
    setAdminUnlocked(false);
    setAdminKey("");
    setAdminKeyInput("");
    setUsuariosAdmin([]);
    setReservasHoje([]);
    setReservasHistorico([]);
    window.localStorage.removeItem(ADMIN_STORAGE_KEY);
    setFeedback("Voce saiu da area administrativa.");
    setView("reserva");
  };

  return (
    <div className="page-shell">
      <header className="top">
        <div className="brand">
          <span className="brand-mark" />
          <div className="brand-copy">
            <strong className="brand-title">BDP Reservas</strong>
            <span className="brand-subtitle">Area publica de reserva e painel interno</span>
          </div>
        </div>

        <nav className="nav">
          <button
            type="button"
            className={`nav-link ${view === "reserva" ? "nav-link-active" : ""}`}
            onClick={() => setView("reserva")}
          >
            <span>Faca sua reserva aqui</span>
            <small>Cadastro e reserva assistida</small>
          </button>
          <button
            type="button"
            className={`nav-link ${view === "admin" ? "nav-link-active" : ""}`}
            onClick={() => setView("admin")}
          >
            <span>Admin</span>
            <small>{adminUnlocked ? "Painel interno liberado" : "Area protegida por chave"}</small>
          </button>
        </nav>
      </header>

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">BDP | Reserva</p>
          <h1>Publico para reservar, privado para administrar.</h1>
          <p className="hero-text">
            A area de administracao agora fica protegida por chave e o historico foi integrado dentro do painel admin.
          </p>

          <div className="hero-cta">
            <button type="button" className="primary-button" onClick={() => setView("reserva")}>
              Fazer reserva
            </button>
            <button type="button" className="ghost-button" onClick={() => setView("admin")}>
              Entrar no admin
            </button>
          </div>

          <div className="hero-badges">
            <span className="pill">Fuso automatico</span>
            <span className="pill">Horarios sugeridos</span>
            <span className="pill">Admin protegido</span>
          </div>
        </div>

        <div className="hero-stack">
          <div className="hero-card hero-card-api">
            <span className="status-dot" />
            <div>
              <strong>API alvo</strong>
              <p>{apiUrl}</p>
            </div>
          </div>

          <div className="hero-card hero-card-feature">
            <div className="hero-card-heading">
              <p className="hero-card-title">Resumo rapido</p>
              <span className="pill">{adminUnlocked ? "Admin liberado" : "Admin protegido"}</span>
            </div>
            <div className="stack">
              {adminUnlocked ? (
                <p className="muted">
                  Usuarios <strong>{metricasAdmin.usuarios}</strong> | Reservas hoje <strong>{metricasAdmin.reservasHoje}</strong>
                </p>
              ) : (
                <p className="muted">So funcionarios e dono podem acessar o painel interno.</p>
              )}
              <p className={error ? "danger-text" : "muted"}>{error || feedback}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="dashboard">
        {view === "reserva" ? (
          <>
            <section className="panel panel-form">
              <div className="panel-heading">
                <p className="panel-kicker">Etapa 1</p>
                <h2>Cadastre-se</h2>
              </div>

              <form className="form-grid" onSubmit={handleUsuarioSubmit}>
                <label>
                  Nome
                  <input
                    required
                    value={usuarioForm.nome}
                    onChange={(event) => setUsuarioForm((current) => ({ ...current, nome: event.target.value }))}
                    placeholder="Ex.: Maria Silva"
                  />
                </label>

                <label>
                  E-mail
                  <input
                    required
                    type="email"
                    value={usuarioForm.email}
                    onChange={(event) => setUsuarioForm((current) => ({ ...current, email: event.target.value }))}
                    placeholder="maria@exemplo.com"
                  />
                </label>

                <label>
                  WhatsApp
                  <input
                    required
                    value={usuarioForm.telefoneWhatsApp}
                    onChange={(event) =>
                      setUsuarioForm((current) => ({ ...current, telefoneWhatsApp: event.target.value }))
                    }
                    placeholder="+5568999999999"
                  />
                </label>

                <label>
                  Perfil
                  <select
                    value={usuarioForm.role}
                    onChange={(event) =>
                      setUsuarioForm((current) => ({ ...current, role: event.target.value as Usuario["role"] }))
                    }
                  >
                    <option value="Cliente">Cliente</option>
                    <option value="Admin">Admin</option>
                  </select>
                </label>

                <button className="primary-button" type="submit" disabled={submittingUsuario}>
                  {submittingUsuario ? "Salvando..." : "Criar usuario"}
                </button>
              </form>

              {ultimoUsuario ? (
                <div className="callout success">
                  <strong>Ultimo usuario criado</strong>
                  <p>{ultimoUsuario.nome}</p>
                  <code>{ultimoUsuario.id}</code>
                </div>
              ) : null}
            </section>

            <section className="panel panel-form">
              <div className="panel-heading">
                <p className="panel-kicker">Etapa 2</p>
                <h2>Faca sua reserva aqui</h2>
              </div>

              <form className="form-grid" onSubmit={handleReservaSubmit}>
                <label className="span-2">
                  Codigo do usuario
                  <input
                    required
                    value={reservaUsuarioId}
                    onChange={(event) => setReservaUsuarioId(event.target.value)}
                    placeholder="Se acabou de se cadastrar, o codigo ja aparece aqui"
                  />
                </label>

                <label>
                  Data da reserva
                  <input required type="date" value={reservaData} onChange={(event) => setReservaData(event.target.value)} />
                </label>

                <label>
                  Hora local
                  <select required value={reservaHoraLocal} onChange={(event) => setReservaHoraLocal(event.target.value)} disabled={loadingPublicData}>
                    {horariosSugeridos.length === 0 ? (
                      <option value={reservaHoraLocal}>Sem horarios cadastrados</option>
                    ) : (
                      horariosSugeridos.map((horario) => (
                        <option key={horario} value={horario}>
                          {horario}
                        </option>
                      ))
                    )}
                  </select>
                </label>

                <label>
                  Quantidade de pessoas
                  <input
                    required
                    min={1}
                    type="number"
                    value={reservaQuantidade}
                    onChange={(event) => setReservaQuantidade(Number(event.target.value))}
                  />
                </label>

                <div className="schedule-summary span-2">
                  <span className="iso-label">Configuracao do dia</span>
                  {weekday ? (
                    <p>
                      {weekdayLabels[weekday]}:{" "}
                      {configuracoesDoDia.length > 0
                        ? configuracoesDoDia
                            .map(
                              (configuracao) =>
                                `${configuracao.horaAbertura.slice(0, 5)}-${configuracao.horaFechamento.slice(0, 5)} (${configuracao.capacidadeMaximaPessoas} pessoas)`,
                            )
                            .join(" | ")
                        : "nenhum horario cadastrado"}
                    </p>
                  ) : (
                    <p>Selecione uma data para ver os horarios.</p>
                  )}
                </div>

                <div className="iso-preview span-2">
                  <span className="iso-label">Hora ISO enviada para a API</span>
                  <code>{horaReservaMontada}</code>
                  <p>O frontend monta automaticamente no fuso de Rio Branco ({RIO_BRANCO_OFFSET}).</p>
                </div>

                <button className="primary-button warm" type="submit" disabled={submittingReserva || !reservaUsuarioId}>
                  {submittingReserva ? "Reservando..." : "Criar reserva"}
                </button>
              </form>
            </section>
          </>
        ) : null}

        {view === "admin" ? (
          !adminUnlocked ? (
            <section className="panel panel-form admin-lock">
              <div className="panel-heading">
                <p className="panel-kicker">Area restrita</p>
                <h2>Entrar no admin</h2>
              </div>

              <form className="history-filter" onSubmit={handleAdminSubmit}>
                <label>
                  Chave de acesso
                  <input
                    required
                    type="password"
                    value={adminKeyInput}
                    onChange={(event) => setAdminKeyInput(event.target.value)}
                    placeholder="Somente dono e funcionarios"
                  />
                </label>

                <button className="primary-button" type="submit" disabled={submittingAdminLogin || loadingAdminData}>
                  {submittingAdminLogin || loadingAdminData ? "Validando..." : "Entrar"}
                </button>
              </form>

              <div className="callout neutral">
                <strong>Privacidade</strong>
                <p>A partir de agora, a area admin e o historico nao ficam mais expostos para qualquer visitante.</p>
              </div>
            </section>
          ) : (
            <>
              <section className="panel metrics-panel">
                <div className="panel-heading row-between">
                  <div>
                    <p className="panel-kicker">Admin</p>
                    <h2>Painel interno</h2>
                  </div>
                  <button className="ghost-button" type="button" onClick={sairDoAdmin}>
                    Sair do admin
                  </button>
                </div>

                <div className="metrics-grid">
                  <article className="metric-card">
                    <span className="metric-label">Usuarios</span>
                    <strong>{metricasAdmin.usuarios}</strong>
                  </article>
                  <article className="metric-card">
                    <span className="metric-label">Reservas hoje</span>
                    <strong>{metricasAdmin.reservasHoje}</strong>
                  </article>
                  <article className="metric-card">
                    <span className="metric-label">Ativas</span>
                    <strong>{metricasAdmin.reservasAtivas}</strong>
                  </article>
                  <article className="metric-card">
                    <span className="metric-label">Pessoas previstas</span>
                    <strong>{metricasAdmin.totalPessoasHoje}</strong>
                  </article>
                </div>
              </section>

              <section className="panel panel-table">
                <div className="panel-heading row-between">
                  <div>
                    <p className="panel-kicker">Hoje</p>
                    <h2>Reservas do dia</h2>
                  </div>
                  <button className="ghost-button" type="button" onClick={() => void carregarAdmin(adminKey)} disabled={loadingAdminData}>
                    {loadingAdminData ? "Atualizando..." : "Atualizar"}
                  </button>
                </div>

                <div className="status-strip">
                  {error ? <p className="error-text">{error}</p> : <p className="success-text">{feedback}</p>}
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Usuario</th>
                        <th>Data</th>
                        <th>Horario local</th>
                        <th>Pessoas</th>
                        <th>Status</th>
                        <th>Acoes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reservasHoje.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="empty-state">
                            Nenhuma reserva encontrada para hoje.
                          </td>
                        </tr>
                      ) : (
                        reservasHoje.map((reserva) => (
                          <tr key={reserva.id}>
                            <td>{getUsuarioNome(usuariosAdmin, reserva.usuarioId)}</td>
                            <td>{reserva.dataReserva}</td>
                            <td>{formatReservaHora(reserva.horaReserva)}</td>
                            <td>{reserva.quantidadePessoas}</td>
                            <td>
                              <span className={`badge badge-${reserva.status.toLowerCase()}`}>{reserva.status}</span>
                            </td>
                            <td className="actions-cell">
                              <button type="button" className="mini-button" onClick={() => void atualizarStatus(reserva.id, "confirmar")}>
                                Confirmar
                              </button>
                              <button
                                type="button"
                                className="mini-button danger"
                                onClick={() => void atualizarStatus(reserva.id, "cancelar")}
                              >
                                Cancelar
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="panel panel-form">
                <div className="panel-heading">
                  <p className="panel-kicker">Historico</p>
                  <h2>Consultar por data</h2>
                </div>

                <form className="history-filter" onSubmit={buscarHistorico}>
                  <label>
                    Data
                    <input type="date" value={historicoData} onChange={(event) => setHistoricoData(event.target.value)} />
                  </label>

                  <button className="primary-button" type="submit" disabled={loadingHistorico}>
                    {loadingHistorico ? "Buscando..." : "Buscar historico"}
                  </button>
                </form>
              </section>

              <section className="panel panel-table">
                <div className="panel-heading">
                  <p className="panel-kicker">Resultado</p>
                  <h2>Historico em {historicoData}</h2>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Usuario</th>
                        <th>Data</th>
                        <th>Horario local</th>
                        <th>Pessoas</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reservasHistorico.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="empty-state">
                            Nenhuma reserva encontrada para essa data.
                          </td>
                        </tr>
                      ) : (
                        reservasHistorico.map((reserva) => (
                          <tr key={reserva.id}>
                            <td>{getUsuarioNome(usuariosAdmin, reserva.usuarioId)}</td>
                            <td>{reserva.dataReserva}</td>
                            <td>{formatReservaHora(reserva.horaReserva)}</td>
                            <td>{reserva.quantidadePessoas}</td>
                            <td>
                              <span className={`badge badge-${reserva.status.toLowerCase()}`}>{reserva.status}</span>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )
        ) : null}
      </main>
    </div>
  );
}

export default App;
