# Repository Operations

ARIA treats the repository as both source and authority boundary.

## Build directories

- `.aria/build`: compiled `.ariac` artifacts and provenance.
- `.aria/state`: explicit program memory.
- `.aria/gates`: reserved for future signed gate reports.

These directories are ignored by Git. Source, specifications, schemas, and tests remain versioned.

## PowerShell development loop

```powershell
.\aria.ps1 test
.\aria.ps1 gate .\examples\hello.aria
.\aria.ps1 run .\examples\hello.aria
.\aria.ps1 inspect .\.aria\build\HelloARIA-0.1.0.ariac
```

Every `run` starts from source, passes the gate, writes a compressed artifact, verifies it, and then executes it. The VM does not execute stale unverified source directly.
