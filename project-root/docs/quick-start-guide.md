# Getting started with HBntory

This guide walks you through installing and running HBntory from scratch, step by step. No prior knowledge of the project is assumed.

The project runs as **5 separate services**, each in its own terminal window. Follow the steps in order.

---

## 0. Prerequisites

- **Python 3.12** installed (`python3 --version` to check)
- **Git** installed
- A terminal (macOS Terminal, Linux shell, or WSL/Git Bash on Windows)

---

## 1. Clone the project

```bash
git clone https://github.com/Souf-F/HBntory-Inventor-Management-Platform.git
cd HBntory-Inventor-Management-Platform
```

---

## 2. Create and activate a virtual environment

A virtual environment keeps this project's Python packages separate from the rest of your system.

```bash
python3 -m venv .venv
```

Activate it (you'll need to do this again every time you open a new terminal for this project):

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Windows (Git Bash):**
```bash
source .venv/Scripts/activate
```

You'll know it worked if your terminal prompt now starts with `(.venv)`.

> **If `python3 -m venv .venv` fails** with something like `ensurepip is not available`, install the venv package for your system first, e.g. on Ubuntu/Debian: `sudo apt install python3-venv`, then retry.

---

## 3. Install dependencies

With the virtual environment active, install each service's requirements:

```bash
cd project-root/backoffice
pip install -r requirements.txt

cd ../product_mcp_server
pip install -r requirements.txt

cd ../ai_service
pip install -r requirements.txt

cd ../..
```

> **If you see `error: externally-managed-environment`**, add `--break-system-packages` to each `pip install` command above. This happens on some Linux systems (like recent Ubuntu) that block installing packages outside a virtual environment. If you already created and activated the venv in step 2, this shouldn't happen — double check the `(.venv)` prefix is showing in your prompt.

> **If `pip` says a package failed to build**, make sure you're using Python 3.12 (`python3 --version`). Older or much newer versions can fail on some dependencies.

---

## 4. Set up the AI Service API key

The AI assistant needs a free Groq API key to work. The rest of the app (Backoffice, stock management) works fine without it.

```bash
cd project-root/ai_service
cp .env.example .env
```

Open the new `.env` file in a text editor and paste your Groq API key:

```
GROQ_API_KEY=your-key-here
```

Get a free key at [console.groq.com](https://console.groq.com) if you don't have one.

```bash
cd ../..
```

> **If you skip this step**, everything except the AI chat assistant will still work. The public chat page will just show an error when you ask it a question.

---

## 5. Initialize the database

This creates the database file and fills it with test accounts and sample stock data.

```bash
cd project-root/backoffice
python3 -m app.seed
cd ../..
```

You should see:
```
Database seeded: 3 branches, 1 admin, 3 common users, 25 stock rows.
```

> **If you see `Database already seeded — skipping.`**, that's fine — it means the database already exists. To start fresh, delete the file first: `rm project-root/backoffice/hbntory.db`, then run the seed command again.
>
> **If you get an import error** (something like `ImportError: attempted relative import`), you ran the command from the wrong folder, or ran `python3 app/seed.py` directly instead of `python3 -m app.seed`. Go back to `project-root/backoffice/` and use the exact command above.

---

## 6. Start the 5 services

Open **5 separate terminal windows or tabs**. In each one, activate the virtual environment first (`source .venv/bin/activate` from the project root), then run the matching command below.

### Terminal 1 — Product API (port 5001)

```bash
cd project-root/hbntory-products-api
export HBN_PRODUCTS_PORT=5001
python3 app.py
```

### Terminal 2 — MCP Server (port 8000)

```bash
cd project-root/product_mcp_server
python3 server.py
```

### Terminal 3 — AI Query Service (port 8100)

```bash
cd project-root/ai_service
python3 app.py
```

> **If this fails with `ModuleNotFoundError: No module named 'groq'`**, go back to step 3 and make sure `pip install -r requirements.txt` completed successfully in this folder.

### Terminal 4 — Backoffice (port 5000)

```bash
cd project-root/backoffice
python3 run.py
```

### Terminal 5 — Static frontends (port 5502)

```bash
cd project-root
python3 -m http.server 5502
```

> **Don't use "Live Server" or any tool with auto-reload for this step.** Auto-reload tools can wrongly detect the database file changing and reload the whole page, which looks like a random logout. A plain static server avoids this.

---

## 7. Open the app

- **Backoffice** (login required): [http://127.0.0.1:5502/admin/](http://127.0.0.1:5502/admin/)
- **Public site** (chat + catalog, no login): [http://127.0.0.1:5502/client_web/](http://127.0.0.1:5502/client_web/)

### Test accounts

| Username | Password | Role | Branch |
|---|---|---|---|
| `admin` | `ChangeMe123!` | Admin | — |
| `employee1` | `ChangeMe123!` | Common user | HBntory Paris |
| `employee2` | `ChangeMe123!` | Common user | HBntory Lyon |
| `employee3` | `ChangeMe123!` | Common user | HBntory Marseille |

---

## Common problems

**"Address already in use" when starting a service**
Something is already running on that port. Either you already have that service open in another terminal, or a previous run didn't close properly. Find and stop it:
```bash
lsof -ti:5000 | xargs kill -9
```
(Replace `5000` with the port that's stuck.)

**Login fails with no visible error, or the page looks broken after login**
Open your browser's developer console (F12 → Console tab) and look for a CORS error. If you're serving the frontend on a different port than 5502, that port needs to be added to the allowed origins in `project-root/backoffice/app/__init__.py`.

**The chat assistant says "technical problem" or "rate limit reached"**
This is the free Groq API being temporarily overloaded or rate-limited, not a bug in the app. Wait a minute and try again.

**The page keeps logging you out unexpectedly**
Make sure Terminal 5 is a plain `python3 -m http.server`, not a live-reload tool (see the warning in step 6).

**Everything looks empty / no branches or stock show up**
The database might be out of date. Reset it:
```bash
cd project-root/backoffice
rm hbntory.db
python3 -m app.seed
```
Then restart Terminal 4 (Backoffice) and Terminal 2 (MCP Server).