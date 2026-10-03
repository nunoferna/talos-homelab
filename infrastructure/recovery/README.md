# R2 recovery destination (preparation only)

OpenTofu 1.12.6 and Cloudflare provider 5.24.0 manage a **new** R2 Standard
snapshot bucket, disabled public `r2.dev` access, and lock/lifecycle rules for
`etcd/`. No existing state bucket is managed, imported or changed by this root.
The state key is `homelab/recovery.tfstate` in the existing encrypted, locked R2
backend. State and saved plans enforce client-side AES-GCM encryption.

This root has not been applied. Do not initialize a local production backend or
change an existing root's backend. The private control repository's recovery
plan workflow is the execution boundary; application of a reviewed plan remains
a separate, explicitly approved step. Do not dispatch a foundation Cilium/Flux
workflow with this root: recovery needs no Kubernetes or Talos credentials.

## Input and identity boundaries

Supply private non-secret account/bucket identifiers and sizing bounds through
a reviewed `recovery/r2.json` in the private repository. Supply the existing
state bucket and endpoint through protected runtime configuration.

Inject a dedicated Cloudflare API token as `CLOUDFLARE_API_TOKEN`, scoped to the
selected account and required R2 configuration operations. Use a read-only token
for plan where the provider's read endpoints support it; keep write credentials
in a separate protected apply boundary. Never use the global API key. Account
R2 configuration permissions may be broader than one bucket: do not claim
bucket-level admin isolation. No token or S3 credential resource is created here.

Backend object credentials are separate from bucket administration credentials.
After bucket creation, provision one bucket-scoped S3 writer and a separate
read-only recovery identity through the operator's identity bootstrap process.
Keep private values in the password manager/protected runtime secret store and
deliver only the writer as a SOPS bootstrap exception. A standard R2 Object
Read & Write credential permits deletion too; the prefix lock compensates while
active, but a bucket administrator can remove it. This is not irreversible WORM.

No custom domain is declared. Before any snapshot upload, independently inspect
the bucket's custom-domain bindings and ensure none expose it publicly. Managing
`r2.dev=false` alone cannot prevent an administrator attaching a custom domain.

## Retention and free-tier guard

The proposal is seven days of lock and expiry, not an approved recovery SLA.
Lifecycle deletion is asynchronous and locks take precedence over expiry. This
root refuses a plan whose size/frequency/retention estimate exceeds its allocated
storage budget, or whose allocated budget plus other account usage exceeds an
8 decimal GB planning ceiling. That leaves headroom below the account-wide
10 GB-month Standard free allowance, but **does not enforce a billing cap**.

Sizing uses `snapshot_size_bound_bytes * snapshots_per_day * (retention_days + 2)
* 1.25`. The two days and 25% are planning headroom, not guaranteed bounds on
deletion delay or database growth. Include old objects, test uploads, any other
prefixes, retries and other buckets in account-wide monitoring. Never transition
to Infrequent Access: it is outside the free allowance. Recheck operation counts
and actual daily peak storage before enabling or increasing the schedule.

At the staged 15-minute interval, 96 snapshots/day with seven days' retention
and this headroom need 1,080 times the per-snapshot byte bound. A 10 MB bound
needs 10.8 GB and fails the default 4 GB budget. Measure first; if necessary,
review a slower schedule or shorter retention and acknowledge the changed RPO
or history. The `snapshots_per_day` input must match the CronJob; OpenTofu does
not control that schedule and cannot enforce the cross-repository match.

Use a conservative native database-size-based bound for an initial plan; record
how it was derived. Confirm it against real compressed/encrypted objects before
activation. Do not enter a tiny invented value just to pass the guard.

Expiry intentionally deletes aged snapshots. Preserve a verified independent
recovery point outside this expiring prefix. Never shorten retention, change
jurisdiction, replace the bucket or remove protection during rollback. Suspend
the writer through Git, preserve evidence/objects, and review the incident first.
`prevent_destroy` guards resources while their declarations remain present; it
is not protection against removed configuration or account administration.

## Validation

```sh
tofu fmt -check -diff -recursive infrastructure
tofu -chdir=infrastructure/recovery init -backend=false -input=false
tofu -chdir=infrastructure/recovery validate
```

These checks need no Cloudflare credential or live backend. The private workflow
will run `plan -out` only after public CI, source ancestry, input and toolchain
checks, then publish a checksum-bound encrypted plan. Never apply an unreviewed
plan or re-plan during apply. Existing encrypted state must be snapshotted before
and after any future state-mutating apply, without exporting decrypted state.

See [key custody](../../docs/recovery-key-custody.md) and the
[Talos activation runbook](../../platform/backup/talos/README.md).

Sources: [provider 5.24.0 schemas](https://github.com/cloudflare/terraform-provider-cloudflare/tree/v5.24.0/docs/resources),
[R2 pricing](https://developers.cloudflare.com/r2/pricing/),
[bucket locks](https://developers.cloudflare.com/r2/buckets/bucket-locks/),
[lifecycle behavior](https://developers.cloudflare.com/r2/buckets/object-lifecycles/).
