## Example 1

Get the Antimony for BIOMD0000000054.
If I increase the concentration of ions in the reaction between ions and the energy pool,
will the output increase exponentially?



Here's the Antimony model and my analysis of your question:

---

## BIOMD0000000054 — Ataullahkhanov1996_Adenylate

This is a model of **adenylate metabolism in human erythrocytes (red blood cells)**, with three species:
- **I** — Ions (Na⁺)
- **E** — Energy pool (ATP + ADP)
- **A** — Adenylate pool (ATP + ADP + AMP)

The relevant reaction is **U2** — *ATP consumption by the ion pump*:

```
U2: 3 I + E => ;   rate = W2 * I * T
```

This consumes 3 ions and 1 unit of the energy pool (via ATP, `T`), driven by the ion pump.

---

## Will increasing ion concentration cause exponential output increase?

**No — the output will not increase exponentially.** Here's why:

**U2 rate = W2 × I × T**

The rate is **bilinear** (linear in both `I` and `T`). However, `T` (ATP) is not a fixed constant — it's computed from `A` and `E` via a nonlinear algebraic rule:

```
T := (A + 3*E - sqrt((6*A*E - 3*E²) + A²)) / 6
```

As you raise `I`, the ion pump (U2) **consumes more ATP**, which **depletes T**, which in turn **feeds back to slow U2 down** — a classic negative feedback loop. The system is self-limiting, not exponential.

Additionally:
- **Passive ion influx (U1)** = `P × J` — a constant inflow unaffected by `I`
- There is **no positive feedback on ions** in this model

So in short: increasing `[I]` will increase the pump rate initially, but the resulting ATP depletion will dampen the effect. The system reaches a **new steady state**, not runaway exponential growth.