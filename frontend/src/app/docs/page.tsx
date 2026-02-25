import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "limes docs — how everything works",
  description: "technical documentation for limes: architecture, encryption, boards, relay protocol, proof-of-work, $LIME token, staking, and security model.",
};

const GITHUB_URL = "https://github.com/limedotxyz/limes";
const CLANKER_URL = "#";

function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-[var(--color-lime)] font-bold text-lg mt-12 mb-4 scroll-mt-20 group">
      <a href={`#${id}`} className="hover:underline">
        {">"} {children}
      </a>
    </h2>
  );
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[var(--color-foreground)] font-bold text-sm mt-6 mb-2">{children}</h3>;
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="text-[var(--color-foreground)]/70 text-sm leading-relaxed mb-3">{children}</p>;
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs font-mono space-y-1 my-4 overflow-x-auto">
      {children}
    </div>
  );
}

function Lime({ children }: { children: React.ReactNode }) {
  return <span className="text-[var(--color-lime)]">{children}</span>;
}

function Dim({ children }: { children: React.ReactNode }) {
  return <span className="text-[var(--color-foreground)]/40">{children}</span>;
}

function TableRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-1.5 border-b border-[var(--color-border)]/20 last:border-0 text-sm">
      <span className="text-[var(--color-foreground)]/40">{label}</span>
      <span className="text-[var(--color-foreground)]/80 text-right">{value}</span>
    </div>
  );
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
    </svg>
  );
}

const TOC = [
  { id: "overview", label: "overview" },
  { id: "architecture", label: "architecture" },
  { id: "boards", label: "boards & threads" },
  { id: "identity", label: "identity & anonymity" },
  { id: "encryption", label: "end-to-end encryption" },
  { id: "relay", label: "relay protocol" },
  { id: "pow", label: "proof-of-work" },
  { id: "token", label: "$LIME token & vault" },
  { id: "security", label: "security model" },
  { id: "commands", label: "CLI & chat commands" },
  { id: "faq", label: "FAQ" },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-[var(--color-background)] font-mono">
      <main className="mx-auto max-w-3xl px-6 py-12">
        {/* header */}
        <header className="mb-10">
          <div className="flex items-center gap-3 mb-6">
            <a href="/" className="text-[var(--color-lime)] font-bold text-xl hover:underline" style={{ fontFamily: "var(--font-geist-pixel-square)" }}>
              limes
            </a>
            <span className="text-[var(--color-foreground)]/20">/</span>
            <span className="text-[var(--color-foreground)] font-bold">docs</span>
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-lime)] mb-2">documentation</h1>
          <p className="text-sm text-[var(--color-foreground)]/50">how limes works, from the ground up.</p>
        </header>

        {/* table of contents */}
        <nav className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 mb-10">
          <div className="text-[var(--color-foreground)]/30 text-xs uppercase tracking-wider mb-3">contents</div>
          <div className="space-y-1">
            {TOC.map((item, i) => (
              <a key={item.id} href={`#${item.id}`} className="flex items-center gap-2 text-sm text-[var(--color-foreground)]/60 hover:text-[var(--color-lime)] transition-colors py-0.5">
                <span className="text-[var(--color-foreground)]/20 w-5 text-right text-xs">{i + 1}.</span>
                <span>{item.label}</span>
              </a>
            ))}
          </div>
        </nav>

        {/* ── OVERVIEW ── */}
        <H2 id="overview">overview</H2>
        <P>
          limes is an anonymous, ephemeral, peer-to-peer broadcast network that runs in your terminal.
          you pick a pseudonym, send messages that self-destruct after 24 minutes, and relay operators earn{" "}
          <Lime>$LIME</Lime> tokens for forwarding messages. there are no accounts, no servers that store
          data, and no history.
        </P>
        <P>the network is composed of three types of participants:</P>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-3 my-4">
          <div><Lime>peers</Lime> <Dim>— run the limes TUI, send and receive messages in boards and threads</Dim></div>
          <div><Lime>relays</Lime> <Dim>— forward encrypted traffic between peers, stake $LIME and earn rewards, cannot read anything</Dim></div>
          <div><Lime>scanners</Lime> <Dim>— full peers that serve a web dashboard (limescan) for live viewing</Dim></div>
        </div>

        {/* ── ARCHITECTURE ── */}
        <H2 id="architecture">architecture</H2>
        <P>
          limes uses a hybrid peer-to-peer architecture. peers on the same LAN discover each other via
          UDP multicast and connect directly over TCP. peers behind NATs connect through relay servers
          over WebSocket.
        </P>
        <Code>
          <p><Dim>{"// network topology"}</Dim></p>
          <p>&nbsp;</p>
          <p>{"  peer A ──TCP──> peer B        (LAN, direct)"}</p>
          <p>{"  peer C ──WS───> relay ──WS──> peer D   (NAT traversal)"}</p>
          <p>{"  scanner ──WS──> relay         (joins as a peer)"}</p>
          <p>{"  browser ──WS──> scanner       (read-only feed)"}</p>
        </Code>
        <H3>relay servers</H3>
        <P>
          relays are lightweight WebSocket servers that anyone can run with <Lime>limes relay</Lime>.
          they forward encrypted message blobs between connected peers. relays never see message content,
          usernames, or signing keys — only random session UUIDs and opaque ciphertext.
        </P>
        <H3>LAN discovery</H3>
        <P>
          on local networks, limes announces itself via UDP multicast on <Lime>239.42.42.42:4200</Lime>.
          peers that hear the announcement connect directly over TCP on port <Lime>4201</Lime>.
        </P>
        <H3>scanner servers</H3>
        <P>
          a scanner is a full limes peer that also runs a WebSocket server for the limescan web dashboard.
          it connects to a relay, participates in the key exchange, decrypts messages, and streams them
          to connected browsers. the relay itself remains blind — only the scanner can read content.
        </P>

        {/* ── BOARDS & THREADS ── */}
        <H2 id="boards">boards & threads</H2>
        <P>
          limes organizes conversations into <Lime>boards</Lime> and <Lime>threads</Lime>.
          boards are persistent — they exist as long as they&apos;re approved on-chain. threads within
          boards are ephemeral — they vanish when all their messages expire after 24 minutes.
        </P>
        <H3>board chat</H3>
        <P>
          <Lime>/general/</Lime> is the default board. users spawn directly into the board&apos;s
          main chat — just type and your message appears. no need to create a thread first.
          new boards are proposed and voted on by relay operators through the LimesVault smart
          contract. a board is approved when 3 relay operators vote for it.
        </P>
        <H3>threads</H3>
        <P>
          threads are optional — use <Lime>/t [title]</Lime> to spin up a focused discussion.
          press <Lime>t</Lime> in feed mode to view the thread list, then press <Lime>1-9</Lime> to
          enter one. threads disappear when all their messages expire.
        </P>
        <Code>
          <p><Dim>{"// board chat — just type"}</Dim></p>
          <p>&nbsp;</p>
          <p>{"  open limes → you're in /general/ chat"}</p>
          <p>{"  type a message → appears in the board feed"}</p>
          <p>&nbsp;</p>
          <p><Dim>{"// thread lifecycle"}</Dim></p>
          <p>&nbsp;</p>
          <p>{"  user types: /t gm everyone"}</p>
          <p>{"  → creates thread 't_a1b2c3' in /general/"}</p>
          <p>{"  → press [t] to see thread list"}</p>
          <p>{"  → press [1] to enter, type to reply"}</p>
          <p>{"  → press [q] to go back to board chat"}</p>
          <p>{"  → all messages expire after 24 min"}</p>
          <p>{"  → thread vanishes"}</p>
        </Code>
        <H3>board governance</H3>
        <P>
          relay operators (staked on-chain) can propose new boards via the LimesVault contract.
          each relay gets one vote per proposal. once 3 relays vote for a board, it&apos;s approved
          and available to all peers. this prevents spam boards while keeping governance decentralized.
        </P>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-1 my-4">
          <TableRow label="default board" value="/general/" />
          <TableRow label="board persistence" value="permanent (on-chain)" />
          <TableRow label="thread persistence" value="ephemeral (24 min)" />
          <TableRow label="approval threshold" value="3 relay votes" />
          <TableRow label="who can propose" value="staked relay operators" />
        </div>

        {/* ── IDENTITY ── */}
        <H2 id="identity">identity & anonymity</H2>
        <P>
          when you first run limes, you pick a pseudonym (1-20 characters, no spaces). limes generates a
          fresh <Lime>Ed25519</Lime> keypair and derives a 4-character hex tag from the public key. your
          identity is displayed as <Lime>name#tag</Lime> (e.g. &quot;alice#7f2a&quot;).
        </P>
        <P>
          the keypair is stored locally at <Lime>~/.lime/identity.json</Lime>. it never leaves your
          machine. if you delete it (<Lime>limes reset</Lime>), a new identity is generated next time.
        </P>
        <H3>what the network sees</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-2 my-4">
          <TableRow label="other limes peers" value="your name#tag + public key (not IP)" />
          <TableRow label="relay operators" value="random session UUID + encrypted blobs" />
          <TableRow label="LAN peers" value="your local IP + name#tag (same network only)" />
          <TableRow label="limescan viewers" value="name#tag + message content (public by design)" />
          <TableRow label="ISPs / network observers" value="that you connected to a relay IP (use VPN/Tor)" />
        </div>

        {/* ── ENCRYPTION ── */}
        <H2 id="encryption">end-to-end encryption</H2>
        <P>
          all messages sent through relay servers are end-to-end encrypted. the relay forwards
          ciphertext it cannot decrypt. this is implemented in three steps:
        </P>
        <H3>1. key derivation</H3>
        <P>
          each peer&apos;s Ed25519 signing key is converted to an X25519 key using NaCl&apos;s
          standard conversion. this gives each peer a Curve25519 keypair for Diffie-Hellman
          key exchange, without requiring a second keypair.
        </P>
        <H3>2. room key exchange</H3>
        <P>
          when the first peer connects to a relay, it generates a random 32-byte <Lime>room key</Lime>.
          when a new peer joins, existing peers encrypt the room key using NaCl <Lime>SealedBox</Lime> (anonymous
          public-key encryption) with the new peer&apos;s X25519 public key. the relay forwards this sealed
          blob but cannot open it.
        </P>
        <Code>
          <p><Dim>{"// key exchange flow"}</Dim></p>
          <p>&nbsp;</p>
          <p>{"  peer A: generates room_key (32 random bytes)"}</p>
          <p>{"  peer B: connects, sends curve25519 public key"}</p>
          <p>{"  peer A: SealedBox(room_key, B_public) → encrypted blob"}</p>
          <p>{"  relay:  forwards blob to B (cannot decrypt)"}</p>
          <p>{"  peer B: SealedBox.open(blob, B_private) → room_key"}</p>
        </Code>
        <H3>3. message encryption</H3>
        <P>
          all messages are serialized to JSON, then encrypted with NaCl <Lime>SecretBox</Lime> using
          the shared room key. the encrypted envelope (base64) is sent through the relay.
        </P>
        <H3>timing obfuscation</H3>
        <P>
          the relay adds a random delay of <Lime>50-300ms</Lime> before forwarding each message.
          this prevents timing-based traffic analysis.
        </P>

        {/* ── RELAY PROTOCOL ── */}
        <H2 id="relay">relay protocol</H2>
        <P>
          the relay speaks a simple JSON protocol over WebSocket. it understands 5 message types
          but cannot read the contents of any encrypted payload.
        </P>
        <H3>client → relay</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-3 my-4 overflow-x-auto">
          <div><Lime>hello</Lime> <Dim>— register with random session UUID + X25519 public key</Dim></div>
          <div><Lime>msg</Lime> <Dim>— encrypted message envelope (relay cannot read)</Dim></div>
          <div><Lime>key_request</Lime> <Dim>— ask peers for the room key</Dim></div>
          <div><Lime>key_share</Lime> <Dim>— send sealed room key to a specific session</Dim></div>
        </div>
        <H3>relay → client</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-3 my-4 overflow-x-auto">
          <div><Lime>relay_peers</Lime> <Dim>— list of connected sessions + X25519 keys</Dim></div>
          <div><Lime>relay_join</Lime> <Dim>— a new session connected (UUID only)</Dim></div>
          <div><Lime>relay_leave</Lime> <Dim>— a session disconnected</Dim></div>
          <div><Lime>relay_wallet</Lime> <Dim>— relay operator&apos;s $LIME wallet address</Dim></div>
        </div>
        <H3>relay limits</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-1 my-4">
          <TableRow label="max peers" value="500 concurrent" />
          <TableRow label="max scanners" value="20 concurrent" />
          <TableRow label="max message size" value="64 KB" />
          <TableRow label="rate limit" value="10 messages/second per peer" />
          <TableRow label="forwarding delay" value="50-300ms random" />
        </div>

        {/* ── POW ── */}
        <H2 id="pow">proof-of-work</H2>
        <P>
          every message requires a hashcash-style proof-of-work before it can be sent. this prevents
          spam and forms the basis for <Lime>$LIME</Lime> token rewards.
        </P>
        <H3>how it works</H3>
        <P>
          the message payload (id, author, content, board, thread, timestamp) is serialized to canonical JSON.
          the client iterates nonces until <Lime>SHA-256(payload || nonce)</Lime> has at least{" "}
          <Lime>20 leading zero bits</Lime>. this takes roughly 1-2 seconds.
        </P>
        <Code>
          <p><Dim>{"// PoW algorithm"}</Dim></p>
          <p>&nbsp;</p>
          <p>{"  payload = canonical_json(id, author, content, board, thread, timestamp)"}</p>
          <p>{"  nonce = 0"}</p>
          <p>{"  loop:"}</p>
          <p>{"    hash = SHA-256(payload || nonce_bytes)"}</p>
          <p>{"    if hash < 2^(256 - 20):  // 20 leading zero bits"}</p>
          <p>{"      return (nonce, hash)"}</p>
          <p>{"    nonce += 1"}</p>
        </Code>

        {/* ── TOKEN & VAULT ── */}
        <H2 id="token">$LIME token & vault</H2>
        <P>
          <Lime>$LIME</Lime> is an ERC-20 token on <Lime>Base L2</Lime>, deployed via{" "}
          <Lime>Clanker</Lime>. 30% of the total supply (300M LIME) is held in the{" "}
          <Lime>LimesVault</Lime> smart contract, which handles staking, rewards, and board governance.
        </P>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-1 my-4">
          <TableRow label="chain" value="Base L2 (chain ID 8453)" />
          <TableRow label="token standard" value="ERC-20" />
          <TableRow label="total supply" value="1,000,000,000 LIME" />
          <TableRow label="launch" value="Clanker (70% to Uniswap liquidity)" />
          <TableRow label="vault pool" value="30% (300,000,000 LIME)" />
          <TableRow label="reward per proof" value="1.0 LIME (from vault)" />
          <TableRow label="min stake" value="250,000 LIME" />
          <TableRow label="unstake cooldown" value="7 days" />
          <TableRow label="PoW difficulty" value="20 bits (SHA-256)" />
        </div>
        <H3>staking</H3>
        <P>
          relay operators must stake at least <Lime>250,000 LIME</Lime> to the LimesVault to register
          as an active relay. staking gives them the right to claim PoW rewards and vote on board proposals.
          unstaking requires a 7-day cooldown to prevent flash-stake attacks.
        </P>
        <H3>rewards</H3>
        <P>
          when a relay operator forwards a message, they can submit the PoW proof (payload + nonce) to the
          vault&apos;s <Lime>claimReward()</Lime> function. the vault verifies the proof on-chain and sends
          1.0 LIME from the pool. each proof can only be claimed once. only staked relay operators can claim.
          message senders do not earn tokens.
        </P>
        <H3>supply math</H3>
        <P>
          the vault holds 300M LIME. at 1 LIME per proof, the pool sustains 300 million messages before
          depletion. at 1,000 messages per day network-wide, that&apos;s ~822 years of rewards.
        </P>
        <H3>board governance</H3>
        <P>
          staked relay operators can call <Lime>proposeBoard(&quot;name&quot;)</Lime> on the vault contract.
          each relay gets one vote. when 3 relays have voted for a board, it&apos;s approved and goes live
          for all peers. /general/ is approved by default at deployment.
        </P>

        {/* ── SECURITY ── */}
        <H2 id="security">security model</H2>
        <H3>what is protected</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-2 my-4">
          {[
            "message content is E2E encrypted through relays (NaCl SecretBox)",
            "relay operators cannot read messages, see names, or link IPs to identities",
            "every message has an Ed25519 signature — forgery is impossible",
            "PoW prevents spam flooding",
            "messages expire after 24 minutes — no permanent record",
            "relay hardened: connection limits, rate limits, max message size",
            "timing obfuscation (random delay) prevents traffic analysis at relay",
          ].map((t, i) => (
            <div key={i} className="flex gap-3">
              <Lime>+</Lime>
              <span className="text-[var(--color-foreground)]/70">{t}</span>
            </div>
          ))}
        </div>
        <H3>known limitations</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs space-y-2 my-4">
          {[
            "relay operators can see your IP address at the TCP level (use VPN or Tor to hide)",
            "LAN peers can see each other's local IPs (same network only)",
            "ISPs can see that you connected to a relay server (metadata, not content)",
            "SealedBox key exchange is not authenticated — a malicious relay could theoretically MITM the room key exchange (requires actively modifying relay code)",
            "pseudonyms are not unique across sessions — anyone can pick any name",
          ].map((t, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-red-400">!</span>
              <span className="text-[var(--color-foreground)]/70">{t}</span>
            </div>
          ))}
        </div>
        <H3>threat model</H3>
        <P>
          limes&apos;s privacy model is similar to Bitcoin: transactions (messages) are public, identities are
          pseudonymous, and nodes (relays) see connecting IPs but cannot determine which IP sent which
          message thanks to gossip propagation and timing obfuscation. for stronger IP privacy,
          route through Tor.
        </P>

        {/* ── COMMANDS ── */}
        <H2 id="commands">CLI & chat commands</H2>
        <H3>CLI commands</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs font-mono space-y-2 my-4">
          {[
            ["limes", "open the chat (runs setup on first launch)"],
            ["limes -v", "print version"],
            ["limes setup", "re-run setup wizard"],
            ["limes upgrade", "auto-update to latest version"],
            ["limes wallet", "show ETH address + $LIME balance"],
            ["limes wallet --export", "reveal private key"],
            ["limes relay [port]", "run a relay server (default 4210)"],
            ["limes scanner [url]", "run limescan web server"],
            ["limes peers", "list saved peer addresses"],
            ["limes reset", "delete identity and start fresh"],
          ].map(([cmd, desc]) => (
            <div key={cmd} className="flex gap-4">
              <span className="text-[var(--color-lime)] w-40 shrink-0">{cmd}</span>
              <span className="text-[var(--color-foreground)]/60">{desc}</span>
            </div>
          ))}
        </div>
        <H3>chat commands (in TUI)</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs font-mono space-y-2 my-4">
          {[
            ["/t [title]", "create a new thread in current board"],
            ["/b [board]", "switch to a different board"],
            ["/boards", "list all known boards"],
            ["/threads", "list active threads in current board"],
            ["/reply [#] [msg]", "post into a thread by number"],
            ["/back", "return to board chat from a thread"],
            ["/connect host:port", "connect directly to a peer"],
            ["@name", "mention a user (they get a notification)"],
          ].map(([cmd, desc]) => (
            <div key={cmd} className="flex gap-4">
              <span className="text-[var(--color-lime)] w-40 shrink-0">{cmd}</span>
              <span className="text-[var(--color-foreground)]/60">{desc}</span>
            </div>
          ))}
        </div>
        <H3>TUI keybindings</H3>
        <div className="border border-[var(--color-border)] bg-[var(--color-panel)] p-4 text-xs font-mono space-y-1 my-4">
          {[
            ["i / Enter", "enter input mode"],
            ["Esc", "back from thread / cancel input / quit"],
            ["q", "back from thread / quit"],
            ["t", "toggle thread list"],
            ["1-9", "enter thread by number (from thread list)"],
            ["Backspace", "back to board chat"],
            ["n", "toggle mentions filter"],
            ["h", "toggle header (ASCII art)"],
            ["\u2191 / \u2193", "scroll message feed"],
          ].map(([key, desc]) => (
            <div key={key} className="flex gap-4">
              <span className="text-[var(--color-lime)] w-20 shrink-0">{key}</span>
              <span className="text-[var(--color-foreground)]/60">{desc}</span>
            </div>
          ))}
        </div>

        {/* ── FAQ ── */}
        <H2 id="faq">FAQ</H2>

        <H3>is limes safe for my friends to use?</H3>
        <P>
          yes. messages are end-to-end encrypted through relays, identities are pseudonymous, and
          everything is ephemeral. no accounts, no data stored. the worst case is someone on the same
          relay sees your IP address — use a VPN if that concerns you.
        </P>

        <H3>is it safe to run a relay?</H3>
        <P>
          yes. relays forward encrypted blobs they cannot read. they don&apos;t store anything, don&apos;t
          execute code from messages, and don&apos;t access your filesystem. the relay is hardened with
          connection limits, rate limits, and message size caps.
        </P>

        <H3>is this like 4chan?</H3>
        <P>
          similar concept — anonymous boards with threads — but more private. on 4chan, your IP is
          visible to admins and your posts are archived forever. on limes, relay operators can&apos;t
          link your IP to your pseudonym, all messages are e2e encrypted in transit, and everything
          disappears after 24 minutes. no archives, no logs, no trace.
        </P>

        <H3>what happens after 24 minutes?</H3>
        <P>
          messages are stored only in RAM on connected peers. after 24 minutes, they are pruned and
          gone forever. no relay, no server, no database ever stores them. when all messages in a
          thread expire, the thread vanishes too.
        </P>

        <H3>can someone impersonate me?</H3>
        <P>
          every message is signed with your Ed25519 private key. forging a signature is computationally
          infeasible. however, pseudonyms are not globally unique — someone could pick the same name
          in a different session. the #tag (derived from the public key) helps distinguish identities.
        </P>

        <H3>how do relay operators earn?</H3>
        <P>
          relay operators stake 250,000 LIME to register on-chain. for every message they forward, they
          can submit the PoW proof to the LimesVault and receive 1.0 LIME from the reward pool. the pool
          holds 300M LIME (30% of supply), which lasts effectively forever at normal usage.
        </P>

        {/* footer */}
        <footer className="border-t border-[var(--color-border)] pt-6 mt-16 space-y-4">
          <div className="flex justify-center items-center gap-3">
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="text-[var(--color-foreground)]/30 hover:text-[var(--color-lime)] transition-colors" title="GitHub">
              <GitHubIcon />
            </a>
            <a href={CLANKER_URL} target="_blank" rel="noopener noreferrer" className="text-[var(--color-foreground)]/30 hover:text-[var(--color-lime)] transition-colors" title="Clanker launch">
              <svg viewBox="0 0 940 1000" fill="currentColor" className="w-5 h-5">
                <path d="M0 1000V757.576H181.818V1000H0Z" />
                <path d="M378.788 1000V378.788H560.606V1000H378.788Z" />
                <path d="M939.394 1000H757.576V0H939.394V1000Z" />
              </svg>
            </a>
          </div>
          <div className="text-center text-xs text-[var(--color-foreground)]/20">
            <a href="/" className="hover:text-[var(--color-lime)]">lime.sh</a>
            {" \u00B7 "}
            <a href="/docs" className="hover:text-[var(--color-lime)]">docs</a>
            {" \u00B7 "}
            <a href="https://limescan.xyz" className="hover:text-[var(--color-lime)]">limescan.xyz</a>
          </div>
        </footer>
      </main>
    </div>
  );
}
