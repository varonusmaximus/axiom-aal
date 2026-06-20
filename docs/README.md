# AAL (Agent Annotation Language) in AxiomPy

Documentation for domain annotations, inject-on-edit hooks, and CI validation.

| Document | Purpose |
|----------|---------|
| [HLD.md](./HLD.md) | Executive narrative, onboarding journey, FAQs |
| [spec.md](./spec.md) | Normative grammar, placement, CLI contracts |
| [deployment.md](./deployment.md) | Install, CI, upgrade runbooks |
| [examples.md](./examples.md) | Annotated code examples |
| [implementation.md](./implementation.md) | Implementation backlog and phases |
| [axiompy-mapping.md](./axiompy-mapping.md) | Spec placeholders → AxiomPy names |
| [design-review.md](./design-review.md) | Design grill Q&A (archive) |

## Quick start

```bash
pip install axiom-aal
aal install --project --hooks
aal bootstrap suggest
aal bootstrap apply --level file --apply
aal verify-domains --strict
```

Branch: `varona/aal-v1.3-merge`
