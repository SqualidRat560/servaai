import { useEffect, useState } from "react";
import Customer from "./pages/Customer.jsx";
import Portfolio from "./pages/Portfolio.jsx";
import Method from "./pages/Method.jsx";

const PAGES = { customer: "Customer", portfolio: "Portfolio", method: "Method" };

function readHash() {
  const [page, id] = window.location.hash.replace(/^#\/?/, "").split("/");
  return { page: PAGES[page] ? page : "customer", id: id || null };
}

function load3D() {
  try { return localStorage.getItem("servaai-3d") !== "off"; } catch { return true; }
}

export default function App() {
  const [route, setRoute] = useState(readHash);
  const [threeD, setThreeD] = useState(load3D);

  useEffect(() => {
    const on = () => setRoute(readHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);

  const toggle3D = () => {
    const next = !threeD;
    setThreeD(next);
    try { localStorage.setItem("servaai-3d", next ? "on" : "off"); } catch { /* storage blocked */ }
  };

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-4 pt-5 pb-3 sm:px-6">
        <a href="#/customer" className="display text-2xl font-bold text-frost no-underline">
          Serva<span className="text-tangerine">AI</span>
        </a>
        <nav className="flex gap-5 text-[15px]">
          {Object.entries(PAGES).map(([key, label]) => (
            <a key={key} href={`#/${key}`}
               className={`no-underline ${route.page === key ? "text-frost underline decoration-tangerine decoration-2 underline-offset-8" : "text-mist hover:text-frost"}`}>
              {label}
            </a>
          ))}
        </nav>
        <button onClick={toggle3D} aria-pressed={threeD}
                className="ml-auto rounded-full border border-line px-3 py-1 text-sm text-mist hover:text-frost">
          3D {threeD ? "on" : "off"}
        </button>
      </header>
      <main className="mx-auto max-w-6xl px-4 pb-16 sm:px-6">
        {route.page === "customer" && <Customer initialId={route.id} threeD={threeD} />}
        {route.page === "portfolio" && <Portfolio threeD={threeD} />}
        {route.page === "method" && <Method />}
      </main>
    </div>
  );
}
