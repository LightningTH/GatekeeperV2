'''
   Copyright (C) 2021-2022 Katelynn Cadwallader.

   This file is part of Gatekeeper, the AMP Minecraft Discord Bot.

   Gatekeeper is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 3, or (at your option)
   any later version.

   Gatekeeper is distributed in the hope that it will be useful, but WITHOUT
   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
   or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
   License for more details.

   You should have received a copy of the GNU General Public License
   along with Gatekeeper; see the file COPYING.  If not, write to the Free
   Software Foundation, 51 Franklin Street - Fifth Floor, Boston, MA
   02110-1301, USA. 
'''
import logging
import discord
from discord.ext import commands

import DB
import AMP
import utils

class botEmbeds():
    """Gatekeeper Embeds/Banners"""
    def __init__ (self, client:commands.Bot=None):
        self._client = client
        self.logger = logging.getLogger(__name__)
        self.logger.debug('Utils Bot Loaded')

        self.DBHandler = DB.getDBHandler()
        self.DB = self.DBHandler.DB #Main Database object
        self.DBConfig = self.DBHandler.DBConfig
        self.uBot = utils.botUtils(client)

        self.AMPHandler = AMP.getAMPHandler()
        self.AMPInstances = self.AMPHandler.AMP_Instances
        self.AMPServer_Avatar_urls = []

    def default_embedmsg(self, title, context:commands.Context, description=None, field=None, field_value=None) -> discord.Embed:
        """This Embed has only one Field Entry."""
        embed=discord.Embed(title=title, description=description, color=0x808000) #color is RED 
        embed.set_author(name=context.author.display_name, icon_url=context.author.avatar)
        embed.add_field(name=field, value=field_value, inline=False)
        return embed

    async def server_info_embed(self, server:AMP.AMPInstance, context:commands.Context) -> discord.Embed:
        """For Individual Server info embed replies"""
        db_server = self.DB.GetServer(InstanceID = server.InstanceID)
        server_name = db_server.InstanceName
        if db_server.DisplayName != None:
            server_name = db_server.DisplayName

        embed=discord.Embed(title= f'__**{server_name}**__ - {[server.TargetName]}', color= 0x00ff00, description= server.Description)

        discord_role = db_server.Discord_Role
        if discord_role != None:
            discord_role = context.guild.get_role(int(db_server.Discord_Role)).name

        avatar = await self.uBot.validate_avatar(db_server)
        if avatar != None:
            embed.set_thumbnail(url= avatar)

        embed.add_field(name=f'Host:', value=str(db_server.Host), inline= False)
        embed.add_field(name='Donator Only:', value= str(bool(db_server.Donator)), inline= True)
        embed.add_field(name='Whitelist Open:' , value= str(bool(db_server.Whitelist)), inline= True)
        embed.add_field(name='Role:', value= str(discord_role), inline= False)
        embed.add_field(name='Hidden', value= bool(db_server.Hidden), inline= True)
        embed.add_field(name='Whitelist Hidden', value= bool(db_server.Whitelist_disabled), inline= True)

        embed.add_field(name='Filtered Console:', value= str(bool(db_server.Whitelist)), inline= False)
        embed.add_field(name='Console Filter Type:', value= bool(db_server.Console_Filtered_Type), inline= True)
        if db_server.Discord_Console_Channel != None:
            discord_channel = context.guild.get_channel(db_server.Discord_Console_Channel)
            embed.add_field(name='Console Channel:', value= discord_channel.name, inline= False)
        else:
            embed.add_field(name='Console Channel:', value= db_server.Discord_Console_Channel, inline= False)

        embed.add_field(name='Discord Chat Prefix:', value= str(db_server.Discord_Chat_Prefix), inline= False)
        if db_server.Discord_Chat_Channel != None:
            discord_channel = context.guild.get_channel(db_server.Discord_Chat_Channel)
            embed.add_field(name='Chat Channel:', value= discord_channel.name, inline= True)
        else:
            embed.add_field(name='Chat Channel:', value= db_server.Discord_Chat_Channel, inline= True)
        
        if db_server.Discord_Event_Channel != None:
            discord_channel = context.guild.get_channel(db_server.Discord_Event_Channel)
            embed.add_field(name='Event Channel:', value= discord_channel.name, inline= True)
        else:
            embed.add_field(name='Event Channel:', value= db_server.Discord_Event_Channel, inline= True)

        return embed

    async def server_display_embed(self, guild:discord.Guild=None) -> list[discord.Embed]:
        """Used for `/server display command`"""
        embed_list = []
        for server in self.AMPInstances:
            server = self.AMPInstances[server]

            db_server = self.DB.GetServer(InstanceID= server.InstanceID)
            #Lightning: Could flip this if statement logic and remove an indentation
            #with or statements the first true part will avoid the second part of the statement
            #so if db_server is none there is no risk of a crash due to attempting to access Hidden
            #saving an additional if statement check below for continuing
            #if db_server == None or db_server.Hidden == 1:
            #   continue
            #-vs-
            #if db_server == None:
            #   continue
            #if db_server.Hidden == 1:
            #   continue
            if db_server != None and db_server.Hidden != 1:

                instance_status = 'Offline'
                dedicated_status = 'Offline'
                Users = None
                User_list = None
                if server.Running:
                    instance_status = 'Online'
                    #Lightning: server is online, check if ads is good
                    if server._ADScheck() and server.ADS_Running:
                        dedicated_status = 'Online'
                        #Lightning: go get all users to display
                        Users = server.getUsersOnline()

                        #Lightning: so what happens if user list is 1? user_list will be None
                        #and then used lower for players online but is a None object
                        #fairly certain such a join with 1 entry won't have the join'd data
                        #but double check in a python terminal
                        #parens aren't required either fyi
                        if len(server.getUserList()) > 1:
                            User_list = (', ').join(server.getUserList())

                embed_color = 0x71368a
                if guild != None and db_server.Discord_Role != None:
                    db_server_role = guild.get_role(int(db_server.Discord_Role))
                    if db_server_role != None:
                        embed_color = db_server_role.color

                server_name = server.FriendlyName
                if server.DisplayName != None:
                    server_name = db_server.DisplayName

                embed=discord.Embed(title=f'**=======  {server_name}  =======**',description= server.Description, color=embed_color)
                #This is for future custom avatar support.
                avatar = await self.uBot.validate_avatar(db_server)
                if avatar != None:
                    embed.set_thumbnail(url=avatar)
                embed.add_field(name='**Instance Status**:' , value= instance_status, inline= False)
                embed.add_field(name='**Dedicated Server Status**:', value= dedicated_status, inline= False)
                embed.add_field(name='**Host**:', value= str(db_server.Host), inline=True)
                embed.add_field(name='**Donator Only**:', value= str(bool(db_server.Donator)), inline= True)
                embed.add_field(name='**Whitelist Open**:', value= str(bool(db_server.Whitelist)), inline= True)
                if Users != None:
                    embed.add_field(name=f'**Players**:', value= f'{Users[0]}/{Users[1]}',inline=True)
                else:
                    embed.add_field(name='**Player Limit**:', value= str(Users), inline= True)
                embed.add_field(name='**Players Online**:', value=str(User_list), inline=False)
                embed_list.append(embed)
        
        return embed_list

    async def server_status_embed(self, context:commands.Context, server:AMP.AMPInstance, TPS=None, Users=None, CPU=None, Memory=None, Uptime=None, Users_Online=None) -> discord.Embed:
        """This is the Server Status Embed Message"""
        db_server = self.DB.GetServer(InstanceID= server.InstanceID)
        
        if server.Running:
            instance_status = 'Online'
        else:
            instance_status = 'Offline'

        if server.ADS_Running:
            server_status = 'Online'
        else:
            server_status = 'Offline'

        embed_color = 0x71368a
        if db_server.Discord_Role != None:
            db_server_role = context.guild.get_role(int(db_server.Discord_Role))
            if db_server_role != None:
                embed_color = db_server_role.color

        server_name = server.FriendlyName
        if server.DisplayName != None:
            server_name = db_server.DisplayName

        embed=discord.Embed(title= f"{server_name} - [{server.TargetName}]", description=f'Instance Server Status: **{instance_status}**', color=embed_color)
        
        avatar = await self.uBot.validate_avatar(db_server)
        if avatar != None:
            embed.set_thumbnail(url=avatar)

        embed.add_field(name='**Dedicated Server Status**:', value= server_status, inline= True)

        if db_server.Host != None:
            embed.add_field(name=f'Host: ', value=db_server.Host, inline=False)

        #embed.add_field(name='\u1CBC\u1CBC',value='\u1CBC\u1CBC',inline=False)
        embed.add_field(name='Donator Only:', value= str(bool(db_server.Donator)), inline=True)
        embed.add_field(name='Whitelist Open:' , value= str(bool(db_server.Whitelist)), inline=True)
        #embed.add_field(name='\u1CBC\u1CBC',value='\u1CBC\u1CBC',inline=False) #This Generates a BLANK Field entirely.

        if server.ADS_Running:
            embed.add_field(name='TPS', value=TPS, inline=True)
            embed.add_field(name='Player Count', value=f'{Users[0]}/{Users[1]}', inline=True)
            embed.add_field(name='Memory Usage', value=f'{Memory[0]}/{Memory[1]}', inline=False)
            embed.add_field(name='CPU Usage', value=f'{CPU}/100%', inline=True)
            #!UPTIME is disabled until AMP Impliments the feature.
            #embed.add_field(name='Uptime', value=Uptime, inline=True)
            embed.add_field(name='Players Online', value=Users_Online, inline=False)
        return embed
                
    async def server_whitelist_embed(self, context:commands.Context, server:AMP.AMPInstance) -> discord.Embed:
        """Default Embed Reply for Successful Whitelist requests"""
        db_server = self.DB.GetServer(InstanceID= server.InstanceID)

        embed_color = 0x71368a
        #Lightning: Another example of inverted logic helps with extra indentation
        #granted nothing has been seen that is extremely indented so not bad
        if db_server != None:
            if db_server.Discord_Role != None:
                db_server_role = context.guild.get_role(int(db_server.Discord_Role))
                if db_server_role != None:
                    embed_color = db_server_role.color

            User_list = None
            if len(server.getUserList()) > 1:
                User_list = (', ').join(server.getUserList())

            server_name = server.FriendlyName
            if server.DisplayName != None:
                server_name = db_server.DisplayName

            embed=discord.Embed(title=f'**=======  {server_name}  =======**',description= db_server.Description, color=embed_color)
            avatar = await self.uBot.validate_avatar(db_server)
            if avatar != None:
                embed.set_thumbnail(url=avatar)

            embed.add_field(name='**Host**:', value= str(db_server.Host), inline=True)
            embed.add_field(name='Users Online:' , value=str(User_list), inline=False)
            return embed
            
    def bot_settings_embed(self, context:commands.Context) -> discord.Embed:
        """Default Embed Reply for command /bot settings, please pass in a List of Dictionaries eg {'setting_name': 'value'}"""

        dbsettings_list = self.DBConfig.GetSettingList()
        settings = {}
        for setting in dbsettings_list:
            #Lightning: these two lines could be combined
            config = self.DBConfig.GetSetting(setting)
            settings[setting] = config

        embed=discord.Embed(title= f'**Bot Settings**', color= 0x71368a)
        embed.set_thumbnail(url= context.guild.icon)
        embed.add_field(name='\u1CBC\u1CBC', value='\u1CBC\u1CBC', inline= False)
        #Lightning: this could be altered to avoid the loop above, maybe something like...
        #for key in self.DBConfig.GetSettingList():
        #  value = self.dBConfig.GetSetting(key)
        #  ...
        #
        #avoids making the dictionary and in a lot of ways simplifies the logic when attempting to understand it
        for key, value in settings.items():
            if type(value) == str and value != 'None' and  value.isnumeric():
                value = int(value)
                embed.add_field(name= f'{key.replace("_"," ")}', value= value, inline= False)

            #Lightning: If you don't care about the original capitalization of key then just do
            #key = key.lower()
            #and check key, also if/elif/elif/elif/... logic
            if key.lower() == 'whitelist_wait_time':
                embed.add_field(name= 'Whitelist Wait Time:', value= f'{value} Minutes', inline= False)

            if key.lower() == 'permissions':
                if value == 0:
                    value = 'Default'
                if value == 1:
                    value = 'Custom'

                embed.add_field(name= 'Permissions:', value= f'{value}', inline= False)
            
            if key.lower() == 'banner_type':
                if value == 0:
                    value = 'Discord Embeds'
                if value == 1:
                    value = 'Custom Banner Images'

                embed.add_field(name= 'Banner Type:', value= f'{value}', inline= False)

            if key.lower() == 'db_version':
                embed.add_field(name= 'SQL Database Version:', value= f'{value}', inline= True)

            if key.lower() == 'bot_version':
                embed.add_field(name= 'Gatekeeper Version:', value= f'{value}', inline= True)

            if key.lower() == 'guild_id':
                if self._client != None and value != 'None':
                    value = self._client.get_guild(value)

                    embed.add_field(name= 'Guild ID:', value= f'{value.name if value != None else value}', inline= False)

            if key.lower() == 'moderator_role_id':
                if value != 'None':
                    value = context.guild.get_role(value)
               
                embed.add_field(name= 'Moderator Role:', value= f'{value.name if value != None else value}', inline= False)
                
            if key.lower() == 'whitelist_request_channel':
                if value != 'None':
                    value = context.guild.get_channel(value)
                
                embed.add_field(name= 'Whitelist Request Channel', value= f'{value.name if value != None else value}', inline= False)

            #Lightning: If the logic above handled a string of value that isn't none and is an int then how does this
            #ever pass? This is now int compared to str
            #also, should this be under an else statement when key doesn't match anything else?
            if value == '0' or value == '1':
                value = bool(value)
                embed.add_field(name= f'{list(key).replace("_", " ")}', value= f'{value}', inline= False)

        return embed

    def user_info_embed(self, db_user:DB.DBUser, discord_user:discord.User)-> discord.Embed:
        embed=discord.Embed(title=f'{discord_user.name}',description=f'**Discord ID**: {discord_user.id}', color=discord_user.color)
        embed.set_thumbnail(url= discord_user.avatar.url)
        embed.add_field(name='In Database:', value=f'{"True" if db_user != None else "False"}')
        if db_user != None:
            if db_user.MC_IngameName != None:
                embed.add_field(name='Minecraft IGN:', value=f'{db_user.MC_IngameName}', inline= False)

            if db_user.MC_UUID != None:
                embed.add_field(name='Minecraft UUID:', value=f'{db_user.MC_UUID}', inline= True)

            if db_user.SteamID != None:
                embed.add_field(name='Steam ID:', value=f'{db_user.SteamID}', inline=False)

            if db_user.Role != None:
                embed.add_field(name='Permission Role:', value=f'{db_user.Role}', inline=False)
                
        return embed