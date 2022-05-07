import TouchPortalAPI as TP
#required: pip install TouchPortal-API
#required: python v3.8

# Setup callbacks and connection
TPClient = TP.Client("SCNav")

# This event handler will run once when the client connects to Touch Portal
@TPClient.on(TP.TYPES.onConnect) # Or replace TYPES.onConnect with 'info'
def onStart(data):
    print("Connected!", data)
    # Update a state value in TouchPortal
    TPClient.stateUpdate("SCNavState", "Connected!")

# Action handlers, called when user activates one of this plugin's actions in Touch Portal.
@TPClient.on(TP.TYPES.onAction) # Or 'action'
def onAction(data):
    print(data)
    # do something based on the action ID and the data value
    if data['actionId'] == "SelectDstPlanet":
      # get the value from the action data (a string the user specified)
      #action_value = getActionDataValue(data.get('data'), 'ExampleTextData')
      #print(action_value)
      # We can also update our ExampleStates with the Action Value
      TPClient.stateUpdate("SCNavState", "Planet selected")
    if data['actionId'] == "SelectPOIonPlanet":
      # get the value from the action data (a string the user specified)
      action_value = getActionDataValue(data.get('data'), 'ExampleTextData2')
      print(action_value)
      # We can also update our ExampleStates with the Action Value
      TPClient.stateUpdate("SCNavState", action_value)  

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