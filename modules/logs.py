import discord
from discord.ext import commands
import datetime


class GlobalLogs(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def get_log_channel(self, guild, key):
        """Récupère le salon de logs défini dans la configuration."""
        channel_name = self.bot.config.get("logs", {}).get(key)
        if not channel_name:
            return None
        return discord.utils.get(guild.text_channels, name=channel_name)

    async def get_audit_entry(self, guild, action, target_id=None):
        """Recherche dans les logs d'audit Discord l'exécuteur de l'action."""
        try:
            async for entry in guild.audit_logs(limit=3, action=action):
                # Vérifie que l'action s'est produite il y a moins de 10 secondes
                if (
                    datetime.datetime.now(datetime.timezone.utc) - entry.created_at
                ).total_seconds() < 10:
                    if target_id is None or (
                        hasattr(entry.target, "id") and entry.target.id == target_id
                    ):
                        return entry.user
        except discord.Forbidden:
            return None
        return None

    # =========================================================
    # 1. LOGS RÔLES
    # =========================================================
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        log_chan = await self.get_log_channel(role.guild, "roles")
        if not log_chan:
            return

        executor = await self.get_audit_entry(
            role.guild, discord.AuditLogAction.role_create, role.id
        )
        embed = discord.Embed(
            title="✨ Rôle Créé",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(
            name="Rôle", value=f"{role.mention} (`{role.name}` | `{role.id}`)"
        )
        embed.add_field(
            name="Exécuteur",
            value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu/Bot",
        )
        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        log_chan = await self.get_log_channel(role.guild, "roles")
        if not log_chan:
            return

        executor = await self.get_audit_entry(
            role.guild, discord.AuditLogAction.role_delete, role.id
        )
        embed = discord.Embed(
            title="🗑️ Rôle Supprimé",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Nom du rôle", value=f"`{role.name}` (`{role.id}`)")
        embed.add_field(
            name="Exécuteur",
            value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu/Bot",
        )
        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        log_chan = await self.get_log_channel(before.guild, "roles")
        if not log_chan:
            return

        executor = await self.get_audit_entry(
            before.guild, discord.AuditLogAction.role_update, after.id
        )
        now = datetime.datetime.now(datetime.timezone.utc)

        if before.name != after.name:
            embed = discord.Embed(
                title="🏷️ Rôle Renommé", color=discord.Color.blue(), timestamp=now
            )
            embed.add_field(name="Rôle", value=after.mention)
            embed.add_field(name="Ancien nom", value=f"`{before.name}`")
            embed.add_field(name="Nouveau nom", value=f"`{after.name}`")
            embed.add_field(
                name="Exécuteur",
                value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
            )
            await log_chan.send(embed=embed)

        if before.permissions != after.permissions:
            embed = discord.Embed(
                title="⚙️ Permissions de Rôle Modifiées",
                color=discord.Color.orange(),
                timestamp=now,
            )
            embed.add_field(name="Rôle", value=after.mention)
            embed.add_field(
                name="Exécuteur",
                value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
            )
            await log_chan.send(embed=embed)

    # =========================================================
    # 2. LOGS SALONS ET CATÉGORIES
    # =========================================================
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_chan = await self.get_log_channel(channel.guild, "salons")
        if not log_chan:
            return

        executor = await self.get_audit_entry(
            channel.guild, discord.AuditLogAction.channel_create, channel.id
        )
        embed = discord.Embed(
            title="📁 Salon / Catégorie Créé(e)",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(
            name="Salon", value=f"{channel.mention} (`{channel.name}` | `{channel.id}`)"
        )
        embed.add_field(name="Type", value=str(channel.type))
        embed.add_field(
            name="Exécuteur",
            value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
        )
        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_chan = await self.get_log_channel(channel.guild, "salons")
        if not log_chan:
            return

        executor = await self.get_audit_entry(
            channel.guild, discord.AuditLogAction.channel_delete, channel.id
        )
        embed = discord.Embed(
            title="💥 Salon / Catégorie Supprimé(e)",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Nom", value=f"`{channel.name}` (`{channel.id}`)")
        embed.add_field(name="Type", value=str(channel.type))
        embed.add_field(
            name="Exécuteur",
            value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
        )
        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        log_chan = await self.get_log_channel(before.guild, "salons")
        if not log_chan:
            return

        if before.name != after.name:
            executor = await self.get_audit_entry(
                before.guild, discord.AuditLogAction.channel_update, after.id
            )
            embed = discord.Embed(
                title="✏️ Salon Renommé",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.add_field(name="Salon", value=after.mention)
            embed.add_field(
                name="Changement", value=f"`{before.name}` ➔ `{after.name}`"
            )
            embed.add_field(
                name="Exécuteur",
                value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
            )
            await log_chan.send(embed=embed)

    # =========================================================
    # 3. LOGS SERVEUR
    # =========================================================
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        log_chan = await self.get_log_channel(before, "serveur")
        if not log_chan:
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        executor = await self.get_audit_entry(
            after, discord.AuditLogAction.guild_update
        )

        if before.name != after.name:
            embed = discord.Embed(
                title="🏰 Nom du Serveur Modifié",
                color=discord.Color.gold(),
                timestamp=now,
            )
            embed.add_field(
                name="Changement", value=f"`{before.name}` ➔ `{after.name}`"
            )
            embed.add_field(
                name="Exécuteur",
                value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
            )
            await log_chan.send(embed=embed)

        if before.icon != after.icon:
            embed = discord.Embed(
                title="🖼️ Icône du Serveur Modifiée",
                color=discord.Color.gold(),
                timestamp=now,
            )
            if after.icon:
                embed.set_thumbnail(url=after.icon.url)
            embed.add_field(
                name="Exécuteur",
                value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
            )
            await log_chan.send(embed=embed)

    # =========================================================
    # 4. LOGS MEMBRES
    # =========================================================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        log_chan = await self.get_log_channel(member.guild, "membres")
        if not log_chan:
            return

        created_at = member.created_at.strftime("%d/%m/%Y %H:%M:%S")
        account_age = (
            datetime.datetime.now(datetime.timezone.utc) - member.created_at
        ).days

        embed = discord.Embed(
            title="📥 Nouveau Membre",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Membre", value=f"{member.mention} (`{member.name}` | `{member.id}`)"
        )
        embed.add_field(
            name="Création du compte",
            value=f"{created_at} ({account_age} jours)",
            inline=False,
        )
        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        log_chan = await self.get_log_channel(member.guild, "membres")
        if not log_chan:
            return

        # Vérifier si c'est un Kick ou Ban
        kick_executor = await self.get_audit_entry(
            member.guild, discord.AuditLogAction.kick, member.id
        )

        embed = discord.Embed(
            title="📤 Départ / Expulsion d'un Membre",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Membre", value=f"{member.mention} (`{member.name}` | `{member.id}`)"
        )

        if kick_executor:
            embed.title = "👢 Membre Expulsé (Kick)"
            embed.add_field(
                name="Expulsé par", value=f"{kick_executor.mention} (`{kick_executor.id}`)"
            )
        else:
            embed.add_field(name="Type", value="Départ volontaire ou expulsion")

        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        log_chan = await self.get_log_channel(before.guild, "membres")
        if not log_chan:
            return

        now = datetime.datetime.now(datetime.timezone.utc)

        # Changement de Pseudo / Surnom
        if before.nick != after.nick:
            embed = discord.Embed(
                title="✏️ Modification de Surnom",
                color=discord.Color.blue(),
                timestamp=now,
            )
            embed.add_field(name="Membre", value=after.mention)
            embed.add_field(name="Ancien surnom", value=f"`{before.nick}`")
            embed.add_field(name="Nouveau surnom", value=f"`{after.nick}`")
            await log_chan.send(embed=embed)

        # Attribution / Retrait de rôles
        if before.roles != after.roles:
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]

            executor = await self.get_audit_entry(
                before.guild, discord.AuditLogAction.member_role_update, after.id
            )

            if added_roles:
                embed = discord.Embed(
                    title="➕ Rôle(s) Ajouté(s)",
                    color=discord.Color.green(),
                    timestamp=now,
                )
                embed.add_field(name="Membre", value=after.mention)
                embed.add_field(
                    name="Rôle(s)",
                    value=", ".join([r.mention for r in added_roles]),
                )
                embed.add_field(
                    name="Par",
                    value=f"{executor.mention}" if executor else "Système/Inconnu",
                )
                await log_chan.send(embed=embed)

            if removed_roles:
                embed = discord.Embed(
                    title="➖ Rôle(s) Retiré(s)",
                    color=discord.Color.orange(),
                    timestamp=now,
                )
                embed.add_field(name="Membre", value=after.mention)
                embed.add_field(
                    name="Rôle(s)",
                    value=", ".join([r.mention for r in removed_roles]),
                )
                embed.add_field(
                    name="Par",
                    value=f"{executor.mention}" if executor else "Système/Inconnu",
                )
                await log_chan.send(embed=embed)

    # =========================================================
    # 5. LOGS VOCAL (Inclus Mute / Deafen Moderateur)
    # =========================================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        log_chan = await self.get_log_channel(member.guild, "vocal")
        if not log_chan:
            return

        now = datetime.datetime.now(datetime.timezone.utc)

        # Connexion
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="🔊 Connexion Vocale", color=discord.Color.green(), timestamp=now
            )
            embed.add_field(name="Membre", value=f"{member.mention} (`{member.id}`)")
            embed.add_field(name="Salon", value=after.channel.mention)
            await log_chan.send(embed=embed)

        # Déconnexion
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="🔇 Déconnexion Vocale", color=discord.Color.red(), timestamp=now
            )
            embed.add_field(name="Membre", value=f"{member.mention} (`{member.id}`)")
            embed.add_field(name="Salon quitté", value=f"`{before.channel.name}`")
            await log_chan.send(embed=embed)

        # Déplacement
        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel.id != after.channel.id
        ):
            embed = discord.Embed(
                title="🔀 Déplacement Vocal", color=discord.Color.blue(), timestamp=now
            )
            embed.add_field(name="Membre", value=f"{member.mention} (`{member.id}`)")
            embed.add_field(
                name="Parcours",
                value=f"{before.channel.mention} ➔ {after.channel.mention}",
            )
            await log_chan.send(embed=embed)

        # Mute Serveur (par un modérateur)
        if before.mute != after.mute:
            executor = await self.get_audit_entry(
                member.guild, discord.AuditLogAction.member_update, member.id
            )
            action_text = "Rendu muet (Server Mute)" if after.mute else "Rendu la parole"
            embed = discord.Embed(
                title=f"🎙️ Modération Vocale : {action_text}",
                color=discord.Color.purple(),
                timestamp=now,
            )
            embed.add_field(name="Membre", value=member.mention)
            embed.add_field(
                name="Modérateur",
                value=f"{executor.mention}" if executor else "Auto/Inconnu",
            )
            await log_chan.send(embed=embed)

    # =========================================================
    # 6. LOGS MESSAGES (Inclus Images & Modérateur suppresseur)
    # =========================================================
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.author.bot:
            return

        log_chan = await self.get_log_channel(message.guild, "messages")
        if not log_chan:
            return

        now = datetime.datetime.now(datetime.timezone.utc)

        # Chercher si un modérateur a supprimé le message
        executor = await self.get_audit_entry(
            message.guild, discord.AuditLogAction.message_delete, message.author.id
        )

        embed = discord.Embed(
            title="🗑️ Message Supprimé",
            color=discord.Color.red(),
            timestamp=now,
        )
        embed.add_field(
            name="Auteur du message",
            value=f"{message.author.mention} (`{message.author.id}`)",
            inline=False,
        )
        embed.add_field(name="Salon", value=message.channel.mention, inline=False)
        embed.add_field(
            name="Contenu du message",
            value=message.content[:1024] or "*Aucun contenu texte (Image/Fichier)*",
            inline=False,
        )

        if executor and executor.id != message.author.id:
            embed.add_field(
                name="Supprimé par (Modérateur)",
                value=f"{executor.mention} (`{executor.id}`)",
                inline=False,
            )
        else:
            embed.add_field(
                name="Supprimé par",
                value=f"{message.author.mention} (L'auteur lui-même ou nettoyé)",
                inline=False,
            )

        # Conserver et afficher l'image/pièce jointe supprimée
        if message.attachments:
            attachment = message.attachments[0]
            embed.add_field(
                name="Pièce jointe", value=f"[{attachment.filename}]({attachment.url})"
            )
            if attachment.content_type and "image" in attachment.content_type:
                embed.set_image(url=attachment.url)

        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not before.guild or before.author.bot or before.content == after.content:
            return

        log_chan = await self.get_log_channel(before.guild, "messages")
        if not log_chan:
            return

        embed = discord.Embed(
            title="✏️ Message Modifié",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(
            name="Auteur", value=f"{before.author.mention} (`{before.author.id}`)"
        )
        embed.add_field(name="Salon", value=before.channel.mention)
        embed.add_field(
            name="Avant", value=before.content[:1024] or "*Vide*", inline=False
        )
        embed.add_field(
            name="Après", value=after.content[:1024] or "*Vide*", inline=False
        )
        embed.add_field(
            name="Lien du message", value=f"[Accéder au message]({after.jump_url})"
        )

        await log_chan.send(embed=embed)

    # =========================================================
    # 7. LOGS MODÉRATION (Bans / Unbans)
    # =========================================================
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        log_chan = await self.get_log_channel(guild, "moderation")
        if not log_chan:
            return

        executor = await self.get_audit_entry(
            guild, discord.AuditLogAction.ban, user.id
        )
        embed = discord.Embed(
            title="🔨 Membre Banni",
            color=discord.Color.dark_red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Utilisateur banni", value=f"{user.mention} (`{user.id}`)")
        embed.add_field(
            name="Banni par",
            value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
        )
        await log_chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        log_chan = await self.get_log_channel(guild, "moderation")
        if not log_chan:
            return

        executor = await self.get_audit_entry(
            guild, discord.AuditLogAction.unban, user.id
        )
        embed = discord.Embed(
            title="🔓 Membre Débanni",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Utilisateur débanni", value=f"{user.mention} (`{user.id}`)")
        embed.add_field(
            name="Débanni par",
            value=f"{executor.mention} (`{executor.id}`)" if executor else "Inconnu",
        )
        await log_chan.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GlobalLogs(bot))