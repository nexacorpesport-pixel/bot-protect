import asyncio
import json
import os
from aiohttp import web
import discord
from discord.ext import commands

# --- 1. CONFIGURATION DU SERVEUR WEB POUR RENDER & UPTIME ROBOT ---
async def handle_ping(request):
    """Répond aux pings de UptimeRobot sur le port 3000."""
    return web.Response(text="HLR Protect est en ligne !", status=200)


async def start_web_server():
    """Démarre le serveur web aiohttp sur le port 3000."""
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()

    # Render définit automatiquement une variable d'environnement PORT, sinon 3000 par défaut
    port = int(os.environ.get("PORT", 3000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Serveur Web démarré sur le port {port} (Prêt pour UptimeRobot)")


# --- 2. CHARGEMENT CONFIGURATION ET INTENTS ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix=config["prefix"], intents=intents)
bot.config = config


# --- 3. ÉVÉNEMENT ON_READY & STATUT TWITCH (STREAMING) ---
@bot.event
async def on_ready():
    print(f"✅ Bot de sécurité en ligne : {bot.user} (ID: {bot.user.id})")

    # Statut "En direct sur Twitch"
    # Remplace TON_NOM_TWITCH par le nom de ta chaîne Twitch
    activity = discord.Streaming(
        name="Développé par Heloria",
        url="https://www.twitch.tv/heloriaesport",
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)


# --- 4. ÉXÉCUTION DU BOT ET DU SERVEUR WEB ---
async def main():
    # Lancement du serveur Web en arrière-plan
    await start_web_server()

    async with bot:
        # Chargement automatique de tous les modules dans ./modules (antispam, logs, etc.)
        if os.path.exists("./modules"):
            for file in os.listdir("./modules"):
                if file.endswith(".py"):
                    module_name = file[:-3]
                    await bot.load_extension(f"modules.{module_name}")
                    print(f"📦 Module chargé : {module_name}")

        await bot.start(config["token"])


if __name__ == "__main__":
    asyncio.run(main())