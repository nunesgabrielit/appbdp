export type UsuarioRole = "Cliente" | "Admin";
export type ReservaStatus =
  | "Pendente"
  | "Aguardando_Confirmacao"
  | "Confirmado"
  | "Cancelado"
  | "Concluido"
  | "No_Show";

export type UsuarioInput = {
  nome: string;
  email: string;
  telefoneWhatsApp: string;
  role: UsuarioRole;
};

export type Usuario = {
  id: string;
  nome: string;
  email: string;
  telefoneWhatsApp: string;
  role: UsuarioRole;
  dataCriacao: string;
};

export type ReservaInput = {
  usuarioId: string;
  dataReserva: string;
  horaReserva: string;
  quantidadePessoas: number;
};

export type Reserva = {
  id: string;
  usuarioId: string;
  dataReserva: string;
  horaReserva: string;
  quantidadePessoas: number;
  status: ReservaStatus;
  dataCriacao: string;
  dataAtualizacao: string;
};

export type ConfiguracaoHorario = {
  id: string;
  diaDaSemana: number;
  horaAbertura: string;
  horaFechamento: string;
  capacidadeMaximaPessoas: number;
};
