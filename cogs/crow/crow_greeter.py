from typing import List
import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.predicates import MessagePredicate


class CrowGreeter:
    bot: Red
    config: Config

    @commands.mod()
    @commands.group()
    async def greeter(self, ctx: commands.Context):
        """
        Configure welcome messages and images.
        """

        defaults = {
            "message": "Welcome $USER to our server!",
            "channel": 0,
            "images": [],
            "next_image": 0,
        }
        self.config.register_guild(greeter=defaults)

    @commands.admin()
    @greeter.command(name="config")
    async def greeter_config(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
    ):
        """Set up a greeting channel."""

        await ctx.reply(
            f"Configuring channel <#{channel.id}> to be used for new member greetings. You can enter a greeting message that will be sent when someone joins the server. Use `$USER` to mention them. For example, 'Welcome $USER to our server!'.\n"
            + "Enter your greeting message now (or type `cancel`):"
        )

        message: discord.Message = await self.bot.wait_for(
            "message", check=MessagePredicate.same_context(ctx)
        )

        config = self.config.guild(ctx.guild)
        async with config.greeter() as greeter:
            greeter["message"] = message.content
            greeter["channel"] = channel.id

        await ctx.reply(
            "Done! To change the message, run this command again, or use other greeter commands to further customize the greeting (like adding images)."
        )

    @commands.admin()
    @greeter.command(name="banneradd")
    async def greeter_add_banner(
        self,
        ctx: commands.Context,
        url: str,
    ):
        """Add a banner image to the greeter rotation."""

        config = self.config.guild(ctx.guild)
        async with config.greeter() as greeter:
            greeter["images"].append(url)
        await ctx.react_quietly("✅")

    @commands.admin()
    @greeter.command(name="bannerlist")
    async def greeter_list_banner(
        self,
        ctx: commands.Context,
    ):
        """List all active banner images."""

        config = self.config.guild(ctx.guild)
        greeter = await config.greeter()
        images = greeter["images"]
        image_text = [f"<{i}>" for i in images]
        images = "\n".join(image_text)
        await ctx.reply(images)

    @commands.admin()
    @greeter.command(name="bannerremove")
    async def greeter_remove_banner(
        self,
        ctx: commands.Context,
        url: str,
    ):
        """Remove a banner image from the greeter rotation."""

        config = self.config.guild(ctx.guild)
        async with config.greeter() as greeter:
            greeter["images"].remove(url)
        await ctx.react_quietly("✅")

    @commands.mod()
    @greeter.command(name="greet")
    async def greeter_greet(self, ctx: commands.Context, member: discord.Member = None):
        to = member if member else ctx.author
        await self._send_greeter_message(to)

    @commands.Cog.listener("on_member_update")
    async def greeter_member_verified(
        self, before: discord.Member, after: discord.Member
    ):
        # we don't use on_member_joined because that'll trigger immediately on join, where we want
        # people to "complete a few more steps before you can start talking" and get verified
        # first. so wait for pending state to change to False
        if before.pending == after.pending:
            return
        if after.pending:
            return
        await self._send_greeter_message(after)

    async def _send_greeter_message(self, member: discord.Member):
        config = self.config.guild(member.guild)
        greeter = await config.greeter()
        message = greeter["message"]
        channel_id = greeter["channel"]

        if channel_id == 0:
            return

        channel: discord.TextChannel = member.guild.get_channel(channel_id)
        formatted = message.replace("$USER", f"<@{member.id}>")

        image_url = await self._greeter_next_image(member.guild)

        embed = discord.Embed(
            description=formatted,
        )
        embed.set_image(url=image_url)
        await channel.send(
            f"<@{member.id}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=[member]),
        )

    async def _greeter_next_image(self, guild: discord.Guild):
        config = self.config.guild(guild)
        greeter = await config.greeter()
        images: List[str] = greeter["images"]
        index: int = greeter["next_image"]

        # wrap around at the start, instead of afterwards, so we can still show images recently
        # added at the end (if the pointer was already at the end)
        if index >= len(images):
            index = 0
        url = images[index]

        async with config.greeter() as greeter:
            greeter["next_image"] = index + 1

        return url
