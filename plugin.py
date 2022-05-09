import TouchPortalAPI as TP
import json
import os
import sys

#required: pip install TouchPortal-API
#required: python v3.8

# Setup callbacks and connection
TPClient = TP.Client("SCNav")

planetsListPointer = 0
poiListPointer = 0

#setup DATA, Database.json from valalol's sc navi tool https://github.com/Valalol/Star-Citizen-Navigation/releases
with open('Database.json') as f:
    Database = json.load(f)
Container_list = []
for i in Database["Containers"]:
    Container_list.append(Database["Containers"][i]["Name"])
Planetary_POI_list = {}
for container_name in Database["Containers"]:
    Planetary_POI_list[container_name] = []
    for poi in Database["Containers"][container_name]["POI"]:
        if "OM-" not in poi and "Comm Array" not in poi: 
          Planetary_POI_list[container_name].append(poi)
        
            
# This event handler will run once when the client connects to Touch Portal
@TPClient.on(TP.TYPES.onConnect) # Or replace TYPES.onConnect with 'info'
def onStart(data):
    print("Connected!", data)
    # Update a state value in TouchPortal
    TPClient.stateUpdate("SCNavState", "Connected!")
    TPClient.stateUpdate ("selectedPlanet", Container_list[0])

# Action handlers, called when user activates one of this plugin's actions in Touch Portal.
@TPClient.on(TP.TYPES.onAction) # Or 'action'

def onAction(data):
    global planetsListPointer,poiListPointer,Container_list, Planetary_POI_list
    print(data)
    # do something based on the action ID and the data value
    
    if data['actionId'] == "UpPlanet":
      # get the value from the action data (a string the user specified)
      if planetsListPointer > 0: 
        planetsListPointer -= 1
        print("UpPlanet ", str(planetsListPointer))
       
        TPClient.stateUpdate("selectedPlanet",  Container_list[planetsListPointer])
        TPClient.stateUpdate("selectedPOI", Planetary_POI_list[Container_list[planetsListPointer]][0] )
        poiListPointer = 0
        
    if data['actionId'] == "DownPlanet":
      # get the value from the action data (a string the user specified)
      if planetsListPointer < len(Container_list)-1:
        planetsListPointer += 1
        print("DownPlanet ", str(planetsListPointer))
        #TPClient.stateUpdate ("selectedPlanet", "Daymar")
        TPClient.stateUpdate("selectedPlanet",  Container_list[planetsListPointer])
        TPClient.stateUpdate("selectedPOI", Planetary_POI_list[Container_list[planetsListPointer]][0] )
        poiListPointer = 0
                         
    if data['actionId'] == "UpPoiName":
      # get the value from the action data (a string the user specified)
      if poiListPointer > 0:
        poiListPointer -= 1
        print("DownPoiName ", str(poiListPointer))
        TPClient.stateUpdate("selectedPOI", Planetary_POI_list[Container_list[planetsListPointer]][poiListPointer] )
        
        
    if data['actionId'] == "DownPoiName":
      # get the value from the action data (a string the user specified)
      if poiListPointer < len(Planetary_POI_list[Container_list[planetsListPointer]])-1:
        poiListPointer += 1
        print("DownPoiName ", str(poiListPointer))
        TPClient.stateUpdate("selectedPOI", Planetary_POI_list[Container_list[planetsListPointer]][poiListPointer] )
        
        
    if data['actionId'] == "startNav":
      # get the value from the action data (a string the user specified)
      print("startNav for ", Container_list[planetsListPointer], ", ", Planetary_POI_list[Container_list[planetsListPointer]][poiListPointer] )
    if data['actionId'] == "saveLocation":
      # get the value from the action data (a string the user specified)
      print("saveLocation")
    if data['actionId'] == "updateLocation":
      # get the value from the action data (a string the user specified)
      print("updateLocation")

# Shutdown handler, called when Touch Portal wants to stop your plugin.
@TPClient.on(TP.TYPES.onShutdown) # or 'closePlugin'
def onShutdown(data):
    print("Got Shutdown Message! Shutting Down the Plugin!")
    # Terminates the connection and returns from connect()
    TPClient.disconnect()

# After callback setup like we did then we can connect.
# Note that `connect()` blocks further execution until
# `disconnect()` is called in an event handler, or an
# internal error occurs.
TPClient.connect()