# Skill : React Frontend

Expert en frontend React pour le chatbot medical.

## Scope
Tout travail dans `frontend/`.

## Stack
React 18 + Vite + TailwindCSS (deja en place).

## Composants
- `ChatWindow.jsx` — Messages + streaming (existe)
- `MessageBubble.jsx` — Bulle de message (existe)
- `SourcePanel.jsx` — Citations sidebar expandable (existe)
- `ModelSelector.jsx` — Dropdown : BioMistral / Gemini / GPT-4o
- `ModeSelector.jsx` — Toggle : RAG local / Deep Search PubMed
- `App.jsx` — Integre les selecteurs, envoie via WebSocket

## Requete envoyee au backend
```json
{
  "question": "...",
  "model": "biomistral | gemini | gpt4o",
  "mode": "rag | deep_search"
}
```

## Regles
- WebSocket pour le streaming (deja en place)
- Axios pour les appels REST
- Respecter le style Tailwind existant
- Build multi-stage : npm build → nginx dans Docker
