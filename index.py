import asyncio
import json
import os

from aiohttp import web
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Charge le fichier .env en local (sur Render, les variables viennent de l'onglet Environment)
load_dotenv()


# --- 1. SERVEUR WEB POUR RENDER & UPTIMEROBOT ---
async def handle_ping(request):
    """Repond aux pings de UptimeRobot."""
    return web.Response(text="HLR Protect est en ligne !", status=200)


async def start_web_server():
    """Demarre le serveur web aiohttp sur le port fourni par Render (PORT)."""
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 3000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Serveur Web démarré sur le port {port} (Prêt pour UptimeRobot)")


# --- 2. CONFIGURATION ET INTENTS ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix=config["prefix"], intents=intents)
bot.config = config


# --- 3. ON_READY & STATUT STREAMING ---
@bot.event
async def on_ready():
    print(f"✅ Bot de sécurité en ligne : {bot.user} (ID: {bot.user.id})")

    activity = discord.Streaming(
        name="Développé par Heloria",
        url="https://www.twitch.tv/heloriaesport",
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)


# --- 4. LANCEMENT ---
async def main():
    # Le token vient UNIQUEMENT de la variable d'environnement DISCORD_TOKEN
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN manquant : ajoute-le dans .env (local) "
            "ou dans Environment (Render)."
        )

    await start_web_server()

    async with bot:
        # Chargement automatique des modules dans ./modules
        if os.path.exists("./modules"):
            for file in os.listdir("./modules"):
                if file.endswith(".py") and not file.startswith("_"):
                    module_name = file[:-3]
                    try:
                        await bot.load_extension(f"modules.{module_name}")
                        print(f"📦 Module chargé : {module_name}")
                    except Exception as e:
                        print(f"❌ Échec du chargement du module {module_name} : {e}")

        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())