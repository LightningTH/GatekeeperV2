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
import sqlite3
import pathlib
import datetime
import json
import time
import logging
import sys

from AMP import AMPInstance

def dump_to_json(data):
    for entry in data:
        if type(data[entry]) == datetime.datetime:
            data[entry] = data[entry].isoformat()
        elif type(data[entry]) == bool:
            data[entry] = int(data[entry])
    return json.dumps(data)

Handler = None
#!DB Version
DB_Version = 2.7

class DBHandler():
    def __init__(self):
        global DB_Version
        self.logger = logging.getLogger(__name__)
        self.DB = Database(Handler = self)
        self.DBConfig = self.DB.DBConfig
        self.SuccessfulDatabase = True
        self.Bot_Version = ''
        self.bot_sync_required = False

        #Always update this value when changing Tables!
        self.DB_Version = DB_Version

        #self.DBConfig.SetSetting('DB_Version', 2.5)
        #This should ONLY BE TRUE on new Database's going forward. 
        if self.DBConfig.GetSetting('DB_Version') == None and self.DB.DBExists:
            DBUpdate(self.DB, 1.0)
            return

        #This is to handle 1.0.0 Converting to new DB Version systems.
        if type(self.DBConfig.GetSetting('DB_Version')) == str and self.DBConfig.GetSetting('DB_Version') == '1.0.0':
            self.DBConfig.SetSetting('DB_Version', '1.0')

        #This handles version checks and calling all updates from version 1.0
        if self.DB_Version > float(self.DBConfig.GetSetting('DB_Version')):
            self.logger.warn(f"**ATTENTION** Gatekeeperv2 Database is on Version: {self.DB_Version}, your Database is on Version: {self.DBConfig.GetSetting('DB_Version')}")
            self.DBUpdate = DBUpdate(self.DB, float(self.DBConfig.GetSetting('DB_Version')))
        
        self.logger.info(f'DB Handler Initialization...DB Version: {self.DBConfig.GetSetting("DB_Version")}')

    def dbServerConsoleSetup(self,server:AMPInstance):
        """This sets the DB Server Console_Flag, Console_Filtered and Discord_Console_Channel to default values"""
        self.DB_Server = self.DB.GetServer(server.InstanceID)
        try:
            self.DB_Server.Console_Flag = True
            self.DB_Server.Console_Filtered = True
            self.DB_Server.Discord_Console_Channel = None #Should be a str, can be an int. eg 289450670581350401
        except:
            self.logger.warning(f'**ATTENTION** DBConfig Default Console Settings have been set for {server.FriendlyName}')

def getDBHandler() -> DBHandler:
    global Handler
    if Handler == None:
        Handler = DBHandler()
    return Handler

class Database:
    def __init__(self, Handler=None):
        self.DBExists = False

        db_file = pathlib.Path("discordBot.db")
        if pathlib.Path.exists(db_file):
            self.DBExists = True


        if Handler:
            self.DBHandler = Handler
        else:
            self.DBHandler = getDBHandler()

        self._db = sqlite3.connect("discordBot.db", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        if not self.DBExists:
            self._InitializeDatabase()
            # self._InitializeDefaultData()
        self.DBConfig = self.GetConfig()

    def _InitializeDatabase(self):
        global DB_Version
        cur = self._db.cursor()

        cur.execute("""create table Servers (
                        ID integer primary key,
                        InstanceID text not null unique collate nocase,
                        InstanceName text,
                        FriendlyName text,
                        DisplayName text,
                        Host text,
                        Whitelist integer not null,
                        Whitelist_disabled integer not null,
                        Donator integer not null,
                        Console_Flag integer not null,
                        Console_Filtered integer not null,
                        Console_Filtered_Type integer not null,
                        Discord_Console_Channel text nocase,
                        Discord_Chat_Channel text nocase,
                        Discord_Chat_Prefix text,
                        Discord_Event_Channel text nocase,
                        Discord_Role text collate nocase,
                        Avatar_url text,
                        Hidden integer not null
                        )""")

        cur.execute("""create table RegexPatterns (
                        ID integer primary key,
                        Name text unique not null,
                        Type integer not null,
                        Pattern text unique not null
                        )""")

        cur.execute("""create table ServerRegexPatterns (
                        ServerID integeter not null,
                        RegexPatternID integer not null,
                        foreign key (RegexPatternID) references RegexPatterns(ID),
                        foreign key(ServerID) references Servers(ID)
                        UNIQUE(ServerID, RegexPatternID)
                        )""")

        cur.execute("""create table Users (
                        ID integer primary key,
                        DiscordID text not null unique collate nocase,
                        DiscordName text collate nocase,
                        MC_IngameName text unique collate nocase,
                        MC_UUID text unique collate nocase,
                        SteamID text unique collate nocase,
                        Role text collate nocase
                        )""")

        cur.execute("""create table ServerDisplayBanners (
                        ID integer primary key,
                        Discord_Guild_ID text nocase,
                        Discord_Channel_ID text nocase,
                        Discord_Message_ID text nocase
                        )""")

        cur.execute("""create table ServerBanners (
                        ServerID integer not null,
                        background_path text,
                        blur_background_amount integer,
                        color_header text,
                        color_body text,
                        color_Host text,
                        color_whitelist_open text,
                        color_whitelist_closed text,
                        color_donator text,
                        color_status_online text,
                        color_status_offline text,
                        color_player_limit_min text,
                        color_player_limit_max text,
                        color_player_online text,
                        foreign key(ServerID) references Servers(ID)
                        )""")

        cur.execute("""create table WhitelistReply (
                        ID integer primary key,
                        Message text
                        )""")

        cur.execute("""create table Log (
                        ID integer primary key,
                        Log text not null,
                        LogDate timestamp default (datetime('now'))
                        )""")

        cur.execute("""create table Config (
                        ID integer primary key,
                        Name text not null unique,
                        Value text
                        )""")

        self._db.commit()

        #Any Default Config Settings should go here during INIT.
        #Still keep the ones in Update; just in case existing DBs need updating.
        self._AddConfig('DB_Version', DB_Version)
        self._AddConfig('Guild_ID', None)
        self._AddConfig('Moderator_role_id', None)
        self._AddConfig('Permissions', 0) #0 = Default | 1 = Custom
        self._AddConfig('Server_Info_Display', None)
        self._AddConfig('Whitelist_Request_Channel', None)
        self._AddConfig('WhiteList_Wait_Time', 5)
        self._AddConfig('Auto_Whitelist', False)
        #self._AddConfig('Whitelist_Emoji_Pending', ':arrows_counterclockwise:')
        #self._AddConfig('Whitelist_Emoji_Done', ':ballot_box_with_check:')
        self._AddConfig('Banner_Auto_Update', True)
        self._AddConfig('Banner_Type', 0) #0 = Discord embeds | 1 = Custom Banner Images
        self._AddConfig('Bot_Version', None)
        self._AddConfig('Message_Timeout', 60)

    def _execute(self, SQL, params):
        Retry = 0

        while(1):
            try:
                cur = self._db.cursor()
                cur.execute(SQL, params)
                cur.close()
                self._db.commit()
                return

            except sqlite3.OperationalError as ex:
                # if locked then try up to 3 times before bailing
                if Retry == 3:
                    raise Exception(ex)
                Retry += 1
                time.sleep(0.1)
                continue

            except Exception as e:
                raise e

    def _fetchone(self, SQL, params):
        cur = self._db.cursor()
        cur.execute(SQL, params)
        return (cur.fetchone(), cur)

    def _fetchall(self, SQL, params):
        cur = self._db.cursor()
        cur.execute(SQL, params)
        return (cur.fetchall(), cur)

    def _logdata(self, data):
        self._execute("insert into log(log) values(?)", (data,))

    def _UpdateServer(self, dbserver, **args):
        # get the property to update
        entry = list(args.keys())[0]
        self._execute(f"Update servers set {entry}=? where ID=?", (args[entry], dbserver.ID))
        jdata = dump_to_json({"Type": "ServerUpdate", "ServerID": dbserver.ID, "Field": entry, "Value": args[entry]})
        self._logdata(jdata)
    
    def _UpdateBanner(self, dbbanner, **args):
        entry = list(args.keys())[0]
        self._execute(f"Update ServerBanners set {entry}=? where ServerID=?", (args[entry], dbbanner.ServerID))
        jdata = dump_to_json({"Type": "BannerUpdate", "ServerID": dbbanner.ServerID, "Field": entry, "Value": args[entry]})
        self._logdata(jdata)

    def _UpdateUser(self, dbuser, **args):
        # get the property to update
        entry = list(args.keys())[0]
        self._execute(f"Update users set {entry}=? where ID=?", (args[entry], dbuser.ID))
        jdata = dump_to_json({"Type": "UserUpdate", "UserID": dbuser.ID, "Field": entry, "Value": args[entry]})
        self._logdata(jdata)

    def AddServer(self, InstanceID:str, InstanceName:str= None, FriendlyName:str = None): 
        return DBServer(db=self, InstanceID= InstanceID, InstanceName= InstanceName, FriendlyName= FriendlyName)
    
    def GetServer(self, InstanceID: str = None):
        if not InstanceID:
            return None

        (row, cur) = self._fetchone("select ID from Servers where InstanceID=?", (InstanceID,))
        if not row:
            cur.close()
            return None
        # create a new server to return and let the object populate itself
        ret = DBServer(ID=int(row["ID"]), db=self)

        cur.close()
        return ret
    
    def GetAllServers(self):
        """Gets all Servers current in the DB"""
        serverlist = {}
        SQLArgs = []
        
        (rows, cur) = self._fetchall("Select ID from Servers", tuple(SQLArgs))
        for entry in rows:
            Server = DBServer(self, ID=entry["ID"])
            serverlist[Server.InstanceID] = ('InstanceName: ' + Server.InstanceName)

        cur.close()
        return serverlist

    def GetUser(self, value:str):
        """Finds a User using either DiscordID, DiscordName, MC_InGameName, MC_UUID, or SteamID."""
        #find the user
        (row, cur) = self._fetchone(f"select ID from Users where DiscordID=? or DiscordName=? or MC_IngameName=? or MC_UUID=? or SteamID=?", (value,value,value,value,value))
        if not row:
            cur.close()
            return None

        # create a new user object to return and let the object populate itself
        ret = DBUser(ID=int(row["ID"]), db=self)

        cur.close()
        return ret

    def AddUser(self, DiscordID: str = None, DiscordName: str = None, MC_IngameName: str = None, MC_UUID: str = None, SteamID: str = None):
        try:
            return DBUser(db=self, DiscordID=DiscordID, DiscordName=DiscordName, MC_IngameName=MC_IngameName, MC_UUID=MC_UUID, SteamID=SteamID)
        except Exception as e:
            print('DBUser error', e)
            return None

    def GetAllUsers(self):
        # get all servers that we are on
        SQL = "Select ID from Users"
        SQLWhere = []
        SQLArgs = []

        if len(SQLWhere):
            SQL = SQL + " where " + " and ".join(SQLWhere)

        (rows, cur) = self._fetchall(SQL, tuple(SQLArgs))
        ret = []
        for entry in rows:
            User = DBUser(self, ID=entry["ID"])
            ret.append(User)

        cur.close()
        return ret

    def AddRegexPattern(self, Name:str, Pattern:str, Type:int)-> bool:
        """Adds a entry to table RegexPatterns, else Updates a matching pattern."""
        try:
            self._execute("INSERT into RegexPatterns(Name, Type, Pattern) values(?, ?, ?)", (Name, Type, Pattern))
        except Exception as e:
            print(e)
            return False
        return True
    
    def DelRegexPattern(self, ID:int=None, Name:str=None)-> bool:
        """Removes a entry RegexPatterns Table using either its `Name` or `ID`"""
        if ID == None:
            (row ,cur) = self._fetchone("SELECT ID from RegexPatterns WHERE Name=?", (Name,))
            if not row:
                cur.close()
                return False
            ID = row["ID"]
            cur.close()
        try:
            self._execute("DELETE from ServerRegexPatterns WHERE RegexPatternID =?",(ID,))
        except Exception as e:
            print(e)
            
        self._execute("DELETE from RegexPatterns WHERE ID=?", (ID,))
        return True
       
    def GetRegexPattern(self, ID:int=None, Name:str=None):
        """Returns RegexPatterns Table \n
        Returns `row['ID'] = {'Name': row['Name'], 'Type': row['Type'], 'Pattern': row['Pattern']}`
        """
        (row ,cur) = self._fetchone("SELECT ID, Name, Type, Pattern from RegexPatterns WHERE Name=? or ID=?", (Name, ID))
        if not row:
            cur.close()
            return False

        regex = {'ID': row['ID'], 'Name': row['Name'], 'Type': row['Type'], 'Pattern': row['Pattern']}
        cur.close()
        return regex

    def UpdateRegexPattern(self, Pattern:str= None, Type:int= None, ID:int= None, Pattern_Name:str= None, Name:str= None)-> bool:
        """Update a Regex Pattern in the RegexPatterns Table using either its `Name` or `ID`"""
        if ID == None:
            (row ,cur) = self._fetchone("SELECT ID from RegexPatterns WHERE Name=?", (Pattern_Name,))
            if not row:
                cur.close()
                return False
            ID = row["ID"]
            cur.close()

        SQL = "UPDATE RegexPatterns SET "
        SQL_Val = ''
        SQLArgs = []

        args = locals()
        for arg in args:
            if args[arg] != None and arg in ['Pattern', 'Type', 'Name']: 
                if len(SQL_Val):
                    SQL_Val = SQL_Val + ','

                SQL_Val = SQL_Val + f'{arg}=? '
                SQLArgs.append(args[arg])
            
                
        SQL = SQL + SQL_Val + 'WHERE ID=?'
        SQLArgs.append(ID) #Need to append ID last.
        self._execute(SQL, tuple(SQLArgs))
        return True

    def GetAllRegexPatterns(self):
        """Gets all Regex Patterns from the RegexPatterns Table. \n
        Returns `dict[entry['ID']] = {'Name': entry['Name'], 'Type': entry['Type'], 'Pattern': entry['Pattern']}`"""
        regex_patterns = {}
        SQLArgs = []
        (rows, cur) = self._fetchall("SELECT ID, Name, Type, Pattern FROM RegexPatterns ORDER BY ID", tuple(SQLArgs))
        for entry in rows:
            regex_patterns[entry['ID']] = {'Name': entry['Name'], 'Type': entry['Type'], 'Pattern': entry['Pattern']}

        cur.close()
        return regex_patterns
        
    def GetAllWhitelistReplies(self):
        """Gets all Whitelist Replies currently in the DB"""
        whitelist_replies = []
        SQLArgs = []
        
        (rows, cur) = self._fetchall("Select ID, Message from WhitelistReply order by ID", tuple(SQLArgs))
        for entry in rows:
            #reply = {'ID' : entry["ID"], 'Message' : entry["Message"]}
            #reply = {entry["Message"]}
            whitelist_replies.append(entry['Message'])

        cur.close()
        return whitelist_replies

    def AddWhitelistReply(self, Message:str=None):
        """Adds a Whitelist Reply to the DB"""
        self._execute("insert into WhitelistReply(Message) values(?)", (Message,))
        return 

    def DeleteWhitelistReply(self, Message:str=None):
        """Deletes a Whitelist Reply from the DB"""
        self._execute("delete from WhitelistReply where Message=?", (Message,))
        return
       
    def AddServerDisplayBanner(self, Discord_Guild_ID:int, Discord_Channel_ID:int, Discord_Message_List:list[int]):
        """Adds a Server Banner to the DB"""
        self._execute("delete from ServerDisplayBanners where Discord_Guild_ID=? and Discord_Channel_ID=?", (Discord_Guild_ID, Discord_Channel_ID))
        for message_id in Discord_Message_List:
            self._execute("insert into ServerDisplayBanners(Discord_Guild_ID, Discord_Channel_ID, Discord_Message_ID) values(?,?,?)", (Discord_Guild_ID, Discord_Channel_ID, message_id))
        return

    def DelServerDisplayBanner(self, Discord_Guild_ID:int, Discord_Channel_ID:int):
        """Delete a Server Banner for a specific channel in the DB"""
        self._execute("delete from ServerDisplayBanners where Discord_Guild_ID=? and Discord_Channel_ID=?", (Discord_Guild_ID, Discord_Channel_ID))
        return

    def GetServerDisplayBanner(self) -> list[dict]:
        """Gets a Server Banner from the DB
        `{"GuildID": entry["Discord_Guild_ID"], "ChannelID": entry["Discord_Channel_ID"], "MessageID": entry["Discord_Message_ID"]}`"""
        SQL = "Select * from ServerDisplayBanners order by ID"
        SQLArgs = []
        (rows, cur) = self._fetchall(SQL, tuple(SQLArgs))
        ret = []
        for entry in rows:
            ret.append({"GuildID": int(entry["Discord_Guild_ID"]), "ChannelID": int(entry["Discord_Channel_ID"]), "MessageID": int(entry["Discord_Message_ID"])})
        cur.close()
        return ret

    def _AddConfig(self, Name, Value):
        self._execute("Insert into config(Name, Value) values(?, ?)", (Name, Value))
        (ret, cur) = self._fetchone("Select ID from Config where Name=?", (Name,))
        if not ret:
            return None
        ID = int(ret["ID"])
        cur.close()
        jdata = dump_to_json({"Type": "AddConfig", "Name": Name, "Value": Value})
        self._logdata(jdata)
        return ID

    def GetConfig(self):
        return DBConfig(self)

    def _DeleteConfig(self, ConfigID, ConfigName):
        self._execute("Delete from Config where ID=?", (ConfigID,))
        jdata = dump_to_json({"Type": "DeleteConfig", "Name": ConfigName})
        self._logdata(jdata)

    def _UpdateConfig(self, ID, Name, Value):
        self._execute("Update Config set Value=? where ID=?", (Value, ID))
        jdata = dump_to_json({"Type": "UpdateConfig", "Name": Name, "Value": Value})
        self._logdata(jdata)

    def GetLog(self, AfterTime:datetime.datetime=None, BeforeTime:datetime.datetime=None, StartingID:int=None, Limit:int=100):
        SQL = "Select L.ID, L.Log, L.LogDate from Log L"
        Params = []
        if StartingID or AfterTime or BeforeTime:
            NeedAND = False
            SQL += " Where "
            if StartingID:
                SQL += " L.ID >= ? "
                Params.append(StartingID)
                NeedAND = True
            if AfterTime:
                if NeedAND:
                    SQL += " and "
                SQL += " L.LogDate > "
                Params.append(AfterTime)
                NeedAND = True
            if BeforeTime:
                if NeedAND:
                    SQL += " and "
                SQL += " L.LogDate < "
                Params.append(BeforeTime)
                NeedAND = True
        SQL += " order by L.LogDate "
        if Limit:
            SQL += " Limit ?"
            Params.append(Limit)

        NeededUsers = []
        NeededServers = []
        (rows, cur) = self._fetchall(SQL, tuple(Params))
        ret = []
        for entry in rows:
            logentry = {}
            logentry["ID"] = entry["ID"]
            logentry["Log"] = json.loads(entry["Log"])
            logentry["Date"] = entry["LogDate"]
            ret.append(logentry)

            # if we have a userid, serverid, or modid in the log json then store it as needed
            if ("UserID" in logentry["Log"]) and (logentry["Log"]["UserID"] not in NeededUsers):
                NeededUsers.append(logentry["Log"]["UserID"])
            if ("ModID" in logentry["Log"]) and (logentry["Log"]["ModID"] not in NeededUsers):
                NeededUsers.append(logentry["Log"]["ModID"])
            if ("ServerID" in logentry["Log"]) and (logentry["Log"]["ServerID"] not in NeededServers):
                NeededServers.append(logentry["Log"]["ServerID"])

        cur.close()

        # go get all of the users to fill in
        Users = {}
        while len(NeededUsers):
            Count = len(NeededUsers)
            if len(NeededUsers) > 50:
                Count = 50
            qentries = ("?,"*Count)[:-1]
            Params = tuple(NeededUsers[0:Count])
            NeededUsers = NeededUsers[Count:]
            (rows, cur) = self._fetchall(f"Select ID, DiscordID, DiscordName, IngameName, UUID from Users where ID in ({qentries})", tuple(Params))
            for entry in rows:
                Users[int(entry["ID"])] = {"DiscordID": int(entry["DiscordID"]), "DiscordName": entry["DiscordName"], "IngameName": entry["IngameName"], "UUID": entry["UUID"]}
            cur.close()

        # get servers
        Servers = {}
        while len(NeededServers):
            Count = len(NeededServers)
            if len(NeededServers) > 50:
                Count = 50
            qentries = ("?,"*Count)[:-1]
            Params = tuple(NeededServers[0:Count])
            NeededServers = NeededServers[Count:]
            (rows, cur) = self._fetchall(f"Select ID, InstanceName from Servers where ID in ({qentries})", tuple(Params))
            for entry in rows:
                Servers[int(entry["ID"])] = entry["InstanceName"]
            cur.close()

        # now update all log entries
        for entry in ret:
            if "UserID" in entry["Log"]:
                UID = int(entry["Log"]["UserID"])
                if UID in Users:
                    entry["Log"].pop("UserID")
                    entry["Log"]["User_DiscordID"] = int(Users[UID]["DiscordID"])
                    entry["Log"]["User_DiscordName"] = Users[UID]["DiscordName"]
                    entry["Log"]["User_IngameName"] = Users[UID]["IngameName"]
            if "ModID" in entry["Log"]:
                MID = int(entry["Log"]["ModID"])
                if MID in Users:
                    entry["Log"].pop("ModID")
                    entry["Log"]["Mod_DiscordID"] = int(Users[MID]["DiscordID"])
                    entry["Log"]["Mod_DiscordName"] = Users[MID]["DiscordName"]
                    entry["Log"]["Mod_IngameName"] = Users[MID]["IngameName"]
            if "ServerID" in entry["Log"]:
                if entry["Log"]["ServerID"] in Servers:
                    entry["Log"]["Server"] = Servers[int(entry["Log"]["ServerID"])]
                    entry["Log"].pop("ServerID")

        return ret

class DBUser:
    def __init__(self, db:Database, ID:int=None, DiscordID:str=None, DiscordName:str=None, MC_IngameName:str=None, MC_UUID:str=None, SteamID:str=None, Role:str=None):
        #set defaults
        Params = locals()
        Params.pop("self")
        Params.pop("db")
        Params.pop("__class__")
        super().__setattr__("_db", db)
        for entry in Params:
            super().__setattr__(entry, Params[entry])

        #if given a database and ID then look up our values
        if ID:
            (row, cur) = self._db._fetchone("Select * From Users where ID=?", (ID,))
            if row:
                for entry in row.keys():
                    super().__setattr__(entry, row[entry])
            else:
                raise Exception(f"Unable to locate User ID {ID}")
            cur.close()
            super().__setattr__("ID", int(self.ID))
            #super().__setattr__("DiscordID", int(self.DiscordID))
        else:
            #we should have a discord id
            if not DiscordID or DiscordID == 0:
                raise Exception("Missing discord ID on new user")

            #add user to the database
            DBFields = Params

            #create the sql line
            SQL = "insert into users ("
            SQLVars = []

            for entry in DBFields:
                if DBFields[entry] != None:
                    SQL += entry + ","
                    SQLVars.append(DBFields[entry])

            SQL = SQL[:-1] + ") values (" + ("?,"*len(SQLVars))[:-1] + ")"
            #create the tuple needed
            SQLTuple = tuple(SQLVars)
            
            #execute it
            self._db._execute(SQL, SQLTuple)

            #now find the ID
            (row, cur) = self._db._fetchone("Select ID From Users where DiscordID=?", (DiscordID,))
            if row:
                super().__setattr__("ID", int(row["ID"]))
            else:
                raise Exception(f"Unable to locate new user with Discord ID {DiscordID}")
            cur.close()

            jdata = dump_to_json({"Type": "AddUser", "UserID": self.ID})
            self._db._logdata(jdata)

        super().__setattr__("DiscordID", int(self.DiscordID))

    def __setattr__(self, name: str, value):
        if (name == "ID") or (name[0] == "_"):
            return
 
        elif name == "DiscordID":
            # conver to int
            value = int(value)

        # set value and update the user
        super().__setattr__(name, value)
        self._db._UpdateUser(self, **{name: value})

class DBServer:
    """DB Server Attributes:
        `InstanceID: str` \n
        `InstanceName: str` \n
        `FriendlyName: str` \n
        `DisplayName: str` \n
        `Description: str` \n
        `Host: str` \n
        `Whitelist: bool (0/1)` \n
        `Whitelist_disabled: bool` \n
        `Donator: bool (0/1)` \n
        `Discord_Console_Channel: int` \n
        `Discord_Chat_Channel: int` \n
        `Discord_Chat_Prefix: str` \n
        `Discord_Event_Channel: int` \n
        `Discord_Role: int` \n
        `Console_Flag: bool (0/1)` \n
        `Console_Filtered: bool (0/1)` \n
        `Console_Filtered_Type: integer (0 = Blacklist| 1 = Whitelist)` \n
        `Avatar_url: str` \n
        `Hidden: bool (0/1)` \n
        """
    def __init__(self, db: Database, ID: int = None, InstanceID: str = None, InstanceName: str = None, FriendlyName: str = None):
        # set defaults
        Params = locals()
        Params.pop("self")
        Params.pop("db")
        Params.pop("__class__")
        super().__setattr__("_db", db)
        server_attr = {'DisplayName': None,
                        'Description': None, 
                        'Host': '192.168.1.1', 
                        'Whitelist': False, 
                        'Whitelist_disabled': 0, 
                        'Donator': 0, 
                        'Console_Flag': 1,
                        'Console_Filtered': 0,
                        'Console_Filtered_Type': 0,
                        'Discord_Console_Channel': None,
                        'Discord_Chat_Channel': None,
                        'Discord_Chat_Prefix': None,
                        'Discord_Event_Channel': None,
                        'Discord_Role': None,
                        'Avatar_url': None,
                        'Hidden': 0
                        }
        
        for key, value  in server_attr.items():
            super().__setattr__(key, value)

        for entry in Params:
            super().__setattr__(entry, Params[entry])

        if(self.ID is not None):
            super().__setattr__("ID", int(self.ID))

        # if given a database and ID then look up our values
        if ID:
            (row, cur) = self._db._fetchone("Select * From Servers where ID=?", (ID,))
            if row:
                for entry in row.keys():
                    super().__setattr__(entry, row[entry])
            else:
                raise Exception(f"Unable to locate Server ID {ID}")
            cur.close()
        else:
            # we should have an InstanceID
            if not InstanceID or (not len(InstanceID)):
                raise Exception("Missing friendly name on server")

            # add server to the database after making sure the friendly name isn't already used as a nickname
            server = self._db.GetServer(InstanceID)
            if server:
                raise Exception("InstanceID already found")

           # DBFields = Params

            # create the sql line
            SQL = "insert into Servers ("
            SQLVars = []

            for key, value in Params.items():
                if value is not None:
                    SQL += key + ","
                    SQLVars.append(value)
            
            for key, value in server_attr.items():
                if value is not None:
                    SQL += key + ","
                    SQLVars.append(value)

            SQL = SQL[:-1] + ") values (" + ("?," * len(SQLVars))[:-1] + ")"
            # create the tuple needed
            SQLTuple = tuple(SQLVars)

            # execute it
            self._db._execute(SQL, SQLTuple)

            # now find the ID
            (row, cur) = self._db._fetchone("Select ID From Servers where InstanceID=?", (InstanceID,))
            if row:
                super().__setattr__("ID", int(row["ID"]))
            else:
                raise Exception(f"Unable to locate new server with InstanceID {InstanceID}")
            cur.close()

            jdata = dump_to_json({"Type": "AddServer", "ServerID": self.ID, "InstanceID": InstanceID})
            self._db._logdata(jdata)

        if(self.Discord_Console_Channel is not None):
            super().__setattr__("Discord_Console_Channel", int(self.Discord_Console_Channel))
        if(self.Discord_Chat_Channel is not None):
            super().__setattr__("Discord_Chat_Channel", int(self.Discord_Chat_Channel))
        if(self.Discord_Event_Channel is not None):
            super().__setattr__("Discord_Event_Channel", int(self.Discord_Event_Channel))
        if(self.Discord_Role is not None):
            super().__setattr__("Discord_Role", int(self.Discord_Role))
        
    def __setattr__(self, name: str, value):
        if (name in ["ID"]) or (name[0] == "_"):
            return

        elif name in ["Whitelist", "Donator", "Console_Flag", "Console_Filtered"]:
            # convert to bool
            value = bool(value)
    
        elif name in ["Discord_Console_Channel", "Discord_Chat_Channel", "Discord_Event_Channel", "Discord_Role", "Console_Filtered_Type"]:
            if value is not None:
                value = int(value)

        # set value and update the user
        super().__setattr__(name, value)
        self._db._UpdateServer(self, **{name: value})

    def delServer(self):
        #self._db._execute("delete from ServerNicknames where ServerID=?", (self.ID,))
        self._db._execute("delete from Servers where ID=?", (self.ID,))

    def setDisplayName(self, DisplayName: str):
        try:
            self._db._execute("update Servers set DisplayName=? where ID=?", (DisplayName, self.ID))
        except:
            return False
        jdata = dump_to_json({"Type": "UpdateServerDisplayName", "ServerID": self.ID, "DisplayName": DisplayName})
        self._db._logdata(jdata)

    def getBanner(self, background_path:str = None):
        return DBBanner(self._db, self.ID, background_path)

    def AddServerRegexPattern(self, ID:int= None, Name:str=None):
        """Adds the provided RegexPattern ID/Name to the ServerRegexPatterns Table."""
        if ID == None:
            (row ,cur) = self._db._fetchone("SELECT ID from RegexPatterns WHERE Name=?", (Name,))
            if not row:
                cur.close()
                return False
            ID = row["ID"]

        try:
            self._db._execute("INSERT into ServerRegexPatterns (RegexPatternID, ServerID) values(?,?)", (ID, self.ID))

        except Exception as e:
            print(e)
            return False
        return True
        
    def DelServerRegexPattern(self, ID:int= None, Name:str= None):
        """Removes the provided RegexPattern ID/Name from the ServerRegexPatterns Table."""
        if ID == None:
            (row ,cur) = self._db._fetchone("SELECT ID from RegexPatterns WHERE Name=?", (Name,))
            if not row:
                cur.close()
                return False
            ID = row["ID"]

        self._db._execute("DELETE from ServerRegexPatterns where RegexPatternID=? and ServerID=?", (ID, self.ID))
        return True
        
    def GetServerRegexPatterns(self):
        """Gets all Regex Patterns related to Server \n
        Returns `dict['ID': {'Name': entry['Name'], 'Type': entry['Type'], 'Pattern': entry['Pattern']}]`"""
        regex_patterns = {}
        SQLArgs = []
        (rows, cur) = self._db._fetchall("SELECT RP.ID, RP.Name, RP.Type, RP.Pattern FROM ServerRegexPatterns SRP, RegexPatterns RP WHERE SRP.ServerID=? and SRP.RegexPatternID = RP.ID", (self.ID,))
        for entry in rows:
            regex_patterns[entry['ID']] = {'Name': entry['Name'], 'Type': entry['Type'], 'Pattern': entry['Pattern']}
        
        cur.close()
        return regex_patterns

class DBConfig:
    def __init__(self, db: Database = None):
        # set defaults
        Params = locals()
        Params.pop("self")
        Params.pop("db")
        super().__setattr__("_db", db)

        # get the known config settings
        super().__setattr__("_ConfigNameToID", {})
        (rows, cur) = self._db._fetchall("Select ID, Name, Value from Config", ())
        for entry in rows:
            self._ConfigNameToID[entry["Name"].capitalize()] = entry["ID"]
            super().__setattr__(entry["Name"].capitalize(), entry["Value"])
        cur.close()

    def __setattr__(self, name, value):
        if name in self._ConfigNameToID:
            if type(value) == bool:
                value = int(value)
            super().__setattr__(name, value)
            self._db._UpdateConfig(self._ConfigNameToID[name], name, value)

    def __getattribute__(self, name):
        val = super().__getattribute__(name)
        if name == "_ConfigNameToID":
            return val

        if name == 'Message_Timeout':
            if (type(val) == str) and val == 'None':
                val = None

            if (type(val) == str) and val.isnumeric():
                val = int(val)

        if name in self._ConfigNameToID:
            if (type(val) == str) and val.isnumeric():
                val = int(val)
            
        return val

    # list(self._ConfigNameToID.keys())
    def GetSettingList(self):
        settings = list(self._ConfigNameToID.keys())
        return settings

    def SetSetting(self, name: str, value):
        name = name.capitalize().replace(" ", "_").replace("-", "_")
        if name not in self._ConfigNameToID:
            self.AddSetting(name, value)
        else:
            setattr(self, name, value)

    def GetSetting(self, name: str):
        name = name.capitalize().replace(" ", "_").replace("-", "_")
        if name not in self._ConfigNameToID:
            return None
        return getattr(self, name)

    def AddSetting(self, name: str, value):
        name = name.capitalize().replace(" ", "_").replace("-", "_")
        if name not in self._ConfigNameToID:
            super().__setattr__(name, value)
            self._ConfigNameToID[name] = self._db._AddConfig(name, value)

    def DeleteSetting(self, name: str):
        name = name.capitalize()
        if name not in self._ConfigNameToID:
            return
        self._db._DeleteConfig(self._ConfigNameToID[name], name)
        super().__delattr__(name)
        self._ConfigNameToID.pop(name)
 
class DBBanner:
    def __init__(self, DB:Database, ServerID: int= None, background_path:str= None):
        self.attr_list = {'_db': DB,
                    'ServerID': int(ServerID),
                    'background_path': background_path,
                    'blur_background_amount': 2,
                    'color_header': "#85c1e9",
                    'color_body': "#f2f3f4",
                    'color_host': "#5dade2",
                    'color_whitelist_open': "#f7dc6f",
                    'color_whitelist_closed': "#cb4335",
                    'color_donator': "#212f3c",
                    'color_status_online': "#28b463",
                    'color_status_offline': "#e74c3c",
                    'color_player_limit_min': "#ba4a00",
                    'color_player_limit_max': "#5dade2",
                    'color_player_online': "#f7dc6f"}

        for attr in self.attr_list:
            super().__setattr__(attr, self.attr_list[attr])

        (row, cur) = self._db._fetchone("Select * from ServerBanners where ServerID=?", (self.ServerID,))
        if row:
            for entry in row.keys():
                super().__setattr__(entry, row[entry])

        else:
            # create the sql line
            SQL = "insert into ServerBanners ("
            SQLVars = []

            for entry in self.attr_list:
                if entry.startswith('_'):
                    continue
                SQL += entry + ","
                SQLVars.append(self.attr_list[entry])


            SQL = SQL[:-1] + ") values (" + ("?," * len(SQLVars))[:-1] + ")"
            # create the tuple needed
            SQLTuple = tuple(SQLVars)

            # execute it
            self._db._execute(SQL, SQLTuple)

        cur.close()

    def __setattr__(self, name: str, value):

        if name == 'blur_background_amount':
            value = int(value)

        super().__setattr__(name, value)
        
        if name != 'attr_list':
            self._db._UpdateBanner(self, **{name: value})
       
class DBUpdate:
    def __init__(self, DB:Database, Version:float=None):
        self.logger = logging.getLogger(__name__)
        self.DB = DB
        self.DBConfig = self.DB.DBConfig

        if Version == None:
            self.DBConfig.AddSetting('DB_Version', 1.0)

        #Lightning: No comments, debatable. However one of the rare times
        #if without elif for the same variable check makes sense as you need
        #repeated updates
        #I personally prefer the flipped logic as I don't like constants at
        #the beginning of an if statement but have seen other code written with
        #constants first
        #if Version < 1.1:
        if 1.1 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.1')
            self.DBConfig.AddSetting('Guild_ID', None)
            self.DBConfig.AddSetting('Moderator_role_id', None)
            self.DBConfig.AddSetting('Permissions', 0)
            self.DBConfig.AddSetting('Whitelist_Request_Channel', None)
            self.DBConfig.AddSetting('WhiteList_Wait_Time', 5)
            self.DBConfig.AddSetting('Auto_Whitelist', False)
            self.DBConfig.AddSetting('Whitelist_Emoji_Pending', None)
            self.DBConfig.AddSetting('Whitelist_Emoji_Done', None)
            self.DBConfig.SetSetting('DB_Version', '1.1')

        if 1.2 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.2')
            self.user_roles()
            self.DBConfig.SetSetting('DB_Version', '1.2')

        if 1.3 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.3')
            #self.nicknames_unique()
            self.DBConfig.SetSetting('DB_Version', '1.3')

        if 1.4 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.4')
            self.user_Donator_removal()
            self.DBConfig.SetSetting('DB_Version', '1.4')

        if 1.5 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.5')
            self.server_Discord_reaction_removal()
            self.DBConfig.SetSetting('DB_Version', '1.5')

        if 1.6 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.6')
            self.server_Discord_Chat_prefix()
            self.server_Discord_event_channel()
            self.server_Avatar_url()
            #self.DBConfig.AddSetting('Server_Info_Display', None)
            #self.DBConfig.AddSetting('Auto_Display', True)
            self.DBConfig.SetSetting('DB_Version', '1.6')
        
        if 1.7 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.7')
            self.DBConfig.AddSetting('Banner_Auto_Update', True)
            self.server_banner_table()
            self.whitelist_reply_table()
            self.DBConfig.DeleteSetting('Server_Info_Display')
            self.DBConfig.DeleteSetting('Auto_Display')
            self.DBConfig.SetSetting('DB_Version', '1.7')
        
        if 1.8 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.8')
            self.server_hide_column()
            #self.server_ip_constraint_update()
            self.server_display_name_reset()
            #self.server_display_name_constraint_update()
            self.DBConfig.SetSetting('DB_Version', '1.8')

        if 1.9 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 1.9')
            self.banner_table_creation()
            self.DBConfig.SetSetting('DB_Version', '1.9')

        if 2.1 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 2.1')
            self.server_ip_name_change()
            self.DBConfig.SetSetting('DB_Version', '2.1')

        if 2.2 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 2.2')
            self.DBConfig.DeleteSetting('Embed_Auto_Update')
            self.banner_name_conversion()
            self.DBConfig.SetSetting('DB_Version', '2.2')

        if 2.4 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 2.4')
            self.server_table_whitelist_disabled_column()
            self.regex_pattern_table_creation()
            self.server_regex_pattern_table_creation()
            self.server_console_filter_type()
            self.DBConfig.AddSetting('Message_Timeout', 60)
            self.DBConfig.SetSetting('DB_Version', '2.4')

        if 2.5 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 2.5')
            self.DBConfig.AddSetting('Banner_Type', 0)
            self.DBConfig.SetSetting('DB_Version', '2.5')

        if 2.6 > Version:
            self.logger.info('**ATTENTION** Updating DB to Version 2.6')
            #self.user_MC_IngameName_unique_constraint()
            self.DBConfig.DeleteSetting('Whitelist_Emoji_Pending')
            self.DBConfig.DeleteSetting('Whitelist_Emoji_Done')
            self.DBConfig.SetSetting('DB_Version', '2.6')
        
        if 2.7 > Version:
            """Hotfix for Failed Table creation in version 2.4"""
            self.logger.info('**ATTENTION** Updating DB to Version 2.7')
            self.server_add_FriendlyName_column()
            try:
                SQL = 'select * from ServerRegexPatterns'
                self.DB._execute(SQL, ())
            except:
                self.server_regex_pattern_table_creation()
            self.DBConfig.SetSetting('DB_Version', '2.7')
        

    def user_roles(self):
        try:
            SQL = "alter table users add column Role text collate nocase default None"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'user_roles {e}')
            sys.exit(-1)

    def nicknames_unique(self):
        try:
            SQL = "alter table ServerNicknames add constraint Nickname unique"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'nicknames_unique {e}')
            sys.exit(-1)

    def user_Donator_removal(self):
        try:
            SQL = "alter table users drop column Donator"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'user_Donator_removal {e}')
            sys.exit(-1)

    def server_Discord_reaction_removal(self):
        try:
            SQL = "alter table servers drop column Discord_Reaction"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_Discord_reaction_removal {e}')
            sys.exit(-1)

    def server_Discord_Chat_prefix(self):
        try:
            SQL = "alter table servers add column Discord_Chat_Prefix text"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_Discord_Chat_prefix {e}')
            sys.exit(-1)

    def server_Discord_event_channel(self):
        try:
            SQL = "alter table servers add column Discord_Event_Channel text nocase"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_Discord_event_channel {e}')
            sys.exit(-1)

    def server_Avatar_url(self):
        try:
            SQL = "alter table servers add column Avatar_url text"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_Avatar_url {e}')
            sys.exit(-1)

    def server_banner_table(self):
        try:
            SQL = 'create table ServerEmbed (ID integer primary key, Discord_Guild_ID text nocase, Discord_Channel_ID text nocase, Discord_Message_ID text)'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_banner_table {e}')
            sys.exit(-1)
    
    def whitelist_reply_table(self):
        try:
            SQL = 'create table WhitelistReply (ID integer primary key, Message text)'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'whitelist_reply_table {e}')
            sys.exit(-1)
    
    def server_hide_column(self):
        """1.8 Update"""
        try:
            SQL = 'alter table servers add column Hidden integer default 0'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_hide_column {e}')
            sys.exit(-1)

    def server_ip_constraint_update(self):
        """SQLITE does not support dropping UNIQUE constraint"""
        try:
            SQL = 'alter table servers drop constraint IP unique'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_ip_constraint_update {e}')
            sys.exit(-1)

    def server_display_name_reset(self):
        try:
            SQL= 'update Servers set DisplayName=InstanceName'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_display_name_reset {e}')
            sys.exit(-1)

    def server_display_name_constraint_update(self):
        """SQLITE does not support adding UNIQUE constraint"""
        try:
            SQL = "alter table Servers add constraint DisplayName unique"
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_display_name_constraint_update {e}')
            sys.exit(-1)

    def banner_table_creation(self):
        try:
            SQL = 'create table ServerBanners (ServerID integer not null, background_path text, blur_background_amount integer, color_header text, color_body text, color_Host text, color_whitelist_open text, color_whitelist_closed text, color_donator text, color_status_online text, color_status_offline text, color_player_limit_min text, color_player_limit_max text, color_player_online text, foreign key(ServerID) references Servers(ID))'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'banner_table_creation {e}')
            sys.exit(-1)
    
    def server_ip_name_change(self):
        try:
            # SQL = 'select IP from Servers limit 1'
            # self.DB._execute(SQL, ())

            # SQL = "alter table Servers drop column IP"
            # self.DB._execute(SQL, ())

            SQL = 'alter table Servers add column Host text'
            self.DB._execute(SQL, ())
            return
        except Exception as e:
            self.logger.error(e)
            pass

        try:
            SQL = 'select Display_IP from Servers limit 1'
            self.DB._execute(SQL, ())

            SQL = 'alter table Servers drop column Display_IP'
            self.DB._execute(SQL, ())

            SQL = 'alter table Servers add column Host text'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_ip_name_change {e}')
            sys.exit(-1)
        
    def banner_name_conversion(self):
        #Lightning: need comments about why the 2 try/except that pass/return
        try:
            SQL = 'select * from ServerEmbed limit 1'
            self.DB._execute(SQL, ())

            SQL = 'alter table ServerEmbed rename to ServerDisplayBanners'
            self.DB._execute(SQL, ())
            return
        except:
            pass

        try:
            SQL = 'select * from ServerDisplayBanners'
            self.DB._execute(SQL, ())
            return
        except:
            pass

        try:
            SQL = 'create table ServerDisplayBanners (ID integer primary key,Discord_Guild_ID text nocase,Discord_Channel_ID text nocase, Discord_Message_ID text nocase)'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'banner_name_conversion {e}')
            sys.exit(-1)

    def server_table_whitelist_disabled_column(self):
        try:
            SQL = 'alter table Servers add column Whitelist_disabled integer not null default 0'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_table_whitelist_disabled_column {e}')
            sys.exit(-1)

    def regex_pattern_table_creation(self):
        try:
            SQL = 'create table RegexPatterns (ID integer primary key, Name text unique not null, Type integer not null, Pattern text unique not null)'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'regex_pattern_table_creation {e}')
            sys.exit(-1)

    def server_regex_pattern_table_creation(self):
        try:
            SQL = 'create table ServerRegexPatterns (ServerID integeter not null, RegexPatternID integer not null, foreign key (RegexPatternID) references RegexPatterns(ID), foreign key(ServerID) references Servers(ID) UNIQUE(ServerID, RegexPatternID))'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_regex_pattern_table_creation {e}')
            sys.exit(-1)

    def server_console_filter_type(self):
        try:
            SQL = 'alter table Servers add column Console_Filtered_Type integer not null default 0'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_console_filter_type {e}')
            sys.exit(-1)
        
    def server_add_FriendlyName_column(self):
        try:
            SQL = 'select FriendlyName from Servers'
            self.DB._execute(SQL, ())
            return
        except:
            pass

        try:
            SQL = 'alter table Servers add column FriendlyName text'
            self.DB._execute(SQL, ())
        except Exception as e:
            self.logger.critical(f'server_add_FriendlyName_column {e}')
            sys.exit(-1)
  