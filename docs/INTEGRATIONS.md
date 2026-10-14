# Les dépôts GitHub et leur place dans SessionDNA

L’audit initial porte sur 174 dépôts. Ce document distingue le code réellement utilisé, les options et les alternatives. Ajouter deux outils qui assurent la même fonction ne rendrait pas l’application plus complète.

## Composants de la V2

| Dépôt | État | Utilité concrète |
|---|---|---|
| [React](https://github.com/react/react) | Intégré | Interface en cinq écrans, composants et état réactif. |
| [Radix UI](https://github.com/radix-ui/primitives) | Intégré | Onglets et fenêtres de détail accessibles au clavier. |
| [Lucide](https://github.com/lucide-icons/lucide) | Intégré | Icônes cohérentes dans toute l’application. |
| [React Hook Form](https://github.com/react-hook-form/react-hook-form) | Intégré | Formulaires des contraintes de planning et retours. |
| [TanStack Query](https://github.com/TanStack/query) | Intégré | Chargement, cache mémoire et actualisation des réponses du serveur. |
| [TanStack Table](https://github.com/TanStack/table) | Intégré | Tableau des activités avec colonnes et pagination. |
| [dnd-kit](https://github.com/clauderic/dnd-kit) | Intégré | Déplacement des séances entre créneaux du jour prescrit. |
| [Motion](https://github.com/motiondivision/motion) | Intégré | Transitions légères respectant la préférence de réduction des mouvements. |
| [Apache ECharts](https://github.com/apache/echarts) | Intégré | Courbes des mesures et affichage des contributions du modèle. |
| [MapLibre](https://github.com/maplibre/maplibre-gl-js) | Intégré | Tracé GPS chargé à la demande sur un fond neutre, sans fournisseur de tuiles. |
| [Turf](https://github.com/Turfjs/turf) | Intégré | Cadrage et longueur géométrique du tracé GPS affiché. |
| [FastAPI](https://github.com/fastapi/fastapi) | Intégré | API locale pour les analyses, imports, bilans et sauvegardes. |
| [DuckDB](https://github.com/duckdb/duckdb) | Intégré | Agrégations par semaine et sport, export Parquet contrôlé. |
| [ruptures](https://github.com/deepcharles/ruptures) | Intégré | Recherche de changements statistiques, en séparant pauses et trous. |
| [SHAP](https://github.com/shap/shap) | Intégré | Contributions des six variables à la sortie de la forêt existante ; additivité vérifiée. |
| [MLflow](https://github.com/mlflow/mlflow) | Intégré | Copie locale de l’expérience gelée et de ses empreintes ; pas de réentraînement. |
| [scikit-learn](https://github.com/scikit-learn/scikit-learn) | Existant conservé | Modèle de course et imputation existants conservés. |
| [Garmin Connect](https://github.com/cyberjunky/python-garminconnect) | Existant conservé | Import incrémental avec la session locale et prévention des doublons. |
| [Pydantic AI](https://github.com/pydantic/pydantic-ai) | Intégré, désactivé par défaut | Option de sélection de faits vérifiés du bilan, avec sortie structurée et sources. |
| [Ollama](https://github.com/ollama/ollama) | Connecteur prévu ; modèle à configurer | Fournisseur local optionnel pour cette sélection de faits. |
| [uv](https://github.com/astral-sh/uv) | Intégré | Dépendances Python décrites dans pyproject.toml et verrouillées dans uv.lock. |
| [Ruff](https://github.com/astral-sh/ruff) | Intégré | Contrôles statiques ciblés sur les erreurs de code. |
| [OWASP Cheat Sheet Series](https://github.com/OWASP/CheatSheetSeries) | Pratiques appliquées ; pas une bibliothèque | Principes appliqués : origine vérifiée, chemins bornés, taille limitée, imports validés. |

Le favori `react/react` désigne ici React ; le paquet installé est le paquet officiel `react` (projet `facebook/react`). Les autres outils de construction sont Vite, TypeScript et Vitest. SQLite stocke les saisies. Aucun code de shadcn/ui n’est installé : les composants sont écrits pour SessionDNA sur Radix et CSS.

## Décision pour chacun des 174 favoris

| Dépôt | Décision V2 | Motif ou usage ultérieur |
|---|---|---|
| [alibaba/page-agent](https://github.com/alibaba/page-agent) | Extension possible — non installé | Assistant qui explique une page de SessionDNA et aide à retrouver une séance. |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | Alternative — non installé | Automatiser exceptionnellement un parcours web sans API, par exemple récupérer un export autorisé. |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Alternative — non installé | Organiser un bilan en étapes persistantes: collecte, analyse, proposition, validation. |
| [langflow-ai/langflow](https://github.com/langflow-ai/langflow) | Alternative — non installé | Prototyper visuellement un assistant et découvrir les chaînes de traitement IA. |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Alternative — non installé | Assistant personnel externe qui interroge les rapports de SessionDNA. |
| [openclaw/openclaw](https://github.com/openclaw/openclaw) | Alternative — non installé | Consulter éventuellement son planning depuis une messagerie. |
| [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) | Apprentissage / outillage — non installé | Étudier l'automatisation du développement et la revue de changements. |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | Intégré, désactivé par défaut | Option de sélection de faits vérifiés du bilan, avec sortie structurée et sources. |
| [superdesigndev/treg](https://github.com/superdesigndev/treg) | Alternative — non installé | Centraliser plusieurs outils externes si les connecteurs deviennent nombreux. |
| [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | Alternative — non installé | Aide ponctuelle à récupérer un export depuis un navigateur déjà connecté. |
| [tinyhumansai/openhuman](https://github.com/tinyhumansai/openhuman) | Alternative — non installé | Explorer un autre socle d'assistant personnel. |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | Apprentissage / outillage — non installé | Améliorer les conventions de développement et les routines de contrôle. |
| [anthropics/financial-services](https://github.com/anthropics/financial-services) | Non retenu — non installé | Agents orientés finance, éloignés de l'entraînement triathlon. |
| [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd) | Apprentissage / outillage — non installé | Rendre les explications et tâches plus courtes, ordonnées et faciles à reprendre. |
| [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | Apprentissage / outillage — non installé | Cartographier les dépendances du code quand le projet grandira. |
| [cursor/plugins](https://github.com/cursor/plugins) | Apprentissage / outillage — non installé | Catalogue d'intégrations pour un environnement de développement. |
| [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills) | Apprentissage / outillage — non installé | Structurer une revue de littérature sur segmentation ou séries temporelles. |
| [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | Apprentissage / outillage — non installé | Grilles de relecture UX, données et architecture. |
| [obra/superpowers](https://github.com/obra/superpowers) | Apprentissage / outillage — non installé | Structurer spécifications, petites étapes et vérification des changements. |
| [petergyang/no-ai-slop](https://github.com/petergyang/no-ai-slop) | Apprentissage / outillage — non installé | Rendre les bilans plus précis et moins génériques. |
| [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) | Apprentissage / outillage — non installé | Mémoriser les décisions techniques et faciliter la reprise du développement. |
| [tech-leads-club/agent-skills](https://github.com/tech-leads-club/agent-skills) | Apprentissage / outillage — non installé | Trouver des méthodes de développement ciblées. |
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | Apprentissage / outillage — non installé | Produire une carte interactive pour comprendre l'architecture et les notions DIA. |
| [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) | Apprentissage / outillage — non installé | Transformer des notes de cours personnelles en aide à l'étude. |
| [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) | Alternative — non installé | Router les requêtes entre fournisseurs de modèles. |
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | Alternative — non installé | Exécuter un modèle local et apprendre quantification, mémoire et inférence. |
| [lfnovo/open-notebook](https://github.com/lfnovo/open-notebook) | Extension possible — non installé | Constituer une bibliothèque personnelle de documents et notes avec références. |
| [magnitudedev/magnitude](https://github.com/magnitudedev/magnitude) | Alternative — non installé | Explorer l'inférence locale adaptée au matériel. |
| [miuuyy/codex-chatgpt-web](https://github.com/miuuyy/codex-chatgpt-web) | Non retenu — non installé | Pont tiers entre un outil de développement et des modèles web. |
| [ollama/ollama](https://github.com/ollama/ollama) | Connecteur prévu ; modèle à configurer | Fournisseur local optionnel pour cette sélection de faits. |
| [Open-LLM-VTuber/Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) | Extension possible — non installé | Avatar vocal pour une démonstration interactive du projet. |
| [open-webui/open-webui](https://github.com/open-webui/open-webui) | Alternative — non installé | Discuter avec ses modèles et documents dans une interface compagnon. |
| [Tencent/WeKnora](https://github.com/Tencent/WeKnora) | Alternative — non installé | Construire une base de connaissances avec recherche documentaire. |
| [3b1b/manim](https://github.com/3b1b/manim) | Apprentissage / outillage — non installé | Expliquer visuellement une moyenne glissante, une rupture ou SHAP pour ta formation. |
| [Anil-matcha/Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) | Alternative — non installé | Explorer la création d'illustrations et vidéos de présentation. |
| [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | Alternative — non installé | Créer une identité visuelle ou des illustrations originales. |
| [catherpiee/meowmeowcatcam](https://github.com/catherpiee/meowmeowcatcam) | Apprentissage / outillage — non installé | Petit exercice pédagogique de reconnaissance de gestes. |
| [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) | Extension possible — non installé | Dicter un retour de séance ou écouter un résumé. |
| [FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg) | Extension possible — non installé | Préparer des vidéos sportives, extraire l'audio et générer des récapitulatifs. |
| [hacksider/Deep-Live-Cam](https://github.com/hacksider/Deep-Live-Cam) | Non retenu — non installé | Échange de visages sans bénéfice pour la préparation Ironman. |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Extension possible — non installé | Transformer un bilan HTML animé en vidéo partageable. |
| [obsproject/obs-studio](https://github.com/obsproject/obs-studio) | Apprentissage / outillage — non installé | Enregistrer des démonstrations, explications et ton portfolio. |
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | Alternative — non installé | Réaliser une vidéo hebdomadaire à partir de composants React. |
| [apache/echarts](https://github.com/apache/echarts) | Intégré | Courbes des mesures et affichage des contributions du modèle. |
| [clauderic/dnd-kit](https://github.com/clauderic/dnd-kit) | Intégré | Déplacement des séances entre créneaux du jour prescrit. |
| [lucide-icons/lucide](https://github.com/lucide-icons/lucide) | Intégré | Icônes cohérentes dans toute l’application. |
| [magicuidesign/magicui](https://github.com/magicuidesign/magicui) | Extension possible — non installé | Quelques animations ou cartes valorisant la progression. |
| [mermaid-js/mermaid](https://github.com/mermaid-js/mermaid) | Apprentissage / outillage — non installé | Comprendre et documenter le trajet des données et les composants. |
| [motiondivision/motion](https://github.com/motiondivision/motion) | Intégré | Transitions légères respectant la préférence de réduction des mouvements. |
| [mozilla/pdf.js](https://github.com/mozilla/pdf.js) | Extension possible — non installé | Afficher un plan PDF ou document de préparation dans l'app. |
| [mui/material-ui](https://github.com/mui/material-ui) | Alternative — non installé | Construire vite une interface React avec composants structurés. |
| [pmndrs/drei](https://github.com/pmndrs/drei) | Extension possible — non installé | Helpers pour une visualisation 3D de parcours ou d'équipement. |
| [pmndrs/react-three-fiber](https://github.com/pmndrs/react-three-fiber) | Extension possible — non installé | Rejouer un parcours ou comparer une scène sportive en 3D. |
| [radix-ui/primitives](https://github.com/radix-ui/primitives) | Intégré | Onglets et fenêtres de détail accessibles au clavier. |
| [react-hook-form/react-hook-form](https://github.com/react-hook-form/react-hook-form) | Intégré | Formulaires des contraintes de planning et retours. |
| [react/react](https://github.com/react/react) | Intégré | Interface en cinq écrans, composants et état réactif. |
| [recharts/recharts](https://github.com/recharts/recharts) | Alternative — non installé | Graphiques déclaratifs dans une interface React. |
| [resend/react-email](https://github.com/resend/react-email) | Extension possible — non installé | Mettre en forme un récapitulatif hebdomadaire par e-mail. |
| [shadcn-ui/ui](https://github.com/shadcn-ui/ui) | Alternative non installée | Radix et les composants SessionDNA couvrent ce besoin ; ne pas dupliquer le système de composants. |
| [TanStack/query](https://github.com/TanStack/query) | Intégré | Chargement, cache mémoire et actualisation des réponses du serveur. |
| [TanStack/table](https://github.com/TanStack/table) | Intégré | Tableau des activités avec colonnes et pagination. |
| [tldraw/tldraw](https://github.com/tldraw/tldraw) | Alternative — non installé | Tableau libre pour réfléchir à un cycle d'entraînement. |
| [transloadit/uppy](https://github.com/transloadit/uppy) | Extension possible — non installé | Importer FIT, ICS, JSON ou vidéo avec progression et messages clairs. |
| [ueberdosis/tiptap](https://github.com/ueberdosis/tiptap) | Extension possible — non installé | Journal de préparation enrichi avec listes et photos. |
| [xyflow/xyflow](https://github.com/xyflow/xyflow) | Extension possible — non installé | Éditeur visuel d'une séance: échauffement, répétitions et récupération. |
| [better-auth/better-auth](https://github.com/better-auth/better-auth) | Alternative — non installé | Gérer une authentification complète dans une architecture TypeScript. |
| [electric-sql/electric](https://github.com/electric-sql/electric) | Alternative — non installé | Répliquer une partie des données Postgres vers les clients. |
| [fastapi/fastapi](https://github.com/fastapi/fastapi) | Intégré | API locale pour les analyses, imports, bilans et sauvegardes. |
| [get-convex/convex-backend](https://github.com/get-convex/convex-backend) | Alternative — non installé | Backend réactif avec logique TypeScript et mise à jour des clients. |
| [liveblocks/liveblocks](https://github.com/liveblocks/liveblocks) | Alternative — non installé | Commentaires et collaboration en direct avec un coach. |
| [meilisearch/meilisearch](https://github.com/meilisearch/meilisearch) | Extension possible — non installé | Recherche rapide dans titres, retours et descriptions de séances. |
| [novuhq/novu](https://github.com/novuhq/novu) | Extension possible — non installé | Centraliser rappels et bilans sur plusieurs canaux. |
| [payloadcms/payload](https://github.com/payloadcms/payload) | Alternative — non installé | Administrer une bibliothèque d'exercices et contenus. |
| [pocketbase/pocketbase](https://github.com/pocketbase/pocketbase) | Alternative — non installé | Backend compact avec SQLite, utilisateurs et fichiers. |
| [supabase/supabase](https://github.com/supabase/supabase) | Alternative — non installé | Postgres, authentification et stockage si l'app devient multiutilisateur. |
| [tursodatabase/libsql](https://github.com/tursodatabase/libsql) | Alternative — non installé | Explorer SQLite distant et réplication embarquée. |
| [yjs/yjs](https://github.com/yjs/yjs) | Alternative — non installé | Fusionner des modifications de documents collaboratifs. |
| [D4Vinci/Scrapling](https://github.com/D4Vinci/Scrapling) | Extension possible — non installé | Extraire ponctuellement des horaires publics dans un format structuré. |
| [dagster-io/dagster](https://github.com/dagster-io/dagster) | Alternative — non installé | Suivre les dépendances FIT, tables, features et rapports comme des actifs. |
| [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) | Alternative — non installé | Convertir des pages publiques en documents exploitables pour les sources du bilan. |
| [inngest/inngest](https://github.com/inngest/inngest) | Alternative — non installé | Déclencher des étapes durables après import ou retour utilisateur. |
| [kedro-org/kedro](https://github.com/kedro-org/kedro) | Extension possible — non installé | Structurer le pipeline scientifique, les entrées et les sorties reproductibles. |
| [n8n-io/n8n](https://github.com/n8n-io/n8n) | Alternative — non installé | Automatiser visuellement import, bilan et notifications. |
| [PrefectHQ/prefect](https://github.com/PrefectHQ/prefect) | Extension possible — non installé | Voir ce qui a réussi, échoué et été repris dans l'actualisation. |
| [temporalio/sdk-python](https://github.com/temporalio/sdk-python) | Alternative — non installé | Garantir des workflows durables sur plusieurs services et longues durées. |
| [apache/arrow](https://github.com/apache/arrow) | Extension possible — non installé | Échanger des colonnes typées et produire des fichiers Parquet efficaces. |
| [apache/superset](https://github.com/apache/superset) | Alternative — non installé | Explorer les volumes et performances dans un outil BI distinct. |
| [ClickHouse/ClickHouse](https://github.com/ClickHouse/ClickHouse) | Non retenu — non installé | Analytique à grande échelle, loin de notre volume actuel. |
| [duckdb/duckdb](https://github.com/duckdb/duckdb) | Intégré | Agrégations par semaine et sport, export Parquet contrôlé. |
| [networkx/networkx](https://github.com/networkx/networkx) | Extension possible — non installé | Représenter dépendances, correspondances et contraintes sous forme de graphes. |
| [pola-rs/polars](https://github.com/pola-rs/polars) | Extension possible — non installé | Accélérer les transformations quand les mesures deviennent volumineuses. |
| [pydata/xarray](https://github.com/pydata/xarray) | Extension possible — non installé | Analyser des tableaux séance × intervalle × capteur alignés. |
| [streamlit/streamlit](https://github.com/streamlit/streamlit) | Extension possible — non installé | Créer un laboratoire de comparaison des détecteurs et modèles. |
| [blue-yonder/tsfresh](https://github.com/blue-yonder/tsfresh) | Extension possible — non installé | Extraire des caractéristiques temporelles au-delà des moyennes. |
| [confident-ai/deepeval](https://github.com/confident-ai/deepeval) | Extension possible — non installé | Tester qu'un bilan IA respecte les faits et n'invente pas une séance. |
| [deepcharles/ruptures](https://github.com/deepcharles/ruptures) | Intégré | Recherche de changements statistiques, en séparant pauses et trous. |
| [evidentlyai/evidently](https://github.com/evidentlyai/evidently) | Extension possible — non installé | Repérer changements de capteurs, données manquantes et dérive du modèle. |
| [feast-dev/feast](https://github.com/feast-dev/feast) | Non retenu — non installé | Feature store pour plusieurs équipes et usages production. |
| [google-research/timesfm](https://github.com/google-research/timesfm) | Apprentissage / outillage — non installé | Comparer un modèle préentraîné de séries à des prévisions simples. |
| [huggingface/transformers](https://github.com/huggingface/transformers) | Extension possible — non installé | Classifier des notes, tester embeddings ou transcription avec des modèles choisis. |
| [langfuse/langfuse](https://github.com/langfuse/langfuse) | Extension possible — non installé | Comprendre les appels IA, leurs coûts, durées et échecs. |
| [mlflow/mlflow](https://github.com/mlflow/mlflow) | Intégré | Copie locale de l’expérience gelée et de ses empreintes ; pas de réentraînement. |
| [py-why/dowhy](https://github.com/py-why/dowhy) | Apprentissage / outillage — non installé | Étudier pourquoi corrélation sommeil/performance ne signifie pas causalité. |
| [pymc-devs/pymc](https://github.com/pymc-devs/pymc) | Apprentissage / outillage — non installé | Apprendre les modèles bayésiens et exprimer l'incertitude personnelle. |
| [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn) | Existant conservé | Modèle de course et imputation existants conservés. |
| [shap/shap](https://github.com/shap/shap) | Intégré | Contributions des six variables à la sortie de la forêt existante ; additivité vérifiée. |
| [sktime/sktime](https://github.com/sktime/sktime) | Extension possible — non installé | Comparer classification directe des séries et modèles à caractéristiques. |
| [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels) | Extension possible — non installé | Régressions, tendances et diagnostics statistiques interprétables. |
| [CMU-Perceptual-Computing-Lab/openpose](https://github.com/CMU-Perceptual-Computing-Lab/openpose) | Alternative — non installé | Analyser des positions corporelles dans une vidéo sportive. |
| [deepinsight/insightface](https://github.com/deepinsight/insightface) | Non retenu — non installé | Reconnaissance faciale sans besoin pour SessionDNA. |
| [facebookresearch/segment-anything](https://github.com/facebookresearch/segment-anything) | Extension possible — non installé | Isoler un athlète ou du matériel dans des vidéos/images. |
| [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe) | Extension possible — non installé | Repérer des articulations et comparer des gestes sur tes vidéos. |
| [opencv/opencv](https://github.com/opencv/opencv) | Extension possible — non installé | Préparer la vidéo, suivre un objet et synchroniser des images. |
| [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | Extension possible — non installé | Lire une capture de séance, un tableau d'horaires ou un plan papier. |
| [ultralytics/ultralytics](https://github.com/ultralytics/ultralytics) | Alternative — non installé | Détection ou estimation de pose pour un laboratoire sportif. |
| [alicevision/Meshroom](https://github.com/alicevision/Meshroom) | Apprentissage / outillage — non installé | Explorer la reconstruction 3D d'un objet ou environnement. |
| [blender/blender](https://github.com/blender/blender) | Extension possible — non installé | Créer une animation de parcours, un avatar ou un visuel de présentation. |
| [CadQuery/cadquery](https://github.com/CadQuery/cadquery) | Apprentissage / outillage — non installé | Programmer un support de capteur ou une pièce de démonstration. |
| [FEniCS/dolfinx](https://github.com/FEniCS/dolfinx) | Apprentissage / outillage — non installé | Étudier les équations aux dérivées partielles et éléments finis. |
| [FreeCAD/FreeCAD](https://github.com/FreeCAD/FreeCAD) | Apprentissage / outillage — non installé | Concevoir un accessoire sportif paramétrique. |
| [godotengine/godot](https://github.com/godotengine/godot) | Apprentissage / outillage — non installé | Construire une simulation ou un jeu pédagogique sportif. |
| [google-deepmind/mujoco](https://github.com/google-deepmind/mujoco) | Apprentissage / outillage — non installé | Découvrir simulation physique et apprentissage par renforcement. |
| [huggingface/lerobot](https://github.com/huggingface/lerobot) | Apprentissage / outillage — non installé | Apprendre robotique et apprentissage par imitation. |
| [isl-org/Open3D](https://github.com/isl-org/Open3D) | Apprentissage / outillage — non installé | Traiter des nuages de points et données de profondeur. |
| [KiCad/kicad-source-mirror](https://github.com/KiCad/kicad-source-mirror) | Apprentissage / outillage — non installé | Créer un circuit ou prototype de capteur. |
| [nerfstudio-project/nerfstudio](https://github.com/nerfstudio-project/nerfstudio) | Apprentissage / outillage — non installé | Reconstruire une scène avec des représentations neuronales. |
| [pollen-robotics/microduck_rl](https://github.com/pollen-robotics/microduck_rl) | Apprentissage / outillage — non installé | Découvrir PPO et le contrôle d'un robot simulé. |
| [pyvista/pyvista](https://github.com/pyvista/pyvista) | Apprentissage / outillage — non installé | Visualiser des résultats scientifiques 3D en Python. |
| [ruvnet/RuView](https://github.com/ruvnet/RuView) | Non retenu — non installé | Sensing Wi-Fi présenté comme capable de détecter mouvements et signaux corporels. |
| [bilawalsidhu/gods-eye-view](https://github.com/bilawalsidhu/gods-eye-view) | Apprentissage / outillage — non installé | Inspiration pour une visualisation cartographique spectaculaire. |
| [cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect) | Existant conservé | Import incrémental avec la session locale et prévention des doublons. |
| [hudl/open-data](https://github.com/hudl/open-data) | Apprentissage / outillage — non installé | Projet complémentaire de data science du football avec données annotées. |
| [maplibre/maplibre-gl-js](https://github.com/maplibre/maplibre-gl-js) | Intégré | Tracé GPS chargé à la demande sur un fond neutre, sans fournisseur de tuiles. |
| [OpenDroneMap/ODM](https://github.com/OpenDroneMap/ODM) | Non retenu — non installé | Photogrammétrie de prises de vue aériennes. |
| [stravalib/stravalib](https://github.com/stravalib/stravalib) | Alternative — non installé | Éventuel second connecteur sportif via OAuth. |
| [Turfjs/turf](https://github.com/Turfjs/turf) | Intégré | Cadrage et longueur géométrique du tracé GPS affiché. |
| [alibaba/open-code-review](https://github.com/alibaba/open-code-review) | Apprentissage / outillage — non installé | Deuxième lecture automatisée des changements de code. |
| [astral-sh/ruff](https://github.com/astral-sh/ruff) | Intégré | Contrôles statiques ciblés sur les erreurs de code. |
| [astral-sh/uv](https://github.com/astral-sh/uv) | Intégré | Dépendances Python décrites dans pyproject.toml et verrouillées dans uv.lock. |
| [coollabsio/coolify](https://github.com/coollabsio/coolify) | Extension possible — non installé | Déployer l'application sur une machine disponible en permanence. |
| [getsentry/sentry](https://github.com/getsentry/sentry) | Extension possible — non installé | Repérer les erreurs frontend/API rencontrées sur iPhone. |
| [grafana/grafana](https://github.com/grafana/grafana) | Alternative — non installé | Afficher santé du pipeline, durées et erreurs de services. |
| [open-telemetry/opentelemetry-collector](https://github.com/open-telemetry/opentelemetry-collector) | Extension possible — non installé | Relier une importation à ses traces et métriques entre services. |
| [openstatusHQ/openstatus](https://github.com/openstatusHQ/openstatus) | Extension possible — non installé | Détecter une application indisponible quand elle tourne sur serveur permanent. |
| [PostHog/posthog](https://github.com/PostHog/posthog) | Alternative — non installé | Comprendre les parcours utilisateurs si l'app est utilisée par plusieurs personnes. |
| [Unleash/unleash](https://github.com/Unleash/unleash) | Extension possible — non installé | Activer progressivement un nouveau détecteur ou assistant. |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | Apprentissage / outillage — non installé | Relecture structurée des frontières d'accès et entrées de l'application. |
| [Hack-with-Github/Awesome-Hacking](https://github.com/Hack-with-Github/Awesome-Hacking) | Apprentissage / outillage — non installé | Découvrir la sécurité pour un futur projet de laboratoire. |
| [OWASP/CheatSheetSeries](https://github.com/OWASP/CheatSheetSeries) | Pratiques appliquées ; pas une bibliothèque | Principes appliqués : origine vérifiée, chemins bornés, taille limitée, imports validés. |
| [usestrix/strix](https://github.com/usestrix/strix) | Apprentissage / outillage — non installé | Tester la sécurité de notre application de démonstration. |
| [Z4nzu/hackingtool](https://github.com/Z4nzu/hackingtool) | Non retenu — non installé | Gros assortiment d'outils de sécurité sans besoin produit ciblé. |
| [appsmithorg/appsmith](https://github.com/appsmithorg/appsmith) | Alternative — non installé | Créer une administration interne des annotations et imports. |
| [immich-app/immich](https://github.com/immich-app/immich) | Extension possible — non installé | Bibliothèque personnelle de photos et vidéos de préparation. |
| [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) | Apprentissage / outillage — non installé | Valoriser le projet pour candidatures et entretiens. |
| [nexu-io/open-design](https://github.com/nexu-io/open-design) | Extension possible — non installé | Explorer plusieurs directions visuelles et maquettes avant développement. |
| [penpot/penpot](https://github.com/penpot/penpot) | Extension possible — non installé | Dessiner les écrans, composants et parcours utilisateur. |
| [syncthing/syncthing](https://github.com/syncthing/syncthing) | Alternative — non installé | Répliquer des exports ou sauvegardes entre ordinateurs. |
| [twentyhq/twenty](https://github.com/twentyhq/twenty) | Non retenu — non installé | CRM pour relations clients, hors besoin de préparation personnelle. |
| [asgeirtj/system_prompts_leaks](https://github.com/asgeirtj/system_prompts_leaks) | Non retenu — non installé | Collection de prompts attribués à des produits tiers. |
| [awesome-selfhosted/awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) | Apprentissage / outillage — non installé | Comparer des logiciels à héberger soi-même. |
| [codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) | Apprentissage / outillage — non installé | Comprendre les fondations en reconstruisant un petit composant. |
| [dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide) | Apprentissage / outillage — non installé | Apprendre prompts structurés, contexte et évaluation. |
| [donnemartin/system-design-primer](https://github.com/donnemartin/system-design-primer) | Apprentissage / outillage — non installé | Comprendre API, cache, stockage et compromis d'architecture. |
| [f/prompts.chat](https://github.com/f/prompts.chat) | Apprentissage / outillage — non installé | Trouver des formulations initiales pour résumés et explications. |
| [karpathy/nn-zero-to-hero](https://github.com/karpathy/nn-zero-to-hero) | Apprentissage / outillage — non installé | Comprendre concrètement réseaux neuronaux et rétropropagation. |
| [practical-tutorials/project-based-learning](https://github.com/practical-tutorials/project-based-learning) | Apprentissage / outillage — non installé | Choisir des exercices pratiques pour élargir tes compétences DIA. |
| [public-apis/public-apis](https://github.com/public-apis/public-apis) | Apprentissage / outillage — non installé | Repérer des API météo, transport ou calendrier potentielles. |
| [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | Apprentissage / outillage — non installé | Explorer des connecteurs après stabilisation de l'API. |
| [rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch) | Apprentissage / outillage — non installé | Comprendre tokens, attention, entraînement et adaptation de modèles. |
| [ripienaar/free-for-dev](https://github.com/ripienaar/free-for-dev) | Apprentissage / outillage — non installé | Comparer services et offres de démarrage. |
| [Shubhamsaboo/awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) | Apprentissage / outillage — non installé | Trouver des architectures de démonstration pour assistants et RAG. |
| [sindresorhus/awesome](https://github.com/sindresorhus/awesome) | Apprentissage / outillage — non installé | Explorer d'autres sujets de développement et data science. |
| [THU-MAIC/OpenMAIC](https://github.com/THU-MAIC/OpenMAIC) | Apprentissage / outillage — non installé | Explorer des environnements pédagogiques multiagents. |
| [trimstray/the-book-of-secret-knowledge](https://github.com/trimstray/the-book-of-secret-knowledge) | Apprentissage / outillage — non installé | Apprendre administration, outils et dépannage. |

## Comment reproduire l’intégration

Les dépendances Python sont dans `pyproject.toml` et `uv.lock` ; celles de l’interface dans `app/package.json` et `app/package-lock.json`. Elles se réinstallent avec les commandes du README. Il n’est pas nécessaire de cloner les 174 projets.

Les téléchargements Garmin restent locaux. Aucun agent autonome, compte cloud, fournisseur de cartes, service de surveillance ou transport en direct n’est activé par cette V2. Les codes sources des dépendances conservent leurs licences ; cette liste n’est pas une redistribution de leurs README.
