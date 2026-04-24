/* global React */
const { useMemo } = React;

/* Simple SF-Symbols-ish line icons, stroke-based, 1.6 weight */
const Icon = ({ name, size = 18, color = "currentColor" }) => {
  const p = (d) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {d}
    </svg>
  );
  switch (name) {
    case "bolt": return p(<path d="M13 3 4 14h6l-1 7 9-11h-6l1-7Z" />);
    case "gear": return p(<><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3h0a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8v0a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1Z"/></>);
    case "play": return p(<path d="M8 5v14l11-7Z" fill="currentColor" stroke="none"/>);
    case "refresh": return p(<><path d="M3 12a9 9 0 0 1 15.3-6.4L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.3 6.4L3 16"/><path d="M3 21v-5h5"/></>);
    case "cloud": return p(<path d="M7 18a5 5 0 0 1-.4-10A7 7 0 0 1 20 10a4 4 0 0 1-1 8H7Z"/>);
    case "db": return p(<><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></>);
    case "users": return p(<><circle cx="9" cy="8" r="3.2"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 11a3 3 0 0 0 0-6"/><path d="M15 20a6 6 0 0 1 6 0"/></>);
    case "calendar": return p(<><rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18"/><path d="M8 3v4M16 3v4"/></>);
    case "doc": return p(<><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/><path d="M14 3v5h5"/></>);
    case "list": return p(<><path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1.2" fill="currentColor"/><circle cx="4" cy="12" r="1.2" fill="currentColor"/><circle cx="4" cy="18" r="1.2" fill="currentColor"/></>);
    case "search": return p(<><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>);
    case "plus": return p(<><path d="M12 5v14M5 12h14"/></>);
    case "minus": return p(<path d="M5 12h14"/>);
    case "trash": return p(<><path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7h12l-1 13a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L6 7Z"/><path d="M9 7V4h6v3"/></>);
    case "chev-r": return p(<path d="m9 6 6 6-6 6"/>);
    case "chev-d": return p(<path d="m6 9 6 6 6-6"/>);
    case "chev-u": return p(<path d="m6 15 6-6 6 6"/>);
    case "check": return p(<path d="m5 12 5 5L20 7"/>);
    case "x": return p(<><path d="m6 6 12 12M18 6 6 18"/></>);
    case "dot": return p(<circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none"/>);
    case "moon": return p(<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>);
    case "sun": return p(<><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/></>);
    case "info": return p(<><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></>);
    case "warn": return p(<><path d="M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6A2 2 0 0 0 22 18L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v5M12 18h.01"/></>);
    case "lock": return p(<><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 1 1 8 0v4"/></>);
    case "key": return p(<><circle cx="8" cy="15" r="4"/><path d="m10.8 12.2 10-10"/><path d="m15 5 3 3M18 2l3 3"/></>);
    case "board": return p(<><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 10v10"/></>);
    case "clock": return p(<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>);
    case "sliders": return p(<><path d="M4 6h12M4 12h8M4 18h14"/><circle cx="19" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="18" cy="18" r="2"/></>);
    case "paste": return p(<><rect x="7" y="5" width="10" height="16" rx="2"/><path d="M9 5V3h6v2"/><path d="M11 11h2M11 15h4"/></>);
    case "spark": return p(<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>);
    case "mini-drive": return p(<><path d="M7 4h10l4 8-5 8H8L3 12Z"/><path d="M7 4 3 12"/><path d="M17 4l4 8"/><path d="M8 20l4-8h9"/></>);
    default: return p(null);
  }
};

Object.assign(window, { Icon });
