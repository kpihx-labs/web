# search-unifier — Moteur de Recherche Souverain Multi-Réseaux

Moteur de recherche unifié en CLI permettant de requêter simultanément :
1. **Surface Web** via l'instance locale SearXNG (moteurs Google, Bing, Brave, DDG, Qwant, Startpage, GitHub, etc.).
2. **Dark Web (.onion)** en direct via le proxy SOCKS5 Tor local (`127.0.0.1:9050`).
3. **I2P** (eepsites) via le proxy HTTP I2P local (`127.0.0.1:4444`).

## Installation et intégration globale

Pour lier la commande directement dans ton terminal (`$HOME/.local/bin/search-unifier`) :
```bash
make uv-link
```

## Utilisation

```bash
# Recherche standard Surface Web
search-unifier "privacy tools" --surface -f md --limit 5

# Recherche Dark Web (.onion) pure
search-unifier "security" --no-surface --onion -f json --limit 5

# Recherche simultanée unifiée avec déduplication
search-unifier "cryptography" --surface --onion -f md

# Choisir des moteurs surface précis
search-unifier "machine learning" --engines brave,github -f json
```

## Formats de sortie

- `-f json` : Idéal pour les agents et scripts (objets structurés).
- `-f csv` : Export tableur délimité standard.
- `-f md` : Sortie lisible pour le terminal avec badges de réseau (`[SURFACE]`, `[ONION]`).
