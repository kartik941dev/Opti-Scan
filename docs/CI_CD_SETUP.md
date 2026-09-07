# CI/CD Pipeline & Conditional Deployment Guide

OptiScan uses a continuous integration and deployment pipeline configured via GitHub Actions in [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml).

The pipeline enforces a **hard test condition**:
> **Deployments to Render (Backend) and Vercel (Frontend) will ONLY run if all backend unit/integration tests and frontend production builds pass with 100% success.**

---

## 🛡️ How the Condition Works

In [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml), deployment jobs declare an explicit dependency on test jobs using GitHub Actions Directed Acyclic Graph (DAG):

```yaml
deploy-backend:
  needs: [test-backend, build-frontend]
  if: github.ref == 'refs/heads/main' && (github.event_name == 'push' || github.event_name == 'workflow_dispatch')
```

### Execution Flow:
1. **On Every Push or Pull Request**:
   - `test-backend`: Spawns an isolated Ubuntu runner, installs OpenCV/Python dependencies, and runs `pytest` across all edge-case suites (`test_all_edges.py`, `test_api_endpoints.py`, `test_real_omr_assessment.py`).
   - `build-frontend`: Spawns a Node 20 runner, executes clean `npm ci`, and validates that `npm run build` compiles Vite assets with zero errors.
2. **On Test Failure**:
   - If any test or build fails, GitHub Actions **immediately terminates the pipeline**.
   - The deployment jobs (`deploy-backend`, `deploy-frontend`) are **cancelled/skipped** automatically.
3. **On Test Success (Main Branch Only)**:
   - Only when **both** `test-backend` and `build-frontend` exit with code `0`, GitHub Actions unlocks the deployment jobs.

---

## 🔑 Required GitHub Secrets Configuration

To connect GitHub Actions to your deployment targets, add the following secrets in your repository:
**GitHub Repo > Settings > Secrets and variables > Actions > New repository secret**

### 1. Render (Backend)
- **`RENDER_DEPLOY_HOOK_URL`**:
  1. Open your [Render Dashboard](https://dashboard.render.com).
  2. Select your `optiscan-backend` Web Service.
  3. Go to **Settings > Deploy Hook**.
  4. Copy the URL (e.g. `https://api.render.com/deploy/srv-xxxx?key=yyyy`) and save it as the `RENDER_DEPLOY_HOOK_URL` secret.
  5. *(Recommended)* In Render Service Settings, disable **"Auto-Deploy"**. This ensures Render only deploys when GitHub Actions explicitly fires the webhook after all tests pass!

### 2. Vercel (Frontend)
- **`VERCEL_TOKEN`**:
  - In [Vercel Account Settings > Tokens](https://vercel.com/account/tokens), create an access token.
- **`VERCEL_ORG_ID`** and **`VERCEL_PROJECT_ID`**:
  - In your local frontend directory, if you run `vercel link` (or inspect `.vercel/project.json`), you will see `orgId` and `projectId`.
  - Alternatively, find them in your Vercel Dashboard under **Project Settings > General**.
  - *(Recommended)* In Vercel Git settings, you can disconnect automatic branch deployments or configure it to rely on GitHub Actions so that deployments strictly wait for CI test verification.

---

## 🧪 Local Testing

You can run the exact same test commands locally before pushing:

### Backend Tests
```bash
# Run from repository root
python -m pytest

# Or with verbose output
pytest -v
```

### Frontend Build Verification
```bash
cd frontend
npm run build
```
