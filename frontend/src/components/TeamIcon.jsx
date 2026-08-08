import React from 'react';

const TEAM_CONFIGS = {
  // MLB
  "Los Angeles Dodgers": { bg: "linear-gradient(135deg, #005a9c 0%, #ef3e42 100%)", icon: "🧢", text: "#ffffff", border: "#40c4ff" },
  "New York Yankees": { bg: "linear-gradient(135deg, #003087 0%, #0c2340 100%)", icon: "🗽", text: "#ffffff", border: "#ffffff" },
  "Atlanta Braves": { bg: "linear-gradient(135deg, #ce1141 0%, #13274f 100%)", icon: "🪓", text: "#ffffff", border: "#ff5252" },
  "Houston Astros": { bg: "linear-gradient(135deg, #002d62 0%, #eb6e1f 100%)", icon: "🚀", text: "#ffffff", border: "#ff9100" },
  "Philadelphia Phillies": { bg: "linear-gradient(135deg, #e31837 0%, #002d62 100%)", icon: "🔔", text: "#ffffff", border: "#ff5252" },
  "Baltimore Orioles": { bg: "linear-gradient(135deg, #df4601 0%, #000000 100%)", icon: "🐦", text: "#ffffff", border: "#ff9100" },
  "San Diego Padres": { bg: "linear-gradient(135deg, #2f241d 0%, #ffc425 100%)", icon: "🌴", text: "#ffffff", border: "#ffc425" },
  "Texas Rangers": { bg: "linear-gradient(135deg, #003278 0%, #c0111f 100%)", icon: "🤠", text: "#ffffff", border: "#40c4ff" },
  "Seattle Mariners": { bg: "linear-gradient(135deg, #0c2c56 0%, #005c5c 100%)", icon: "🧭", text: "#ffffff", border: "#00e676" },
  "Chicago Cubs": { bg: "linear-gradient(135deg, #0e3386 0%, #cc3433 100%)", icon: "🐻", text: "#ffffff", border: "#ff5252" },
  "Boston Red Sox": { bg: "linear-gradient(135deg, #bd3039 0%, #0c2340 100%)", icon: "🧦", text: "#ffffff", border: "#ff5252" },
  "Minnesota Twins": { bg: "linear-gradient(135deg, #002b5c 0%, #d31145 100%)", icon: "👯", text: "#ffffff", border: "#40c4ff" },
  "Arizona Diamondbacks": { bg: "linear-gradient(135deg, #a71930 0%, #e3d4ad 100%)", icon: "🐍", text: "#ffffff", border: "#ff5252" },
  "Tampa Bay Rays": { bg: "linear-gradient(135deg, #092c5c 0%, #8fbce6 100%)", icon: "☀️", text: "#ffffff", border: "#8fbce6" },
  "Cleveland Guardians": { bg: "linear-gradient(135deg, #0c2340 0%, #e31937 100%)", icon: "🛡️", text: "#ffffff", border: "#ff5252" },
  "Toronto Blue Jays": { bg: "linear-gradient(135deg, #134a8e 0%, #1d2d5c 100%)", icon: "🐦", text: "#ffffff", border: "#40c4ff" },

  // WNBA
  "Las Vegas Aces": { bg: "linear-gradient(135deg, #000000 0%, #c5b358 100%)", icon: "♠️", text: "#ffffff", border: "#c5b358" },
  "New York Liberty": { bg: "linear-gradient(135deg, #6eceb2 0%, #000000 100%)", icon: "🗽", text: "#ffffff", border: "#6eceb2" },
  "Connecticut Sun": { bg: "linear-gradient(135deg, #ff6b00 0%, #001f3f 100%)", icon: "☀️", text: "#ffffff", border: "#ff9100" },
  "Minnesota Lynx": { bg: "linear-gradient(135deg, #236192 0%, #0c2340 100%)", icon: "🐾", text: "#ffffff", border: "#78be20" },
  "Seattle Storm": { bg: "linear-gradient(135deg, #00471b 0%, #fbe122 100%)", icon: "🌩️", text: "#ffffff", border: "#fbe122" },
  "Dallas Wings": { bg: "linear-gradient(135deg, #002b5e 0%, #c4d600 100%)", icon: "🪽", text: "#ffffff", border: "#c4d600" },
  "Phoenix Mercury": { bg: "linear-gradient(135deg, #281746 0%, #e56020 100%)", icon: "♀️", text: "#ffffff", border: "#ff6d00" },
  "Atlanta Dream": { bg: "linear-gradient(135deg, #c8102e 0%, #418fde 100%)", icon: "💭", text: "#ffffff", border: "#418fde" },
  "Chicago Sky": { bg: "linear-gradient(135deg, #418fde 0%, #fbe122 100%)", icon: "☁️", text: "#ffffff", border: "#fbe122" },
  "Indiana Fever": { bg: "linear-gradient(135deg, #041e42 0%, #c8102e 100%)", icon: "🔥", text: "#ffffff", border: "#ff5252" },
  "Washington Mystics": { bg: "linear-gradient(135deg, #0c2340 0%, #c8102e 100%)", icon: "✨", text: "#ffffff", border: "#ff5252" },
  "Los Angeles Sparks": { bg: "linear-gradient(135deg, #702082 0%, #ffd100 100%)", icon: "⚡", text: "#ffffff", border: "#ffd100" },

  // KBO
  "SSG Landers": { bg: "linear-gradient(135deg, #ce0e2d 0%, #1b1b1b 100%)", icon: "🚀", text: "#ffffff", border: "#ff5252" },
  "LG Twins": { bg: "linear-gradient(135deg, #c3002f 0%, #000000 100%)", icon: "👯", text: "#ffffff", border: "#ff5252" },
  "KT Wiz": { bg: "linear-gradient(135deg, #000000 0%, #e60012 100%)", icon: "🧙‍♂️", text: "#ffffff", border: "#ff5252" },
  "NC Dinos": { bg: "linear-gradient(135deg, #071d49 0%, #b29d6c 100%)", icon: "🦖", text: "#ffffff", border: "#b29d6c" },
  "Doosan Bears": { bg: "linear-gradient(135deg, #131230 0%, #ed1c24 100%)", icon: "🐻", text: "#ffffff", border: "#ed1c24" },
  "KIA Tigers": { bg: "linear-gradient(135deg, #ea0029 0%, #06142e 100%)", icon: "🐯", text: "#ffffff", border: "#ea0029" },
  "Lotte Giants": { bg: "linear-gradient(135deg, #041e42 0%, #dc0228 100%)", icon: "🗽", text: "#ffffff", border: "#40c4ff" },
  "Samsung Lions": { bg: "linear-gradient(135deg, #005bac 0%, #c0c0c0 100%)", icon: "🦁", text: "#ffffff", border: "#40c4ff" },
  "Hanwha Eagles": { bg: "linear-gradient(135deg, #f37321 0%, #231f20 100%)", icon: "🦅", text: "#ffffff", border: "#f37321" },
  "Kiwoom Heroes": { bg: "linear-gradient(135deg, #570514 0%, #990000 100%)", icon: "🦸", text: "#ffffff", border: "#ff5252" },

  // Liga MX (comparten equipos con Leagues Cup 2026)
  "América": { bg: "linear-gradient(135deg, #fce300 0%, #002d62 100%)", icon: "🦅", text: "#ffffff", border: "#fce300" },
  "Atlante": { bg: "linear-gradient(135deg, #1b3f8b 0%, #a9151b 100%)", icon: "🐘", text: "#ffffff", border: "#40c4ff" },
  "Atlas": { bg: "linear-gradient(135deg, #a4171a 0%, #000000 100%)", icon: "🦊", text: "#ffffff", border: "#ff5252" },
  "Atlético San Luis": { bg: "linear-gradient(135deg, #c8102e 0%, #ffffff 100%)", icon: "🔴", text: "#ffffff", border: "#ff5252" },
  "Cruz Azul": { bg: "linear-gradient(135deg, #00539f 0%, #ffffff 100%)", icon: "⚙️", text: "#ffffff", border: "#40c4ff" },
  "FC Juárez": { bg: "linear-gradient(135deg, #00953b 0%, #1b1b1b 100%)", icon: "🐺", text: "#ffffff", border: "#00e676" },
  "Guadalajara": { bg: "linear-gradient(135deg, #a3161a 0%, #002a54 100%)", icon: "🐐", text: "#ffffff", border: "#ff5252" },
  "León": { bg: "linear-gradient(135deg, #00612e 0%, #ffffff 100%)", icon: "🦁", text: "#ffffff", border: "#00e676" },
  "Monterrey": { bg: "linear-gradient(135deg, #001b4d 0%, #a9151b 100%)", icon: "🐐", text: "#ffffff", border: "#40c4ff" },
  "Necaxa": { bg: "linear-gradient(135deg, #d81920 0%, #ffffff 100%)", icon: "⚡", text: "#ffffff", border: "#ff5252" },
  "Pachuca": { bg: "linear-gradient(135deg, #003876 0%, #ffffff 100%)", icon: "🦊", text: "#ffffff", border: "#40c4ff" },
  "Puebla": { bg: "linear-gradient(135deg, #00205b 0%, #ffffff 100%)", icon: "🦉", text: "#ffffff", border: "#40c4ff" },
  "Pumas UNAM": { bg: "linear-gradient(135deg, #002a54 0%, #b5a642 100%)", icon: "🐾", text: "#ffffff", border: "#b5a642" },
  "Querétaro": { bg: "linear-gradient(135deg, #1b1b1b 0%, #a4171a 100%)", icon: "⚔️", text: "#ffffff", border: "#ff5252" },
  "Santos Laguna": { bg: "linear-gradient(135deg, #1b8a3b 0%, #ffffff 100%)", icon: "🌵", text: "#ffffff", border: "#00e676" },
  "Tigres UANL": { bg: "linear-gradient(135deg, #ff8200 0%, #002d62 100%)", icon: "🐯", text: "#ffffff", border: "#ff8200" },
  "Tijuana": { bg: "linear-gradient(135deg, #b71234 0%, #1b1b1b 100%)", icon: "🦁", text: "#ffffff", border: "#ff5252" },
  "Toluca": { bg: "linear-gradient(135deg, #b3182c 0%, #001f5c 100%)", icon: "😈", text: "#ffffff", border: "#ff5252" },

  // Leagues Cup 2026 — clubes MLS / Canadá (30)
  "Atlanta United": { bg: "linear-gradient(135deg, #80000a 0%, #000000 100%)", icon: "🦅", text: "#ffffff", border: "#ff5252" },
  "Austin FC": { bg: "linear-gradient(135deg, #00b140 0%, #1b1b1b 100%)", icon: "🦇", text: "#ffffff", border: "#00e676" },
  "CF Montréal": { bg: "linear-gradient(135deg, #001e62 0%, #7f8083 100%)", icon: "⚜️", text: "#ffffff", border: "#40c4ff" },
  "Charlotte FC": { bg: "linear-gradient(135deg, #1a85c8 0%, #000000 100%)", icon: "👑", text: "#ffffff", border: "#40c4ff" },
  "Chicago Fire": { bg: "linear-gradient(135deg, #7b1c2c 0%, #003399 100%)", icon: "🔥", text: "#ffffff", border: "#ff5252" },
  "Colorado Rapids": { bg: "linear-gradient(135deg, #970d38 0%, #003366 100%)", icon: "🏔️", text: "#ffffff", border: "#40c4ff" },
  "Columbus Crew": { bg: "linear-gradient(135deg, #fde192 0%, #000000 100%)", icon: "⚒️", text: "#ffffff", border: "#fdbb30" },
  "D.C. United": { bg: "linear-gradient(135deg, #000000 0%, #c01130 100%)", icon: "⭐", text: "#ffffff", border: "#ff5252" },
  "FC Cincinnati": { bg: "linear-gradient(135deg, #003087 0%, #f68d2e 100%)", icon: "🐯", text: "#ffffff", border: "#f68d2e" },
  "FC Dallas": { bg: "linear-gradient(135deg, #c30231 0%, #041e42 100%)", icon: "⚡", text: "#ffffff", border: "#ff5252" },
  "Houston Dynamo": { bg: "linear-gradient(135deg, #f4791f 0%, #101820 100%)", icon: "⚡", text: "#ffffff", border: "#f4791f" },
  "Inter Miami CF": { bg: "linear-gradient(135deg, #f7b5cd 0%, #231f20 100%)", icon: "🩷", text: "#ffffff", border: "#f7b5cd" },
  "LA Galaxy": { bg: "linear-gradient(135deg, #00245d 0%, #a5acaf 100%)", icon: "🌌", text: "#ffffff", border: "#40c4ff" },
  "Los Angeles FC": { bg: "linear-gradient(135deg, #000000 0%, #c39e6d 100%)", icon: "🖤", text: "#ffffff", border: "#c39e6d" },
  "Minnesota United": { bg: "linear-gradient(135deg, #8fd0e0 0%, #1b1b1b 100%)", icon: "🐦", text: "#ffffff", border: "#8fd0e0" },
  "Nashville SC": { bg: "linear-gradient(135deg, #ecdd53 0%, #17242d 100%)", icon: "🎸", text: "#ffffff", border: "#ecdd53" },
  "New England Revolution": { bg: "linear-gradient(135deg, #0a2240 0%, #c8102e 100%)", icon: "🇺🇸", text: "#ffffff", border: "#40c4ff" },
  "New York City FC": { bg: "linear-gradient(135deg, #6cace4 0%, #0033a1 100%)", icon: "🗽", text: "#ffffff", border: "#6cace4" },
  "New York Red Bulls": { bg: "linear-gradient(135deg, #ed1e36 0%, #001c58 100%)", icon: "🐂", text: "#ffffff", border: "#ff5252" },
  "Orlando City": { bg: "linear-gradient(135deg, #61259e 0%, #351359 100%)", icon: "🦁", text: "#ffffff", border: "#b388ff" },
  "Philadelphia Union": { bg: "linear-gradient(135deg, #0c1a2b 0%, #b19b67 100%)", icon: "🔔", text: "#ffffff", border: "#b19b67" },
  "Portland Timbers": { bg: "linear-gradient(135deg, #004812 0%, #cba14e 100%)", icon: "🌲", text: "#ffffff", border: "#cba14e" },
  "Real Salt Lake": { bg: "linear-gradient(135deg, #b30838 0%, #013b7f 100%)", icon: "⚡", text: "#ffffff", border: "#ff5252" },
  "San Diego FC": { bg: "linear-gradient(135deg, #6cace4 0%, #051c2c 100%)", icon: "🌊", text: "#ffffff", border: "#6cace4" },
  "San Jose Earthquakes": { bg: "linear-gradient(135deg, #002b5c 0%, #003da5 100%)", icon: "🌎", text: "#ffffff", border: "#40c4ff" },
  "Seattle Sounders FC": { bg: "linear-gradient(135deg, #5d9741 0%, #00243d 100%)", icon: "🌩️", text: "#ffffff", border: "#5d9741" },
  "Sporting Kansas City": { bg: "linear-gradient(135deg, #91b0d5 0%, #002b5c 100%)", icon: "⚔️", text: "#ffffff", border: "#91b0d5" },
  "St. Louis City SC": { bg: "linear-gradient(135deg, #d3242a 0%, #041e42 100%)", icon: "⚜️", text: "#ffffff", border: "#ff5252" },
  "Toronto FC": { bg: "linear-gradient(135deg, #b81137 0%, #1b1b1b 100%)", icon: "🍁", text: "#ffffff", border: "#ff5252" },
  "Vancouver Whitecaps": { bg: "linear-gradient(135deg, #00245e 0%, #a2adb5 100%)", icon: "🏔️", text: "#ffffff", border: "#40c4ff" },
};

export default function TeamIcon({ teamName, size = 48, logoUrl }) {
  const conf = TEAM_CONFIGS[teamName] || {
    bg: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
    icon: "🏆",
    text: "#ffffff",
    border: "#00f2fe"
  };

  const getInitials = (name) => {
    if (!name) return "TM";
    const parts = name.split(" ");
    if (parts.length >= 3) return parts[0][0] + parts[1][0] + parts[2][0];
    if (parts.length === 2) return parts[0][0] + parts[1][0];
    return name.substring(0, 2).toUpperCase();
  };

  if (logoUrl) {
    return (
      <div style={{
        width: `${size}px`,
        height: `${size}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '0 auto 8px',
      }}>
        <img src={logoUrl} alt={teamName} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
      </div>
    );
  }

  return (
    <div style={{
      width: `${size}px`,
      height: `${size}px`,
      borderRadius: '50%',
      background: conf.bg,
      border: `2px solid ${conf.border}`,
      boxShadow: `0 0 16px ${conf.border}40`,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      margin: '0 auto 8px',
      position: 'relative',
      overflow: 'hidden',
      userSelect: 'none'
    }}>
      <span style={{ fontSize: `${size * 0.42}px`, lineHeight: 1 }}>{conf.icon}</span>
      <span style={{
        fontSize: `${size * 0.22}px`,
        fontWeight: 900,
        color: conf.text,
        letterSpacing: '0.5px',
        lineHeight: 1,
        marginTop: '2px',
        textShadow: '0 1px 3px rgba(0,0,0,0.8)'
      }}>
        {getInitials(teamName)}
      </span>
    </div>
  );
}
