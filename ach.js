// Shared achievements list: icons and names from window.ACH (always in English, like the games' own names),
// how-to from window.GUIDE ([en, it], each a paragraph string or an array of numbered steps).
// ACH_UI.init(container, { wiki, check }) where check(key) is undefined before a save is loaded,
// null when the save doesn't record that achievement, else true/false. Call ACH_UI.draw() after loading a save.
const ACH_UI = (() => {
  const S = {
    it: {
      done: "Fatto in questo salvataggio", todo: "Non ancora in questo salvataggio",
      reveal: "Obiettivo segreto: mostra", all: "Tutti", fTodo: "Da fare", fDone: "Fatti", how: "Come si ottiene",
      total: (d, n) => `${d} di ${n} fatti in questo salvataggio`, totalNoSave: n => `${n} obiettivi`,
      hint: w => `Lo stato viene dal salvataggio: dice cosa ha fatto questa partita, non cosa ha sbloccato Steam.${w ? ` Altri dettagli sulla <a href="${w}" target="_blank" rel="noopener">wiki</a>.` : ""}`,
    },
    en: {
      done: "Done in this save", todo: "Not yet in this save",
      reveal: "Secret achievement: show", all: "All", fTodo: "To do", fDone: "Done", how: "How to get it",
      total: (d, n) => `${d} of ${n} done in this save`, totalNoSave: n => `${n} achievements`,
      hint: w => `Status comes from your save: it shows what this playthrough has done, not what Steam has unlocked.${w ? ` More details on the <a href="${w}" target="_blank" rel="noopener">wiki</a>.` : ""}`,
    },
  };
  const s = (k, ...a) => { const v = S[I18N.lang][k]; return typeof v === "function" ? v(...a) : v; };
  const esc = v => String(v).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const revealed = new Set(), opened = new Set();  // opened guides span the whole row so long steps stay readable
  let root, opts, filter = "all";

  const icon = i => `background-image:url(achievements.webp);background-size:${ACH.cols * 64}px auto;background-position:-${(i % ACH.cols) * 64}px -${Math.floor(i / ACH.cols) * 64}px`;
  function state(a) {
    const r = opts.check ? opts.check(a.k) : undefined;
    if (r === undefined) return { cls: "", text: "" };
    if (r === null) return { cls: "unknown", text: "" };  // the save doesn't record it: say nothing rather than repeat "unknown"
    return r ? { cls: "done", text: s("done") } : { cls: "todo", text: s("todo") };
  }

  function draw() {
    if (!root) return;
    const L = I18N.lang === "en" ? 0 : 1, rows = ACH.list.map((a, i) => [a, i, state(a)]);
    const loaded = rows.some(([, , st]) => st.cls), done = rows.filter(([, , st]) => st.cls === "done").length;
    root.querySelector(".ach-total").textContent = loaded ? s("total", done, rows.length) : s("totalNoSave", rows.length);
    root.querySelector(".ach-hint").innerHTML = s("hint", opts.wiki);
    root.querySelectorAll(".ach-filters button").forEach(b => { b.textContent = s(b.dataset.f === "all" ? "all" : b.dataset.f === "todo" ? "fTodo" : "fDone"); b.setAttribute("aria-pressed", b.dataset.f === filter); });
    root.querySelector(".achs").innerHTML = rows
      .filter(([, , st]) => filter === "all" || !loaded || (filter === "done") === (st.cls === "done"))
      .map(([a, i, st]) => {
        const g = (window.GUIDE || {})[a.k], secret = a.h && st.cls !== "done" && !revealed.has(i);
        const how = g && g[L], body = Array.isArray(how) ? `<ol>${how.map(x => `<li>${esc(x)}</li>`).join("")}</ol>` : how ? `<p>${esc(how)}</p>` : "";
        return `<li class="ach ${st.cls}${secret ? " secret" : ""}${opened.has(i) && body ? " open-guide" : ""}" data-i="${i}"><div class="ach-ico" style="${icon(i)}"></div>
          <div><h3>${esc(a.n[0])}</h3><p class="ach-d">${esc(a.d[0])}</p>
          ${body ? `<details class="ach-how"${opened.has(i) ? " open" : ""}><summary>${s("how")}</summary>${body}</details>` : ""}
          ${st.text ? `<p class="ach-st">${esc(st.text)}</p>` : ""}
          ${secret ? `<button type="button" class="ach-reveal" data-a="${i}">${s("reveal")}</button>` : ""}</div></li>`;
      }).join("");
  }

  function init(el, o) {
    root = el; opts = o || {};
    root.innerHTML = `<div class="ach-head"><div><h2 class="ach-total"></h2><p class="ach-hint"></p></div>
      <div class="ach-filters" role="group"><button type="button" data-f="all"></button><button type="button" data-f="todo"></button><button type="button" data-f="done"></button></div></div>
      <ul class="achs"></ul>`;
    root.addEventListener("toggle", e => {
      const li = e.target.closest("[data-i]");
      if (!li) return;
      e.target.open ? opened.add(+li.dataset.i) : opened.delete(+li.dataset.i);
      li.classList.toggle("open-guide", e.target.open);
    }, true);
    root.addEventListener("click", e => {
      const b = e.target.closest("[data-a]"), f = e.target.closest("[data-f]");
      if (b) { revealed.add(+b.dataset.a); draw(); }
      if (f) { filter = f.dataset.f; draw(); }
    });
    draw();
  }
  return { init, draw };
})();
