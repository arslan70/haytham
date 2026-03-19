# OpenSpec Summary

> This summarizes the Phase 4 output. The full OpenSpec is a directory tree with `config.yaml`, `project.md`, and individual domain specs. This page shows what was generated and includes a sample requirement.

**Note:** This spec reflects the **pivoted idea** (invoice-to-PO matching for construction subcontractors), not the original generic SMB concept. The pivot was recommended in Phase 1 and accepted by the founder before Phase 2 began.

## Config

```yaml
name: construction-invoice-matcher
description: Invoice-to-PO matching with progress billing and lien waiver tracking for construction subcontractors
appetite: Medium
generated_at: 2025-02-14T16:42:03Z
traits:
  interface: [browser]
  auth: multi_user
  deployment: [cloud_hosted]
  data_layer: remote_db
  realtime: false
  communication: none
  payments: none
  scheduling: none
```

## Domain Specs

The spec generator grouped capabilities into 5 domains based on the MVP scope boundaries:

| Domain | Spec File | Requirements | Scenarios |
|--------|-----------|-------------|-----------|
| document-processing | `specs/document-processing/spec.md` | 4 | 14 |
| progress-billing | `specs/progress-billing/spec.md` | 3 | 11 |
| lien-waiver-tracking | `specs/lien-waiver-tracking/spec.md` | 3 | 9 |
| discrepancy-dashboard | `specs/discrepancy-dashboard/spec.md` | 3 | 8 |
| project-management | `specs/project-management/spec.md` | 2 | 6 |
| cross-cutting | `specs/cross-cutting/spec.md` | 3 | 7 |
| **Total** | | **18** | **55** |

## Example Requirement

From `specs/progress-billing/spec.md`:

```markdown
### Requirement: Match Invoice Line Items Against PO with Progress Billing [CAP-F-006]

The system SHALL match each invoice line item to the corresponding PO line item
and calculate the remaining billable amount after accounting for all prior
progress payments on the same PO line.

#### Scenario: Invoice matches PO line with prior partial payments

- **Given** PO line item "Electrical rough-in" has a total value of $45,000
  and prior approved invoices totaling $30,000
- **When** a new invoice is uploaded with line item "Electrical rough-in" for $12,000
- **Then** the system displays a match with remaining budget of $15,000
  and flags the $12,000 invoice as within budget (80% of remaining)

#### Scenario: Invoice exceeds remaining PO balance

- **Given** PO line item "Concrete foundation" has a total value of $80,000
  and prior approved invoices totaling $72,000
- **When** a new invoice is uploaded with line item "Concrete foundation" for $12,000
- **Then** the system flags the invoice as a discrepancy with detail
  "Invoice ($12,000) exceeds remaining PO balance ($8,000) by $4,000"

#### Scenario: Invoice line item has no matching PO line

- **Given** a project PO with 8 defined line items
- **When** an invoice is uploaded with line item "Temporary fencing" which does
  not match any PO line item
- **Then** the system marks the line as "Unmatched" and surfaces it in the
  discrepancy dashboard for manual review
```

## Tech Stack (from project.md)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Framework | Next.js + TypeScript | Browser interface, server-side API routes for document processing |
| Database | Supabase Postgres | Multi-user auth included, row-level security for project isolation |
| Document extraction | Google Document AI | BUY. Construction documents have varied layouts; pre-trained models handle this better than custom OCR |
| Hosting | Vercel | Standard for Next.js, handles the expected low-to-moderate traffic |
| File storage | Supabase Storage | Co-located with database, signed URLs for secure document access |

## Build/Buy Summary

| Component | Decision | Service |
|-----------|----------|---------|
| Auth | BUY | Supabase Auth |
| Database | BUY | Supabase Postgres |
| Document extraction | BUY | Google Document AI |
| File storage | BUY | Supabase Storage |
| Hosting | BUY | Vercel |
| Matching logic | BUILD | Core differentiator: progress billing awareness, construction-specific line item matching |
| Lien waiver classification | BUILD | Domain-specific logic for conditional vs. unconditional waiver detection |
