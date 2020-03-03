
"""
<plugin key="Scheduler" name="Weekly Scheduler" author="artbern" version="1.0.0" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://www.google.com/">
    <description>
        <h2>Weekly Scheduler</h2><br/>
        Overview...
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Feature one...</li>
            <li>Feature two...</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Device Type - What it does...</li>
        </ul>
        <h3>Configuration</h3>
        Configuration options...
    </description>
    <params>
        <param field="Address" label="IP Address" width="180px" required="true" default="192.168.1.x"/>
        <param field="Port" label="Domoticz Port" width="60px" required="true" default="8080"/>
        <param field="Mode1" label="Listener Port" width="60px" required="true" default="9005"/>
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
                <option label="Logging" value="File"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import urllib.parse
import os
import sqlite3
from utils import Utils

# sudo pip3 install git+git://github.com/ArtBern/Domoticz-API.git -t /usr/lib/python3.5 --upgrade
import DomoticzAPI as dom

#try:
    #apt-get install libmagic-dev
    #pip3 install python-libmagic
import magic
#except OSError as e:
#    Domoticz.Log ("Error loading python-libmagic: {0}:{1}".format(e.__class__.__name__, e.message))
#except AttributeError as e:
#    Domoticz.Log ("Error loading python-libmagic: {0}:{1}".format(e.__class__.__name__, e.message)) 


#pip3 install accept-types
from accept_types import get_best_match

class BasePlugin:
    enabled = False
        
    httpServerConn = None
    httpServerConns = {}
    dbConnection = None
    domServer = None
    
    
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        Domoticz.Log("onStart called")
        if Parameters["Mode6"] != "Normal":
            Domoticz.Debugging(1)
        DumpConfigToLog()
        self.httpServerConn = Domoticz.Connection(Name="Server Connection", Transport="TCP/IP", Protocol="HTTP", Port=Parameters["Mode1"])
        self.httpServerConn.Listen()

        html = Utils.readFile(os.path.join(Parameters['HomeFolder'], 'web/html/thermostat_schedule.html'), False)
        json = Utils.readFile(os.path.join(Parameters['HomeFolder'], 'web/thermostat_schedule.json'), False)

        html = html.replace(' src="/', ' src="http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/')
        html = html.replace(' href="/', ' href="http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/')
        html = html.replace('"schedule.json"', '"http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/thermostat_schedule.json"')
        html = html.replace('"save"', '"http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/save"')

        Utils.writeText(html, Parameters['StartupFolder'] + 'www/templates/Scheduler-' + str(Parameters["HardwareID"]) + '.html')

        self.dbConnection = sqlite3.connect(Parameters['Database'])

        c = self.dbConnection.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS SchedulerPlugin(HardwareID real, json text, UNIQUE(HardwareID))''')

        c.execute('INSERT OR IGNORE INTO SchedulerPlugin(HardwareID, json) VALUES (?,?)', (Parameters["HardwareID"], json))

        self.dbConnection.commit()

        if (len(Devices) == 0):
            Domoticz.Device(Name="Thermostat", Unit=1, Type=242, Subtype=1, Used=1).Create()

        self.domServer = dom.Server()

        Domoticz.Log("Domoticz-API server is: " + str(self.domServer))
        
        Domoticz.Log("Leaving on start")
        
    def onStop(self):
        LogMessage("onStop called")

        if self.dbConnection != None:
            self.dbConnection.close()

        LogMessage("Leaving onStop")


    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Log("Connected successfully to: "+Connection.Address+":"+Connection.Port)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Connection.Address+":"+Connection.Port+" with error: "+Description)
        Domoticz.Log(str(Connection))

        self.httpServerConns[Connection.Name] = Connection

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called for connection: "+Connection.Address+":"+Connection.Port+":"+Connection.Name)
        DumpHTTPResponseToLog(Data)
        
        # Incoming Requests
        if "Verb" in Data:
            strVerb = Data["Verb"]
            #strData = Data["Data"].decode("utf-8", "ignore")
            LogMessage(strVerb+" request received.")
            data = "<!doctype html><html><head></head><body><h1>Successful GET!!!</h1><body></html>"
            if (strVerb == "GET"):

                strURL = Data["URL"]
                path = urllib.parse.unquote_plus(urllib.parse.urlparse(strURL).path)
                filePath = os.path.join(Parameters['HomeFolder'], "web" + path)

                with magic.Magic() as m:
                    mimetype = m.from_file(filePath)
                
                LogMessage("Mime type determined as " + mimetype)
                LogMessage("Path is " + path)

                #return_type = get_best_match(Data['Headers']['Accept'], ['text/html', 'image/png', 'text/css', '*/*'])
                return_type = mimetype

                if path == '/thermostat_schedule.json':

                    c = self.dbConnection.cursor()
                    c.execute('SELECT json FROM SchedulerPlugin WHERE HardwareID=?', (Parameters["HardwareID"],))
                    data = c.fetchone()[0]
                    
                    self.dbConnection.commit()

                    Connection.Send({"Status":"200", 
                                    "Headers": {"Connection": "keep-alive", 
                                                "Accept-Encoding": "gzip, deflate",
                                                "Access-Control-Allow-Origin":"http://" + Parameters['Address'] + ":" + Parameters['Port'] + "",
                                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                                "Content-Type": "application/json; charset=UTF-8",
                                                "Content-Length":""+str(len(data))+"",
                                                "Pragma": "no-cache",
                                                "Expires": "0"},
                                    "Data": data})               

                elif (return_type == 'text/html' or return_type == 'text/css' or return_type == 'text/plain'):
                    data = Utils.readFile(filePath, False)
     
                    Connection.Send({"Status":"200", 
                                    "Headers": {"Connection": "keep-alive", 
                                                "Accept-Encoding": "gzip, deflate",
                                                "Access-Control-Allow-Origin":"http://" + Parameters['Address'] + ":" + Parameters['Port'] + "",
                                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                                "Content-Type": return_type + "; charset=UTF-8",
                                                "Content-Length":""+str(len(data))+"",
                                                "Pragma": "no-cache",
                                                "Expires": "0"},
                                    "Data": data})

                elif return_type == 'image/png' or return_type == 'image/x-icon':
                    data = Utils.readFile(filePath, True)

                    LogMessage("Legth is " + str(len(data)))
     
                    Connection.Send({"Status":"200", 
                                    "Headers": {"Connection": "keep-alive", 
                                                "Accept-Encoding": "gzip, deflate",
                                                "Access-Control-Allow-Origin":"http://" + Parameters['Address'] + ":" + Parameters['Port'] + "",
                                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                                "Content-Type": return_type,
                                                "Pragma": "no-cache",
                                                "Expires": "0"},
                                    "Data": data})
                elif return_type == None:
                   Connection.Send({"Status":"406"}) 
                                
            elif (strVerb == "POST"):

                strURL = Data["URL"]
                path = urllib.parse.unquote_plus(urllib.parse.urlparse(strURL).path)

                if (path == "/save"):

                    json = Data["Data"]

                    cur = self.dbConnection.cursor()

                    cur.execute("UPDATE SchedulerPlugin SET json=? WHERE HardwareID=?", (json, Parameters["HardwareID"]))

                    self.dbConnection.commit()

                    data = "{""status"":""OK""}"
     
                    Connection.Send({"Status":"200", 
                                    "Headers": {"Connection": "keep-alive", 
                                                "Accept-Encoding": "gzip, deflate",
                                                "Access-Control-Allow-Origin":"http://" + Parameters['Address'] + ":" + Parameters['Port'] + "",
                                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                                "Content-Type": "application/json; charset=UTF-8",
                                                "Content-Length":""+str(len(data))+"",
                                                "Pragma": "no-cache",
                                                "Expires": "0"},
                                    "Data": data})


            elif (strVerb == "OPTIONS"):
                Connection.Send({"Status":"200 OK", 
                                "Headers": { 
                                            "Access-Control-Allow-Origin":"*",
                                            "Access-Control-Allow-Methods":"POST, GET, OPTIONS",
                                            "Access-Control-Max-Age":"86400",
                                            "Access-Control-Allow-Headers": "Content-Type",
                                            "Vary":"Accept-Encoding, Origin",
                                            "Content-Encoding": "gzip",
                                            "Content-Length": "0",
                                            "Keep-Alive": "timeout=2, max=100",
                                            "Connection": "Keep-Alive",
                                            "Content-Type": "text/plain"}
                                            })
            else:
                Domoticz.Error("Unknown verb in request: "+strVerb)

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for connection '"+Connection.Name+"'.")

        if Connection.Name in self.httpServerConns:
            del self.httpServerConns[Connection.Name]

    def onHeartbeat(self):
        Domoticz.Log("onHeartbeat called")

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
	
def LogMessage(Message):
    if Parameters["Mode6"] != "Normal":
        Domoticz.Log(Message)
    elif Parameters["Mode6"] != "Debug":
        Domoticz.Debug(Message)
    else:
        f = open("http.html","w")
        f.write(Message)
        f.close()   

def DumpHTTPResponseToLog(httpResp, level=0):
    if (level==0): Domoticz.Debug("HTTP Details ("+str(len(httpResp))+"):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + ">'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level+1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")