# CHANGELOG — search-unifier

## [1.0.0] - 2026-10-23
- Initialisation du projet sous `~/Labs/KpihX-Labs/search-unifier` selon le standard `k-project`.
- Implémentation du moteur Surface Web interrogeant l'API JSON locale de SearXNG (`127.0.0.1:8081`).
- Implémentation native et synchrone de l'extraction Tor .onion via le proxy local SOCKS5 (`127.0.0.1:9050`) résolvant le bug des fichiers vides d'onionsearch.
- Support des formats de sortie `json`, `csv` et `md`.
- Déduplication déterministe basée sur les URLs normalisées.
- Makefile standard `Makefile.uv` (`check`, `smoke`, `uv-link`, `run-*`).
