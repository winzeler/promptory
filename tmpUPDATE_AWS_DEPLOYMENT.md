# Plan: Update AWS Deployment Documentation

## Context

After deploying Promptdis to AWS Lambda via SAM, numerous issues were discovered and fixed during the actual deployment process. The existing docs (`SERVERLESS_PLAN.md`, `SERVERLESS_README.md`, `PROMPT_APP.md`, `PROMPT_APP_BUILD_CHECKLIST.md`, `PROMPTDIS_API_DOCS.md`) describe the **planned** architecture but don't reflect the **actual** deployed state. This plan covers updating all docs to match reality.

## Files to Update

All in `~/src/futureself/dwight_docs/prompt_mgmt/`:

1. **SERVERLESS_PLAN.md** — Architecture plan (corrections to match actual implementation)
2. **SERVERLESS_README.md** — Operator deployment guide (most changes)
3. **PROMPT_APP.md** §13 — Deployment section
4. **PROMPT_APP_BUILD_CHECKLIST.md** — Phase 6 sprint checklist (mark completed items)
5. **PROMPTDIS_API_DOCS.md** — Configuration reference

Also in `~/src/futureself/prompt-mgmt/`:
6. **RUNBOOK.md** — Operational guide (verify serverless sections are current)

## Discrepancies to Fix

### A. Runtime & Build Changes
| What docs say | What's actually true |
|---|---|
| Python 3.11 runtime | **Python 3.12** runtime |
| `sam build` uses default PythonPipBuilder | **Makefile-based build** (`BuildMethod: makefile`) with `--platform manylinux2014_x86_64` for cross-compilation |
| No mention of requirements.txt | **`requirements.txt`** generated from `uv pip compile` is required |
| No mention of `.samignore` | **`.samignore`** excludes web/, sdk-ts/, .venv/, etc. |
| `lifespan="off"` in Mangum | **`lifespan="auto"`** — required for init_db() to run |
| No stage prefix handling | **`api_gateway_base_path=f"/{stage}"`** strips stage prefix from HTTP API v2 paths |

### B. Networking (Not in Original Plan)
| What docs say | What's actually true |
|---|---|
| Just private subnets + EFS | **NAT Gateway required** — Lambda in VPC has no internet without it |
| No public subnet | **Public subnet (10.0.3.0/24)** with Internet Gateway for NAT Gateway |
| No mention of internet access | **NAT Gateway + route tables** connect private subnets to internet via public subnet |
| Cost estimate ~$2/month | **Add ~$32/month for NAT Gateway** ($0.045/hr + data transfer) |

### C. Custom Domain Support (Not in Original Plan)
| What docs say | What's actually true |
|---|---|
| Raw API Gateway URL | **Custom domain parameters**: `ApiDomainName`, `ApiAcmCertificateArn` |
| No web UI custom domain | **Custom domain parameters**: `DomainName`, `AcmCertificateArn` |
| No conditions | **CloudFormation Conditions**: `HasCustomDomain`, `HasApiDomain` |
| No API Gateway custom domain resource | **`ApiCustomDomain` + `ApiMapping`** resources |
| CloudFront without aliases | **Conditional `Aliases` + `ViewerCertificate`** on CloudFront |
| ACM certs not mentioned | **Two ACM certs**: us-east-1 (CloudFront), us-east-2 (API Gateway) |

### D. Authentication & Cookies
| What docs say | What's actually true |
|---|---|
| No cross-domain cookie handling | **`SameSite=None; Secure`** for cross-subdomain (api.X.com → app.X.com) |
| No cookie domain setting | **`domain=.promptdis.com`** via `settings.cookie_domain` property |
| CORS via API Gateway CorsConfiguration | **CORS handled by FastAPI middleware** (API Gateway CORS removed to avoid conflicts) |

### E. Frontend API URL
| What docs say | What's actually true |
|---|---|
| Build-time `VITE_API_BASE_URL` env var | **Runtime `config.js`** pattern: `window.__PROMPTDIS_CONFIG__` |
| `deploy-web.sh` exports env var before build | **`deploy-web.sh` writes `config.js`** to `dist/` after build |
| No `--region` flag on deploy-web.sh | **`--region` flag** added (default: us-east-2) |

### F. SAM Configuration
| What docs say | What's actually true |
|---|---|
| `ReservedConcurrentExecutions: 1` | **Commented out** — requires concurrency quota increase |
| EFS uses `Tags` | **Uses `FileSystemTags`** (CloudFormation schema requirement) |
| No `STAGE` env var | **`STAGE` env var** passed to Lambda for Mangum base path |
| Secrets entered via `--guided` each time | **`samconfig.toml` stores all params** including secrets (gitignored) |
| `samconfig.toml` not gitignored | **Added to `.gitignore`** (contains secrets) |
| `ElevenLabsApiKey` has default "" | **Default "none"** (SAM guided deploy rejects blank NoEcho params) |

### G. Template Structure Changes
| What docs say | What's actually true |
|---|---|
| No DependsOn for Lambdas | **`DependsOn: [MountTargetA, MountTargetB]`** on both Lambda functions |
| No `BuildMethod: makefile` metadata | **Both functions have `Metadata: BuildMethod: makefile`** |

## Execution Plan

### Step 1: Update SERVERLESS_PLAN.md
- §3.1: Change `lifespan="off"` → `lifespan="auto"`, add `api_gateway_base_path` docs
- §3.2: Add NAT Gateway requirement, update VPC architecture, update cost estimate
- §3.10: Add Makefile-based build approach, cross-compilation requirement
- §5: Update SAM template outline with custom domains, NAT Gateway, conditions
- §6 Risks: Add NAT Gateway cost risk, update concurrency note
- §8 Cost: Add NAT Gateway ~$32/month, update total from ~$2 to ~$34

### Step 2: Update SERVERLESS_README.md
- Prerequisites: Python 3.11 → 3.12
- Architecture diagram: Add NAT Gateway, custom domains
- Quick start: Add `requirements.txt` generation step
- Environment variables: Add `STAGE` env var
- SAM parameters: Add `ApiDomainName`, `ApiAcmCertificateArn`, update `ElevenLabsApiKey` default
- Deploy API section: Document `samconfig.toml` secret storage, remove manual env var update step
- Deploy Web UI section: Document runtime `config.js` pattern, `--region` flag
- Custom domain section: Full rewrite with ACM cert steps for both web + API, Cloudflare DNS instructions
- Troubleshooting: Add "pydantic_core import error" (platform mismatch), "Service Unavailable" (no NAT Gateway), "cookie not sent" (SameSite/domain), "Not Found 404" (stage prefix stripping)
- Cost section: Update with NAT Gateway

### Step 3: Update PROMPT_APP.md §13
- Update IaC row: mention Makefile build, custom domains
- Update cost estimate: ~$2 → ~$34 (NAT Gateway dominates)
- Update runtime: 3.11 → 3.12
- Add note about NAT Gateway requirement for VPC Lambda

### Step 4: Update PROMPT_APP_BUILD_CHECKLIST.md Phase 6
- Mark completed items in Sprint 6.1-6.4
- Add items that were discovered during deployment (NAT Gateway, Makefile build, cookie fixes, runtime config.js)
- Note remaining items (CI/CD pipeline, eval container limitation docs)

### Step 5: Update PROMPTDIS_API_DOCS.md
- Configuration reference: Add `STAGE` env var, update `cookie_domain` property docs
- Deployment options: Update Lambda cost estimate
- Serverless settings: Document actual defaults vs planned

### Step 6: Update RUNBOOK.md
- Verify serverless deployment section matches actual `sam build && sam deploy` flow
- Update troubleshooting with real-world issues encountered
- Verify `deploy-web.sh` documentation matches `--region` flag and runtime config

## Verification
- Read each updated doc and confirm all code snippets/commands match the actual files in `prompt-mgmt/`
- Cross-reference `infra/template.yaml`, `Makefile`, `deploy-web.sh`, `lambda_handler.py`, `config.py`, `github_oauth.py` against doc claims
- Ensure no stale references to Python 3.11, `lifespan="off"`, or build-time `VITE_API_BASE_URL`
