# Arcigy Website Automation

Tento priečinok obsahuje kompletnú logiku pre automatizáciu Arcigy webstránky, vrátane chatbota, rezervačného systému a emailových notifikácií.

## Štruktúra priečinkov

- **backend/**: Obsahuje Python skripty (FastAPI server, AI logika).
  - `main_router.py`: Hlavný vstupný bod servera. Definuje API endpointy.
  - `tony_backend.py`: Logika pre AI chatbota (Tony), napojená na OpenAI a Supabase.
  - `calendar_engine.py`: Integrácia s Cal.com pre overovanie dostupnosti a vytváranie rezervácií.
  - `utils/email_engine.py`: Modul pre posielanie transakčných emailov.
- **assets/**: Statické súbory (obrázky), ktoré sa používajú v emailoch (napr. pozadie).
- **templates/**: HTML šablóny pre emaily (napr. `premium_email.html`).

## Ako spustiť backend

Pre spustenie servera používajte nasledujúci príkaz z koreňového priečinka (`Agentic Workflows`):

```bash
python cloud_automations/Arcigy_website/backend/main_router.py
```

Server beží na porte **8001** (default).

## Funkcionalita

1.  **AI Chatbot (Tony):**
    - Prijíma správy cez `/webhook/chat`.
    - Používa prompt definovaný v `directives/tony_prompt.md`.
    - Ukladá históriu konverzácií do Supabase.

2.  **Rezervácie (Cal.com):**
    - `/webhook/calendar-availability-check`: Zistí voľné termíny.
    - `/webhook/confirm`: Vytvorí rezerváciu v Cal.com a odošle potvrdzovací email.

3.  **Emaily:**
    - Používa šablónu z `templates/premium_email.html`.
    - Obrázky sa načítavajú z `assets/`.
    - Pri odosielaní sa automaticky vložia údaje (meno, čas, link).

## Úpravy

- **Zmena emailu:** Upravte `templates/premium_email.html`. Pozor na Mobile Responsive logiku ("Ghost Table").
- **Zmena AI správania:** Upravte súbor `directives/tony_prompt.md` v hlavnom priečinku.
- **Konfigurácia:** Všetky API kľúče sú v súbore `.env` v koreňovom priečinku.

## Dôležité poznámky

- Frontend (HTML/JS webstránky) komunikuje s týmito endpointmi. Zmena URL endpointov vyžaduje zmenu v `chatbot.js` alebo `calendar.js` na webe.
