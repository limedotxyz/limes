"use client";
// Client component required for WebSocket connection and real-time state updates.

import { useEffect, useRef, useState, useCallback } from "react";

const SCANNER_WS = process.env.NEXT_PUBLIC_SCANNER_WS || "wss://relay-production-e4f7.up.railway.app/live";
const LIME_CONTRACT = process.env.NEXT_PUBLIC_LIME_CONTRACT || "";

interface LimeMessage {
  id: string;
  author_name: string;
  author_tag: string;
  content: string;
  content_type: string;
  timestamp: number;
  ttl: number;
  pow_hash: string;
  nonce: number;
  relayed_at?: number;
  board?: string;
  thread_id?: string;
  thread_title?: string;
  reply_to?: string;
}

interface ScanEvent {
  type: string;
  data?: LimeMessage;
  peer?: string;
  peers_online?: number;
  peers?: string[];
  total_messages?: number;
  total_connections?: number;
  uptime?: number;
  recent_messages?: { data: LimeMessage; relayed_at: number }[];
  relay_wallet?: string;
  ts?: number;
}

interface MiningEvent {
  author: string;
  pow_hash: string;
  nonce: number;
  ts: number;
}

type ExpandedPanel = "authors" | "mining" | "events" | null;

function formatTimeLeft(msg: LimeMessage): string {
  const elapsed = Date.now() / 1000 - msg.timestamp;
  const remaining = msg.ttl - elapsed;
  if (remaining <= 0) return "expired";
  const m = Math.floor(remaining / 60);
  const s = Math.floor(remaining % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatAgo(ts: number): string {
  const ago = Date.now() / 1000 - ts;
  if (ago < 60) return `${Math.floor(ago)}s ago`;
  if (ago < 3600) return `${Math.floor(ago / 60)}m ago`;
  return `${Math.floor(ago / 3600)}h ago`;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function truncateHash(hash: string): string {
  if (!hash) return "";
  return hash.slice(0, 8) + "..." + hash.slice(-6);
}

export default function ScanPage() {
  const [messages, setMessages] = useState<LimeMessage[]>([]);
  const [authors, setAuthors] = useState<string[]>([]);
  const [peerCount, setPeerCount] = useState(0);
  const [totalMessages, setTotalMessages] = useState(0);
  const [relayWallet, setRelayWallet] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<{ text: string; ts: number; type: string }[]>([]);
  const [miningEvents, setMiningEvents] = useState<MiningEvent[]>([]);
  const [tick, setTick] = useState(0);
  const [uptime, setUptime] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedPanel, setExpandedPanel] = useState<ExpandedPanel>(null);
  const [selectedMessage, setSelectedMessage] = useState<LimeMessage | null>(null);
  const [boardFilter, setBoardFilter] = useState<string>("all");
  const [threadFilter, setThreadFilter] = useState<string>("all");
  const wsRef = useRef<WebSocket | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const addEvent = useCallback((text: string, type: string = "info") => {
    setEvents((prev) => [...prev.slice(-200), { text, ts: Date.now() / 1000, type }]);
  }, []);

  useEffect(() => {
    const t = setInterval(() => setTick((p) => p + 1), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const pruneInterval = setInterval(() => {
      setMessages((prev) => {
        const now = Date.now() / 1000;
        return prev.filter((m) => now - m.timestamp < m.ttl);
      });
    }, 5000);
    return () => clearInterval(pruneInterval);
  }, []);

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let hasLoggedDisconnect = false;

    function connect() {
      ws = new WebSocket(SCANNER_WS);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        hasLoggedDisconnect = false;
        addEvent("connected to scanner", "system");
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (!hasLoggedDisconnect) {
          addEvent("disconnected — waiting for scanner", "error");
          hasLoggedDisconnect = true;
        }
        reconnectTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();

      ws.onmessage = (ev) => {
        try {
          const data: ScanEvent = JSON.parse(ev.data);

          if (data.type === "snapshot") {
            if (data.peers) setAuthors(data.peers);
            if (data.peers_online != null) setPeerCount(data.peers_online);
            if (data.total_messages != null) setTotalMessages(data.total_messages);
            if (data.uptime != null) setUptime(data.uptime);
            if (data.relay_wallet) setRelayWallet(data.relay_wallet);
            if (data.recent_messages) {
              const now = Date.now() / 1000;
              const seen = new Set<string>();
              const msgs = data.recent_messages
                .map((rm) => rm.data)
                .filter((m) => {
                  if (seen.has(m.id) || now - m.timestamp >= m.ttl) return false;
                  seen.add(m.id);
                  return true;
                });
              setMessages(msgs);
              msgs.forEach((m) => {
                setMiningEvents((prev) => [
                  ...prev.slice(-50),
                  {
                    author: `${m.author_name}#${m.author_tag}`,
                    pow_hash: m.pow_hash,
                    nonce: m.nonce,
                    ts: m.timestamp,
                  },
                ]);
              });
            }
            addEvent(
              `synced: ${data.peers_online} peers, ${data.total_messages} msgs`,
              "system"
            );
            return;
          }

          if (data.type === "message" && data.data) {
            const msg = data.data;
            setMessages((prev) =>
              prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]
            );
            setTotalMessages((prev) => prev + 1);
            const authorId = `${msg.author_name}#${msg.author_tag}`;
            setAuthors((prev) =>
              prev.includes(authorId) ? prev : [...prev, authorId]
            );
            addEvent(
              `${authorId}: "${msg.content.slice(0, 40)}${msg.content.length > 40 ? "..." : ""}"`,
              "message"
            );
            setMiningEvents((prev) => [
              ...prev.slice(-50),
              { author: authorId, pow_hash: msg.pow_hash, nonce: msg.nonce, ts: msg.timestamp },
            ]);
            return;
          }

          if (data.type === "peer_join") {
            if (data.peers_online != null) setPeerCount(data.peers_online);
            addEvent("a peer joined the network", "join");
            return;
          }

          if (data.type === "peer_leave") {
            if (data.peers_online != null) setPeerCount(data.peers_online);
            addEvent("a peer left the network", "leave");
            return;
          }
        } catch {
          // ignore
        }
      };
    }

    connect();
    return () => {
      ws?.close();
      clearTimeout(reconnectTimeout);
    };
  }, [addEvent]);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages]);

  const activeMessages = messages.filter(
    (m) => Date.now() / 1000 - m.timestamp < m.ttl
  );

  const boards = Array.from(new Set(activeMessages.map((m) => m.board || "general")));
  const boardFiltered = boardFilter === "all"
    ? activeMessages
    : activeMessages.filter((m) => (m.board || "general") === boardFilter);

  const threads = Array.from(
    new Map(
      boardFiltered
        .filter((m) => m.thread_title)
        .map((m) => [m.thread_id!, m.thread_title!])
    )
  );
  const threadFiltered = threadFilter === "all"
    ? boardFiltered
    : boardFiltered.filter((m) => m.thread_id === threadFilter);

  const q = searchQuery.toLowerCase().trim();
  const filteredMessages = q
    ? threadFiltered.filter(
        (m) =>
          m.author_name.toLowerCase().includes(q) ||
          m.author_tag.toLowerCase().includes(q) ||
          m.content.toLowerCase().includes(q) ||
          m.pow_hash.toLowerCase().includes(q)
      )
    : threadFiltered;

  return (
    <div className="min-h-screen bg-[var(--color-background)] font-mono">
      {/* expanded panel overlay */}
      {expandedPanel && (
        <ExpandedOverlay
          panel={expandedPanel}
          authors={authors}
          miningEvents={miningEvents}
          events={events}
          onClose={() => setExpandedPanel(null)}
        />
      )}

      {/* message detail overlay */}
      {selectedMessage && (
        <MessageDetail msg={selectedMessage} onClose={() => setSelectedMessage(null)} />
      )}

      <main className="mx-auto max-w-7xl px-4 py-5 space-y-4">
        {/* header */}
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <a href="https://lime.sh" className="hover:opacity-80 transition-opacity flex items-center gap-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/big lime.png" alt="limes" className="h-8 w-auto" />
              <span className="text-[var(--color-lime)] font-bold text-2xl" style={{ fontFamily: "var(--font-geist-pixel-square)" }}>
                limescan
              </span>
            </a>
            <div className="flex items-center gap-1.5 ml-3">
              <span
                className={`inline-block w-2 h-2 rounded-full ${
                  isConnected
                    ? "bg-[var(--color-lime)] shadow-[0_0_6px_var(--color-lime)]"
                    : "bg-red-500 animate-pulse"
                }`}
              />
              <span className="text-[var(--color-foreground)]/40 text-xs">
                {isConnected ? "live" : "connecting..."}
              </span>
            </div>
          </div>

          {/* search bar */}
          <div className="relative w-full sm:w-96">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by author, content, or pow hash..."
              className="w-full bg-[var(--color-panel)] border border-[var(--color-border)] text-[var(--color-foreground)] text-xs px-3 py-2 pl-8 placeholder:text-[var(--color-foreground)]/20 focus:outline-none focus:border-[var(--color-lime)]/40 transition-colors"
            />
            <svg
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--color-foreground)]/20"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" strokeLinecap="round" />
            </svg>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--color-foreground)]/30 hover:text-[var(--color-foreground)]/60 text-xs"
              >
                &times;
              </button>
            )}
          </div>
        </header>

        {/* stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <StatBox label="peers online" value={peerCount.toString()} highlight />
          <StatBox label="active messages" value={activeMessages.length.toString()} />
          <StatBox label="total relayed" value={totalMessages.toString()} />
          <StatBox label="proofs mined" value={miningEvents.length.toString()} />
          <StatBox label="uptime" value={formatUptime(uptime + tick)} />
          <StatBox
            label="relay wallet"
            value={relayWallet ? truncateHash(relayWallet) : "\u2014"}
            small
          />
        </div>

        {/* main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* message feed */}
          <div className="lg:col-span-8 space-y-2">
            <div className="flex items-center justify-between">
              <SectionHeader
                title="live messages"
                count={filteredMessages.length}
              />
              {q && (
                <span className="text-[10px] text-[var(--color-foreground)]/30">
                  filtered by &quot;{searchQuery}&quot;
                </span>
              )}
            </div>

            {/* board / thread filter */}
            <div className="flex flex-wrap items-center gap-1">
              <FilterBtn active={boardFilter === "all"} onClick={() => { setBoardFilter("all"); setThreadFilter("all"); }}>all</FilterBtn>
              {boards.map((b) => (
                <FilterBtn key={b} active={boardFilter === b} onClick={() => { setBoardFilter(b); setThreadFilter("all"); }}>/{b}/</FilterBtn>
              ))}
              {boardFilter !== "all" && threads.length > 0 && (
                <>
                  <span className="text-[var(--color-foreground)]/15 mx-1">|</span>
                  <FilterBtn active={threadFilter === "all"} onClick={() => setThreadFilter("all")}>all threads</FilterBtn>
                  {threads.map(([tid, title]) => (
                    <FilterBtn key={tid} active={threadFilter === tid} onClick={() => setThreadFilter(tid)}>
                      {(title ?? "untitled").length > 18 ? (title ?? "untitled").slice(0, 17) + "~" : (title ?? "untitled")}
                    </FilterBtn>
                  ))}
                </>
              )}
            </div>

            <div
              ref={feedRef}
              className="border border-[var(--color-border)] bg-[var(--color-panel)] h-[560px] overflow-y-auto text-xs"
            >
              {/* table header */}
              <div className="sticky top-0 bg-[var(--color-panel)] border-b border-[var(--color-border)] px-3 py-1.5 flex items-center text-[10px] text-[var(--color-foreground)]/30 uppercase tracking-wider">
                <span className="w-20 shrink-0">board</span>
                <span className="w-28 shrink-0">author</span>
                <span className="flex-1">message</span>
                <span className="w-24 text-right shrink-0">pow hash</span>
                <span className="w-14 text-right shrink-0">ttl</span>
              </div>
              {filteredMessages.length === 0 && (
                <p className="text-[var(--color-foreground)]/20 text-center py-20">
                  {q ? "no matches" : "waiting for messages..."}
                </p>
              )}
              {filteredMessages.map((msg) => (
                <MessageRow key={msg.id} msg={msg} onSelect={() => setSelectedMessage(msg)} />
              ))}
            </div>
          </div>

          {/* sidebar */}
          <div className="lg:col-span-4 space-y-4">
            {/* active authors */}
            <SidebarCard
              title="active authors"
              count={authors.length}
              onExpand={() => setExpandedPanel("authors")}
            >
              {authors.length === 0 ? (
                <p className="text-[var(--color-foreground)]/20 py-3 text-center">
                  no activity yet
                </p>
              ) : (
                authors.slice(0, 8).map((a) => (
                  <div key={a} className="flex items-center gap-1.5 py-0.5">
                    <span className="text-[var(--color-lime)] text-[8px]">&#x25CF;</span>
                    <span className="text-[var(--color-foreground)]/80">{a}</span>
                  </div>
                ))
              )}
              {authors.length > 8 && (
                <div className="text-[var(--color-foreground)]/20 text-center pt-1">
                  +{authors.length - 8} more
                </div>
              )}
            </SidebarCard>

            {/* mining activity */}
            <SidebarCard
              title="mining activity"
              count={miningEvents.length}
              onExpand={() => setExpandedPanel("mining")}
            >
              {miningEvents.length === 0 ? (
                <p className="text-[var(--color-foreground)]/20 py-3 text-center">
                  no proofs yet
                </p>
              ) : (
                [...miningEvents]
                  .reverse()
                  .slice(0, 5)
                  .map((me, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between py-0.5 border-b border-[var(--color-border)]/10 last:border-0"
                    >
                      <div>
                        <span className="text-[var(--color-lime)]">
                          {me.author.split("#")[0]}
                        </span>
                        <span className="text-[var(--color-foreground)]/20">
                          #{me.author.split("#")[1]}
                        </span>
                      </div>
                      <span className="text-[var(--color-foreground)]/15 text-[10px]">
                        {truncateHash(me.pow_hash)}
                      </span>
                    </div>
                  ))
              )}
              {miningEvents.length > 5 && (
                <div className="text-[var(--color-foreground)]/20 text-center pt-1">
                  +{miningEvents.length - 5} more
                </div>
              )}
            </SidebarCard>

            {/* event log */}
            <SidebarCard
              title="event log"
              onExpand={() => setExpandedPanel("events")}
            >
              {events.length === 0 ? (
                <p className="text-[var(--color-foreground)]/20 py-3 text-center">
                  no events
                </p>
              ) : (
                [...events]
                  .reverse()
                  .slice(0, 6)
                  .map((e, i) => (
                    <div key={i} className="flex gap-2 py-0.5">
                      <span className="text-[var(--color-foreground)]/15 shrink-0 w-10 text-right text-[10px]">
                        {formatAgo(e.ts)}
                      </span>
                      <EventDot type={e.type} />
                      <span
                        className={`truncate ${
                          e.type === "error"
                            ? "text-red-400"
                            : e.type === "join"
                              ? "text-[var(--color-lime)]/70"
                              : e.type === "leave"
                                ? "text-[var(--color-foreground)]/30"
                                : e.type === "message"
                                  ? "text-[var(--color-foreground)]/50"
                                  : "text-[var(--color-foreground)]/40"
                        }`}
                      >
                        {e.text}
                      </span>
                    </div>
                  ))
              )}
              {events.length > 6 && (
                <div className="text-[var(--color-foreground)]/20 text-center pt-1">
                  +{events.length - 6} more
                </div>
              )}
            </SidebarCard>

            {/* $LIME token */}
            <div className="border border-[var(--color-border)] bg-[var(--color-panel)] text-xs">
              <div className="px-3 py-2 border-b border-[var(--color-border)] text-[var(--color-lime)] font-bold text-sm">
                $LIME
              </div>
              <div className="p-3 space-y-1.5">
                <TokenRow label="chain" value="Base L2" />
                <TokenRow label="launch" value="Clanker" />
                <TokenRow label="reward" value="1.0 LIME / proof" lime />
                <TokenRow label="relay rewards" value="100% (vault)" />
                <TokenRow label="min stake" value="250,000 LIME" />
                <TokenRow label="max supply" value="1,000,000,000" />
                <TokenRow label="vault pool" value="30% (300M)" />
                <TokenRow label="difficulty" value="20 bits" />
                {LIME_CONTRACT ? (
                  <div className="flex justify-between">
                    <span className="text-[var(--color-foreground)]/30">contract</span>
                    <a
                      href={`https://basescan.org/address/${LIME_CONTRACT}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[var(--color-lime)] hover:underline"
                    >
                      {truncateHash(LIME_CONTRACT)}
                    </a>
                  </div>
                ) : (
                  <div className="text-[var(--color-foreground)]/20 text-center pt-1">
                    not deployed yet
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* footer */}
        <footer className="border-t border-[var(--color-border)] pt-4 space-y-2">
          <div className="flex justify-center items-center gap-3">
            <a href="https://github.com/limedotxyz/limes" target="_blank" rel="noopener noreferrer" className="text-[var(--color-foreground)]/30 hover:text-[var(--color-lime)] transition-colors" title="GitHub">
              <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
            </a>
            <a href="#" target="_blank" rel="noopener noreferrer" className="text-[var(--color-foreground)]/30 hover:text-[var(--color-lime)] transition-colors" title="Clanker launch">
              <svg viewBox="0 0 940 1000" fill="currentColor" className="w-5 h-5">
                <path d="M0 1000V757.576H181.818V1000H0Z" />
                <path d="M378.788 1000V378.788H560.606V1000H378.788Z" />
                <path d="M939.394 1000H757.576V0H939.394V1000Z" />
              </svg>
            </a>
          </div>
          <div className="text-center text-xs text-[var(--color-foreground)]/20">
            <a href="https://limescan.xyz" className="hover:text-[var(--color-lime)]">limescan.xyz</a>
            {" \u00B7 "}
            <a href="https://lime.sh" className="hover:text-[var(--color-lime)]">lime.sh</a>
            {" \u00B7 "}
            <a href="https://lime.sh/docs" className="hover:text-[var(--color-lime)]">docs</a>
          </div>
        </footer>
      </main>
    </div>
  );
}

// ------------------------------------------------------------------
// Expanded overlay
// ------------------------------------------------------------------

function ExpandedOverlay({
  panel,
  authors,
  miningEvents,
  events,
  onClose,
}: {
  panel: ExpandedPanel;
  authors: string[];
  miningEvents: MiningEvent[];
  events: { text: string; ts: number; type: string }[];
  onClose: () => void;
}) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-[var(--color-background)]/95 backdrop-blur-sm flex items-start justify-center pt-16 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-3xl border border-[var(--color-border)] bg-[var(--color-panel)] max-h-[75vh] flex flex-col">
        {/* overlay header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)] shrink-0">
          <h2 className="text-[var(--color-lime)] font-bold text-sm">
            {panel === "authors" && `active authors (${authors.length})`}
            {panel === "mining" && `mining activity (${miningEvents.length})`}
            {panel === "events" && `event log (${events.length})`}
          </h2>
          <button
            onClick={onClose}
            className="text-[var(--color-foreground)]/30 hover:text-[var(--color-foreground)]/70 text-lg leading-none transition-colors"
          >
            &times;
          </button>
        </div>

        {/* overlay content */}
        <div className="overflow-y-auto p-4 text-xs space-y-0.5">
          {panel === "authors" &&
            (authors.length === 0 ? (
              <p className="text-[var(--color-foreground)]/20 text-center py-10">
                no activity yet
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                {authors.map((a) => (
                  <div key={a} className="flex items-center gap-2 py-1.5 px-2 border border-[var(--color-border)]/20 hover:border-[var(--color-lime)]/20 transition-colors">
                    <span className="text-[var(--color-lime)] text-[8px]">&#x25CF;</span>
                    <span className="text-[var(--color-lime)] font-bold">
                      {a.split("#")[0]}
                    </span>
                    <span className="text-[var(--color-foreground)]/20">
                      #{a.split("#")[1]}
                    </span>
                  </div>
                ))}
              </div>
            ))}

          {panel === "mining" &&
            (miningEvents.length === 0 ? (
              <p className="text-[var(--color-foreground)]/20 text-center py-10">
                no proofs yet
              </p>
            ) : (
              <>
                {/* table header */}
                <div className="flex items-center text-[10px] text-[var(--color-foreground)]/25 uppercase tracking-wider pb-1 border-b border-[var(--color-border)]/20 mb-1">
                  <span className="w-32">author</span>
                  <span className="flex-1">pow hash</span>
                  <span className="w-16 text-right">nonce</span>
                  <span className="w-16 text-right">time</span>
                </div>
                {[...miningEvents].reverse().map((me, i) => (
                  <div
                    key={i}
                    className="flex items-center py-1 border-b border-[var(--color-border)]/10 last:border-0 hover:bg-[var(--color-border)]/10 transition-colors"
                  >
                    <div className="w-32">
                      <span className="text-[var(--color-lime)]">
                        {me.author.split("#")[0]}
                      </span>
                      <span className="text-[var(--color-foreground)]/20">
                        #{me.author.split("#")[1]}
                      </span>
                    </div>
                    <span className="flex-1 text-[var(--color-foreground)]/25 font-mono">
                      {me.pow_hash}
                    </span>
                    <span className="w-16 text-right text-[var(--color-foreground)]/20">
                      {me.nonce}
                    </span>
                    <span className="w-16 text-right text-[var(--color-foreground)]/20">
                      {formatAgo(me.ts)}
                    </span>
                  </div>
                ))}
              </>
            ))}

          {panel === "events" &&
            (events.length === 0 ? (
              <p className="text-[var(--color-foreground)]/20 text-center py-10">
                no events
              </p>
            ) : (
              [...events].reverse().map((e, i) => (
                <div key={i} className="flex gap-3 py-1 border-b border-[var(--color-border)]/10 last:border-0 hover:bg-[var(--color-border)]/10 transition-colors">
                  <span className="text-[var(--color-foreground)]/15 shrink-0 w-14 text-right">
                    {formatAgo(e.ts)}
                  </span>
                  <EventDot type={e.type} />
                  <span
                    className={
                      e.type === "error"
                        ? "text-red-400"
                        : e.type === "join"
                          ? "text-[var(--color-lime)]/70"
                          : e.type === "leave"
                            ? "text-[var(--color-foreground)]/30"
                            : e.type === "message"
                              ? "text-[var(--color-foreground)]/60"
                              : "text-[var(--color-foreground)]/40"
                    }
                  >
                    {e.text}
                  </span>
                </div>
              ))
            ))}
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Message detail overlay (like a tx page)
// ------------------------------------------------------------------

function MessageDetail({ msg, onClose }: { msg: LimeMessage; onClose: () => void }) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const elapsed = Date.now() / 1000 - msg.timestamp;
  const remaining = Math.max(0, msg.ttl - elapsed);
  const remainMin = Math.floor(remaining / 60);
  const remainSec = Math.floor(remaining % 60);
  const date = new Date(msg.timestamp * 1000);
  const board = msg.board || "general";

  return (
    <div
      className="fixed inset-0 z-50 bg-[var(--color-background)]/95 backdrop-blur-sm flex items-start justify-center pt-16 px-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-2xl border border-[var(--color-border)] bg-[var(--color-panel)]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
          <h2 className="text-[var(--color-lime)] font-bold text-sm">proof details</h2>
          <button
            onClick={onClose}
            className="text-[var(--color-foreground)]/30 hover:text-[var(--color-foreground)]/70 text-lg leading-none transition-colors"
          >
            &times;
          </button>
        </div>

        <div className="p-4 space-y-3 text-xs">
          <DetailRow label="pow hash" mono>
            <span className="text-[var(--color-lime)] break-all">{msg.pow_hash}</span>
          </DetailRow>
          <DetailRow label="nonce">
            <span className="text-[var(--color-foreground)]/70">{msg.nonce.toLocaleString()}</span>
          </DetailRow>
          <DetailRow label="status">
            {remaining > 0 ? (
              <span className="text-[var(--color-lime)]">
                active — {remainMin}:{remainSec.toString().padStart(2, "0")} remaining
              </span>
            ) : (
              <span className="text-red-400">expired</span>
            )}
          </DetailRow>

          <div className="border-t border-[var(--color-border)]/20 pt-3" />

          <DetailRow label="author">
            <span className="text-[var(--color-lime)] font-bold">{msg.author_name}</span>
            <span className="text-[var(--color-foreground)]/20">#{msg.author_tag}</span>
          </DetailRow>
          <DetailRow label="board">
            <span className="text-yellow-400/60">/{board}/</span>
          </DetailRow>
          {msg.thread_title && (
            <DetailRow label="thread">
              <span className="text-cyan-400/60">{msg.thread_title}</span>
            </DetailRow>
          )}
          <DetailRow label="timestamp">
            <span className="text-[var(--color-foreground)]/70">
              {date.toISOString()} ({formatAgo(msg.timestamp)})
            </span>
          </DetailRow>
          <DetailRow label="ttl">
            <span className="text-[var(--color-foreground)]/70">{msg.ttl}s ({Math.floor(msg.ttl / 60)} min)</span>
          </DetailRow>
          <DetailRow label="type">
            <span className="text-[var(--color-foreground)]/70">{msg.content_type}</span>
          </DetailRow>
          <DetailRow label="message id" mono>
            <span className="text-[var(--color-foreground)]/40 break-all">{msg.id}</span>
          </DetailRow>

          <div className="border-t border-[var(--color-border)]/20 pt-3" />

          <div>
            <div className="text-[var(--color-foreground)]/30 mb-1.5">content</div>
            <div className="bg-[var(--color-background)] border border-[var(--color-border)]/20 p-3 text-[var(--color-foreground)]/70 break-all whitespace-pre-wrap">
              {msg.content}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, mono, children }: { label: string; mono?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="text-[var(--color-foreground)]/30 shrink-0 w-24 text-right">{label}</span>
      <div className={mono ? "font-mono" : ""}>{children}</div>
    </div>
  );
}

// ------------------------------------------------------------------
// Shared components
// ------------------------------------------------------------------

function FilterBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-2 py-0.5 text-[10px] uppercase tracking-wider border transition-colors ${
        active
          ? "border-[var(--color-lime)] text-[var(--color-lime)] bg-[var(--color-lime)]/10"
          : "border-[var(--color-border)] text-[var(--color-foreground)]/30 hover:text-[var(--color-foreground)]/60"
      }`}
    >
      {children}
    </button>
  );
}

function SectionHeader({
  title,
  count,
}: {
  title: string;
  count?: number;
}) {
  return (
    <h2 className="text-[var(--color-lime)] font-bold text-sm flex items-center gap-2">
      <span>{title}</span>
      {count != null && (
        <span className="text-[var(--color-foreground)]/20 font-normal">
          ({count})
        </span>
      )}
    </h2>
  );
}

function SidebarCard({
  title,
  count,
  onExpand,
  children,
}: {
  title: string;
  count?: number;
  onExpand: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-panel)] text-xs">
      <button
        onClick={onExpand}
        className="w-full flex items-center justify-between px-3 py-2 border-b border-[var(--color-border)] hover:bg-[var(--color-border)]/20 transition-colors text-left group"
      >
        <span className="text-[var(--color-lime)] font-bold text-sm flex items-center gap-2">
          {title}
          {count != null && (
            <span className="text-[var(--color-foreground)]/20 font-normal">
              ({count})
            </span>
          )}
        </span>
        <span className="text-[var(--color-foreground)]/20 group-hover:text-[var(--color-lime)] transition-colors text-xs">
          view all &rarr;
        </span>
      </button>
      <div className="p-2 space-y-0.5">{children}</div>
    </div>
  );
}

function StatBox({
  label,
  value,
  highlight,
  small,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  small?: boolean;
}) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-2.5">
      <div
        className={`font-bold ${
          highlight
            ? "text-[var(--color-lime)] text-xl"
            : small
              ? "text-[var(--color-foreground)]/60 text-xs"
              : "text-[var(--color-foreground)] text-lg"
        }`}
      >
        {value}
      </div>
      <div className="text-[var(--color-foreground)]/30 text-[10px] mt-0.5">
        {label}
      </div>
    </div>
  );
}

function TokenRow({ label, value, lime }: { label: string; value: string; lime?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-[var(--color-foreground)]/30">{label}</span>
      <span className={lime ? "text-[var(--color-lime)]" : "text-[var(--color-foreground)]/70"}>
        {value}
      </span>
    </div>
  );
}

function EventDot({ type }: { type: string }) {
  const color =
    type === "join"
      ? "bg-[var(--color-lime)]"
      : type === "leave"
        ? "bg-[var(--color-foreground)]/30"
        : type === "message"
          ? "bg-cyan-400"
          : type === "error"
            ? "bg-red-400"
            : "bg-[var(--color-foreground)]/20";
  return <span className={`inline-block w-1.5 h-1.5 rounded-full shrink-0 mt-1 ${color}`} />;
}

function MessageRow({ msg, onSelect }: { msg: LimeMessage; onSelect: () => void }) {
  const timeLeft = formatTimeLeft(msg);
  const elapsed = Date.now() / 1000 - msg.timestamp;
  const isExpiring = msg.ttl - elapsed < 120;
  const board = msg.board || "general";
  const isThreadStart = !!msg.thread_title;

  return (
    <div className="flex items-start gap-2 py-1.5 px-3 border-b border-[var(--color-border)]/10 last:border-0 hover:bg-[var(--color-border)]/10 transition-colors">
      <div className="shrink-0 w-20">
        <span className="text-yellow-400/60 text-[10px]">/{board}/</span>
      </div>
      <div className="shrink-0 w-28">
        <span className="text-[var(--color-lime)] font-bold">
          {msg.author_name}
        </span>
        <span className="text-[var(--color-foreground)]/20">
          #{msg.author_tag}
        </span>
      </div>
      <div className="flex-1 text-[var(--color-foreground)]/70 break-all min-w-0">
        {isThreadStart && (
          <span className="text-cyan-400/60 text-[10px] mr-1">[thread]</span>
        )}
        {msg.content_type === "code" ? (
          <code className="bg-[var(--color-background)] px-1 py-0.5 text-[var(--color-foreground)]/60">
            {msg.content}
          </code>
        ) : (
          renderContent(msg.content)
        )}
      </div>
      <div className="shrink-0 w-24 text-right">
        <button
          onClick={onSelect}
          className="text-[9px] text-[var(--color-foreground)]/25 hover:text-[var(--color-lime)] transition-colors cursor-pointer font-mono"
          title="view proof details"
        >
          {truncateHash(msg.pow_hash || "")}
        </button>
      </div>
      <div className="shrink-0 w-14 text-right">
        <span
          className={`text-[10px] ${
            isExpiring
              ? "text-red-400 font-bold"
              : "text-[var(--color-foreground)]/25"
          }`}
        >
          {timeLeft}
        </span>
      </div>
    </div>
  );
}

function renderContent(content: string) {
  const parts = content.split(/@(\w+)/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <span key={i} className="text-cyan-400 font-bold">
        @{part}
      </span>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}
