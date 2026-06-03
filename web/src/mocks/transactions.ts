import type { BankTransaction } from "@/lib/types";

export const MOCK_ACCOUNT = {
  id: "AC-9087-4421-1234",
  holder: "Cliente verificado",
  balance: 18452.73,
  currency: "USD",
};

export const MOCK_TRANSACTIONS: BankTransaction[] = [
  { id: "TX-001", date: "2025-05-28 14:22", description: "Pago nómina mensual",        amount: 4200.0 },
  { id: "TX-002", date: "2025-05-29 09:11", description: "Compra supermercado",        amount: -132.45 },
  { id: "TX-003", date: "2025-05-30 03:14", description: "Transferencia internacional",amount: -2800.0, flagged: true },
  { id: "TX-004", date: "2025-05-31 02:47", description: "Retiro cajero (madrugada)",  amount: -600.0,  flagged: true },
  { id: "TX-005", date: "2025-06-01 18:03", description: "Suscripción streaming",      amount: -14.99 },
];
