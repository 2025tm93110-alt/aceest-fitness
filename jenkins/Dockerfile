# Jenkins controller that can run `docker` commands against the host's Docker daemon.
FROM jenkins/jenkins:lts-jdk17
USER root
COPY --from=docker:cli /usr/local/bin/docker /usr/local/bin/docker
RUN apt-get update \
 && apt-get install -y --no-install-recommends docker.io curl \
 && rm -rf /var/lib/apt/lists/*
USER jenkins
