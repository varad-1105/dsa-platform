(function () {
  const saved = localStorage.getItem("theme") || "dark";
  document.documentElement.dataset.theme = saved;
})();

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("theme", next);
  if (window.monaco && window.editor) {
    monaco.editor.setTheme(next === "dark" ? "vs-dark" : "vs");
  }
}

function renderEducationalVisual(target, type) {
  const el = typeof target === "string" ? document.querySelector(target) : target;
  if (!el) return;
  const templates = {
    "two-pointers": `<svg viewBox="0 0 420 150" width="100%" role="img" aria-label="Two pointer movement">
      <rect x="30" y="60" width="52" height="42" rx="6" fill="#2563eb"/><rect x="92" y="60" width="52" height="42" rx="6" fill="#111827"/>
      <rect x="154" y="60" width="52" height="42" rx="6" fill="#111827"/><rect x="216" y="60" width="52" height="42" rx="6" fill="#111827"/>
      <rect x="278" y="60" width="52" height="42" rx="6" fill="#111827"/><rect x="340" y="60" width="52" height="42" rx="6" fill="#14b8a6"/>
      <text x="48" y="86" fill="white">L</text><text x="358" y="86" fill="white">R</text>
      <path d="M56 50 C100 10 306 10 366 50" fill="none" stroke="#f59e0b" stroke-width="4" stroke-dasharray="8 8"/>
    </svg>`,
    "binary-search": `<svg viewBox="0 0 420 150" width="100%" role="img" aria-label="Binary search range shrinking">
      <rect x="35" y="58" width="350" height="34" rx="6" fill="#172033"/>
      <rect x="115" y="58" width="190" height="34" rx="6" fill="#2563eb"/>
      <line x1="210" y1="42" x2="210" y2="108" stroke="#fbbf24" stroke-width="4"/>
      <text x="174" y="130" fill="#94a3b8">low ... mid ... high</text>
    </svg>`,
    graph: `<svg viewBox="0 0 420 180" width="100%" role="img" aria-label="Graph traversal">
      <g stroke="#64748b" stroke-width="3"><line x1="90" y1="90" x2="190" y2="45"/><line x1="90" y1="90" x2="190" y2="135"/><line x1="190" y1="45" x2="315" y2="90"/><line x1="190" y1="135" x2="315" y2="90"/></g>
      <g fill="#2563eb"><circle cx="90" cy="90" r="24"/><circle cx="190" cy="45" r="24"/><circle cx="190" cy="135" r="24"/><circle cx="315" cy="90" r="24"/></g>
      <text x="82" y="97" fill="white">S</text><text x="184" y="52" fill="white">1</text><text x="184" y="142" fill="white">2</text><text x="309" y="97" fill="white">3</text>
    </svg>`,
    tree: `<svg viewBox="0 0 420 190" width="100%" role="img" aria-label="Tree traversal">
      <g stroke="#64748b" stroke-width="3"><line x1="210" y1="45" x2="130" y2="115"/><line x1="210" y1="45" x2="290" y2="115"/></g>
      <g fill="#14b8a6"><circle cx="210" cy="45" r="25"/><circle cx="130" cy="115" r="25"/><circle cx="290" cy="115" r="25"/></g>
      <text x="202" y="52" fill="#06201c">A</text><text x="122" y="122" fill="#06201c">B</text><text x="282" y="122" fill="#06201c">C</text>
    </svg>`,
    dp: `<svg viewBox="0 0 420 170" width="100%" role="img" aria-label="Dynamic programming table">
      ${Array.from({ length: 24 }).map((_, i) => `<rect x="${35 + (i % 8) * 44}" y="${35 + Math.floor(i / 8) * 34}" width="34" height="24" rx="4" fill="${i % 5 === 0 ? '#14b8a6' : '#1f2937'}"/>`).join("")}
      <path d="M69 47 L113 81 L157 115 L245 115" stroke="#fbbf24" stroke-width="4" fill="none"/>
    </svg>`,
    stack: `<svg viewBox="0 0 420 170" width="100%" role="img" aria-label="Stack animation">
      <rect x="165" y="40" width="90" height="28" rx="5" fill="#2563eb"/><rect x="165" y="74" width="90" height="28" rx="5" fill="#14b8a6"/><rect x="165" y="108" width="90" height="28" rx="5" fill="#f59e0b"/>
      <text x="272" y="61" fill="#94a3b8">top</text><path d="M260 53 H245" stroke="#94a3b8" stroke-width="3"/>
    </svg>`,
    queue: `<svg viewBox="0 0 420 150" width="100%" role="img" aria-label="Queue simulation">
      <path d="M40 72 H380" stroke="#64748b" stroke-width="3"/><g fill="#2563eb"><rect x="92" y="50" width="50" height="44" rx="6"/><rect x="152" y="50" width="50" height="44" rx="6"/><rect x="212" y="50" width="50" height="44" rx="6"/></g>
      <text x="38" y="118" fill="#94a3b8">dequeue</text><text x="305" y="118" fill="#94a3b8">enqueue</text>
    </svg>`,
    "linked-list": `<svg viewBox="0 0 420 150" width="100%" role="img" aria-label="Linked list pointers">
      <g fill="#2563eb"><rect x="40" y="55" width="64" height="42" rx="6"/><rect x="160" y="55" width="64" height="42" rx="6"/><rect x="280" y="55" width="64" height="42" rx="6"/></g>
      <g stroke="#fbbf24" stroke-width="4"><path d="M104 76 H154"/><path d="M224 76 H274"/></g>
      <text x="62" y="82" fill="white">1</text><text x="182" y="82" fill="white">2</text><text x="302" y="82" fill="white">3</text>
    </svg>`,
    window: `<svg viewBox="0 0 420 150" width="100%" role="img" aria-label="Sliding window">
      ${Array.from({ length: 8 }).map((_, i) => `<rect x="${35 + i * 44}" y="58" width="34" height="34" rx="5" fill="${i > 1 && i < 6 ? '#2563eb' : '#111827'}"/>`).join("")}
      <rect x="116" y="48" width="166" height="54" rx="8" fill="none" stroke="#14b8a6" stroke-width="4"/>
    </svg>`,
    array: `<svg viewBox="0 0 420 150" width="100%" role="img" aria-label="Array visualization">
      ${Array.from({ length: 7 }).map((_, i) => `<rect x="${54 + i * 44}" y="${75 - (i % 4) * 10}" width="32" height="${28 + (i % 4) * 10}" rx="5" fill="${i === 3 ? '#14b8a6' : '#2563eb'}"/>`).join("")}
    </svg>`,
  };
  el.innerHTML = templates[type] || templates.array;
}
