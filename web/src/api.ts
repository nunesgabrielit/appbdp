import type { ConfiguracaoHorario, Reserva, ReservaInput, Usuario, UsuarioInput } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "";

type ApiErrorBody = {
  detail?: string | Array<{ msg?: string }>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = `Erro ${response.status}`;
    const rawBody = await response.text();

    try {
      const body = JSON.parse(rawBody) as ApiErrorBody;
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        message = body.detail[0].msg;
      }
    } catch {
      if (rawBody) {
        message = rawBody;
      }
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function adminHeaders(adminKey: string): Record<string, string> {
  return {
    "X-Admin-Key": adminKey,
  };
}

export function createUsuario(payload: UsuarioInput): Promise<Usuario> {
  return request<Usuario>("/usuarios", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getUsuarios(adminKey: string): Promise<Usuario[]> {
  return request<Usuario[]>("/usuarios", {
    headers: adminHeaders(adminKey),
  });
}

export function getConfiguracoesHorarios(): Promise<ConfiguracaoHorario[]> {
  return request<ConfiguracaoHorario[]>("/configuracoes-horarios");
}

export function createReserva(payload: ReservaInput): Promise<Reserva> {
  return request<Reserva>("/reservas", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getReservasHoje(adminKey: string): Promise<Reserva[]> {
  return request<Reserva[]>("/reservas/hoje", {
    headers: adminHeaders(adminKey),
  });
}

export function getReservasByDate(data: string, adminKey: string): Promise<Reserva[]> {
  const query = new URLSearchParams({ data });
  return request<Reserva[]>(`/reservas?${query.toString()}`, {
    headers: adminHeaders(adminKey),
  });
}

export function confirmarReserva(reservaId: string, adminKey: string): Promise<void> {
  return request<void>(`/reservas/${reservaId}/confirmar`, {
    method: "PUT",
    headers: adminHeaders(adminKey),
  });
}

export function cancelarReserva(reservaId: string, adminKey: string): Promise<void> {
  return request<void>(`/reservas/${reservaId}/cancelar`, {
    method: "PUT",
    headers: adminHeaders(adminKey),
  });
}
