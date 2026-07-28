# Mathematical Model

ARIA separates **notation**, **meaning**, **authority**, and **execution**. A glyph is a notation token; the semantic graph and transition system define the language.

## 1. Program definition

An ARIA program is modeled as:

\[
P = (D, G, F, C, A, M, e)
\]

where:

- `D` is the declaration environment;
- `G` is the semantic graph;
- `F` is the set of executable flows;
- `C` is the set of declared capabilities;
- `A` is the set of principals or agents;
- `M` is the set of explicit memory declarations;
- `e` is the entry flow.

The compiler accepts `P` only when every reference is resolved, every host effect has a valid authority path, and `e ∈ F`.

## 2. Semantic graph

The graph is:

\[
G = (V, E, \tau_V, \tau_E, \alpha)
\]

- `V` is a finite set of nodes.
- `E \subseteq V \times V` is a finite set of directed edges.
- `τV : V → NodeKind` assigns a node type.
- `τE : E → RelationKind` assigns a relationship type.
- `α` assigns attributes such as canonical name, glyph alias, state, authority, and provenance.

Visual coordinates are not part of `G`. Two diagrams with different layouts are the same program graph when their canonical node, edge, type, and attribute sets are equal.

### Glyph equivalence

For each glyph `g`, the registry defines a stable semantic identifier:

\[
normalize(g) = k
\]

For example:

\[
normalize(\text{⟁}) = agent
\]

Compilation operates on `k`, never on the visual appearance of `g`. This preserves text/glyph round-tripping and prevents fonts from defining semantics.

## 3. Runtime state

The abstract virtual-machine state is:

\[
\Sigma = (pc, S, L, M, C_a, G, H, O)
\]

- `pc`: instruction pointer;
- `S`: operand stack;
- `L`: local bindings;
- `M`: explicit memory stores;
- `Ca`: active capabilities;
- `G`: compiled semantic graph;
- `H`: provenance/event history;
- `O`: observable output stream.

An instruction `i` defines a deterministic transition:

\[
\Sigma_t \xrightarrow{i} \Sigma_{t+1}
\]

For a valid sequential program, one instruction and one input state yield at most one next state. Host effects may fail, but they do not introduce compiler ambiguity.

## 4. Stack semantics

Let `S · x` mean stack `S` with value `x` pushed on top.

### Constant

\[
(pc,S,L,M,C_a,G,H,O) \xrightarrow{PUSH\_CONST\;n}
(pc+1,S \cdot K[n],L,M,C_a,G,H,O)
\]

### Store

\[
(pc,S \cdot x,L,M,C_a,G,H,O) \xrightarrow{STORE\;v}
(pc+1,S,L[v \mapsto x],M,C_a,G,H,O)
\]

### Emit

When policy permits `console.emit`:

\[
(pc,S \cdot x,L,M,C_a,G,H,O) \xrightarrow{EMIT}
(pc+1,S,L,M,C_a,G,H,O \cdot text(x))
\]

### Assertion

\[
ASSERT\_EQ(x,y) =
\begin{cases}
continue & canonical(x)=canonical(y)\\
error & otherwise
\end{cases}
\]

Canonical equality avoids host-language coercion such as treating the string `"1"` as equal to the number `1`.

## 5. Memory

A memory declaration defines an initial finite map:

\[
M_j : Key \rightharpoonup Value
\]

`MEM_SET` changes runtime state but never mutates compiled bytecode:

\[
M' = M[j \mapsto M_j[k \mapsto x]]
\]

This separation preserves artifact reproducibility. Runtime memory is persisted only after an explicit memory mutation and remains outside `.ariac` containers.

Future event-sourced memory will represent change as an append-only sequence:

\[
M_t = fold(apply, M_0, events_{0..t})
\]

That model enables rollback, provenance queries, expiration, and disputed facts without hiding state in an opaque model context.

## 6. Authority and effects

A capability is a tuple:

\[
c = (name, effect, scope)
\]

A host operation is legal only when all four conditions hold:

\[
Policy \vdash c
\land c \in C_a
\land operation.effect = c.effect
\land target \subseteq c.scope
\]

This distinguishes:

1. **declaration** — the program names the authority;
2. **policy approval** — repository policy allows it;
3. **activation** — the flow executes `require c`;
4. **confinement** — the concrete target remains within scope.

The default decision is denial:

\[
unknown(effect) \Rightarrow deny
\]

## 7. Static judgments

The planned typed core uses a judgment of the form:

\[
\Gamma;C \vdash e : T \triangleright \epsilon
\]

Read as: under bindings `Γ` and capabilities `C`, expression `e` has type `T` and may produce effects `ε`.

A flow is valid only if:

\[
\epsilon(flow) \subseteq effects(C_{activated})
\]

ARIA 0.1 implements a small dynamic value domain with static reference and effect checks. ARIA 0.2 will make `T` explicit through type declarations and typed bytecode.

## 8. Bytecode verification invariant

For each instruction prefix `I[0..n]`, abstract stack depth must satisfy:

\[
depth(n) \ge 0
\]

At termination:

\[
depth(final) = 0
\]

Every constant index, variable load, memory reference, capability reference, and opcode must resolve before execution. No instruction may occur after `HALT`.

The verifier computes the maximum stack requirement:

\[
maxStack = \max_n depth(n)
\]

This is checked independently of container integrity. A correct SHA-256 digest proves that bytes were not changed; it does not prove the bytecode is safe or meaningful.

## 9. Deterministic compilation

Let normalized source be `x`, compiler lock be `l`, and accepted policy environment be `p`.

\[
Compile(x,l,p) = b
\]

Within the locked bootstrap environment, reproducibility requires:

\[
Compile(x,l,p)_1 = Compile(x,l,p)_2
\]

as byte-for-byte equality. Build time, machine path, mutable memory, and timestamped provenance are excluded from `b`.

## 10. Container identity

The canonical payload hash is:

\[
h_p = SHA256(UTF8(canonicalJSON(bytecode)))
\]

The artifact hash is:

\[
h_a = SHA256(header \Vert gzip(payload))
\]

The VM verifies header lengths, decompression bounds, `hp`, bytecode compatibility, and verifier invariants before execution.

## 11. Future graph rewriting

A graph transformation rule is:

\[
L \xRightarrow[c,\phi]{event} R
\]

- `L` is the matched graph pattern;
- `c` is required authority;
- `φ` is a deterministic guard;
- `R` is the replacement graph;
- `event` is the provenance record.

A rewrite is permitted only when the match is type-correct, `φ` is true, and `c` is active. This is the foundation for agents proposing repository transformations without making the model itself the execution authority.

## 12. Concurrency criterion

For future actions `a` and `b`, with read and write sets `R(x)` and `W(x)`, a sufficient conflict-free condition is:

\[
W(a) \cap (R(b) \cup W(b)) = \varnothing
\]

and:

\[
W(b) \cap (R(a) \cup W(a)) = \varnothing
\]

Only then may the runtime schedule both actions in parallel without changing sequentially observable state.
