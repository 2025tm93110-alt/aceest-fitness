# ACEest Fitness & Gym - Assignment 2 Execution and Submission Guide

This guide is the working plan for extending Assignment 1 into the Assignment 2
CI/CD implementation. It is written for two execution environments:

1. **Local Windows machine**: Docker Desktop, PowerShell, Git, Python, and
   Minikube.
2. **University Prayogshala VM**: Linux commands, Docker/Podman, Minikube or
   Kubernetes, Jenkins, and the VM's reachable IP address.

The same GitHub repository and the same image tags must be used in both
environments. Do not commit passwords, registry tokens, kubeconfig files,
database files, `.venv`, coverage output, or Jenkins secrets.

## 1. Assignment 2 target

The final submission must demonstrate this traceable flow:

```text
feature branch
  -> pull request and review
  -> GitHub Actions CI
  -> Jenkins clean build
  -> Pytest and coverage
  -> SonarQube analysis and quality gate
  -> Docker/Podman image
  -> Docker Hub or local registry
  -> Kubernetes deployment
  -> smoke test and evidence
  -> controlled rollout and rollback
```

The Assignment 1 feedback specifically requested:

- more detailed branching and pull-request evidence;
- a clearer explanation of the CI/CD configuration; and
- an actual application deployment stage.

This guide addresses those points and adds evidence checkpoints for every
Assignment 2 requirement.

## 2. Current baseline from Assignment 1

The repository already contains:

| Area | Existing implementation |
|---|---|
| Application | `app.py`, SQLite persistence, health endpoint |
| Tests | `tests/`, Pytest and coverage configuration |
| Local development | `requirements-dev.txt`, Flask startup |
| Containerization | multi-stage `Dockerfile`, non-root runtime, health check |
| GitHub CI | `.github/workflows/main.yml` |
| Jenkins | `Jenkinsfile`, `jenkins/Dockerfile` |
| Version history | `legacy/` and `scripts/replay_versions.sh` |
| Documentation | `README.md` with API, Docker, Jenkins, and Git workflow |

Assignment 2 still requires these additions or updates:

- Kubernetes manifests and deployment helper scripts;
- a documented deployment strategy (blue-green, canary, shadow, A/B, and
  rolling update);
- SonarQube project configuration, scan, and quality-gate evidence;
- Docker Hub or a VM-local registry image tags;
- Jenkins stages for quality analysis, image publication, deployment, smoke
  testing, and rollback;
- an updated README and a short report with architecture, challenges,
  mitigations, and outcomes.

## 3. Recommended repository additions

Create these files using the repository's existing naming conventions:

```text
k8s/
  namespace.yaml
  configmap.yaml
  deployment-blue.yaml
  deployment-green.yaml
  deployment-canary.yaml
  deployment-shadow.yaml
  service.yaml
  ingress-or-nodeport.yaml
  service-shadow.yaml
  rollout-rolling.yaml
scripts/
  deploy-blue-green.sh
  deploy-canary.sh
  rollback.sh
sonar-project.properties
Jenkinsfile
.github/workflows/main.yml
ASSIGNMENT-2-REPORT.md
```

Use placeholders such as `${IMAGE_REPOSITORY}` and `${IMAGE_TAG}` in scripts
and Jenkins parameters. Store actual values in Jenkins credentials or shell
environment variables.

## 4. Phase 0 - verify prerequisites

### 4.1 Windows local machine

Install or verify:

- Git and GitHub access;
- Python 3.12 or the repository-supported Python version;
- Docker Desktop with Linux containers and Kubernetes enabled, or Minikube;
- `kubectl` and `minikube`;
- optional: `helm`, if used by the chosen deployment tooling;
- a Docker Hub account and an access token;
- Java 17+ only if SonarScanner is installed outside a container.

Verify in PowerShell:

```powershell
git --version
python --version
docker version
kubectl version --client
minikube version
```

### 4.2 Prayogshala VM

Verify:

```bash
git --version
python3 --version
docker version || podman version
kubectl version --client
minikube version
```

If Docker is unavailable but Podman is approved by the course, use Podman for
image build/run commands and document the substitution. Jenkins, Kubernetes,
and the registry must still be able to pull the resulting image.

Record the VM address:

```bash
hostname -I
```

Use the VM IP rather than `localhost` when opening the deployed application
from another machine.

## 5. Phase 1 - establish the Git and PR workflow

Do this before changing application or infrastructure files.

```bash
git clone <GITHUB_REPOSITORY_URL>
cd aceest-fitness
git switch main
git pull --ff-only origin main
git switch -c infra/assignment-2-pipeline
```

Recommended branch categories:

```text
feature/<short-description>   application changes
test/<short-description>      tests and coverage
infra/<short-description>     Docker, Kubernetes, SonarQube, Jenkins
docs/<short-description>      README and report
fix/<short-description>       defects
```

For each logical change:

```bash
git status
git add <specific-files>
git commit -m "infra: add Kubernetes deployment manifests"
git push -u origin infra/assignment-2-pipeline
```

Open a pull request into `main`. The PR description should include:

- purpose and changed files;
- test and lint commands executed;
- image tag, if an image was built;
- deployment/smoke-test result, if applicable;
- rollback result, if applicable;
- screenshots or links to GitHub Actions and Jenkins runs.

Merge only after required checks pass. Tag a reproducible release on `main`:

```bash
git switch main
git pull --ff-only origin main
git tag -a v2.0.0 -m "Assignment 2 CI/CD release"
git push origin v2.0.0
```

Capture screenshots of the branch list, PR, review/approval, merged PR, commit
history, and release tag. This directly improves the branching-workflow gap
identified in Assignment 1 feedback.

## 6. Phase 2 - run and extend the application checks

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest --cov=. --cov-report=term-missing
python -m flake8 .
python -m compileall -q .
```

If the virtual environment does not exist:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

### Prayogshala VM

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest --cov=. --cov-report=term-missing
python -m flake8 .
python -m compileall -q .
```

Add tests for every new deployment-related helper or health behavior. Keep the
existing coverage threshold at or above the Assignment 1 result and record the
exact test count, coverage percentage, and lint result in the report. Never
claim a result that was not produced by the current commit.

## 7. Phase 3 - build and verify the image

Set an image name. For Docker Hub:

```text
<DOCKERHUB_USERNAME>/aceest-fitness
```

Build a uniquely traceable tag from the Git commit:

### PowerShell

```powershell
$env:IMAGE_REPOSITORY="<DOCKERHUB_USERNAME>/aceest-fitness"
$env:IMAGE_TAG=(git rev-parse --short HEAD)
docker build --target test -t "${env:IMAGE_REPOSITORY}:test-${env:IMAGE_TAG}" .
docker run --rm "${env:IMAGE_REPOSITORY}:test-${env:IMAGE_TAG}"
docker build -t "${env:IMAGE_REPOSITORY}:${env:IMAGE_TAG}" .
docker run -d --name aceest-local -p 5000:5000 `
  -v aceest-data:/data "${env:IMAGE_REPOSITORY}:${env:IMAGE_TAG}"
curl.exe http://127.0.0.1:5000/health
docker rm -f aceest-local
```

### Linux VM

```bash
export IMAGE_REPOSITORY="<DOCKERHUB_USERNAME>/aceest-fitness"
export IMAGE_TAG="$(git rev-parse --short HEAD)"
docker build --target test -t "$IMAGE_REPOSITORY:test-$IMAGE_TAG" .
docker run --rm "$IMAGE_REPOSITORY:test-$IMAGE_TAG"
docker build -t "$IMAGE_REPOSITORY:$IMAGE_TAG" .
docker run -d --name aceest-local -p 5000:5000 \
  -v aceest-data:/data "$IMAGE_REPOSITORY:$IMAGE_TAG"
curl http://127.0.0.1:5000/health
docker rm -f aceest-local
```

Record `docker image inspect`, the test-container output, and the health
response. Use `docker login` only interactively or with a secret-managed token:

```bash
docker login
docker push "$IMAGE_REPOSITORY:$IMAGE_TAG"
docker tag "$IMAGE_REPOSITORY:$IMAGE_TAG" "$IMAGE_REPOSITORY:v2.0.0"
docker push "$IMAGE_REPOSITORY:v2.0.0"
```

Do not put the Docker Hub token in GitHub files or Jenkinsfile text.

## 8. Phase 4 - run SonarQube quality analysis

Run SonarQube locally on Docker or use the university-provided SonarQube
service. A local Docker example is:

```bash
docker volume create sonarqube-data
docker run -d --name sonarqube -p 9000:9000 \
  -v sonarqube-data:/opt/sonarqube/data \
  sonarqube:lts-community
```

Open `http://localhost:9000`, change the initial password, create a project,
and create a token. Store the token as `SONAR_TOKEN` in Jenkins and GitHub
Actions secrets. Configure `sonar-project.properties` to:

- identify the project and source directory;
- exclude `.venv/`, `tests/`, `legacy/`, `__pycache__/`, and generated reports
  where appropriate;
- point to the coverage XML generated by Pytest;
- enforce the project quality gate in Jenkins.

Run the scanner using the approved SonarScanner installation or scanner
container. Capture:

- project dashboard;
- bugs, vulnerabilities, code smells, and coverage;
- quality-gate status;
- Jenkins stage log showing the gate passed.

If the VM is not reachable from the local browser, use the VM's forwarded port
or open the service on the VM and capture screenshots there.

## 9. Phase 5 - start Kubernetes/Minikube

### Local

```bash
minikube start
kubectl create namespace aceest --dry-run=client -o yaml | kubectl apply -f -
kubectl config set-context --current --namespace=aceest
```

### Prayogshala VM

```bash
minikube start --driver=docker
kubectl create namespace aceest --dry-run=client -o yaml | kubectl apply -f -
kubectl config set-context --current --namespace=aceest
```

If the VM provides an existing Kubernetes cluster, use the assigned context
instead of starting Minikube and document the context name.

For a private Docker Hub repository, create an image-pull secret without
committing it:

```bash
kubectl create secret docker-registry regcred \
  --docker-server=https://index.docker.io/v1/ \
  --docker-username="$DOCKERHUB_USERNAME" \
  --docker-password="$DOCKERHUB_TOKEN" \
  --docker-email="$DOCKERHUB_EMAIL" \
  -n aceest
```

Apply namespace, config, deployment, service, and ingress/NodePort manifests:

```bash
kubectl apply -f k8s/ -n aceest
kubectl get deployments,pods,services -n aceest -o wide
kubectl rollout status deployment/aceest-fitness -n aceest --timeout=180s
```

Find the endpoint:

```bash
minikube service aceest-fitness --url
```

For a NodePort on the VM, use:

```bash
kubectl get service aceest-fitness -n aceest
curl http://<VM_IP>:<NODE_PORT>/health
```

The endpoint and health response are mandatory submission evidence.

## 10. Phase 6 - demonstrate deployment strategies

Implement and document each strategy. The exact traffic mechanism may be
Ingress, a Kubernetes Service selector, or a supported service-mesh feature,
but the evidence must show which version received traffic.

### 10.1 Rolling update

Use the standard Deployment strategy with `maxUnavailable: 0` and
`maxSurge: 1` (or an equivalent safe configuration):

```bash
kubectl set image deployment/aceest-fitness \
  aceest-fitness="$IMAGE_REPOSITORY:$IMAGE_TAG" -n aceest
kubectl rollout status deployment/aceest-fitness -n aceest
kubectl rollout history deployment/aceest-fitness -n aceest
```

Capture the rollout status and old/new ReplicaSets.

### 10.2 Blue-green

Run separate `blue` and `green` Deployments with the same labels except for
the color. The Service selects the active color. Deploy green, verify its
health, switch the Service selector, then verify the endpoint:

```bash
kubectl patch service aceest-fitness -n aceest \
  -p '{"spec":{"selector":{"app":"aceest-fitness","color":"green"}}}'
curl http://<ENDPOINT>/health
```

Rollback by selecting blue again. Record both Service YAML states and health
responses.

### 10.3 Canary

Run a small canary ReplicaSet/Deployment with the candidate image and a
matching Service selector. Keep the stable replicas running, send test traffic,
inspect canary logs/metrics, then scale canary up and stable down only after
the gate passes. A simple deterministic header or separate canary Service is
acceptable if documented and demonstrated.

### 10.4 Shadow

Run a shadow Deployment with no user-facing responses. Duplicate requests to
the shadow Service using an application-level or proxy mechanism, and show
that shadow logs receive the request while the stable response is returned.
Do not send shadow responses to users.

### 10.5 A/B testing

Route two versions using a deterministic request attribute such as a header,
cookie, or documented path. Send requests for both cohorts and show that each
reaches the intended version. Document the routing rule and do not claim
random percentages unless traffic measurement proves them.

For every strategy, capture:

- manifest or command used;
- Pods and Services before and after the switch;
- endpoint request and response;
- relevant logs;
- the rollback command and successful post-rollback health check.

## 11. Phase 7 - Jenkins pipeline

Update the existing `Jenkinsfile` so stages are visible and independently
understandable:

1. Checkout the selected branch/tag.
2. Install or use the pinned build environment.
3. Run syntax check, lint, Pytest, and coverage.
4. Run SonarQube analysis and wait for the quality gate.
5. Build the test and runtime images.
6. Push an immutable commit image tag to Docker Hub/local registry.
7. Deploy the selected Kubernetes strategy.
8. Run `/health` and a representative API smoke test.
9. Publish test/coverage reports.
10. On failure, preserve logs and provide an explicit rollback job/parameter.

Recommended Jenkins parameters:

```text
IMAGE_TAG       immutable Git SHA or release tag
DEPLOY_STRATEGY rolling | blue-green | canary | shadow | ab
ROLLBACK_TAG    last known good image tag
```

Configure Jenkins as **Pipeline script from SCM**, branch `*/main`, script
path `Jenkinsfile`. Use the existing Docker-enabled Jenkins setup from
`README.md`, with the Docker socket only where permitted by the VM policy.
Configure Poll SCM or a GitHub webhook and capture a successful build after a
new commit.

Never echo registry or Sonar tokens. Use Jenkins Credentials Binding and
redact secrets in logs.

## 12. Phase 8 - GitHub Actions

Retain the existing fast CI checks on every push and pull request. Extend the
workflow only for credentials-backed operations:

- pull requests: test, lint, build, and (optionally) SonarQube analysis;
- main branch: publish an immutable image after all checks pass;
- protected environment/manual approval: deploy to Kubernetes;
- deployment job: smoke test and upload evidence.

Use GitHub repository/environment secrets, not plaintext YAML values. Avoid
deploying unreviewed pull-request code to the shared VM.

## 13. Failure and rollback drill

Before submission, intentionally use a known-bad image tag or invalid
configuration in a disposable deployment. Demonstrate that:

```bash
kubectl rollout undo deployment/aceest-fitness -n aceest
kubectl rollout status deployment/aceest-fitness -n aceest
curl http://<ENDPOINT>/health
```

For blue-green, restore the previous Service selector. For other strategies,
restore the last known-good immutable image tag. Record the failure, detection,
rollback action, and recovery time in the report.

## 14. Evidence checklist

Save screenshots or exported logs with meaningful names. The evidence folder
should contain at least:

```text
01-github-repository-and-branches.png
02-pull-request-and-actions.png
03-test-coverage-and-lint.txt
04-docker-build-and-health.txt
05-dockerhub-tags.png
06-sonarqube-quality-gate.png
07-jenkins-successful-pipeline.png
08-kubernetes-pods-services.png
09-application-endpoint-health.txt
10-rolling-update.png
11-blue-green-switch-and-rollback.png
12-canary-evidence.png
13-shadow-evidence.png
14-ab-routing-evidence.png
15-final-rollback.png
```

Use the actual current commit, image tag, endpoint, test count, coverage, and
quality-gate result in every record. Redact tokens, passwords, private keys,
and unrelated user data.

## 15. Final submission contents

Submit:

1. Public GitHub repository URL (or invited reviewer access).
2. Repository at the final tagged commit.
3. Flask application and tests.
4. Dockerfile and image-repository URL with versioned tags.
5. `Jenkinsfile` and successful recent Jenkins build URL/screenshots.
6. GitHub Actions successful workflow URL/screenshots.
7. SonarQube dashboard and quality-gate result.
8. Kubernetes YAML manifests and deployment-strategy scripts.
9. Running cluster endpoint URL and `/health` result.
10. Deployment and rollback evidence for all demonstrated strategies.
11. A 2-3 page report covering architecture, challenges, mitigations, and
    automation outcomes.

Before submitting, run:

```bash
git status
git log --oneline --decorate -10
git tag --list
kubectl get all -n aceest
```

Confirm that the GitHub URL, Docker image tags, Jenkins job, SonarQube result,
cluster endpoint, and evidence all refer to the same final commit.

## 16. Suggested execution order

Use this order to avoid debugging several systems at once:

1. Create the Assignment 2 branch and capture the PR workflow.
2. Make application/test changes and get local checks green.
3. Add SonarQube configuration and pass the quality gate.
4. Add Kubernetes manifests and deploy manually to Minikube.
5. Verify rolling update and rollback.
6. Implement and evidence blue-green, canary, shadow, and A/B routing.
7. Push immutable images to the registry.
8. Add Jenkins quality, publish, deploy, smoke-test, and rollback stages.
9. Extend GitHub Actions only after Jenkins works manually.
10. Repeat the final pipeline on the Prayogshala VM.
11. Update `README.md` and write the 2-3 page report.
12. Run the evidence checklist and submit the final tagged commit.

