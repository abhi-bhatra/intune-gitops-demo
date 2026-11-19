# Jargon Glossary

Plain-English definitions for every Azure/Intune/Windows-enterprise term used in
this repo and in `DEMO_SCRIPT.md`. Written for someone with **zero prior
Intune/Azure/Windows-enterprise background**. Read this before the demo script
if any term there is unfamiliar.

**Tenant**
Your own private, isolated copy of Microsoft 365/Azure - here, `dreamkube.onmicrosoft.com`.
Like a single customer's account on a SaaS platform; nothing in it is shared with
anyone else's tenant.

**Azure AD / Entra ID**
Microsoft's identity system - the thing that knows every user and device in the
tenant and whether they're allowed to do things. "Entra ID" is just the newer
name for "Azure AD" (same product).

**Intune**
Microsoft's MDM (Mobile Device Management) product. It lives inside the tenant
and is what actually pushes settings/policies down to enrolled Windows/iOS/Android
devices and checks whether they're obeying them.

**Enrollment**
The one-time process where a device "joins" Intune's management - like a phone
registering with a parental-control app. Once enrolled, the device periodically
checks in and Intune can push policy to it. Both demo VMs are already enrolled.

**MDM sync channel**
The regular check-in heartbeat between a device and Intune (every few minutes,
or on-demand via a forced `syncDevice` call). This is the *fast* path - the
reason `osMinimumVersion` works great for a live demo (reports back in ~2-2.5 min).

**Compliance Policy**
A JSON rule-set that says "a device must satisfy X, Y, Z to be considered
compliant" (e.g. minimum OS build, password required). It's read-only
grading/reporting - it does not configure the device, it just checks it and
labels it compliant/noncompliant. This repo's `GitOps-Demo-BitLocker-Required.json`
is a compliance policy.

**Device Configuration Profile**
The sibling concept to a compliance policy, but this one actually *pushes
settings onto the device* (e.g. "block USB storage"). Not the same thing as a
compliance policy, though easy to confuse. This repo's
`GitOps-Demo-Block-USB-Storage.json` is a device configuration profile.

**Ring (Pilot-Ring / Prod-Ring)**
Just a named *group* of devices that a policy is assigned to - identical concept
to a Kubernetes canary deployment or a feature-flag cohort. "Pilot-Ring" is the
small, early-exposure group (VM1); "Prod-Ring" is everyone else (VM2). Assigning a
risky policy change to Pilot-Ring only means a bad change blast-radius-limits to
VM1, exactly like rolling a bad container image out to one canary pod first.

**Graph API (Microsoft Graph)**
The single REST API that fronts basically everything in Microsoft 365/Entra
ID/Intune (`https://graph.microsoft.com/...`). The GitOps pipeline doesn't click
around the Intune web portal - it calls Graph directly to read/write policies.

**App Registration**
A Graph/Entra ID concept: "register a robot (non-human) identity that's allowed
to call the Graph API on this tenant's behalf." The `intune-gitops-demo` app
registration (appId `7d1698e0-fc95-43bd-961f-93f77f744849`) is that robot identity,
used by GitHub Actions instead of a human logging in.

**Service Principal**
The "logged-in" instance of an app registration inside a specific tenant - the
actual thing that holds permissions. (App registration = the blueprint; service
principal = the deployed instance with real access.)

**Client Credentials Flow**
The login method for robots - no human, no browser, no password prompt. The app
sends its `client_id` + `client_secret` to Microsoft and gets back a short-lived
access token it uses to call Graph. This is what CI/CD uses instead of a person
typing a password.

**Client Secret**
Literally a password for the app registration/robot identity above. Rotated via
`az ad app credential reset` - never recovered from shell history.

**Access Token**
The short-lived (~1 hour) "ID badge" Graph API hands back after a successful
client-credentials login. Expires and must be refreshed periodically during a
long working session.

**IntuneCD**
The open-source CLI tool that acts as "Terraform for Intune": it can dump the
tenant's current policies to JSON files (`IntuneCD-startbackup`) or push JSON
files back up to the tenant (`IntuneCD-startupdate`). This is what turns Intune
into something git-trackable.

**Guardrail (policy-as-code check)**
`guardrails/validate_policy.py` - a script that runs in CI *before* IntuneCD
ever touches the real tenant. It inspects the JSON files and rejects anything
that violates a baseline rule (e.g. "must have `osMinimumVersion` set"). Same
idea as a Kubernetes admission controller or OPA/Gatekeeper, just for Intune
JSON instead of K8s manifests.

**Dry-run / Plan mode (`-r` flag on IntuneCD-startupdate)**
Computes and shows the diff of what *would* change on the real tenant, without
applying it - the same idea as `terraform plan` or `kubectl diff`.

**vTPM (virtual Trusted Platform Module)**
A virtualized version of the physical security chip found in real laptops,
required for things like BitLocker to work. Azure VMs can emulate one so a
cloud VM behaves like a real security-hardened laptop.

**Trusted Launch / Secure Boot**
An Azure VM security mode guaranteeing the VM boots only verified, untampered
firmware/OS images - the cloud equivalent of a laptop's Secure Boot setting.

**BitLocker**
Windows' built-in full-disk encryption feature.

**Device Health Attestation (DHA)**
A separate, slow, cloud-based process (can take *hours*) that cryptographically
verifies deep security state of a device - e.g. "is BitLocker *really* on," "was
Secure Boot *really* used to boot." It is **not** part of the fast MDM sync
channel. This is exactly why BitLocker/SecureBoot-based compliance settings were
the wrong lever for a live stage demo, and why the policy was redesigned to key
off `osMinimumVersion` instead (see `DEMO_SCRIPT.md` and the root-cause note in
the compliance policy's own `description` field).

**Compliant / Noncompliant**
The grade label Intune puts on a device after evaluating a compliance policy
against it. This is the status value that changes live on stage.
