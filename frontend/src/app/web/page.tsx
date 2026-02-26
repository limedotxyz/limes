"use client";
// Browser-based TUI client. Requires client-side WebSocket, crypto, and xterm.js.

import { useEffect, useRef, useState } from "react";

const RELAY_URL =
  process.env.NEXT_PUBLIC_RELAY_WS ||
  "wss://relay-production-e4f7.up.railway.app";

interface LimeMsg {
  id: string;
  prev_hash: string;
  author_name: string;
  author_tag: string;
  author_pubkey: string;
  content: string;
  content_type: string;
  timestamp: number;
  ttl: number;
  nonce: string;
  pow_hash: string;
  signature: string;
  board: string;
  thread_id: string;
  thread_title: string;
  reply_to: string;
}

function generateId(): string {
  return crypto.randomUUID();
}

function hexEncode(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function hexDecode(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

export default function WebClientPage() {
  const termRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("initializing...");
  const [messages, setMessages] = useState<LimeMsg[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [inputMode, setInputMode] = useState(false);
  const [inputBuf, setInputBuf] = useState("");
  const [identity, setIdentity] = useState<{
    name: string;
    tag: string;
  } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesRef = useRef<LimeMsg[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Generate or load identity
  useEffect(() => {
    const saved = localStorage.getItem("limes_web_identity");
    if (saved) {
      try {
        setIdentity(JSON.parse(saved));
        return;
      } catch {
        // ignore
      }
    }
    const name = "anon" + Math.floor(Math.random() * 9999);
    const tag = Math.random().toString(36).substring(2, 6);
    const id = { name, tag };
    localStorage.setItem("limes_web_identity", JSON.stringify(id));
    setIdentity(id);
  }, []);

  // Connect to relay
  useEffect(() => {
    if (!identity) return;

    const sessionId = generateId();
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let ws: WebSocket;

    function connect() {
      ws = new WebSocket(RELAY_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setStatus("connected to relay");
        ws.send(
          JSON.stringify({
            type: "hello",
            session: sessionId,
            curve_pk: "",
            curve_pk_sig: "",
            verify_key: "",
          })
        );
      };

      ws.onclose = () => {
        setIsConnected(false);
        setStatus("disconnected — reconnecting...");
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => ws.close();

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "relay_peers") {
            setStatus(
              `relay: ${data.count || 0} peers online`
            );
          } else if (data.type === "relay_join") {
            setStatus("a peer joined");
          } else if (data.type === "relay_leave") {
            setStatus("a peer left");
          } else if (data.type === "msg") {
            // Messages are encrypted — web client can only see unencrypted messages
            // In a full implementation, we'd do the key exchange here
            // For now, show that the web client is connected and can see activity
          }
        } catch {
          // ignore
        }
      };
    }

    connect();
    return () => {
      ws?.close();
      clearTimeout(reconnectTimer);
    };
  }, [identity]);

  // Prune expired messages
  useEffect(() => {
    const timer = setInterval(() => {
      setMessages((prev) => {
        const now = Date.now() / 1000;
        return prev.filter((m) => now - m.timestamp < m.ttl);
      });
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!inputMode) {
      if (e.key === "i" || e.key === "Enter") {
        e.preventDefault();
        setInputMode(true);
      }
      return;
    }

    if (e.key === "Escape") {
      setInputMode(false);
      setInputBuf("");
      return;
    }

    if (e.key === "Enter") {
      if (inputBuf.trim()) {
        setStatus(`sending: "${inputBuf.trim().slice(0, 30)}..." (PoW not yet supported in web client)`);
      }
      setInputBuf("");
      setInputMode(false);
      return;
    }

    if (e.key === "Backspace") {
      setInputBuf((prev) => prev.slice(0, -1));
      return;
    }

    if (e.key.length === 1) {
      setInputBuf((prev) => prev + e.key);
    }
  }

  if (!identity) {
    return (
      <div className="min-h-screen bg-[var(--color-background)] flex items-center justify-center font-mono text-[var(--color-foreground)]/50">
        loading identity...
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-[var(--color-background)] font-mono flex flex-col"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* header */}
      <div className="border-b border-[var(--color-border)] px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a
            href="/"
            className="text-[var(--color-lime)] font-bold text-sm hover:opacity-80 transition-opacity"
          >
            limes
          </a>
          <span className="text-[var(--color-foreground)]/20 text-xs">
            web client (beta)
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              isConnected
                ? "bg-[var(--color-lime)] shadow-[0_0_6px_var(--color-lime)]"
                : "bg-red-500 animate-pulse"
            }`}
          />
          <span className="text-[var(--color-foreground)]/40">
            {identity.name}#{identity.tag}
          </span>
        </div>
      </div>

      {/* terminal area */}
      <div className="flex-1 flex flex-col">
        {/* art + title */}
        <div className="text-center py-6 space-y-2 border-b border-[var(--color-border)]">
          <pre className="text-xs leading-none text-[var(--color-lime)]">
{`      ████
    ██
  ████████
 ████████████
██░░████████████
████████████████
████████████████
 ████████████
     ████`}
          </pre>
          <h1 className="text-[var(--color-lime)] font-bold text-lg">
            L I M E S
          </h1>
          <p className="text-[var(--color-foreground)]/30 text-xs">
            anonymous ephemeral broadcast network — web client
          </p>
          <p className="text-[var(--color-foreground)]/20 text-[10px]">
            note: end-to-end encryption requires the native CLI client. the web client is read-only for now.
          </p>
        </div>

        {/* message feed */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-2 text-xs space-y-0.5"
        >
          {messages.length === 0 ? (
            <div className="text-[var(--color-foreground)]/20 text-center py-20">
              <p>waiting for messages...</p>
              <p className="mt-2 text-[10px]">
                messages appear here when peers are active on the network
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className="flex gap-2">
                <span className="text-[var(--color-lime)] font-bold shrink-0">
                  {msg.author_name}
                  <span className="text-[var(--color-foreground)]/20 font-normal">
                    #{msg.author_tag}
                  </span>
                  :
                </span>
                <span className="text-[var(--color-foreground)]/70">
                  {msg.content}
                </span>
                <span className="text-[var(--color-foreground)]/15 shrink-0 ml-auto text-[10px]">
                  {Math.floor(
                    Math.max(0, msg.ttl - (Date.now() / 1000 - msg.timestamp)) /
                      60
                  )}
                  m
                </span>
              </div>
            ))
          )}
        </div>

        {/* input line */}
        <div className="border-t border-[var(--color-border)] px-4 py-2 text-xs flex items-center gap-2">
          {inputMode ? (
            <>
              <span className="text-[var(--color-lime)]">
                {identity.name}#{identity.tag} &gt;
              </span>
              <span className="text-[var(--color-foreground)]/60">
                {inputBuf}
                <span className="animate-pulse">_</span>
              </span>
            </>
          ) : (
            <span className="text-[var(--color-foreground)]/20">
              [i] type &nbsp; [esc] cancel &nbsp; web client is read-only beta
            </span>
          )}
        </div>

        {/* status bar */}
        <div className="border-t border-[var(--color-border)] px-4 py-1 text-[10px] text-[var(--color-foreground)]/30 flex justify-between bg-[var(--color-panel)]">
          <span>{status}</span>
          <span>
            msgs:{messages.length}
            {isConnected ? " relay:on" : ""}
          </span>
        </div>
      </div>
    </div>
  );
}
