const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export type Bilingual = { tradesperson: string; customer: string };

export type LineItem = {
  id: number;
  kind: string;
  text_tradesperson: string;
  text_customer: string;
  quantity: number;
  unit: string;
  unit_price_cents: number | null;
  needs_price: boolean;
  low_confidence: boolean;
  line_total_cents: number;
};

export type Invoice = {
  id: number;
  kind: "deposit" | "change" | "final";
  amount_cents: number;
  status: "draft" | "sent" | "paid";
  payer_url: string;
};

export type Totals = { subtotal_cents: number; tax_cents: number; total_cents: number; needs_price: number };

export type JobSummary = Totals & {
  id: number;
  title: string;
  status: string;
  customer_name: string;
  billing_mode: "fixed" | "tm";
};

export type JobDetail = {
  job: { id: number; title: string; status: string; billing_mode: string; transcript: string; address: string };
  customer: { name: string; email: string; language: string };
  questions: Bilingual[];
  assumptions: Bilingual[];
  line_items: LineItem[];
  invoices: Invoice[];
  totals: Totals;
};

export type MoneySummary = {
  owed_cents: number;
  paid_this_month_cents: number;
  deposits_unpaid: number;
  open_invoices: { id: number; job_id: number; customer: string; kind: string; amount_cents: number; days_out: number }[];
};

export type PriceBookItem = { id: number; trade: string; name: string; unit: string; price_cents: number };

export const api = {
  jobs: () => request<JobSummary[]>("/api/jobs"),
  job: (id: number) => request<JobDetail>(`/api/jobs/${id}`),
  createJob: (body: {
    customer_name: string;
    customer_email: string;
    customer_language: string;
    address: string;
    billing_mode: string;
  }) => request<{ id: number }>("/api/jobs", json(body)),
  walkthrough: (id: number, form: FormData) =>
    request<JobDetail>(`/api/jobs/${id}/walkthrough`, { method: "POST", body: form }),
  setPrice: (itemId: number, cents: number) =>
    request(`/api/line-items/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_price_cents: cents }),
    }),
  send: (id: number) => request<JobDetail>(`/api/jobs/${id}/send`, { method: "POST" }),
  remind: (invoiceId: number) => request(`/api/invoices/${invoiceId}/remind`, { method: "POST" }),
  money: () => request<MoneySummary>("/api/money/summary"),
  ask: (question: string) => request<{ answer: string }>("/api/money/ask", json({ question })),
  priceBook: () => request<PriceBookItem[]>("/api/price-book"),
};

export const dollars = (cents: number | null | undefined) =>
  cents == null ? "—" : (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
