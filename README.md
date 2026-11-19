# intune-gitops-demo

Live GitOps pipeline for Intune device policy, built for the conference talk
"Intune Meets GitOps: Managing Windows Device Policy as Code." Real tenant
(`dreamkube.onmicrosoft.com`), real enrolled Windows 11 VMs — no mocks.

- **Running the stage demo:** see [`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md) —
  full presenter walkthrough, exact commands, pre-show checklist, handover notes.
- **New to Intune/Azure/Windows-enterprise terms?** see [`GLOSSARY.md`](./GLOSSARY.md)
  for plain-English definitions of every term used (tenant, ring, compliance
  policy, Graph API, Device Health Attestation, etc.).
- **Policy source of truth:** `intune/` (Compliance Policies, Device Configurations).
- **Policy-as-code guardrail:** `guardrails/validate_policy.py` — admission-control
  equivalent of OPA/Gatekeeper, runs before anything touches the live tenant.
- **CI/CD reference workflows:** `.github/workflows/` (this repo has no git
  remote, so these are accurate-but-dormant; the demo script runs the same
  steps manually).
