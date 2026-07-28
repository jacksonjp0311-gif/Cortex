# ARIA Operator Renderer

ARIA uses a semantic diamond stream for normal compiler and runtime output.

| Glyph | Meaning |
|---|---|
| `◇` | information or ready state |
| `◈` | active/pulsing operation |
| `◆` | completed gate or successful artifact |
| `⬖` | warning |
| `⬗` | failed gate |
| `∿` | program output stream |

Normal mode is concise. Use `-VerboseOutput` or set `ARIA_VERBOSE=1` when raw diagnostic detail is needed. Set `NO_COLOR=1` or `ARIA_COLOR=0` for plain output. The pulsing diamond uses ANSI blink where the host terminal supports it and degrades to a static colored diamond elsewhere.
