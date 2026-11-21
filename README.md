# ACEest Fitness & Gym – Flask API with CI/CD

![CI](https://github.com/2025tm93110-alt/aceest-fitness/actions/workflows/main.yml/badge.svg)

A Flask web service for gym/fitness management, evolved from the legacy Tkinter desktop
application (`legacy/`). It manages clients, programs, weekly adherence, workouts, body
metrics, BMI, membership status and an AI-style weekly program generator. The repository
demonstrates a full DevOps lifecycle: Git → Pytest → Docker → Jenkins → GitHub Actions.

## Project structure

```
├── app.py                    # Flask application (app factory + business logic)
├── requirements.txt          # runtime dependencies
├── requirements-dev.txt      # + pytest, pytest-cov, flake8
├── tests/                    # Pytest suite (unit + API tests)
├── Dockerfile                # multi-stage: base / test / runtime
├── Jenkinsfile               # Jenkins BUILD pipeline
├── .github/workflows/main.yml# GitHub Actions CI
├── jenkins/Dockerfile        # Jenkins image with the Docker CLI
├── legacy/                   # original Tkinter versions (created by the replay script)
├── scripts/replay_versions.sh# one commit + tag per legacy version (with optional rollback)

```

## 1. Local setup and execution

```bash
git clone https://github.com/<your-username>/aceest-fitness.git
cd aceest-fitness
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python app.py                                          # http://127.0.0.1:5000 (set HOST=0.0.0.0 to expose)
```

Try it:

```bash
curl localhost:5000/health
curl -X POST localhost:5000/clients -H "Content-Type: application/json" \
     -d '{"name":"Arun","height":175,"weight":80,"program":"Fat Loss (FL)","membership_expiry":"2030-01-01"}'
curl localhost:5000/clients/Arun/bmi
curl -X POST localhost:5000/clients/Arun/generate-program -H "Content-Type: application/json" \
     -d '{"experience":"beginner"}'
```

Data is stored in SQLite (`aceest_fitness.db`, override with the `ACEEST_DB` env var).

### API reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | liveness probe |
| GET | `/programs`, `/programs/<name>` | program catalogue (workout, diet, calorie factor) |
| POST / GET | `/clients` | create / list clients (calories auto-computed) |
| GET / PUT / DELETE | `/clients/<name>` | read / update / delete (cascades history) |
| POST / GET | `/clients/<name>/progress` | log / read weekly adherence (0–100) |
| POST / GET | `/clients/<name>/workouts` | log / read workout sessions |
| POST / GET | `/clients/<name>/metrics` | log / read weight, waist, body-fat |
| GET | `/clients/<name>/bmi` | BMI, category, risk note |
| GET | `/clients/<name>/membership` | Active / Expired / Not Set |
| GET | `/clients/<name>/summary` | profile + aggregates |
| POST | `/clients/<name>/generate-program` | weekly plan by experience level |

## 2. Running the tests manually

```bash
pip install -r requirements-dev.txt
pytest                # runs all tests with a coverage report
flake8 .              # lint
```

Run them inside Docker (same environment as CI):

```bash
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

The suite covers pure logic (calories, BMI, membership, program generation) and every API
endpoint including validation errors, 404/409 paths and malformed-input regressions (non-object JSON bodies, wrong types) (78 tests, ~99 % coverage, enforced by a 90 % minimum gate).

## 3. Docker

```bash
docker build -t aceest-fitness .                       # runtime image (default target)
docker run -d -p 5000:5000 -v aceest-data:/data aceest-fitness
curl localhost:5000/health
```

Image design: `python:3.12-slim`, multi-stage (dev tools/tests never reach the runtime image),
non-root user, Gunicorn, `HEALTHCHECK`, layer-cached dependency install, `.dockerignore`.

## 4. CI/CD overview

### GitHub Actions (`.github/workflows/main.yml`)
Triggered on **every push and pull request**:

1. **Build & Lint** – install deps, `compileall` syntax check, `flake8`.
2. **Docker Build & Test** (needs stage 1) – build the `test` target, **run Pytest inside the
   container**, build the `runtime` image and smoke-test `/health`.

### Jenkins (`Jenkinsfile`)
Jenkins acts as the secondary, clean-room BUILD validation:

1. Clean workspace + checkout latest code from GitHub.
2. `docker build --no-cache` of the test image (guarantees a from-scratch build).
3. Run flake8 + Pytest in the container.
4. Build the runtime image and smoke-test it; always remove the test container.

**Jenkins setup (once):**
1. Build and run the Docker-enabled Jenkins image shipped in this repo (Linux / VM):
   ```bash
   docker build -t aceest-jenkins ./jenkins
   docker run -d --name jenkins -p 8080:8080 -p 50000:50000 \
     -v jenkins_home:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock \
     --group-add "$(stat -c '%g' /var/run/docker.sock)" aceest-jenkins
   ```
   (Docker Desktop on Windows/macOS: replace `--group-add …` with `-u root`.)
2. Open `http://localhost:8080`, unlock with
   `docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword`, install suggested plugins.
3. *New Item → Pipeline* → **Pipeline script from SCM** → Git → repo URL, branch `*/main`,
   script path `Jenkinsfile`.
4. *Build Triggers* → **Poll SCM** (`H/2 * * * *`) – or a GitHub webhook if Jenkins is publicly reachable.
5. **Build Now** – every stage should be green; each build tags the image `aceest-fitness:<build-number>`,
   which also enables rollback by re-running an earlier tag.

## 5. Git workflow

* `main` is always releasable. Work starts from `main` on a named branch:
  `feature/*`, `fix/*`, `test/*`, `infra/*`, or `docs/*`.
* Small commits use Conventional Commit prefixes:
  `feat:`, `fix:`, `test:`, `ci:`, `docs:`, `build:`, or `chore:`.
* Every branch is pushed to GitHub and merged through a pull request (PR).
  Direct changes to `main` are not used for Assignment 2 work.
* The PR is expected to trigger GitHub Actions. A merge is evidence-based:
  lint and tests must pass, changed files must be visible, and the PR
  description must identify the purpose and validation performed.
* Release commits on `main` are tagged with immutable versions. The Assignment
  1 legacy desktop versions use `v1.0` through `v3.2.4`. Assignment 2 release
  images use the Git commit SHA or a release tag such as `v2.0.0`.
* Defects are reversed with `git revert`; history is not rewritten on shared
  branches. Docker and Kubernetes also use immutable image tags and explicit
  rollout rollback commands.

### Assignment 2 branch and PR sequence

```bash
git switch main
git pull --ff-only origin main
git switch -c infra/assignment-2-pipeline

# Make and validate one coherent change.
git add <specific-files>
git diff --cached --check
git commit -m "infra: add Assignment 2 pipeline configuration"
git push -u origin infra/assignment-2-pipeline
```

Open a PR from `infra/assignment-2-pipeline` into `main`. The PR description
should include:

1. the problem or requirement addressed;
2. the files changed;
3. commands and test results used for validation;
4. Docker image or Kubernetes evidence, when relevant;
5. Jenkins or GitHub Actions run links; and
6. the rollback or follow-up work, when relevant.

Merge the PR only after GitHub Actions is green and the changes have been
reviewed. Capture evidence of the branch list, PR conversation, CI checks,
merged commit, and release tag for the submission report.
