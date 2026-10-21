// Shared IT/EN switch. English by default; the visitor's choice is remembered.
// Pages call I18N.init(strings, onChange); elements with data-i18n get their text from strings[lang].
const I18N = (() => {
  let lang;
  try { lang = localStorage.getItem("lang"); } catch {}
  if (lang !== "it" && lang !== "en") lang = "en";
  let dict = {}, onChange = () => {};

  const t = (key, ...args) => {
    const v = dict[lang][key] ?? key;
    return typeof v === "function" ? v(...args) : v;
  };

  function apply() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach(el => el.innerHTML = t(el.dataset.i18n));
    document.querySelectorAll("[data-i18n-aria]").forEach(el => el.setAttribute("aria-label", t(el.dataset.i18nAria)));
    document.querySelectorAll(".lang button").forEach(b => b.setAttribute("aria-pressed", b.dataset.lang === lang));
    onChange();
  }

  function init(strings, cb) {
    dict = strings;
    if (cb) onChange = cb;
    document.querySelectorAll(".lang button").forEach(b => b.onclick = () => {
      lang = b.dataset.lang;
      try { localStorage.setItem("lang", lang); } catch {}
      apply();
    });
    apply();
  }

  return { init, t, get lang() { return lang; } };
})();
