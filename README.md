# DumoAI

A Discord bot that acts as a small AI game-studio team for Roblox developers. Ask a virtual game designer, tech lead, marketer or veteran player for feedback, run AI-moderated team meetings, and track your tasks on a built-in Kanban board.

## Features

- **AI team members** – five personas, each with its own role and colour:
  - 🎮 Game Designer
  - ⚙️ Tech & Scope Lead
  - 📈 Marketing & Robux Expert
  - 🕹️ Experienced Roblox Player
  - 📋 Moderator
- **Kanban boards** – create multiple projects, add tasks, move them between *To-Do*, *In Progress* and *Done*, and view the board as a Discord embed. Data is stored in Supabase.
- **Idea tools** – cut a huge idea down to an MVP, split a goal into a sprint To-Do list, or get roasted for procrastinating.
- **Roblox trends** – web-searched trend analysis (DuckDuckGo) summarised by the AI.

## Slash commands

| Command | What it does |
|---|---|
| `/agent` | Send a question to a chosen team member |
| `/meeting` | Start a debate between the AI agents; you can jump in |
| `/mvp` | Reduce a big idea to the absolute minimum |
| `/sprint` | Turn a goal into a To-Do list |
| `/roast` | Get yelled at for procrastinating |
| `/trendy` | Analyse current Roblox trends |
| `/kanban_vytvor` | Create a new board / project |
| `/kanban_seznam` | List all boards |
| `/ukol_pridat` | Add a task to a board |
| `/ukol_stav` | Change a task's status by ID |
| `/kanban` | Show the board for a project |

## Tech stack

Python · [discord.py](https://discordpy.readthedocs.io/) · [Groq](https://groq.com/) (`openai/gpt-oss-120b`) · [Supabase](https://supabase.com/) · DuckDuckGo Search · Flask (keep-alive web server for hosting)

## Setup

1. Install Python 3.10+ and the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create:
   - a Discord application and bot token ([Developer Portal](https://discord.com/developers/applications)),
   - a Groq API key,
   - a Supabase project with the Kanban tables the bot queries (e.g. `projects`).
3. Put your `DISCORD_TOKEN`, `GROQ_API_KEY`, `SUPABASE_URL` and `SUPABASE_KEY` in the configuration section at the top of `bot.py`.
   **Never commit real keys** – prefer loading them from environment variables.
4. Run the bot:
   ```bash
   python bot.py
   ```

The Flask server listens on `$PORT` (default `10000`), so the bot can be hosted on services that expect a web process.

## Status

Work in progress – built as a helper for a small Roblox dev team.
