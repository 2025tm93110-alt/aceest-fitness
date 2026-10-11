# ACEest Fitness DevOps Assignment

This repository contains the Flask application, automated tests, Docker images,
Jenkins pipeline, GitHub Actions workflow, and the supplied legacy Tkinter
versions.

## Local verification

From this directory, install Python 3.10 or newer and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt
py -m flake8 .
py -m pytest
```

The test suite enforces at least 90% coverage. The application health check is
available at `http://127.0.0.1:5000/health` after `py app.py`.

## Version history and rollback

The original desktop releases are tagged `v1.0` through `v3.2.4`. The supplied
`v1.1.2` release has a rollback commit immediately after it. The later
`v3.1.2` release is also retained and followed by an explicit rollback to the
`v3.0.1` code. Releases `v2.1.2` and `v3.0.1` are no-op releases whose source
trees are identical to their preceding releases; their tags are retained as
evidence of the supplied version sequence.

To inspect the history:

```powershell
git log --oneline --decorate --graph
git tag --list --sort=version:refname
```

To demonstrate rollback without rewriting history:

```powershell
git show v3.1.2:legacy/ACEest_Fitness.py
git show HEAD:legacy/ACEest_Fitness.py
```

## Docker and CI/CD

```powershell
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
docker build -t aceest-fitness:runtime .
docker run --rm -p 5000:5000 aceest-fitness:runtime
```

GitHub Actions runs linting, syntax checks, containerized tests, and a runtime
smoke test. Jenkins uses the `Jenkinsfile` to perform the same clean-room build
with Docker. The Jenkins controller image is built from `jenkins/Dockerfile`.

## Submission checklist

- [ ] Push `main` and all version tags: `git push origin main --tags`
- [ ] Confirm the GitHub Actions workflow is green.
- [ ] Run the local test and Docker commands and retain screenshots or logs.
- [ ] Configure Jenkins from the public repository and retain one successful
      build with the stage view visible.
- [ ] Demonstrate a tagged release and its rollback commit during the viva.