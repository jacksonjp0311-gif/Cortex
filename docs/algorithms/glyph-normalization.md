# Algorithm: Glyph Normalization

For every visual node, preserve the triple:

```text
(glyph, stable node kind, stable identifier)
```

The stable node kind and identifier determine semantics. The glyph is display metadata. A renderer may substitute a fallback glyph or spoken name without changing the program.

Before expanding the glyph vocabulary, each new glyph requires:

- stable token identifier;
- category and arity;
- input/output type rules;
- textual spelling;
- accessibility label;
- normalization and confusability review;
- compiler and round-trip tests.
