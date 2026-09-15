import discord
from discord import app_commands
from groq import AsyncGroq
import asyncio
from duckduckgo_search import DDGS
import os
from flask import Flask
from threading import Thread
from supabase import create_client, Client

# === KONFIGURACE ===
DISCORD_TOKEN = "MTU0OTMxNjIyOTEzNzY5ODgzNg.GbwV-Z.vsPNab8u9EGNFMUNaHufz7KsHzrK0vuBJ76yhs"
GROQ_API_KEY = "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"
GUILD_ID = 1259045709659766874

# === SUPABASE KONFIGURACE ===
SUPABASE_URL = "https://ogzewuvlnqsbsegupntu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9nemV3dXZsbnFzYnNlZ3VwbnR1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk0NjEzNzcsImV4cCI6MjEwNTAzNzM3N30.1V8ZeIpqaVQTfGp5HJlKP280K5t7LJIAa9-vhgbEU78"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- ZMĚNA: Přesné instrukce na rozdělení textu ---
PRAVIDLA = "Odpovídej VÝHRADNĚ česky. ZAKÁZÁNO používat tabulky. TVŮJ VÝSTUP MUSÍ MÍT PŘESNĚ DVĚ ČÁSTI: 1. Nejprve napiš JEDNU údernou větu (shrnutí tvého postoje). 2. Poté VYNECH PRÁZDNÝ ŘÁDEK a pod ním detailně rozepiš své argumenty (max 2 odstavce)."

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        try:
            my_guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=my_guild)
            await self.tree.sync(guild=my_guild)
            print("✅ Slash příkazy byly úspěšně zsynchronizovány pro server!")
        except Exception as e:
            print(f"❌ Chyba při synchronizaci příkazů: {e}")

client = MyClient()
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# === DEFINICE AGENTŮ A POMOCNÉ FUNKCE ===
DEBATERS = [
    {"id": "designer", "name": "🎮 Herní Designér", "color": 0x3498db, "system": f"Jsi hlavní designér. Vyvíjíme hry v Robloxu. Zhodnoť nápad, hledej způsoby jak ho udělat zábavný. {PRAVIDLA}"},
    {"id": "tech", "name": "⚙️ Tech & Scope Lead", "color": 0xe74c3c, "system": f"Jsi pesimistický hlavní programátor v Luau. Jsme dvoučlenné nezávislé Roblox studio. Zkritizuj nápady z hlediska časové a technické náročnosti. Hledej bugy. {PRAVIDLA}"},
    {"id": "marketing", "name": "📈 Marketing & Robux Expert", "color": 0xf1c40f, "system": f"Jsi expert na Roblox algoritmus, retenci hráčů a monetizaci. Řešíš, jestli má hra virální potenciál (TikTok) a jak přirozeně prodávat Gamepassy. {PRAVIDLA}"},
    {"id": "player", "name": "🕹️ Zkušený Roblox Hráč", "color": 0x9b59b6, "system": f"Jsi ostřílený hráč Robloxu. Hodnotíš nápady čistě z pohledu hratelnosti (gameplaye), ovládání a zábavnosti. Porovnávej to s tím, co běžně na Robloxu funguje a jestli by tě to bavilo hrát s kamarády. {PRAVIDLA}"}
]

MODERATOR = {
    "id": "moderator",
    "name": "📋 Moderátor",
    "color": 0x2ecc71,
    "system": f"Jsi vedoucí projektu. Přečti celou debatu a udělej finální kompromis. ZAKÁZÁNO používat tabulky. Napiš 3 stručné odrážky (Schváleno, Zamítnuto, Další krok). Odpovídej VÝHRADNĚ česky."
}

def get_trends_sync():
    try:
        results = DDGS().text("current most popular Roblox game trends genres mechanics 2026", max_results=4)
        trend_text = ""
        for res in results:
            trend_text += f"- {res['body']}\n"
        return trend_text
    except Exception:
        return "Nepodařilo se načíst trendy (výpadek sítě)."

async def ask_agent(agent_system: str, conversation_history: str) -> str:
    try:
        response = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": agent_system},
                {"role": "user", "content": conversation_history}
            ],
            model="openai/gpt-oss-120b", 
            temperature=0.7,
            max_tokens=1000 
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Došlo k chybě: {e}"

def format_output(text: str) -> str:
    cisty_text = text.replace("###", "").strip()
    if "\n\n" in cisty_text:
        nadpis, zbytek = cisty_text.split("\n\n", 1)
    elif "\n" in cisty_text:
        nadpis, zbytek = cisty_text.split("\n", 1)
    else:
        nadpis = cisty_text
        zbytek = ""
    
    if zbytek:
        return f"### {nadpis.strip()}\n\n{zbytek.strip()}"
    return f"### {nadpis.strip()}"

# === POMOCNÁ FUNKCE PRO AUTOCOMPLETE PROJEKTŮ ===
async def project_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    response = supabase.table("projects").select("name").execute()
    projects = response.data if response.data else []
    return [
        app_commands.Choice(name=p["name"], value=p["name"])
        for p in projects if current.lower() in p["name"].lower()
    ]

# === DISCORD PŘÍKAZY ===

@client.tree.command(name="agent", description="Odešle dotaz vybranému členovi týmu.")
@app_commands.choices(jmeno=[
    app_commands.Choice(name="🎮 Herní Designér", value="designer"),
    app_commands.Choice(name="⚙️ Tech & Scope Lead", value="tech"),
    app_commands.Choice(name="📈 Marketing & Robux Expert", value="marketing"),
    app_commands.Choice(name="🕹️ Zkušený Roblox Hráč", value="player"),
    app_commands.Choice(name="📋 Moderátor", value="moderator")
])
async def agent_command(interaction: discord.Interaction, jmeno: str, dotaz: str):
    await interaction.response.defer()
    selected = MODERATOR if jmeno == "moderator" else next((a for a in DEBATERS if a["id"] == jmeno), DEBATERS[0])
    msg = await interaction.followup.send(f"💬 **{selected['name']}** přemýšlí nad tvým dotazem...", wait=True)
    ans = await ask_agent(selected["system"], dotaz)
    embed = discord.Embed(description=format_output(ans), color=selected["color"])
    embed.set_author(name=selected["name"])
    embed.add_field(name="Dotaz", value=dotaz, inline=False)
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="kanban_vytvor", description="Vytvoří novou vývojovou nástěnku (projekt/hru).")
async def kanban_vytvor(interaction: discord.Interaction, nazev_projektu: str):
    await interaction.response.defer()
    try:
        supabase.table("projects").insert({"name": nazev_projektu}).execute()
        await interaction.followup.send(f"🎉 Nová vývojová nástěnka **{nazev_projektu}** byla úspěšně vytvořena!")
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba: Nástěnka s tímto názvem pravděpodobně již existuje.")

@client.tree.command(name="kanban_seznam", description="Zobrazí seznam všech vytvořených nástěnek/projektů.")
async def kanban_seznam(interaction: discord.Interaction):
    await interaction.response.defer()
    response = supabase.table("projects").select("*").execute()
    projects = response.data
    if not projects:
        await interaction.followup.send("📭 Zatím nejsou vytvořené žádné nástěnky. Vytvoř ji příkazem `/kanban_vytvor`.")
        return
    
    seznam = [f"• **{p['name']}** (ID: `{p['id']}`)" for p in projects]
    embed = discord.Embed(title="📁 Seznam projektů a nástěnek", description="\n".join(seznam), color=0x3498db)
    await interaction.followup.send(embed=embed)

@client.tree.command(name="ukol_pridat", description="Přidá nový úkol do vybrané nástěnky.")
@app_commands.autocomplete(projekt=project_autocomplete)
@app_commands.choices(status=[
    app_commands.Choice(name="To-Do (K řešení)", value="todo"),
    app_commands.Choice(name="In Progress (Pracuje se)", value="in_progress")
])
async def ukol_pridat(interaction: discord.Interaction, projekt: str, nazev: str, status: str, prirazeno: str = "Tým"):
    await interaction.response.defer()
    proj_res = supabase.table("projects").select("id").eq("name", projekt).execute()
    if not proj_res.data:
        await interaction.followup.send(f"❌ Projekt '{projekt}' nebyl nalezen.")
        return
    
    project_id = proj_res.data[0]["id"]
    data = {"project_id": project_id, "title": nazev, "status": status, "assignee": prirazeno}
    supabase.table("tasks").insert(data).execute()
    
    embed = discord.Embed(title=f"✅ Úkol přidán do nástěnky: {projekt}", color=0x2ecc71)
    embed.add_field(name="Název", value=nazev, inline=False)
    embed.add_field(name="Stav", value=status, inline=True)
    embed.add_field(name="Pro", value=prirazeno, inline=True)
    await interaction.followup.send(embed=embed)

@client.tree.command(name="kanban", description="Zobrazí grafickou Kanban nástěnku pro vybraný projekt.")
@app_commands.autocomplete(projekt=project_autocomplete)
async def kanban(interaction: discord.Interaction, projekt: str):
    await interaction.response.defer()
    proj_res = supabase.table("projects").select("id").eq("name", projekt).execute()
    if not proj_res.data:
        await interaction.followup.send(f"❌ Projekt '{projekt}' nebyl nalezen.")
        return
    
    project_id = proj_res.data[0]["id"]
    response = supabase.table("tasks").select("*").eq("project_id", project_id).execute()
    tasks = response.data
    
    if not tasks:
        await interaction.followup.send(f"📭 Nástěnka pro projekt **{projekt}** je zatím prázdná!")
        return

    todo_list, in_progress_list, done_list = [], [], []
    for t in tasks:
        line = f"🆔 **`#{t['id']}`** | {t['title']} \n 👤 *{t['assignee']}*\n"
        if t['status'] == 'todo':
            todo_list.append(line)
        elif t['status'] == 'in_progress':
            in_progress_list.append(line)
        elif t['status'] == 'done':
            done_list.append(line)

    embed = discord.Embed(title=f"📋 DuoDumo Studio — {projekt}", description=f"Vývojová nástěnka pro projekt {projekt}.", color=0x9b59b6)
    embed.add_field(name="📌 To-Do", value="\n".join(todo_list) if todo_list else "*Žádné úkoly*", inline=False)
    embed.add_field(name="⏳ In Progress", value="\n".join(in_progress_list) if in_progress_list else "*Žádné úkoly*", inline=False)
    embed.add_field(name="✅ Done", value="\n".join(done_list) if done_list else "*Žádné úkoly*", inline=False)
    embed.set_footer(text="Pro změnu stavu použij příkaz /ukol_stav [id_ukolu] [novy_stav]")
    await interaction.followup.send(embed=embed)

@client.tree.command(name="ukol_stav", description="Změní stav úkolu podle jeho ID.")
@app_commands.choices(novy_stav=[
    app_commands.Choice(name="To-Do", value="todo"),
    app_commands.Choice(name="In Progress", value="in_progress"),
    app_commands.Choice(name="Done (Hotovo)", value="done")
])
async def ukol_stav(interaction: discord.Interaction, id_ukolu: int, novy_stav: str):
    await interaction.response.defer()
    supabase.table("tasks").update({"status": novy_stav}).eq("id", id_ukolu).execute()
    await interaction.followup.send(f"🔄 Úkol s ID `#{id_ukolu}` byl úspěšně přesunut do stavu: **{novy_stav}**!")

@client.tree.command(name="meeting", description="Zahájí poradu AI agentů (s možností zásahu člověka).")
async def meeting(interaction: discord.Interaction, napad: str):
    await interaction.response.send_message(f"🚀 **Zahajuji poradu nad nápadem:** {napad}\n*Zakládám vlákno a volám agenty...*", ephemeral=False)
    msg = await interaction.original_response()
    thread = await interaction.channel.create_thread(name=f"Porada: {napad[:15]}...", message=msg, auto_archive_duration=60)
    
    transcript = f"Téma porady: {napad}\n\n"
    is_first_message = True 
    
    for kolo in range(2):
        await thread.send(f"## 🔄 Začíná {kolo + 1}. kolo debaty")
        for agent in DEBATERS:
            async with thread.typing():
                if is_first_message:
                    await asyncio.sleep(2)
                    is_first_message = False
                else:
                    await asyncio.sleep(6)
                ai_response = await ask_agent(agent["system"], transcript)
                cisty_text = ai_response.replace("###", "").strip()
                transcript += f"V {kolo + 1}. kole {agent['name']} řekl: {cisty_text}\n\n"
                embed = discord.Embed(description=format_output(ai_response), color=agent["color"])
                embed.set_author(name=agent["name"])
                await thread.send(embed=embed)
            await asyncio.sleep(3)

        if kolo == 0:
            await thread.send("👤 **Tvůj tah!** Napiš sem svůj komentář nebo nový nápad. *(Pro přeskočení napiš `dál`)*.\n⏳ *Máš 5 minut.*")
            def check(m):
                return m.channel == thread and not m.author.bot
            try:
                user_msg = await client.wait_for('message', check=check, timeout=300.0) 
                if user_msg.content.lower().strip() != 'dál':
                    transcript += f"Lidský šéf zasahuje do debaty: {user_msg.content}\n\n"
                    await thread.send("✅ *Komentář zaznamenán...*")
                else:
                    await thread.send("▶️ *Pokračujeme rovnou do dalšího kola.*")
            except asyncio.TimeoutError:
                await thread.send("⏳ *Čas vypršel, pokračujeme automaticky.*")

    await thread.send(f"## 📋 Závěrečné slovo Moderátora")
    async with thread.typing():
        await asyncio.sleep(6)
        ai_response = await ask_agent(MODERATOR["system"], transcript)
        embed = discord.Embed(description=format_output(ai_response), color=MODERATOR["color"])
        embed.set_author(name=MODERATOR["name"])
        await thread.send(embed=embed)
    
    await interaction.channel.send(f"✅ Porada u konce! Závěr najdete ve vlákně: {thread.mention}")

@client.tree.command(name="mvp", description="Oseká obří nápad na absolutní minimum.")
async def mvp(interaction: discord.Interaction, napad: str):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"🔪 **Řežeme nápad na dřeň:** {napad}\n*Tech Lead a Hráč přemýšlí...*", wait=True)
    tech, player = DEBATERS[1], DEBATERS[3]
    tech_ans = await ask_agent(tech["system"] + " Zredukuj na MVP pro 2 lidi na víkend.", napad)
    player_ans = await ask_agent(player["system"] + " Napiš klíčovou mechaniku pro zábavu.", napad)
    embed1 = discord.Embed(description=format_output(tech_ans), color=tech["color"]).set_author(name=tech["name"])
    embed2 = discord.Embed(description=format_output(player_ans), color=player["color"]).set_author(name=player["name"])
    await msg.edit(content=f"🔪 **MVP pro nápad:** {napad}", embeds=[embed1, embed2])

@client.tree.command(name="sprint", description="Rozdělí cíl na To-Do list.")
async def sprint(interaction: discord.Interaction, cil: str):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"🏃 **Plánování sprintu pro:** {cil}", wait=True)
    ans = await ask_agent(MODERATOR["system"] + " Rozpadni cíl na To-Do list v odrážkách.", cil)
    embed = discord.Embed(description=format_output(ans), color=MODERATOR["color"]).set_author(name=MODERATOR["name"])
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="roast", description="Seřve vás za prokrastinaci.")
async def roast(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = await interaction.followup.send("🔥 *Tech Lead si bere slovo...*", wait=True)
    ans = await ask_agent("Jsi drsný programátor. Seřvi tým za hraní her místo kódování.", "Seřvi nás!")
    embed = discord.Embed(description=format_output(ans), color=DEBATERS[1]["color"]).set_author(name=DEBATERS[1]["name"])
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="trendy", description="Analyzuje Roblox trendy.")
async def trendy(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = await interaction.followup.send("🔎 *Hledám trendy...*", wait=True)
    data = await asyncio.to_thread(get_trends_sync)
    ans = await ask_agent("Jsi expert na Roblox trendy.", f"Data: {data}")
    embed = discord.Embed(description=format_output(ans), color=0xf1c40f).set_author(name="📈 Trend Expert")
    await msg.edit(content=None, embed=embed)

# === WEBSERVER PRO RENDER ===
app = Flask('')
@app.route('/')
def home():
    return "DumoAI bot bezi 24/7!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

Thread(target=run).start()
client.run(DISCORD_TOKEN)