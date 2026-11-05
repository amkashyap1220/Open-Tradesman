import { useEffect, useState } from "react";
import { api, dollars, type PriceBookItem } from "../api";
import { useT, type Lang } from "../i18n";

export default function Settings() {
  const { t, lang, setLang } = useT();
  const [book, setBook] = useState<PriceBookItem[]>([]);

  useEffect(() => {
    api.priceBook().then(setBook).catch(() => setBook([]));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="font-cond text-3xl font-bold">{t.settings}</h1>

      <label className="block">
        <span className="text-slate-soft">{t.language}</span>
        <select value={lang} onChange={(e) => setLang(e.target.value as Lang)}
          className="mt-1 w-full rounded-[4px] border border-rule bg-paper px-3 py-3 text-[17px]">
          <option value="es">Español</option>
          <option value="en">English</option>
        </select>
        <span className="mt-1 block text-sm text-slate-soft">{t.languageHint}</span>
      </label>

      <section>
        <h2 className="mb-2 font-cond text-xl font-semibold">{t.priceBook}</h2>
        <div className="slip">
          {book.map((b) => (
            <div key={b.id} className="slip-row flex items-baseline gap-3 px-4 py-3">
              <p className="flex-1">{b.name}</p>
              <p className="figures whitespace-nowrap font-semibold">
                {dollars(b.price_cents)} <span className="font-normal text-slate-soft">/ {b.unit}</span>
              </p>
            </div>
          ))}
        </div>
        {/* TODO: edit prices, add items. */}
      </section>
    </div>
  );
}
