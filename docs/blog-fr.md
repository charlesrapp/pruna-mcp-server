# Construire un serveur MCP pour Pruna AI — De la spec à la production en une session

*Publié en avril 2026*

![Un chat assis à côté d'un laptop — généré par Pruna AI en 1,5 seconde](hero.jpg)
*Cette image a été générée en tapant un prompt dans mon assistant IA (en anglais — les modèles répondent mieux aux prompts en anglais). 1,5 seconde, 0,005$.*

## Tout a commencé avec un bol de dal

Dimanche dernier, je construisais une appli de menu de cantine pour mes enfants. Le menu affichait "Dal indien avec riz" et je voulais générer une belle image pour l'accompagner. J'ouvre Claude Desktop, je tape "génère-moi une image de dal indien avec du riz"... et Claude me répond poliment qu'il ne peut pas faire ça.

![Dal indien — généré par Pruna AI](dal.jpg)
*Cette image de dal ? Générée 2 secondes plus tard, une fois le serveur MCP en place.*

J'ai dû quitter mon workflow, ouvrir un navigateur, trouver un générateur d'images, retaper le prompt, télécharger le résultat, le déplacer dans le bon dossier. Cinq minutes pour quelque chose qui devrait prendre cinq secondes.

C'est là que je me suis dit : et si mon assistant IA pouvait simplement appeler une API de génération d'images ?

## MCP + Pruna AI = La pièce manquante

[MCP (Model Context Protocol)](https://modelcontextprotocol.io/) est un standard ouvert qui permet aux assistants IA d'appeler des outils externes — pensez-y comme l'USB-C de l'IA. [Pruna AI](https://pruna.ai) est une API de génération d'images et de vidéos ultra-rapide : 0,005$/image, génération en moins de 2 secondes, 18 modèles.

Le plan : construire un serveur MCP qui encapsule l'API Pruna. N'importe quel client MCP — Kiro, Claude Desktop, Cursor — obtient des super-pouvoirs de génération d'images.

## Le résultat : 6 outils, 7 prompts, un après-midi

Voici ce que ça donne une fois le serveur installé :

```
> génère-moi une image de coucher de soleil sur les Alpes

✓ Appel de generate_image...
  file_path: pruna-output/1776068896_p-image_v5A5xIED.jpg
  model: p-image
  generation_time_ms: 1532
  [image affichée inline]
```

**6 outils MCP :**
- `generate_image` — texte vers image avec 10 modèles (~1,5s, 0,005$)
- `edit_image` — modifier des images avec des instructions texte (~2s, 0,01$)
- `upscale_image` — amélioration IA jusqu'à 8 mégapixels (~4,5s, 0,005$)
- `generate_video` — texte/image vers vidéo (~43s, 0,02-0,04$/s)
- `list_models` — parcourir le catalogue (gratuit)
- `upload_file` — envoyer des fichiers locaux pour l'édition (gratuit)

Pour comparaison : DALL-E 3 coûte 0,04-0,08$/image et nécessite une intégration API séparée. Midjourney nécessite Discord. Pruna est 8 à 16 fois moins cher et vit directement dans votre assistant IA.

**7 prompts MCP** encodent les bonnes pratiques pour les cas d'usage courants : photos produit, home staging virtuel, visuels réseaux sociaux, concept art de jeux, créations publicitaires, vidéos pub, et amélioration d'images. Pas besoin de connaître les conventions de prompting de Pruna — les prompts s'en chargent.

## Architecture : 400 lignes de logique réelle

```
┌─────────────┐     STDIO/JSON-RPC     ┌──────────────────┐     HTTPS     ┌───────────┐
│  Client MCP │ ◄──────────────────────► │  pruna-mcp-server │ ◄────────────► │ API Pruna │
│(Kiro/Claude) │                        │                  │               │           │
└─────────────┘                         └──────────────────┘               └───────────┘
```

Cinq modules, chacun avec une responsabilité claire :

- **`server.py`** — Serveur FastMCP, outils, ressources, prompts
- **`client.py`** — Client HTTP async avec retry exponentiel
- **`models.py`** — Registre statique de 18 modèles avec tarification
- **`prompts.py`** — Templates de prompts avec défauts adaptés par plateforme
- **`config.py`** — Configuration par variables d'environnement avec validation fail-fast

Quatre décisions de design qui comptent :

1. **Sync pour les images, async pour la vidéo.** Les images prennent 1-2s → endpoint sync. La vidéo prend 30-60s → polling async avec reporting de progression. Si le sync timeout, on bascule automatiquement en async. Aucune intervention utilisateur.

2. **Gestion transparente des fichiers.** Passez un chemin local ou une URL — si c'est local, on envoie automatiquement vers Pruna. L'utilisateur n'y pense jamais.

3. **ImageContent MCP natif.** Les outils retournent `[TextContent, ImageContent]` — métadonnées JSON plus image en base64. Les clients qui supportent l'affichage inline montrent l'image directement dans le chat.

4. **Sécurité par défaut.** Protection contre le path traversal sur les uploads/downloads, validation des URLs de livraison, clé API jamais loggée ni retournée dans les résultats.

## Les pièges (a.k.a. pourquoi ce blog existe)

C'est là que ça devient intéressant. Quatre bugs qui m'ont coûté plus de temps que l'implémentation elle-même.

### 1. Le PATH invisible de Claude Desktop

Claude Desktop lance les serveurs MCP via `launchd` avec un PATH minimal : `/usr/bin:/bin`. Mon binaire `uv` est dans `~/.local/bin/`. Le serveur échouait silencieusement — pas d'erreur, pas de log, juste "Server disconnected."

**Fix :** Chemin complet vers `uv` dans la config. Toujours.
```json
"args": ["-c", "PRUNA_API_KEY=$(security ...) /Users/me/.local/bin/uv run ..."]
```

**Leçon :** Testez votre serveur MCP avec `env -i PATH=/usr/bin:/bin` avant de le déployer sur des clients GUI.

### 2. La triple whitelist de Kiro CLI

Les agents Kiro nécessitent trois entrées de config séparées pour que les outils MCP apparaissent :
- `mcpServers` — définition du serveur
- `tools` — whitelist avec la syntaxe `@pruna/*`
- `allowedTools` — noms individuels des outils

Oubliez-en une → les outils ne se chargent pas, silencieusement. J'ai passé 20 minutes à fixer `/mcp` qui affichait "pruna: running, 6 tools" pendant que le LLM insistait qu'il n'avait aucune capacité de génération d'images.

### 3. Le trou de sérialisation de FastMCP

Ma première tentative retournait le helper `Image` de FastMCP dans une liste :
```python
return [json.dumps(metadata), Image(path=out_path)]  # 💥 Erreur de sérialisation
```

La fonction `_convert_to_content` de FastMCP gère `Image` au premier niveau, mais pas dans une liste mixte avec des strings. Le fix : utiliser les types MCP natifs directement :
```python
from mcp.types import ImageContent, TextContent

return [
    TextContent(type="text", text=json.dumps(metadata)),
    ImageContent(type="image", data=base64_data, mimeType="image/jpeg"),
]
```

### 4. Le Content-Type multipart écrasé

Le client HTTP avait `Content-Type: application/json` comme header par défaut. Lors de l'envoi de fichiers en multipart, ce header écrasait la détection automatique du boundary par httpx → `400 Bad Request: Missing content`.

**Fix :** Client httpx séparé pour les uploads, sans le header JSON.

## Les chiffres

| Métrique | Valeur |
|----------|--------|
| Code source | 400 lignes (7 modules) |
| Tests | 100 |
| Couverture | 93% |
| mypy strict | 0 erreurs |
| Génération image | ~1,5s, 0,005$ |
| Génération vidéo | ~43s, 0,02-0,04$/s |
| Dépendances | 2 (mcp, httpx) |

## Essayez-le

```bash
git clone https://github.com/charlesrapp/pruna-mcp-server.git
cd pruna-mcp-server
uv sync

# Stocker votre clé API (obtenez-en une sur pruna.ai — macOS Keychain)
security add-generic-password -a $USER -s PRUNA_API_KEY -w "votre-clé"

# Sur Linux/Windows, utilisez une variable d'environnement :
# export PRUNA_API_KEY="votre-clé"

# Lancer
PRUNA_API_KEY=$(security find-generic-password -a $USER -s PRUNA_API_KEY -w) uv run pruna-mcp
```

Ajoutez-le à la config de votre client MCP et demandez une image. C'est tout.

→ [Repo GitHub](https://github.com/charlesrapp/pruna-mcp-server) — ⭐ si ça vous est utile
→ [Obtenir une clé API Pruna](https://pruna.ai)

## Et ensuite ?

- **Publication PyPI** — `uvx pruna-mcp-server` pour une installation zéro
- **MCP Registry** — soumission pour la découvrabilité dans l'écosystème
- **Entraînement LoRA** — fine-tuning de modèles custom quand Pruna sortira l'API trainer
- **Transport HTTP/SSE** — déploiement distant sans STDIO

## Ce qu'il faut retenir

Si vous avez une API — n'importe quelle API — vous pouvez la rendre accessible aux assistants IA en un après-midi. L'écosystème MCP est jeune mais l'expérience développeur est déjà solide. Le plus dur, ce n'est pas le code, ce sont les particularités de configuration de chaque client.

L'intégralité du projet — spec, implémentation, 100 tests, documentation, tests live sur deux clients MCP — a été construite en une seule session. Votre API pourrait être la prochaine.

---

*Charles Rapp — Solutions Architect chez AWS, Strasbourg. Je construis des choses à l'intersection de l'infrastructure cloud et de l'IA. Retrouvez-moi sur [GitHub](https://github.com/charlesrapp).*
