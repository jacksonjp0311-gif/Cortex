# ARIA First Run on Windows

## AI and tool discovery

An unfamiliar AI or automation client should begin with:

```powershell
.\aria.cmd handshake --json
```

The returned record supplies the canonical read order, shared vocabulary,
resource digests, manifest state, authority boundary, and next valid command.
Discovery grants no authority.

ARIA `0.1.0-alpha.1` is a local language laboratory. The folder contains the language specification, compiler, bytecode verifier, compressed `.ariac` container, virtual machine, tests, policy, examples, and research documentation.

## 1. Put the folder on your desktop

Extract the release so this file exists:

```text
C:\Users\<you>\Desktop\aria-language\aria.ps1
```

Keep the folder in a normal local directory. Do not run the alpha compiler from an untrusted or shared repository.

## 2. Install and verify

Right-click **Windows PowerShell**, choose **Run as administrator** only if your machine policy requires it, then run:

```powershell
cd "$HOME\Desktop\aria-language"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\Install-ARIA.ps1
```

The installer removes downloaded-file blocks, verifies the strict repository manifest, runs the compiler/VM test suite, and creates an **ARIA Language Laboratory** desktop shortcut.

Administrator rights are not normally required because ARIA runs inside its own folder and the selected workspace.

## 3. Run ARIA

Double-click `Start-ARIA.cmd`, or use:

```powershell
.\aria.cmd run .\examples\hello.aria -Strict
```

The `run` command always performs this pipeline:

```text
source → parse → semantic validation → policy gate → bytecode
       → independent verification → canonical serialization
       → gzip-compressed .ariac container → integrity verification → local VM
```

The compiled file is written to:

```text
.aria\build\HelloARIA-0.1.0.ariac
```

Persistent language memory is stored separately under:

```text
.aria\state\HelloARIA.memory.json
```

## 4. Create a program

```powershell
.\aria.cmd init MyFirstProgram
notepad .\MyFirstProgram.aria
.\aria.cmd run .\MyFirstProgram.aria -Strict
```

## 5. Development loop

After changing the compiler or specification:

```powershell
.\aria.cmd test
.\aria.cmd gate .\examples\hello.aria
.\aria.cmd manifest
.\aria.cmd doctor -Strict
.\aria.cmd run .\examples\hello.aria -Strict
```

`manifest` must be the last intentional repository change before the strict gate. It records every compiler, grammar, schema, test, example, and documentation file in `MANIFEST.sha256`.

## 6. Important alpha boundary

ARIA does not call an AI model and does not evaluate ARIA source as PowerShell. Version `0.1` executes a deliberately small opcode set. Network and subprocess execution are absent, and filesystem writes are denied by the default policy.

Read `README.md`, `SECURITY.md`, and `docs/01-language-spec.md` before extending host effects.
