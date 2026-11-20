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

---

## Known rough edges / live Q&A prep

- **"Why doesn't the policy enforce BitLocker/SecureBoot directly?"** — those
  fields are graded via Device Health Attestation (DHA), an async cloud
  attestation pipeline that can take *hours* to report, fully decoupled from
  the fast MDM sync channel `osMinimumVersion` uses. Wrong lever for a live
  stage demo with a 2-3 minute attention budget — explained in the policy
  file's own `description` field, not hidden. BitLocker is still genuinely
  enabled on VM1 as a bonus, just not the compliance *trigger* used live.
- **"What if the Graph token expires on stage?"** — re-run the token mint
  command from the pre-show checklist; takes a few seconds, framed as normal
  credential hygiene if it happens live, not a failure.
- **"What if propagation takes longer than ~2.5 min live?"** — have the Act 7
  talking points ready to fill time; this has consistently been ~2–2.5 min in
  rehearsal but is still a real async system, not guaranteed instant.
- **No git remote on this repo** — CI/CD YAML (`.github/workflows/*.yml`)
  exists and is accurate to what a real pipeline would do, but nothing
  auto-triggers here; all "CI"/"CD" steps in Acts 3/4/6 are run manually to
  simulate the pipeline rather than relying on an actual push-triggered
  GitHub Actions run. If asked, be upfront about this rather than implying a
  live GitHub Actions run is firing.

---

## Architecture, in one paragraph

Policies live as Graph-API-shaped JSON under `intune/`. `guardrails/validate_policy.py`
is a pure-Python, dependency-free static check (no tenant contact) that walks
every JSON file and rejects known-bad shapes (missing `osMinimumVersion`,
missing scheduled actions, empty assignments) — this is the "admission
control" layer. `IntuneCD` (pip package) is the actual apply engine: `-r`
mode diffs the JSON against the live tenant without writing (CI "plan"),
no `-r` mode pushes the JSON state onto the tenant for real via Microsoft
Graph (CD "apply"). The GitHub Actions workflows in `.github/workflows/`
wire guardrail→plan on PR and guardrail→apply on push to `master`, but this
repo currently has no git remote, so those workflows are reference/accurate-
but-dormant; the demo runs the same commands manually. Device-side truth
(compliant/noncompliant, last sync time) is read directly from Graph's
`deviceManagement/managedDevices` endpoint, not inferred.

## Handover notes (for another engineer or agent)

- **Repo path:** `/Users/abhinav/kodekloud/intune-gitops-demo`, local-only git
  (`git remote -v` is empty — do not assume a push triggers anything).
- **Secrets:** never stored in the repo or shell history. Mint fresh via
  `az ad app credential reset --id 7d1698e0-fc95-43bd-961f-93f77f744849`.
  Requires `az account set --subscription 71c4bcf1-4a96-4cba-b9b4-688a6f8d2860`
  first (tenant-level subscription, not the VM compute one).
- **Resetting to a clean baseline before rehearsing again:** confirm `master`
  is at the commit where `GitOps-Demo-BitLocker-Required.json` has
  `osMinimumVersion: "10.0.19041"` and `bitLockerEnabled`/`secureBootEnabled`/
  `codeIntegrityEnabled`/`earlyLaunchAntiMalwareDriverEnabled` all `false`.
  If the demo branch was merged and not yet reverted, `git revert --no-edit HEAD`
  and re-apply with IntuneCD as shown in Act 6.
  Re-apply any time the live tenant state might have drifted from git:
  `IntuneCD-startupdate -m 1 -p ./intune -v -g -e ScopeTags Roles`.
- **VM cost hygiene:** stop/deallocate both VMs between rehearsals —
  `az vm deallocate -g RG-INTUNE-DEMO-VMS -n intune-demo-vm1` (and `vm2`) —
  and start them again (Pre-show checklist step 1) before the next run.
- **Full historical context, root-cause writeups, and verified timings:**
  `~/.claude/projects/-Users-abhinav-kodekloud/memory/project_intune_gitops_demo.md`.
- **Jargon:** see `GLOSSARY.md` in this same repo — written for zero prior
  Intune/Azure background.
- **Standing autonomy note:** per prior direction from the repo owner, this
  project (personal demo tenant, not company infra) can be operated on
  without per-command permission prompts — see
  `~/.claude/projects/-Users-abhinav-kodekloud/memory/feedback_intune_gitops_demo_autonomy.md`.
  This does not extend to any other repo/tenant.
