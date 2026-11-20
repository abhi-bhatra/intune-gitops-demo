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
   going on stage, not 30 min before). Always rotate a fresh client secret
   first — don't rely on `$CLIENT_SECRET` surviving from a previous shell
   session, and never recover an old one from history:
   ```bash
   az account set --subscription 71c4bcf1-4a96-4cba-b9b4-688a6f8d2860
   CLIENT_SECRET=$(az ad app credential reset --id 7d1698e0-fc95-43bd-961f-93f77f744849 --query password -o tsv)

   TOKEN=$(curl -s -X POST \
     "https://login.microsoftonline.com/71c4bcf1-4a96-4cba-b9b4-688a6f8d2860/oauth2/v2.0/token" \
     -d "client_id=7d1698e0-fc95-43bd-961f-93f77f744849" \
     -d "scope=https://graph.microsoft.com/.default" \
     -d "client_secret=$CLIENT_SECRET" \
     -d "grant_type=client_credentials" | jq -r .access_token)
   ```
   Sanity-check the token before moving on — `TOKEN=null` means the secret
   was empty/stale or the request was otherwise rejected:
   ```bash
   echo "token length: ${#TOKEN}"
   ```
   A real token is a few thousand characters. If `token length: 0` (or
   `TOKEN` prints literally `null`), re-run the `jq -r .access_token` curl
   above without the `-r .access_token` (i.e. just `| jq .`) to see the raw
   Entra error body before retrying.
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
4. Force an immediate device check-in so you don't wait for the natural cycle.
   `-d ''` is required — without a body, curl sends no `Content-Length`
   header and Graph rejects the bodyless POST with `411 Length Required`:
   ```bash
   curl -s -X POST -d '' -H "Authorization: Bearer $TOKEN" \
     "https://graph.microsoft.com/beta/deviceManagement/managedDevices/8a527f1c-27b7-43eb-a697-ee26aa435666/syncDevice"
   ```

**Talking point while this fires:** "I just pushed a bad config to a real
Windows fleet the same way I'd push a bad Deployment manifest to Kubernetes —
let's watch it actually break."

## Act 5 — Watch loop (fills the ~2–2.5 min propagation wait)

```bash
while true; do
  clear
  date
  curl -s -H "Authorization: Bearer $TOKEN" \
    "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/8a527f1c-27b7-43eb-a697-ee26aa435666?\$select=deviceName,complianceState,lastSyncDateTime" | jq .
  echo ---
  curl -s -H "Authorization: Bearer $TOKEN" \
    "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/a9e37cba-63c3-4090-b496-606f5fc6d360?\$select=deviceName,complianceState,lastSyncDateTime" | jq .
  sleep 15
done
```
(`Ctrl+C` to break out once you've seen the state you're watching for. Plain
shell loop, not the GNU `watch` command — macOS doesn't ship `watch` by
default and this needs zero dependencies on stage.)
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
curl -s -X POST -d '' -H "Authorization: Bearer $TOKEN" \
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
