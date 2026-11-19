# Stage Demo Script — "Intune Meets GitOps: Managing Windows Device Policy as Code"

Live, presenter-facing walkthrough for the demo portion of the talk only.
Theory slides and narrative framing are designed separately (not in this file).
If any term below is unfamiliar, see `GLOSSARY.md` first — it defines every
Azure/Intune/Windows term used here in plain English.

> **For a handover agent / engineer picking this up cold:** read
> "Architecture, in one paragraph" and "Handover notes" at the bottom first.
> Everything above that is the stage script itself.

---

## What this demo proves

A policy change to a Windows fleet, managed entirely as JSON in git, flows
through the same GitOps loop as Kubernetes manifests: **guardrail check → CI
dry-run plan → merge → CD apply → real device state changes → bad change
caught live → `git revert` → fleet heals** — and a canary ring (Pilot-Ring)
contains the blast radius so Prod-Ring never even notices.

## Cast of characters

| Thing | Value |
|---|---|
| Tenant | `dreamkube.onmicrosoft.com` (tenant id `71c4bcf1-4a96-4cba-b9b4-688a6f8d2860`) |
| App registration | `intune-gitops-demo` (appId `7d1698e0-fc95-43bd-961f-93f77f744849`) |
| VM1 — Pilot-Ring | `intune-demo-vm1`, device id `8a527f1c-27b7-43eb-a697-ee26aa435666` |
| VM2 — Prod-Ring | `intune-demo-vm2`, device id `a9e37cba-63c3-4090-b496-606f5fc6d360` |
| VM1/VM2 Azure location | RG `RG-INTUNE-DEMO-VMS`, subscription `0ba13b43-2636-491a-9c51-8f1d4474cbbb` ("Visual Studio Enterprise Subscription") |
| VM1 real OS build | `10.0.26200.9974` (Windows 11 Enterprise) |
| Repo | `/Users/abhinav/kodekloud/intune-gitops-demo` (local git, **no remote** — CI/CD workflows exist but nothing auto-triggers; apply steps below are run manually to simulate what the pipeline would do on push) |
| Policy under demo | `intune/Compliance Policies/Policies/GitOps-Demo-BitLocker-Required.json` |
| Guardrail script | `guardrails/validate_policy.py` |

**Azure CLI subscription gotcha:** `az ad app ...` commands need the tenant's
own subscription context; `az vm ...` commands need the VS Enterprise
subscription where the VMs actually live. If a command fails with
"SubscriptionNotFound" or "Resource does not exist," you're on the wrong one:

```bash
# For az ad app * commands:
az account set --subscription 71c4bcf1-4a96-4cba-b9b4-688a6f8d2860
# For az vm * commands:
az account set --subscription 0ba13b43-2636-491a-9c51-8f1d4474cbbb
```

---

## Pre-show checklist (T-30 min)

1. Start both VMs if deallocated:
   ```bash
   az vm start -g RG-INTUNE-DEMO-VMS -n intune-demo-vm1
   az vm start -g RG-INTUNE-DEMO-VMS -n intune-demo-vm2
   ```
2. Confirm `master` is clean and at the known-good baseline:
   ```bash
   git status
   git log --oneline -5
   ```
   Should be clean, HEAD at the commit that scopes the policy to
   `osMinimumVersion` only (no pending demo branch merged in).
3. Mint a fresh Graph access token (tokens expire ~1hr; do this right before
   going on stage, not 30 min before):
   ```bash
   az account set --subscription 71c4bcf1-4a96-4cba-b9b4-688a6f8d2860
   TOKEN=$(curl -s -X POST \
     "https://login.microsoftonline.com/71c4bcf1-4a96-4cba-b9b4-688a6f8d2860/oauth2/v2.0/token" \
     -d "client_id=7d1698e0-fc95-43bd-961f-93f77f744849" \
     -d "scope=https://graph.microsoft.com/.default" \
     -d "client_secret=$CLIENT_SECRET" \
     -d "grant_type=client_credentials" | jq -r .access_token)
   ```
   (If `$CLIENT_SECRET` isn't already in your shell env, rotate a fresh one —
   never recover an old one from history — with
   `az ad app credential reset --id 7d1698e0-fc95-43bd-961f-93f77f744849 --query password -o tsv`.)
4. Confirm both devices currently show `compliant`:
   ```bash
   for id in 8a527f1c-27b7-43eb-a697-ee26aa435666 a9e37cba-63c3-4090-b496-606f5fc6d360; do
     curl -s -H "Authorization: Bearer $TOKEN" \
       "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/$id?\$select=deviceName,complianceState,lastSyncDateTime" \
       | jq .
   done
   ```
5. Have a second terminal tab open and pre-authenticated so you're not typing
   `az`/`curl` boilerplate live on stage.

---

## Stage flow overview

| Act | What the audience sees | Real system state change? |
|---|---|---|
| 1 | Architecture + ring explanation (slides/talk) | No |
| 2 | Guardrail rejects a bad policy locally, instantly | No (local script only) |
| 3 | CI "plan" shows the diff before anything is applied | No (dry-run) |
| 4 | **The break** — bad commit applied to the real tenant | **Yes — real Graph write** |
| 5 | Watch loop — device goes noncompliant live | Yes (observation only) |
| 6 | **The recovery** — `git revert` + re-apply | **Yes — real Graph write** |
| 7 | Close — ring containment recap | No |

---

## Act 1 — Architecture & rings (talking points)

- This is a real tenant, real enrolled Windows 11 VMs, no mocks.
- Walk through `GLOSSARY.md` concepts briefly as needed for the room: tenant,
  Intune, compliance policy, Graph API, IntuneCD.
- Introduce the two rings: **Pilot-Ring** (VM1, canary) and **Prod-Ring**
  (VM2, everyone else) — same idea as a Kubernetes canary rollout. Show the
  `assignments` block in the policy JSON scoped to `Pilot-Ring` only.

## Act 2 — Guardrail demo (local, instant, no tenant contact)

Show the guardrail catching a bad policy *before* it ever reaches the pipeline:

```bash
# Make a throwaway bad copy in /tmp and run the guardrail against it to show a failure
mkdir -p /tmp/guardrail-demo/Policies
jq '.osMinimumVersion = ""' "intune/Compliance Policies/Policies/GitOps-Demo-BitLocker-Required.json" \
  > /tmp/guardrail-demo/Policies/bad.json
python3 guardrails/validate_policy.py /tmp/guardrail-demo
```
Expected: guardrail prints `GUARDRAIL FAILED` with
`osMinimumVersion is not set - devices on any build would pass`, exit code 1.

Then run it clean against the real repo to show it passing:
```bash
python3 guardrails/validate_policy.py intune
```
Expected: `All policies pass guardrail checks.`, exit code 0.

**Talking point:** this is the Gatekeeper/OPA-admission-control equivalent for
Intune — runs before IntuneCD ever gets a chance to touch the tenant.

## Act 3 — CI dry-run / plan (no changes applied)

```bash
az account set --subscription 71c4bcf1-4a96-4cba-b9b4-688a6f8d2860
export TENANT_NAME=dreamkube.onmicrosoft.com
export CLIENT_ID=7d1698e0-fc95-43bd-961f-93f77f744849
export CLIENT_SECRET=<fresh secret>
IntuneCD-startupdate -m 1 -p ./intune -r -v -e ScopeTags Roles
```
`-r` = dry-run/plan mode, identical idea to `terraform plan`. Shows what
*would* change without writing anything. Confirms "no diff" on a clean tree.

## Act 4 — The break (live, real tenant write)

1. Create the demo branch pointing at a genuinely-breaking change (the
   existing branch `demo/bad-os-minimum-version` already has this commit;
   if recreating fresh on stage):
   ```bash
   git checkout -b demo/bad-os-minimum-version
   ```
   Edit `intune/Compliance Policies/Policies/GitOps-Demo-BitLocker-Required.json`,
   bump:
   ```json
   "osMinimumVersion": "10.0.27000.0"
   ```
   This is **above** VM1's real build (`10.0.26200.9974`) — guaranteed genuine
   break, not cosmetic. (A previous value that was *below* VM1's real build
   was tried in an earlier rehearsal and was a silent no-op — worth knowing if
   asked "why this exact number.")
   ```bash
   git add "intune/Compliance Policies/Policies/GitOps-Demo-BitLocker-Required.json"
   git commit -m "demo: bump osMinimumVersion to 10.0.27000.0 (above VM1's real build) to force noncompliance"
   ```
2. Guardrail still passes (osMinimumVersion is set — it's just a bad value, a
   legitimate judgment-call mistake, not a malformed policy):
   ```bash
   python3 guardrails/validate_policy.py intune
   ```
3. Merge to `master` and apply for real:
   ```bash
   git checkout master && git merge demo/bad-os-minimum-version
   IntuneCD-startupdate -m 1 -p ./intune -v -g -e ScopeTags Roles
   ```
4. Force an immediate device check-in so you don't wait for the natural cycle:
   ```bash
   curl -s -X POST -H "Authorization: Bearer $TOKEN" \
     "https://graph.microsoft.com/beta/deviceManagement/managedDevices/8a527f1c-27b7-43eb-a697-ee26aa435666/syncDevice"
   ```

**Talking point while this fires:** "I just pushed a bad config to a real
Windows fleet the same way I'd push a bad Deployment manifest to Kubernetes —
let's watch it actually break."

## Act 5 — Watch loop (fills the ~2–2.5 min propagation wait)

```bash
watch -n 15 '
curl -s -H "Authorization: Bearer '"$TOKEN"'" \
  "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/8a527f1c-27b7-43eb-a697-ee26aa435666?\$select=deviceName,complianceState,lastSyncDateTime" | jq .
echo ---
curl -s -H "Authorization: Bearer '"$TOKEN"'" \
  "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/a9e37cba-63c3-4090-b496-606f5fc6d360?\$select=deviceName,complianceState,lastSyncDateTime" | jq .
'
```
Talk through the ring containment while waiting: VM1 (Pilot-Ring) flips to
`noncompliant`; VM2 (Prod-Ring) stays `compliant` throughout because it was
never assigned this policy version's blast radius. This has been verified
live end-to-end: break→noncompliant in ~2.5 min.

**If token expires mid-wait** (`401`/"Invalid token lifetime"): re-run the
token curl from the pre-show checklist, it's expected on a long session, not a
bug.

## Act 6 — The recovery (git revert, real re-apply)

Once VM1 shows `noncompliant` on camera:

```bash
git revert --no-edit HEAD
IntuneCD-startupdate -m 1 -p ./intune -v -g -e ScopeTags Roles
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "https://graph.microsoft.com/beta/deviceManagement/managedDevices/8a527f1c-27b7-43eb-a697-ee26aa435666/syncDevice"
```
Re-run the Act 5 watch loop. Verified live: VM1 returns to `compliant` in
~2.5 min, exactly mirroring the break timing.

## Act 7 — Close (talking points)

- Same loop as Kubernetes GitOps: declare desired state in git → guardrail →
  plan → apply → observe → revert on bad state, except the "nodes" are real
  enrolled Windows laptops instead of pods.
- Ring assignment = canary rollout. The bad change never touched Prod-Ring.
- Everything shown was against a real Microsoft 365 tenant and two real,
  enrolled, Trusted Launch Windows 11 VMs — no mocked API responses anywhere.

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
