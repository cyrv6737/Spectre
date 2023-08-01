from discord.ext import commands
import requests, re
import discord, asyncio
from discord.ui import Button

active_search = False

class ModSearch(commands.Cog):
    def __init__(self, bot :commands.Bot) -> None:
        self.bot = bot 
        
    @commands.hybrid_command(description="Search Northstar Thunderstore for mods")
    async def modsearch(self, ctx, search_string: str):
        
        global active_search
        
        if len(search_string) < 3:
            character_warning = await ctx.send("Search must be at least 3 characters", ephemeral=True)
            await asyncio.sleep(5)
            await character_warning.delete()
            return
        
        if active_search:
            active_warning = await ctx.send("Please wait for the active search to timeout", ephemeral=True)
            await asyncio.sleep(5)
            await active_warning.delete()
            return
        
        try:
            response = requests.get("https://northstar.thunderstore.io/api/v1/package/")
            if response.status_code == 200:
                data = response.json()
        
        except requests.exceptions.RequestException as err:
            print(err)
            return
        
        mods = {}
        for i, item in enumerate(data):
            match = re.search(search_string, item["name"], re.IGNORECASE)
            if match:
                downloads = 0
                for version in item['versions']:
                    downloads = downloads + version['downloads']
                mods[item['owner'] + "." + item['name']] = {
                    "name": item['name'].replace("_", " "),
                    "owner": item['owner'],
                    "icon_url": item['versions'][0]['icon'],
                    "ts_url": item['package_url'],
                    "last_update": item['date_updated'][:(item['date_updated'].index('T'))], # Remove time from date string
                    "total_dl": downloads,
                    "description": item['versions'][0]['description']
                }
                
        if not mods:
            no_mods_warning = await ctx.send("No mods found")
            await asyncio.sleep(5)
            await no_mods_warning.delete()
            return
        
        # Sort mods by most downloaded by default until we get better sorting later        
        sorted_mods_by_dl = dict(sorted(mods.items(), key=lambda item: item[1]['total_dl'], reverse=True))
        
        pages = list(sorted_mods_by_dl.keys())
        current_page = 0
        
        def get_mod_embed():
            key = pages[current_page]
            mod = sorted_mods_by_dl[key]
            mod_embed_desc = f"By {mod['owner']}\n{mod['description']}\n\nLast updated on {mod['last_update']} (YY/MM/DD)\n{mod['total_dl']} Downloads\n{mod['ts_url']}"
            embed_title = f"{mod['name']} ({current_page + 1}/{len(pages)})"
            embed = discord.Embed(
                title=embed_title,
                description=mod_embed_desc
            )
            embed.set_thumbnail(url=mod['icon_url'])
            return embed
        
        control_view = discord.ui.View()
        prev_button = Button(label="Prev", style=discord.ButtonStyle.primary)
        next_button = Button(label="Next", style=discord.ButtonStyle.primary)
        stop_button = Button(label="Stop", style=discord.ButtonStyle.danger)
        control_view.add_item(prev_button)
        control_view.add_item(next_button)
        control_view.add_item(stop_button)
        
        message = await ctx.send(embed=get_mod_embed(), view=control_view)
        
        active_search = True
        
        
        async def button_callback(interaction, button):
                    global active_search
                    if button == prev_button:
                        current_page = (current_page - 1) % len(pages)
                    elif button == next_button:
                        current_page = (current_page + 1) % len(pages)
                    elif button == stop_button:
                        active_search = False
                        await message.delete()
                        cancelled_message = await ctx.send("Search cancelled", ephemeral=True)
                        await asyncio.sleep(5)
                        await cancelled_message.delete()
                        return
                    
        prev_button.callback = button_callback
        next_button.callback = button_callback
        stop_button.callback = button_callback
        
        while True:
            try:
                interaction, _ = await self.wait_for('button_click', timeout=30.0, check=lambda i: i.message.id == message.id)
                interaction.defer()
                await message.edit(embed=get_mod_embed(), view=control_view)
                
            except asyncio.TimeoutError:
                break
            
        await message.clear_reactions()
        active_search = False
        return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModSearch(bot))
