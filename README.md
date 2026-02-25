# limes

anonymous ephemeral broadcast network.

decentralized terminal chat with boards and threads. messages self-destruct after 24 minutes. end-to-end encrypted. relay operators stake and earn **$LIME**.

## install

download `limes.exe` from [releases](https://github.com/limedotxyz/limes/releases) and run it.

```
limes setup
limes
```

## commands

| command | description |
|---|---|
| `limes` | open the chat |
| `limes relay` | run a relay server |
| `limes scanner` | run limescan server |
| `limes wallet` | show $LIME balance |
| `limes upgrade` | update to latest |
| `limes setup` | run setup wizard |
| `limes -v` | show version |

## chat commands

| command | description |
|---|---|
| `/t [title]` | create a thread |
| `/threads` | list active threads |
| `/b [board]` | switch boards |
| `/boards` | list boards |
| `/reply [#] [msg]` | reply to thread |
| `/back` | back to board chat |
| `@name` | mention a user |

## how it works

- **ephemeral** — messages vanish after 24 minutes
- **anonymous** — pseudonymous identities, new keys each session
- **e2e encrypted** — relay operators cannot read messages
- **proof-of-work** — hashcash prevents spam
- **decentralized** — anyone can run a relay

## links

- [lime.sh](https://lime.sh) — landing page
- [limescan.xyz](https://limescan.xyz) — live message explorer
- [docs](https://lime.sh/docs) — full documentation

## license

MIT
