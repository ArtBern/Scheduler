"""
<plugin key="Scheduler" name="Weekly Scheduler" author="artbern" version="1.0.0" wikilink="https://github.com/ArtBern/Scheduler" externallink="https://github.com/ArtBern/Scheduler">
    <description>
        <h2>Weekly Scheduler</h2><br/>
        Thermostat with weekly scheduler.
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Reach UI for OnTime timers manipulation</li>
            <li>Switch timerplans</li>
        </ul>
        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Device Type - Virtual Thermostat with timers.</li>
        </ul>
        <h3>Configuration</h3>
		Ensure Custom tab is enabled at Domoticz settings.
        Create Hardware, specify Domoticz connection and separate port.
		Observe new menu item under "Custom" tab.
		<h3>Prerequisites</h3>
		Plugin requires Domoticz-API module
		https://github.com/ArtBern/Domoticz-API
		<br/>
		Domoticz-API installation instruction:
		https://github.com/Xorfor/Domoticz-API/wiki/Installation
		
    </description>
    <params>
        <param field="Address" label="IP Address" width="180px" required="true" default="192.168.1.x"/>
        <param field="Port" label="Domoticz Port" width="60px" required="true" default="8080"/>
        <param field="Mode1" label="Listener Port" width="60px" required="true" default="9005"/>
        <param field="Mode2" label="Max temperature" width="60px" required="true" default="30"/>
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
import json
import base64
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
    domServer = None
    
    
    def __init__(self):
        self.__filename = ""
        return

    def onStart(self):
        Domoticz.Log("onStart called")
        if Parameters["Mode6"] != "Normal":
            Domoticz.Debugging(1)
        DumpConfigToLog()
        self.httpServerConn = Domoticz.Connection(Name="Server Connection", Transport="TCP/IP", Protocol="HTTP", Port=Parameters["Mode1"])
        self.httpServerConn.Listen()
		
        self.__domServer = dom.Server(Parameters['Address'], Parameters['Port'])

        html = Utils.readFile(os.path.join(Parameters['HomeFolder'], 'web/html/thermostat_schedule.html'), False)
        javascript = Utils.readFile(os.path.join(Parameters['HomeFolder'], 'web/javascript/thermostat_schedule.js'), False)
        pointer = Utils.readFile(os.path.join(Parameters['HomeFolder'], 'web/images/downArrow_white.png'), True)
        pointerselected = Utils.readFile(os.path.join(Parameters['HomeFolder'], 'web/images/downArrow_red.png'), True)
        #json = Utils.readFile(os.path.join(Parameters['HomeFolder'], 'web/thermostat_schedule.json'), False)

        html = html.replace('src="/images/downArrow_white.png"', 'src="data:image/png;base64, ' + base64.b64encode(pointer).decode("ascii") + '"')
        html = html.replace('src="/images/downArrow_red.png"', 'src="data:image/png;base64, ' + base64.b64encode(pointerselected).decode("ascii") + '"')
        

        html = html.replace('<script src="/javascript/thermostat_schedule.js">', '<script>' + javascript)
        
        html = html.replace('<script src="/tobereplaced.js">', '<script>var maxslider=' + Parameters['Mode2'] + ";")
        
        
        html = html.replace(' src="/', ' src="http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/')
        html = html.replace(' href="/', ' href="http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/')
        html = html.replace('"schedule.json"', '"http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/thermostat_schedule.json"')
        html = html.replace('"timer_plans.json"', '"http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/timer_plans.json"')
        html = html.replace('"save"', '"http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/save"')
        html = html.replace('"changetimerplan"', '"http://' + Parameters['Address'] + ':' + Parameters['Mode1'] + '/changetimerplan"')
        
        if (len(Devices) == 0):
            Domoticz.Device(Name=Parameters['Name'], Unit=1, Type=242, Subtype=1, Used=1).Create()
        
        self.__filename = Parameters['StartupFolder'] + 'www/templates/Scheduler-' + "".join(x for x in Parameters['Name'] if x.isalnum()) + '.html'
        Utils.writeText(html, self.__filename)

        Domoticz.Log("Domoticz-API server is: " + str(self.__domServer))

        self.__thermostat = dom.Device(self.__domServer, Devices[1].ID)
   
        Domoticz.Log("Leaving on start")
        
    def onStop(self):
        LogMessage("onStop called")
        Utils.deleteFile(self.__filename)
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

                return_type = mimetype

                if path == '/thermostat_schedule.json':

                    timers = dom.SetPointTimer.loadbythermostat(self.__thermostat)
                    data = str(TimersToJson(timers)).replace("'", "\"")

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
                                    
                elif path == '/timer_plans.json':

                    plans = self.__domServer.timerplans
                    activeplan = self.__domServer.setting.get_value("ActiveTimerPlan")
                    
                    for plan in plans:
                        if (str(activeplan) == str(plan["idx"])):
                            plan["isactive"] = "true"
                        else:
                            plan["isactive"] = "false"
                            
                    timerplans = str(plans).replace("'", "\"")
                            
                    Connection.Send({"Status":"200", 
                                    "Headers": {"Connection": "keep-alive", 
                                                "Accept-Encoding": "gzip, deflate",
                                                "Access-Control-Allow-Origin":"http://" + Parameters['Address'] + ":" + Parameters['Port'] + "",
                                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                                "Content-Type": "application/json; charset=UTF-8",
                                                "Content-Length":""+str(len(timerplans))+"",
                                                "Pragma": "no-cache",
                                                "Expires": "0"},
                                    "Data": timerplans})               
    

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

                jsn = Data["Data"]
                              
                if (path == "/save"):

                    newtimers = JsonToTimers(self.__thermostat, jsn)
                    
                    oldtimers = dom.SetPointTimer.loadbythermostat(self.__thermostat)
                    
                    for oldtimer in oldtimers:
                        if (oldtimer.timertype is dom.TimerTypes.TME_TYPE_ON_TIME):
                            oldtimer.delete()
                            
                    for newtimer in newtimers:
                        newtimer.add()

                elif (path == "/changetimerplan"):
                    
                    j = json.loads(jsn)
                                                         
                    self.__domServer.setting.set_value("ActiveTimerPlan", j["activetimerplan"])
                                      
                data = "{\"status\":\"OK\"}"
 
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
        
        currentValue = self.__thermostat.get_value("SetPoint")
        if (str(currentValue) == str(Level)):
            return
        
        self.__thermostat.set_value("setpoint", Level) 

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called for connection '"+Connection.Name+"'.")

        if Connection.Name in self.httpServerConns:
            del self.httpServerConns[Connection.Name]

    def onHeartbeat(self):
        Domoticz.Log("onHeartbeat called")
        
#    def onDeviceModified(self, Unit):
#        Domoticz.Log("onCommand called for Unit " + str(Unit))
       
      

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
    
#def onDeviceModified(Unit):
    #global _plugin
    #_plugin.onDeviceModified(Unit)    

# Generic helper functions
def TimersToJson(timers):
    tmrdict = {  "monday": [], "tuesday": [], "wednesday": [], "thursday": [], "friday" : [], "saturday": [], "sunday": []}
    for timer in timers:
        if (timer.timertype == dom.TimerTypes.TME_TYPE_ON_TIME):
            if dom.TimerDays.Monday in timer.days:
                tmrdict["monday"].append([f"{timer.hour:02d}:{timer.minute:02d}", timer.temperature ])
            if dom.TimerDays.Tuesday in timer.days:
                tmrdict["tuesday"].append([f"{timer.hour:02d}:{timer.minute:02d}", timer.temperature ])
            if dom.TimerDays.Wednesday in timer.days:
                tmrdict["wednesday"].append([f"{timer.hour:02d}:{timer.minute:02d}", timer.temperature ])
            if dom.TimerDays.Thursday in timer.days:
                tmrdict["thursday"].append([f"{timer.hour:02d}:{timer.minute:02d}", timer.temperature ])
            if dom.TimerDays.Friday in timer.days:
                tmrdict["friday"].append([f"{timer.hour:02d}:{timer.minute:02d}", timer.temperature ])
            if dom.TimerDays.Saturday in timer.days:
                tmrdict["saturday"].append([f"{timer.hour:02d}:{timer.minute:02d}", timer.temperature ])
            if dom.TimerDays.Sunday in timer.days:
                tmrdict["sunday"].append([f"{timer.hour:02d}:{timer.minute:02d}", timer.temperature ])   
    return tmrdict
        
def JsonToTimers(device, data):
    plan = json.loads(data)
    timers = []
    for day in plan:
        timerday = dom.TimerDays[day.capitalize()]
        for tmr in plan[day]:
            timers.append(dom.SetPointTimer(device, Active=True, Days=timerday, Temperature=tmr[1], Time=tmr[0], Type=dom.TimerTypes.TME_TYPE_ON_TIME))
    
    return timers

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

