import { createContext, useContext, useState, type ReactNode } from "react";

// The app speaks the tradesperson's language. Customer-facing text comes from the AI instead.
const strings = {
  es: {
    home: "Inicio",
    jobs: "Trabajos",
    money: "Dinero",
    settings: "Ajustes",
    record: "Grabar",
    owed: "Te deben",
    depositsUnpaid: (n: number) => (n === 1 ? "1 depósito sin pagar" : `${n} depósitos sin pagar`),
    paidThisMonth: "Cobrado este mes",
    newJob: "Nuevo trabajo",
    noJobs: "Aún no hay trabajos. Toca el botón amarillo para grabar tu primer recorrido.",
    customer: "Cliente",
    customerName: "Nombre del cliente",
    customerEmail: "Correo del cliente",
    customerLanguage: "Idioma del cliente",
    address: "Dirección",
    billing: "Cobro",
    fixed: "Precio fijo",
    tm: "Tiempo y materiales",
    next: "Siguiente",
    walkthroughTitle: "Describe el trabajo",
    walkthroughHint: "Habla en tu idioma. Di las medidas y cantidades en voz alta.",
    tapToRecord: "Toca para grabar",
    recording: "Grabando… toca para parar",
    recorded: "Nota de voz lista",
    addPhotos: "Agregar fotos",
    typedNotes: "O escribe aquí",
    makeEstimate: "Hacer presupuesto",
    working: "Preparando el presupuesto…",
    workOrder: "Orden de trabajo",
    questions: "Antes de enviar",
    answer: "Tu respuesta",
    updateEstimate: "Actualizar presupuesto",
    assumptions: "Supuestos",
    needsPrice: "Falta precio",
    checkTranslation: "Revisa la traducción",
    setPrice: "Precio $",
    mine: "Mi versión",
    asCustomer: "Como lo ve el cliente",
    subtotal: "Subtotal",
    tax: "Impuesto",
    total: "Total",
    sendEstimate: "Enviar presupuesto y depósito",
    fixPrices: (n: number) => `Pon precio a ${n} línea(s) para poder enviar`,
    invoices: "Facturas PayPal",
    deposit: "Depósito",
    change: "Cambio",
    final: "Final",
    sent: "Enviada",
    paid: "Pagada",
    remind: "Recordar",
    reminded: "Recordatorio enviado",
    openInvoices: "Facturas abiertas",
    daysOut: (d: number) => `${d} días`,
    ask: "Pregunta sobre tu dinero",
    askPlaceholder: "¿Cuánto me deben este mes?",
    askButton: "Preguntar",
    priceBook: "Lista de precios",
    language: "Idioma de la app",
    status: {
      draft: "Borrador",
      estimate_sent: "Presupuesto enviado",
      deposit_paid: "Depósito pagado",
      in_progress: "En curso",
      invoiced: "Facturado",
      paid: "Pagado",
    } as Record<string, string>,
  },
  en: {
    home: "Home",
    jobs: "Jobs",
    money: "Money",
    settings: "Settings",
    record: "Record",
    owed: "You're owed",
    depositsUnpaid: (n: number) => (n === 1 ? "1 deposit unpaid" : `${n} deposits unpaid`),
    paidThisMonth: "Collected this month",
    newJob: "New job",
    noJobs: "No jobs yet. Tap the yellow button to record your first walkthrough.",
    customer: "Customer",
    customerName: "Customer name",
    customerEmail: "Customer email",
    customerLanguage: "Customer's language",
    address: "Address",
    billing: "Billing",
    fixed: "Fixed price",
    tm: "Time and materials",
    next: "Next",
    walkthroughTitle: "Describe the job",
    walkthroughHint: "Talk in your language. Say measurements and counts out loud.",
    tapToRecord: "Tap to record",
    recording: "Recording… tap to stop",
    recorded: "Voice note ready",
    addPhotos: "Add photos",
    typedNotes: "Or type here",
    makeEstimate: "Make estimate",
    working: "Building the estimate…",
    workOrder: "Work order",
    questions: "Before you send",
    answer: "Your answer",
    updateEstimate: "Update estimate",
    assumptions: "Assumptions",
    needsPrice: "Needs price",
    checkTranslation: "Check translation",
    setPrice: "Price $",
    mine: "My version",
    asCustomer: "Customer's view",
    subtotal: "Subtotal",
    tax: "Tax",
    total: "Total",
    sendEstimate: "Send estimate and deposit",
    fixPrices: (n: number) => `Price ${n} line(s) before sending`,
    invoices: "PayPal invoices",
    deposit: "Deposit",
    change: "Change",
    final: "Final",
    sent: "Sent",
    paid: "Paid",
    remind: "Remind",
    reminded: "Reminder sent",
    openInvoices: "Open invoices",
    daysOut: (d: number) => `${d} days`,
    ask: "Ask about your money",
    askPlaceholder: "How much am I owed this month?",
    askButton: "Ask",
    priceBook: "Price book",
    language: "App language",
    status: {
      draft: "Draft",
      estimate_sent: "Estimate sent",
      deposit_paid: "Deposit paid",
      in_progress: "In progress",
      invoiced: "Invoiced",
      paid: "Paid",
    } as Record<string, string>,
  },
};

export type Lang = keyof typeof strings;
type Strings = (typeof strings)["es"];

const Ctx = createContext<{ t: Strings; lang: Lang; setLang: (l: Lang) => void }>({
  t: strings.es,
  lang: "es",
  setLang: () => {},
});

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem("lang");
    if (saved === "es" || saved === "en") return saved;
  } catch {
    /* storage unavailable */
  }
  return "es";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("lang", l);
    } catch {
      /* storage unavailable */
    }
    document.documentElement.lang = l;
  };
  return <Ctx.Provider value={{ t: strings[lang] as Strings, lang, setLang }}>{children}</Ctx.Provider>;
}

export const useT = () => useContext(Ctx);
