# limes

anonymous ephemeral broadcast network.

decentralized terminal chat with boards, threads, DMs, and file sharing. messages self-destruct after 24 minutes. end-to-end encrypted with authenticated key exchange. relay operators stake and earn **$LIME**.

## install

download the latest binary for your platform from [releases](https://github.com/limedotxyz/limes/releases/latest):

- **Windows**: `limes.exe`
- **macOS**: `limes-macos`
- **Linux**: `limes-linux`

```
limes setup
limes
```

or install via pip:

```
pip install -e .
```

## commands

| command | description |
|---|---|
| `limes` | open the chat |
| `limes relay` | run a relay node (includes scanner) |
| `limes wallet` | show $LIME balance |
| `limes upgrade` | update to latest |
| `limes setup` | run setup wizard |
| `limes peers` | list saved peers |
| `limes reset` | reset identity |
| `limes -v` | show version |

## chat commands

| command | description |
|---|---|
| `/t [title]` | create a thread |
| `/threads` | list active threads |
| `/b [board]` | switch boards |
| `/boards` | list boards |
| `/reply [#] [msg]` | reply to thread |
| `/dm @name msg` | send a direct message |
| `/file path` | share a file (<45KB) |
| `/save # [path]` | save a received file |
| `/help` | show all commands |
| `/back` | back to board chat |
| `@name` | mention a user |

## keybindings

| key | action |
|---|---|
| `i` / `Enter` | input mode |
| `Esc` / `q` | back / quit |
| `t` | thread list |
| `d` | toggle DMs |
| `?` | help screen |
| `n` | mentions filter |
| `h` | toggle header |
| `1-9` | enter thread |

## how it works

- **ephemeral** — messages vanish after 24 minutes
- **anonymous** — pseudonymous identities, Ed25519 keypairs
- **e2e encrypted** — authenticated key exchange prevents MITM
- **proof-of-work** — hashcash prevents spam
- **decentralized** — on-chain relay registry on Base L2
- **DMs** — encrypted 1-on-1 messages, relay-targeted delivery
- **file sharing** — base64-encoded files within 64KB relay limit
- **message sync** — recover missed messages on reconnect
- **cross-platform** — Windows, macOS, Linux + web client

## links

- [lime.sh](https://lime.sh) — landing page
- [lime.sh/web](https://lime.sh/web) — web client (beta)
- [limescan.xyz](https://limescan.xyz) — live message explorer
- [docs](https://lime.sh/docs) — full documentation

## license

MIT
