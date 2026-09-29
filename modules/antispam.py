import discord
from discord.ext import commands, tasks
import datetime
import re
import unicodedata
from collections import defaultdict, deque
from difflib import SequenceMatcher

DISCORD_INVITE_REGEX = re.compile(
    r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9]+",
    re.IGNORECASE,
)

EMOJI_REGEX = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>|[\U00010000-\U0010ffff]")

CRYPTO_SCAM_KEYWORDS = [
    "airdrop", "freenitro", "cryptogift", "claimnow", "ethgiveaway",
    "btcgiveaway", "binancepromo", "solanaairdrop", "bonuspool",
    "connectwallet", "claimyour", "freeusdt", "doubler",
    "distributionevent", "steamgift", "giftcard", "whitelistspot", "mintlive",
]

# IDs des roles autorises a utiliser des applications externes / commandes.
# ATTENTION : ce doivent etre des IDs de ROLES (clic droit sur le role dans
# Parametres du serveur > Roles > Copier l'identifiant, mode developpeur active).
ALLOWED_ROLE_IDS = {
    1532015052511514686,
    1532014988426875031,
    1523475520447053934,
    1522733508370628618,
    1532019022928023633,
    1208405611658739784,
}


def normalize_text(text: str) -> str:
    nfkd_form = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd_form if not unicodedata.combining(c))
    return unicodedata.normalize("NFKC", no_accents)


def strip_punctuation(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()


async def safe_delete(message: discord.Message):
    try:
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass


async def temp_warn(channel, text: str):
    try:
        warn = await channel.send(text)
        await warn.delete(delay=5)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        pass


class AntiSpamHoneypot(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.user_messages = defaultdict(list)
        self.user_history = defaultdict(lambda: deque(maxlen=5))
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    @tasks.loop(hours=1.0)
    async def cleanup_task(self):
        now = datetime.datetime.now(datetime.timezone.utc)

        to_delete = []
        for user_id, timestamps in self.user_messages.items():
            valid = [t for t in timestamps if (now - t).total_seconds() < 10]
            if not valid:
                to_delete.append(user_id)
            else:
                self.user_messages[user_id] = valid
        for uid in to_delete:
            del self.user_messages[uid]

        for uid in [u for u, h in self.user_history.items() if not h]:
            del self.user_history[uid]

    async def get_log_channel(self, guild, key):
        channel_name = self.bot.config.get("logs", {}).get(key)
        if not channel_name:
            return None
        return discord.utils.get(guild.text_channels, name=channel_name)

    async def check_authorization(self, guild: discord.Guild, user_id: int):
        """
        Verifie si l'utilisateur a un role autorise.
        Retourne (autorise: bool, raison: str).

        CORRECTION : guild.get_member() renvoie None si le membre n'est pas en
        cache (intent Members manquant, cache incomplet...). Avant, cela
        equivalait a "non autorise". On fait maintenant un fetch_member en
        secours pour interroger directement l'API Discord.
        """
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                return False, "Membre introuvable sur le serveur."
            except discord.HTTPException:
                return False, "Erreur API lors de la recuperation du membre."

        member_role_ids = {r.id for r in member.roles}
        if member_role_ids & ALLOWED_ROLE_IDS:
            return True, ""
        return False, "Aucun role autorise."

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.id == self.bot.user.id:
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        author = message.author
        author_id = author.id

        # ---------------------------------------------------------
        # 0. CONTROLE DES APPLICATIONS EXTERNES ET INTERACTIONS
        # ---------------------------------------------------------
        interaction_data = getattr(message, "interaction_metadata", None)

        if interaction_data is not None:
            trigger_user = getattr(interaction_data, "user", None)

            if trigger_user is not None:
                authorized, reason = await self.check_authorization(
                    message.guild, trigger_user.id
                )
            else:
                authorized, reason = False, "Utilisateur declencheur inconnu."

            print(
                f"[ANTISPAM] Interaction de {trigger_user} via {author} "
                f"-> autorise={authorized} ({reason or 'ok'})"
            )

            if not authorized:
                await safe_delete(message)

                log_chan = await self.get_log_channel(message.guild, "moderation")
                if log_chan and trigger_user:
                    embed = discord.Embed(
                        title="Application Externe Non Autorisee Bloquee",
                        color=discord.Color.red(),
                        timestamp=now,
                    )
                    embed.add_field(
                        name="Utilisateur",
                        value=f"{trigger_user.mention} (`{trigger_user.id}`)",
                    )
                    embed.add_field(
                        name="Application",
                        value=f"{author.mention} (`{author.id}`)",
                    )
                    embed.add_field(name="Salon", value=message.channel.mention)
                    embed.add_field(name="Raison", value=reason, inline=False)
                    embed.add_field(
                        name="Action",
                        value="Message supprime.",
                        inline=False,
                    )
                    await log_chan.send(embed=embed)
                return
            # Autorise : on laisse passer, sans appliquer l'anti-spam au
            # message de reponse de l'application.
            return

        # ---------------------------------------------------------
        # 1. PIEGE HONEYPOT
        # ---------------------------------------------------------
        if "honeypot" in message.channel.name.lower():
            if author.bot:
                return

            await safe_delete(message)

            try:
                await author.timeout(
                    datetime.timedelta(days=7),
                    reason="Declenchement du piege Honeypot (Bot / Spammer)",
                )
            except discord.Forbidden:
                pass

            log_chan = await self.get_log_channel(message.guild, "honeypot")
            if log_chan:
                embed = discord.Embed(
                    title="Alerte Honeypot",
                    description=(
                        f"Le membre {author.mention} (`{author.id}`) est tombe dans le"
                        " salon piege."
                    ),
                    color=discord.Color.red(),
                    timestamp=now,
                )
                embed.add_field(name="Salon", value=message.channel.mention)
                embed.add_field(
                    name="Contenu",
                    value=message.content[:1024] or "Aucun texte (media/embed)",
                )
                embed.add_field(name="Sanction", value="Timeout de 7 jours applique.")
                await log_chan.send(embed=embed)
            return

        if author.bot:
            return

        raw_content = message.content
        normalized_content = normalize_text(raw_content)
        cleaned_content = strip_punctuation(normalized_content)

        # ---------------------------------------------------------
        # 2. DOUBLONS ET REPETITIONS
        # ---------------------------------------------------------
        if len(raw_content) > 5:
            history = self.user_history[author_id]
            duplicate_count = sum(
                1
                for prev in history
                if SequenceMatcher(None, normalized_content, prev).ratio() >= 0.90
            )
            history.append(normalized_content)

            if duplicate_count >= 2:
                await safe_delete(message)
                try:
                    await author.timeout(
                        datetime.timedelta(minutes=10),
                        reason="Anti-Spam : Envoi de messages repetitifs/doublons",
                    )
                except discord.Forbidden:
                    pass

                await temp_warn(
                    message.channel,
                    f"{author.mention}, la repetition de messages identiques est interdite.",
                )

                log_chan = await self.get_log_channel(message.guild, "moderation")
                if log_chan:
                    embed = discord.Embed(
                        title="Detection de Spam Repetitif (Doublons)",
                        color=discord.Color.orange(),
                        timestamp=now,
                    )
                    embed.add_field(name="Membre", value=f"{author.mention} (`{author.id}`)")
                    embed.add_field(name="Salon", value=message.channel.mention)
                    embed.add_field(name="Contenu", value=raw_content[:1024])
                    embed.add_field(name="Action", value="Timeout de 10 minutes applique.")
                    await log_chan.send(embed=embed)
                return

        # ---------------------------------------------------------
        # 3. ARNAQUES CRYPTO & PHISHING (TEXTE + PJ)
        # ---------------------------------------------------------
        is_crypto_scam = False
        scam_reason = ""

        for keyword in CRYPTO_SCAM_KEYWORDS:
            if keyword in cleaned_content:
                is_crypto_scam = True
                scam_reason = f"Mot-cle suspect detecte : `{keyword}`"
                break

        if not is_crypto_scam and message.attachments:
            for attachment in message.attachments:
                att_cleaned = strip_punctuation(normalize_text(attachment.filename))
                for keyword in CRYPTO_SCAM_KEYWORDS:
                    if keyword in att_cleaned:
                        is_crypto_scam = True
                        scam_reason = f"Fichier suspect detecte : `{attachment.filename}`"
                        break
                if is_crypto_scam:
                    break

        if is_crypto_scam:
            await safe_delete(message)

            sanction_status = "Timeout de 7 jours applique (compte potentiellement compromis)."
            try:
                await author.timeout(
                    datetime.timedelta(days=7),
                    reason=f"Detection Arnaque Crypto/Phishing : {scam_reason}",
                )
            except discord.Forbidden:
                sanction_status = "Echec du timeout (permissions insuffisantes)."

            await temp_warn(
                message.channel,
                f"{author.mention}, votre message a ete supprime car il contient"
                " du contenu assimile a une arnaque ou un phishing.",
            )

            log_chan = await self.get_log_channel(message.guild, "moderation")
            if log_chan:
                embed = discord.Embed(
                    title="Detection Arnaque Crypto / Phishing",
                    color=discord.Color.purple(),
                    timestamp=now,
                )
                embed.add_field(name="Membre", value=f"{author.mention} (`{author.id}`)", inline=False)
                embed.add_field(name="Raison", value=scam_reason, inline=False)
                embed.add_field(name="Salon", value=message.channel.mention, inline=False)
                embed.add_field(
                    name="Contenu supprime",
                    value=raw_content[:1024] or "Piece jointe / Image",
                    inline=False,
                )
                embed.add_field(name="Sanction", value=sanction_status, inline=False)
                await log_chan.send(embed=embed)
            return

        # ---------------------------------------------------------
        # 4. MAJUSCULES ET EMOJIS
        # ---------------------------------------------------------
        if len(raw_content) > 15:
            uppercase_count = sum(1 for c in raw_content if c.isupper())
            if (uppercase_count / len(raw_content)) > 0.60:
                await safe_delete(message)
                await temp_warn(
                    message.channel,
                    f"{author.mention}, l'usage excessif de majuscules est interdit.",
                )
                return

        if len(EMOJI_REGEX.findall(raw_content)) > 8:
            await safe_delete(message)
            await temp_warn(
                message.channel,
                f"{author.mention}, l'envoi massif d'emojis est interdit.",
            )
            return

        # ---------------------------------------------------------
        # 5. MENTIONS MASSIVES ET LIENS D'INVITATION
        # ---------------------------------------------------------
        if len(message.mentions) > 3 or len(message.role_mentions) > 2:
            await safe_delete(message)
            try:
                await author.timeout(
                    datetime.timedelta(minutes=30),
                    reason="Spam de mentions massives",
                )
            except discord.Forbidden:
                pass

            log_chan = await self.get_log_channel(message.guild, "moderation")
            if log_chan:
                embed = discord.Embed(
                    title="Spam de Mentions Detecte",
                    color=discord.Color.orange(),
                    timestamp=now,
                )
                embed.add_field(name="Membre", value=f"{author.mention} (`{author.id}`)")
                embed.add_field(
                    name="Mentions",
                    value=f"{len(message.mentions)} membres, {len(message.role_mentions)} roles",
                )
                embed.add_field(name="Action", value="Timeout de 30 minutes applique.")
                await log_chan.send(embed=embed)
            return

        if DISCORD_INVITE_REGEX.search(raw_content):
            await safe_delete(message)
            await temp_warn(
                message.channel,
                f"{author.mention}, les liens d'invitation Discord sont interdits.",
            )

            log_chan = await self.get_log_channel(message.guild, "moderation")
            if log_chan:
                embed = discord.Embed(
                    title="Invitation Discord Bloquee",
                    color=discord.Color.gold(),
                    timestamp=now,
                )
                embed.add_field(name="Membre", value=f"{author.mention} (`{author.id}`)")
                embed.add_field(name="Salon", value=message.channel.mention)
                embed.add_field(name="Contenu", value=raw_content[:1024] or "Contenu vide")
                await log_chan.send(embed=embed)
            return

        # ---------------------------------------------------------
        # 6. ANTI-SPAM DE DEBIT (5 messages / 5 sec)
        # ---------------------------------------------------------
        self.user_messages[author_id] = [
            t for t in self.user_messages[author_id] if (now - t).total_seconds() < 5
        ]
        self.user_messages[author_id].append(now)

        if len(self.user_messages[author_id]) >= 5:
            try:
                deleted = await message.channel.purge(
                    limit=15,
                    check=lambda m: m.author.id == author_id
                    and (now - m.created_at).total_seconds() < 120,
                )
                deleted_count = len(deleted)
            except (discord.Forbidden, discord.HTTPException):
                deleted_count = 0

            sanction_text = "Timeout de 15 minutes applique."
            try:
                await author.timeout(
                    datetime.timedelta(minutes=15),
                    reason="Anti-Spam : Debit de messages excessif",
                )
            except discord.Forbidden:
                sanction_text = "Echec du timeout (permissions insuffisantes)."

            await temp_warn(
                message.channel,
                f"{author.mention}, le spam rapide est interdit. Vos messages"
                " recents ont ete nettoyes.",
            )

            log_chan = await self.get_log_channel(message.guild, "moderation")
            if log_chan:
                embed = discord.Embed(
                    title="Detection Anti-Spam (Debit)",
                    color=discord.Color.orange(),
                    timestamp=now,
                )
                embed.add_field(name="Membre", value=f"{author.mention} (`{author.id}`)")
                embed.add_field(name="Salon", value=message.channel.mention)
                embed.add_field(name="Messages nettoyes", value=str(deleted_count))
                embed.add_field(name="Action", value=sanction_text)
                await log_chan.send(embed=embed)

            self.user_messages[author_id].clear()


async def setup(bot):
    await bot.add_cog(AntiSpamHoneypot(bot))