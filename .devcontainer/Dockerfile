FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Le dépôt Yarn livré avec l'image a une clé de signature expirée, ce qui fait
# échouer apt-get update (et donc l'installation de Docker). Yarn n'est pas utilisé ici.
RUN rm -f /etc/apt/sources.list.d/yarn.list
