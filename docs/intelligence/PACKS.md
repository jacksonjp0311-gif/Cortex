# Binary-intel packs ▣

**Version:** v6.9.1 (taught pack v1.1)  
**Schema:** `cortex.binary-intel-pack/1.0`  
**CLI:** `cortex packs …` · teach: `cortex teach --seed`

Portable intelligence packages that extend Cortex memory: **zero-in** by domain
binary geometry, **expand** cards when mass coheres. Works for any user home —
not customized to one machine.

## Install (any machine)

```powershell
$env:CORTEX_HOME = "$env:USERPROFILE\.cortex"   # or $HOME/.cortex
python -m cortex packs install path/to/pack-dir --json
python -m cortex packs index --repo MyRepo --json
python -m cortex packs probe --task "geometry triangle proof" --json
python -m cortex activate --repo MyRepo --task "geometry triangle proof" --json
```

Shipped example:

```text
packs/cortex-core-intel-v1/
```

## Layout

```text
manifest.json          # schema, id, domains, cards, binary
cards/*.md             # L1 searchable distillates
field.cortexbf1        # L3 CORTEXBF1 domain geometry (built on install)
```

## Runtime path

```text
task → domain_route (binary + keywords)
     → index cards as cortex-packs/<id>/… memories
     → expand into packet when score ≥ threshold
     → agent sees packet.packs (top_domain, expand)
```

## Teach / enter / connect

Taught intelligence lives in **cards** (operators + doctrine), not in LLM weight dumps.
`cortex teach --seed` installs `packs/cortex-core-intel-v1`, indexes it, and seals
memory packets (including binary-intel claims) via ritual.

```text
enter   activate → stream rebind → domain zero-in → expand
connect mesh pulse (⧉) already rides activate
teach   cards + reinstall + optional distill
evolve  harness/evolve after verified work only
```

Core pack v1.1 domains add **interconnect** and **evolution** with operator cards
`06-teach` … `09-agent-operating-loop`.

## Claim boundary

Packs are **routing + curated cards**. They never grant mutation rights, never
auto-execute, and never replace source/tests/runtime as authority.
