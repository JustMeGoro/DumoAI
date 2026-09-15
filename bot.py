import discord
from discord import app_commands
from groq import AsyncGroq
import asyncio
from duckduckgo_search import DDGS
import os
from flask import Flask
from threading import Thread

# === KONFIGURACE ===
DISCORD_TOKEN = "MTU0OTMxNjIyOTEzNzY5ODgzNg.GbwV-Z.vsPNab8u9EGNFMUNaHufz7KsHzrK0vuBJ76yhs"
GROQ_API_KEY = "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"
GUILD_ID = 1259045709659766874


# --- ZMĚNA: Přesné instrukce na rozdělení textu ---
PRAVIDLA = "Odpovídej VÝHRADNĚ česky. ZAKÁZÁNO používat tabulky. TVŮJ VÝSTUP MUSÍ MÍT PŘESNĚ DVĚ ČÁSTI: 1. Nejprve napiš JEDNU údernou větu (shrnutí tvého postoje). 2. Poté VYNECH PRÁZDNÝ ŘÁDEK a pod ním detailně rozepiš své argumenty (max 2 odstavce)."

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        my_guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=my_guild)
        await self.tree.sync(guild=my_guild)

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

# === DISCORD PŘÍKAZY ===

@client.tree.command(name="agent", description="Odešle dotaz vybranému členovi týmu (designer, tech, marketing, player, moderator).")
@app_commands.choices(jmeno=[
    app_commands.Choice(name="🎮 Herní Designér", value="designer"),
    app_commands.Choice(name="⚙️ Tech & Scope Lead", value="tech"),
    app_commands.Choice(name="📈 Marketing & Robux Expert", value="marketing"),
    app_commands.Choice(name="🕹️ Zkušený Roblox Hráč", value="player"),
    app_commands.Choice(name="📋 Moderátor", value="moderator")
])
async def agent_command(interaction: discord.Interaction, jmeno: str, dotaz: str):
    await interaction.response.defer()
    
    # Vybereme správného agenta podle volby
    if jmeno == "moderator":
        selected = MODERATOR
    else:
        selected = next((a for a in DEBATERS if a["id"] == jmeno), DEBATERS[0])
    
    msg = await interaction.followup.send(f"💬 **{selected['name']}** přemýšlí nad tvým dotazem...", wait=True)
    
    ans = await ask_agent(selected["system"], dotaz)
    
    embed = discord.Embed(description=format_output(ans), color=selected["color"])
    embed.set_author(name=selected["name"])
    embed.add_field(name="Dotaz", value=dotaz, inline=False)
    
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="mvp", description="Oseká obří nápad na absolutní minimum (Minimum Viable Product).")
async def mvp(interaction: discord.Interaction, napad: str):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"🔪 **Řežeme nápad na dřeň:** {napad}\n*Tech Lead a Hráč přemýšlí...*", wait=True)
    tech = DEBATERS[1]
    player = DEBATERS[3]
    tech_sys = tech["system"] + " SPECIFICKÝ ÚKOL PRO TEĎ: Zredukuj tento nápad na absolutní minimum (MVP) pro dvoučlenný tým. Vyškrtej všechny složitosti a nech jen to, co se dá nakódit za víkend."
    player_sys = player["system"] + " SPECIFICKÝ ÚKOL PRO TEĎ: Napiš, jaká JEDNA jediná mechanika musí v tomto ořezaném MVP perfektně fungovat, aby to byla zábava a hráči to hned nevypli."
    tech_ans = await ask_agent(tech_sys, napad)
    player_ans = await ask_agent(player_sys, napad)
    embed1 = discord.Embed(description=format_output(tech_ans), color=tech["color"])
    embed1.set_author(name=tech["name"])
    embed2 = discord.Embed(description=format_output(player_ans), color=player["color"])
    embed2.set_author(name=player["name"])
    await msg.edit(content=f"🔪 **MVP pro nápad:** {napad}", embeds=[embed1, embed2])

@client.tree.command(name="sprint", description="Rozdělí schválený nápad nebo cíl na To-Do list.")
async def sprint(interaction: discord.Interaction, cil: str):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"🏃 **Plánování sprintu pro:** {cil}\n*Moderátor připravuje úkoly...*", wait=True)
    sys = MODERATOR["system"] + " SPECIFICKÝ ÚKOL PRO TEĎ: Rozpadni tento cíl na konkrétní odškrtávací To-Do list pro 2členný indie tým (kódování a design). Napiš to v odrážkách a buď velmi konkrétní."
    ans = await ask_agent(sys, cil)
    embed = discord.Embed(description=format_output(ans), color=MODERATOR["color"])
    embed.set_author(name=MODERATOR["name"])
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="lore", description="Vygeneruje názvy, texty nebo herní lore pro dané téma.")
async def lore(interaction: discord.Interaction, tema: str):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"✍️ **Tvorba obsahu pro:** {tema}\n*Designér píše...*", wait=True)
    designer = DEBATERS[0]
    sys = designer["system"] + " SPECIFICKÝ ÚKOL PRO TEĎ: Vygeneruj kreativní herní texty, názvy předmětů nebo lore pozadí pro zadané téma. Vypiš to v přehledném seznamu jako odrážky, ať se to dá hned použít ve hře."
    ans = await ask_agent(sys, tema)
    embed = discord.Embed(description=format_output(ans), color=designer["color"])
    embed.set_author(name=designer["name"])
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="monetizace", description="Navrhne způsoby zpeněžení bez Pay-to-Win prvků.")
async def monetizace(interaction: discord.Interaction, napad: str):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"💰 **Monetizační strategie pro:** {napad}\n*Markeťák počítá Robuxy...*", wait=True)
    marketing = DEBATERS[2]
    sys = marketing["system"] + " SPECIFICKÝ ÚKOL PRO TEĎ: Navrhni 2-3 konkrétní způsoby, jak tento prvek/hru zpeněžit v Robloxu (Gamepassy, kosmetika atd.), ale přísně se vyhni Pay-to-Win. Napiš to v odrážkách."
    ans = await ask_agent(sys, napad)
    embed = discord.Embed(description=format_output(ans), color=marketing["color"])
    embed.set_author(name=marketing["name"])
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="roast", description="Slouží jako bič proti prokrastinaci. Vynadá vám.")
async def roast(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = await interaction.followup.send("🔥 *Tech Lead si bere slovo...*", wait=True)
    tech = DEBATERS[1]
    sys = "Jsi drsný, uštěpačný hlavní programátor. Tvůj dvoučlenný vývojářský tým zase prokrastinuje a hraje Counter-Strike 2 nebo Gran Turismo 7, místo aby psali kód v Luau pro vaši novou hru. Brutálně, sarkasticky a vtipně je seřvi a pošli je makat. PRAVIDLA: Odpovídej VÝHRADNĚ česky. Napiš JEDNU velkou nadpisovou větu a pod ní jeden odstavec výtek."
    ans = await ask_agent(sys, "Seřvi nás za to, že nehrajeme a neděláme na hře!")
    embed = discord.Embed(description=format_output(ans), color=tech["color"])
    embed.set_author(name=tech["name"])
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="trendy", description="Analyzuje aktuální Roblox trendy pro váš brainstorming.")
async def trendy(interaction: discord.Interaction):
    await interaction.response.defer()
    msg = await interaction.followup.send("🔎 *Marketingový expert prohledává internet a analyzuje aktuální Roblox trendy...*", wait=True)
    trendy_z_internetu = await asyncio.to_thread(get_trends_sync)
    system_prompt = "Jsi expert na Roblox algoritmus a herní trendy. Přečti si následující čerstvá data a vytvoř pro vývojářský tým stručný report o tom, jaké žánry teď frčí a jaké mechaniky v nich fungují. Odpovídej VÝHRADNĚ česky. Použij formát: Jedna úderná věta na začátek a pod to 2 stručné odstavce."
    user_prompt = f"Aktuální data z vyhledávače:\n{trendy_z_internetu}"
    ans = await ask_agent(system_prompt, user_prompt)
    embed = discord.Embed(description=format_output(ans), color=0xf1c40f)
    embed.set_author(name="📈 Marketing & Robux Expert (Analýza Trendů)")
    await msg.edit(content=None, embed=embed)

@client.tree.command(name="meeting", description="Zahájí poradu AI agentů (s možností zásahu člověka).")
async def meeting(interaction: discord.Interaction, napad: str):
    await interaction.response.defer()
    msg = await interaction.followup.send(f"🚀 **Zahajuji poradu nad nápadem:** {napad}", wait=True)
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
                    transcript += f"Lidský šéf (Adrian) zasahuje do debaty: {user_msg.content}\n\n"
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

# === NASTAVENÍ FALEŠNÉHO WEBSERVERU PRO RENDER ===
app = Flask('')

@app.route('/')
def home():
    return "DumoAI bot bezi 24/7 na Renderu!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()
client.run(DISCORD_TOKEN)