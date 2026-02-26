"use client";
// Client component needed for command filter tabs and CA copy button.

import { useState } from "react";

const LIME_ART = `
      ████
    ██
  ████████
 ████████████
██░░████████████
████████████████
████████████████
 ████████████
     ████
`.trim();

const GITHUB_URL = "https://github.com/limedotxyz/limes";
const CLANKER_URL = "#"; // replace with clanker launch URL once live
const CONTRACT_ADDRESS = process.env.NEXT_PUBLIC_LIME_CONTRACT || "";

type CmdCat = "all" | "cli" | "network" | "chat";

const COMMANDS: { cmd: string; desc: string; cat: CmdCat }[] = [
  { cmd: "limes", desc: "open the chat", cat: "cli" },
  { cmd: "limes -v", desc: "show version", cat: "cli" },
  { cmd: "limes setup", desc: "run setup wizard", cat: "cli" },
  { cmd: "limes upgrade", desc: "update to latest", cat: "cli" },
  { cmd: "limes wallet", desc: "$LIME balance & address", cat: "cli" },
  { cmd: "limes reset", desc: "reset identity", cat: "cli" },
  { cmd: "limes relay", desc: "run a relay node (includes scanner)", cat: "network" },
  { cmd: "limes peers", desc: "list saved peers", cat: "network" },
  { cmd: "limes connect h:p", desc: "connect to peer by IP", cat: "network" },
  { cmd: "/t [title]", desc: "create a thread", cat: "chat" },
  { cmd: "/b [board]", desc: "switch boards", cat: "chat" },
  { cmd: "/boards", desc: "list boards", cat: "chat" },
  { cmd: "/threads", desc: "list threads", cat: "chat" },
  { cmd: "/reply [#] [msg]", desc: "reply to thread", cat: "chat" },
  { cmd: "/dm @name msg", desc: "send a direct message", cat: "chat" },
  { cmd: "/file path", desc: "share a file (<45KB)", cat: "chat" },
  { cmd: "/save # [path]", desc: "save a received file", cat: "chat" },
  { cmd: "/help", desc: "show all commands", cat: "chat" },
  { cmd: "/back", desc: "back to board chat", cat: "chat" },
  { cmd: "@name", desc: "mention a user", cat: "chat" },
];

function AsciiLime() {
  return (
    <pre className="text-xs leading-none sm:text-sm" aria-label="lime pixel art">
      {LIME_ART.split("\n").map((line, i) => (
        <span key={i} className="block">
          {[...line].map((ch, j) => {
            if (ch === "░")
              return <span key={j} className="text-white">{ch}</span>;
            if (ch === "█") {
              const isStem = i < 2;
              return (
                <span key={j} className={isStem ? "text-[var(--color-brown)]" : "text-[var(--color-lime)]"}>
                  {ch}
                </span>
              );
            }
            return <span key={j}>{ch}</span>;
          })}
        </span>
      ))}
    </pre>
  );
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}

export default function Home() {
  const [cmdFilter, setCmdFilter] = useState<CmdCat>("all");
  const [copied, setCopied] = useState(false);

  const filtered = cmdFilter === "all" ? COMMANDS : COMMANDS.filter((c) => c.cat === cmdFilter);

  function copyCA() {
    if (!CONTRACT_ADDRESS) return;
    navigator.clipboard.writeText(CONTRACT_ADDRESS);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="min-h-screen bg-[var(--color-background)] flex items-center justify-center">
      <main className="mx-auto max-w-xl px-6 py-8 space-y-6">
        {/* header */}
        <header className="space-y-2">
          <div className="flex justify-center">
            <AsciiLime />
          </div>
          <div className="text-center space-y-1">
            <h1
              className="text-4xl font-bold text-[var(--color-lime)]"
              style={{ fontFamily: "var(--font-geist-pixel-square)" }}
            >
              limes
            </h1>
            <p className="text-sm text-[var(--color-foreground)]/50">
              anonymous ephemeral broadcast network
            </p>
          </div>
          <nav className="flex justify-center gap-4 text-xs pt-1">
            <a href="/docs" className="text-[var(--color-lime)] hover:underline">docs</a>
            <a href="/web" className="text-[var(--color-foreground)]/40 hover:text-[var(--color-lime)]">web client</a>
            <a href="https://limescan.xyz" className="text-[var(--color-foreground)]/40 hover:text-[var(--color-lime)]">limescan</a>
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="text-[var(--color-foreground)]/40 hover:text-[var(--color-lime)]">github</a>
          </nav>
        </header>

        {/* brief description */}
        <p className="text-sm text-[var(--color-foreground)]/60 text-center leading-relaxed">
          decentralized terminal chat with boards and threads.
          messages self-destruct after 24 minutes. e2e encrypted.
          relay operators stake and earn{" "}
          <span className="text-[var(--color-lime)]">$LIME</span>.
        </p>

        {/* download */}
        <div className="flex justify-center">
          <a
            href={`${GITHUB_URL}/releases/latest`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block border border-[var(--color-lime)] text-[var(--color-lime)] px-8 py-2.5 text-sm hover:bg-[var(--color-lime)] hover:text-black transition-colors"
          >
            latest release
          </a>
        </div>

        {/* commands */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-[var(--color-lime)] font-bold text-sm">
              {">"} commands
            </h2>
            <div className="flex gap-1">
              {(["all", "cli", "network", "chat"] as CmdCat[]).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setCmdFilter(cat)}
                  className={`px-2.5 py-1 text-[10px] uppercase tracking-wider border transition-colors ${
                    cmdFilter === cat
                      ? "border-[var(--color-lime)] text-[var(--color-lime)] bg-[var(--color-lime)]/10"
                      : "border-[var(--color-border)] text-[var(--color-foreground)]/30 hover:text-[var(--color-foreground)]/60"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="border border-[var(--color-border)] bg-[var(--color-panel)] divide-y divide-[var(--color-border)]/20">
            {filtered.map((c) => (
              <div key={c.cmd} className="flex items-center px-3 py-1.5 text-xs font-mono">
                <span className="text-[var(--color-lime)] w-36 sm:w-40 shrink-0">{c.cmd}</span>
                <span className="text-[var(--color-foreground)]/40">{c.desc}</span>
              </div>
            ))}
          </div>

          <p className="text-[10px] text-[var(--color-foreground)]/20 text-center">
            see <a href="/docs#commands" className="text-[var(--color-lime)]/40 hover:underline">docs</a> for full reference and keybindings
          </p>
        </section>

        {/* footer */}
        <footer className="border-t border-[var(--color-border)] pt-4">
          {/* icon row */}
          <div className="flex justify-center items-center gap-3">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-foreground)]/30 hover:text-[var(--color-lime)] transition-colors"
              title="GitHub"
            >
              <GitHubIcon />
            </a>

            <a
              href={CLANKER_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[var(--color-foreground)]/30 hover:text-[var(--color-lime)] transition-colors"
              title="Clanker launch"
            >
              <svg viewBox="0 0 940 1000" fill="currentColor" className="w-5 h-5">
                <path d="M0 1000V757.576H181.818V1000H0Z" />
                <path d="M378.788 1000V378.788H560.606V1000H378.788Z" />
                <path d="M939.394 1000H757.576V0H939.394V1000Z" />
              </svg>
            </a>

            {CONTRACT_ADDRESS ? (
              <button
                onClick={copyCA}
                className="flex items-center gap-1.5 text-[10px] border border-[var(--color-border)] px-2 py-1 hover:border-[var(--color-lime)]/40 transition-colors"
                title={`Copy CA: ${CONTRACT_ADDRESS}`}
              >
                <span className="text-[var(--color-foreground)]/30">CA</span>
                <span className="text-[var(--color-foreground)]/50 font-mono">
                  {CONTRACT_ADDRESS.slice(0, 6)}...{CONTRACT_ADDRESS.slice(-4)}
                </span>
                <span className="text-[var(--color-lime)] text-[9px]">
                  {copied ? "copied" : "copy"}
                </span>
              </button>
            ) : (
              <span className="text-[10px] text-[var(--color-foreground)]/15 border border-[var(--color-border)] px-2 py-1">
                CA: not deployed
              </span>
            )}
          </div>

        </footer>
      </main>
    </div>
  );
}
