from pathlib import PosixPath
import TouchPortalAPI as TP
import json
import os
import sys
from math import sqrt, degrees, radians, cos, acos, sin, asin, tan, atan2, copysign, pi
import pyperclip
import time
import datetime
import csv
import ntplib
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt


c = ntplib.NTPClient()
response = c.request('uk.pool.ntp.org', version=3)
server_time = response.tx_time
offset = response.offset
#local_time = time.time()
#time_difference = server_time - local_time
#print(str(time_difference) + " offset: " + str(offset))
correction_value=offset # time_difference

#required: pip install TouchPortal-API
#required: python v3.8

# Setup callbacks and connection
TPClient = TP.Client("SCNav")

toggle_qt_marker_switch = 0

planetsListPointer = 0
edit_coordinate="none"
poiListPointer = 0
player_Longitude = 0
New_player_local_rotated_coordinates = 0
player_Latitude = 0
#correction_value = 0
custom_x = ""
custom_y = ""
custom_z = ""
Mode = "Planetary Navigation"
Old_clipboard = ""
Target = ""
Old_time = time.time()
Actual_Container = {}
#setup DATA, Database.json from valalol's sc navi tool https://github.com/Valalol/Star-Citizen-Navigation/releases
with open('Database.json') as f:
    Database = json.load(f)
Container_list = []
for i in Database["Containers"]:
    Container_list.append(Database["Containers"][i]["Name"])
Planetary_POI_list = {}
container_name = ""
Database_own = ""

def loadPOIList():
    global Planetary_POI_list, container_name, Database, Database_own
    print("loadPOIList")
    Planetary_POI_list.clear()
    
    for container_name in Database["Containers"]:
        Planetary_POI_list[container_name] = []
        for poi in Database["Containers"][container_name]["POI"]:
            if toggle_qt_marker_switch == 0: #without QT marker
                if Database["Containers"][container_name]["POI"][poi]["QTMarker"] == "FALSE": 
                    Planetary_POI_list[container_name].append(poi)
                    print("false:", poi)
            elif toggle_qt_marker_switch == 1: #saved pois
                print("Loading saved POI list...")
                with open('saved_pois.json') as f:
                    Database_own = json.load(f)
            else: #complete database.json               
                Planetary_POI_list[container_name].append(poi)
                print("true:", poi)        
    TPClient.stateUpdate("selectedPlanet",  Container_list[planetsListPointer])
    TPClient.stateUpdate("selectedPOI", Planetary_POI_list[Container_list[planetsListPointer]][0] )
    
    
loadPOIList()
    
# --------------------- NAV Magic -----------------------
def trig(angle):
  r = radians(angle)
  return cos(r), sin(r)

def matrix(rotation=(0,0,0), translation=(0,0,0)):
  xC, xS = trig(rotation[0])
  yC, yS = trig(rotation[1])
  zC, zS = trig(rotation[2])
  dX = translation[0]
  dY = translation[1]
  dZ = translation[2]
  return [[yC*xC, -zC*xS+zS*yS*xC, zS*xS+zC*yS*xC, dX],
    [yC*xS, zC*xC+zS*yS*xS, -zS*xC+zC*yS*xS, dY],
    [-yS, zS*yC, zC*yC, dZ],
    [0, 0, 0, 1]]

def transform(point=(0,0,0), vector=(0,0,0)):
  p = [0,0,0]
  for r in range(3):
    p[r] += vector[r][3]
    for c in range(3):
      p[r] += point[c] * vector[r][c]
  return p

def vector_norm(a):
    """Returns the norm of a vector"""
    return sqrt(a["X"]**2 + a["Y"]**2 + a["Z"]**2)

def vector_product(a, b):
    """Returns the dot product of two vectors"""
    return a["X"]*b["X"] + a["Y"]*b["Y"] + a["Z"]*b["Z"]

def angle_between_vectors(a, b):
    """Function that returns an angle in degrees between 2 vectors"""
    try :
        angle = degrees(acos(vector_product(a, b) / (vector_norm(a) * vector_norm(b))))
    except ZeroDivisionError:
        angle = 0.0
    return angle

def rotate_point_2D(Unrotated_coordinates, angle):
    Rotated_coordinates = {}
    Rotated_coordinates["X"] = Unrotated_coordinates["X"] * cos(angle) - Unrotated_coordinates["Y"]*sin(angle)
    Rotated_coordinates["Y"] = Unrotated_coordinates["X"] * sin(angle) + Unrotated_coordinates["Y"]*cos(angle)
    Rotated_coordinates["Z"] = Unrotated_coordinates["Z"]
    return (Rotated_coordinates)

def get_current_container(X : float, Y : float, Z : float):
    Actual_Container = {
        "Name": "None",
        "X": 0,
        "Y": 0,
        "Z": 0,
        "Rotation Speed": 0,
        "Rotation Adjust": 0,
        "OM Radius": 0,
        "Body Radius": 0,
        "POI": {}
    }
    for i in Database["Containers"] :
        Container_vector = {"X" : Database["Containers"][i]["X"] - X, "Y" : Database["Containers"][i]["Y"] - Y, "Z" : Database["Containers"][i]["Z"] - Z}
        if vector_norm(Container_vector) <= 3 * Database["Containers"][i]["OM Radius"]:
            Actual_Container = Database["Containers"][i]
    return Actual_Container


def get_local_rotated_coordinates(Time_passed : float, X : float, Y : float, Z : float, Actual_Container : dict):

    try:
        Rotation_speed_in_degrees_per_second = 0.1 * (1/Actual_Container["Rotation Speed"])
    except ZeroDivisionError:
        Rotation_speed_in_degrees_per_second = 0

    Rotation_state_in_degrees = ((Rotation_speed_in_degrees_per_second * Time_passed) + Actual_Container["Rotation Adjust"]) % 360

    local_unrotated_coordinates = {
        "X": X - Actual_Container["X"],
        "Y": Y - Actual_Container["Y"],
        "Z": Z - Actual_Container["Z"]
    }

    local_rotated_coordinates = rotate_point_2D(local_unrotated_coordinates, radians(-1*Rotation_state_in_degrees))

    return local_rotated_coordinates


def get_lat_long_height(X : float, Y : float, Z : float, Container : dict):
    Radius = Container["Body Radius"]

    Radial_Distance = sqrt(X**2 + Y**2 + Z**2)

    Height = Radial_Distance - Radius

    #Latitude
    try :
        Latitude = degrees(asin(Z/Radial_Distance))
    except :
        Latitude = 0

    try :
        Longitude = -1*degrees(atan2(X, Y))
    except :
        Longitude = 0

    return [Latitude, Longitude, Height]


def get_closest_POI(X : float, Y : float, Z : float, Container : dict, Quantum_marker : bool = False):

    Distances_to_POIs = []

    for POI in Container["POI"]:
        Vector_POI = {
            "X": abs(X - Container["POI"][POI]["X"]),
            "Y": abs(Y - Container["POI"][POI]["Y"]),
            "Z": abs(Z - Container["POI"][POI]["Z"])
        }

        Distance_POI = vector_norm(Vector_POI)

        if Quantum_marker and Container["POI"][POI]["QTMarker"] == "TRUE" or not Quantum_marker:
            Distances_to_POIs.append({"Name" : POI, "Distance" : Distance_POI})

    Target_to_POIs_Distances_Sorted = sorted(Distances_to_POIs, key=lambda k: k['Distance'])
    return Target_to_POIs_Distances_Sorted



def get_closest_oms(X : float, Y : float, Z : float, Container : dict):
    Closest_OM = {}

    if X >= 0:
        Closest_OM["X"] = {"OM" : Container["POI"]["OM-5"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-5"]["X"], "Y" : Y - Container["POI"]["OM-5"]["Y"], "Z" : Z - Container["POI"]["OM-5"]["Z"]})}
    else:
        Closest_OM["X"] = {"OM" : Container["POI"]["OM-6"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-6"]["X"], "Y" : Y - Container["POI"]["OM-6"]["Y"], "Z" : Z - Container["POI"]["OM-6"]["Z"]})}
    if Y >= 0:
        Closest_OM["Y"] = {"OM" : Container["POI"]["OM-3"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-3"]["X"], "Y" : Y - Container["POI"]["OM-3"]["Y"], "Z" : Z - Container["POI"]["OM-3"]["Z"]})}
    else:
        Closest_OM["Y"] = {"OM" : Container["POI"]["OM-4"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-4"]["X"], "Y" : Y - Container["POI"]["OM-4"]["Y"], "Z" : Z - Container["POI"]["OM-4"]["Z"]})}
    if Z >= 0:
        Closest_OM["Z"] = {"OM" : Container["POI"]["OM-1"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-1"]["X"], "Y" : Y - Container["POI"]["OM-1"]["Y"], "Z" : Z - Container["POI"]["OM-1"]["Z"]})}
    else:
        Closest_OM["Z"] = {"OM" : Container["POI"]["OM-2"], "Distance" : vector_norm({"X" : X - Container["POI"]["OM-2"]["X"], "Y" : Y - Container["POI"]["OM-2"]["Y"], "Z" : Z - Container["POI"]["OM-2"]["Z"]})}

    return Closest_OM



def get_sunset_sunrise_predictions(X : float, Y : float, Z : float, Latitude : float, Longitude : float, Height : float, Container : dict, Star : dict):
    global Time_passed_since_reference_in_seconds
    try :
        # Stanton X Y Z coordinates in refrence of the center of the system
        sx, sy, sz = Star["X"], Star["Y"], Star["Z"]
        
        # Container X Y Z coordinates in refrence of the center of the system
        bx, by, bz = Container["X"], Container["Y"], Container["Z"]
        
        # Rotation speed of the container
        rotation_speed = Container["Rotation Speed"]
        
        # Container qw/qx/qy/qz quaternion rotation 
        qw, qx, qy, qz = Container["qw"], Container["qx"], Container["qy"], Container["qz"]
        
        # Stanton X Y Z coordinates in refrence of the center of the container
        bsx = ((1-(2*qy**2)-(2*qz**2))*(sx-bx))+(((2*qx*qy)-(2*qz*qw))*(sy-by))+(((2*qx*qz)+(2*qy*qw))*(sz-bz))
        bsy = (((2*qx*qy)+(2*qz*qw))*(sx-bx))+((1-(2*qx**2)-(2*qz**2))*(sy-by))+(((2*qy*qz)-(2*qx*qw))*(sz-bz))
        bsz = (((2*qx*qz)-(2*qy*qw))*(sx-bx))+(((2*qy*qz)+(2*qx*qw))*(sy-by))+((1-(2*qx**2)-(2*qy**2))*(sz-bz))
        
        # Solar Declination of Stanton
        Solar_declination = degrees(acos((((sqrt(bsx**2+bsy**2+bsz**2))**2)+((sqrt(bsx**2+bsy**2))**2)-(bsz**2))/(2*(sqrt(bsx**2+bsy**2+bsz**2))*(sqrt(bsx**2+bsy**2)))))*copysign(1,bsz)
        
        # Radius of Stanton
        StarRadius = Star["Body Radius"] # OK
        
        # Apparent Radius of Stanton
        Apparent_Radius = degrees(asin(StarRadius/(sqrt((bsx)**2+(bsy)**2+(bsz)**2))))
        
        # Length of day is the planet rotation rate expressed as a fraction of a 24 hr day.
        LengthOfDay = 3600*rotation_speed/86400
        
        
        
        # A Julian Date is simply the number of days and fraction of a day since a specific event. (01/01/2020 00:00:00)
        JulianDate = Time_passed_since_reference_in_seconds/(24*60*60) # OK
        
        # Determine the current day/night cycle of the planet.
        # The current cycle is expressed as the number of day/night cycles and fraction of the cycle that have occurred
        # on that planet since Jan 1, 2020 given the length of day. While the number of sunrises that have occurred on the 
        # planet since Jan 1, 2020 is interesting, we are really only interested in the fractional part.
        try :
            CurrentCycle = JulianDate/LengthOfDay
        except ZeroDivisionError :
            CurrentCycle = 1
        
        
        # The rotation correction is a value that accounts for the rotation of the planet on Jan 1, 2020 as we don’t know
        # exactly when the rotation of the planet started.  This value is measured and corrected during a rotation
        # alignment that is performed periodically in-game and is retrieved from the navigation database.
        RotationCorrection = Container["Rotation Adjust"]
        
        # CurrentRotation is how far the planet has rotated in this current day/night cycle expressed in the number of
        # degrees remaining before the planet completes another day/night cycle.
        CurrentRotation = (360-(CurrentCycle%1)*360-RotationCorrection)%360
        
        
        # Meridian determine where the star would be if the planet did not rotate.
        # Between the planet and Stanton there is a plane that contains the north pole and south pole
        # of the planet and the center of Stanton. Locations on the surface of the planet on this plane
        # experience the phenomenon we call noon.
        Meridian = degrees( (atan2(bsy,bsx)-(pi/2)) % (2*pi) )
        
        # Because the planet rotates, the location of noon is constantly moving. This equation
        # computes the current longitude where noon is occurring on the planet.
        SolarLongitude = CurrentRotation-(0-Meridian)%360
        if SolarLongitude>180:
            SolarLongitude = SolarLongitude-360
        elif SolarLongitude<-180:
            SolarLongitude = SolarLongitude+360
        
        
        
        # The difference between Longitude and Longitude360 is that for Longitude, Positive values
        # indicate locations in the Eastern Hemisphere, Negative values indicate locations in the Western
        # Hemisphere.
        # For Longitude360, locations in longitude 0-180 are in the Eastern Hemisphere, locations in
        # longitude 180-359 are in the Western Hemisphere.
        Longitude360 = Longitude%360 # OK
        
        # Determine correction for location height
        ElevationCorrection = degrees(acos(Container["Body Radius"]/(Container["Body Radius"]))) if Height<0 else degrees(acos(Container["Body Radius"]/(Container["Body Radius"]+Height)))
        
        # Determine Rise/Set Hour Angle
        # The star rises at + (positive value) rise/set hour angle and sets at - (negative value) rise/set hour angle
        # Solar Declination and Apparent Radius come from the first set of equations when we determined where the star is.
        RiseSetHourAngle = degrees(acos(-tan(radians(Latitude))*tan(radians(Solar_declination))))+Apparent_Radius+ElevationCorrection
        
        # Determine the current Hour Angle of the star
        
        # Hour Angles between 180 and the +Rise Hour Angle are before sunrise.
        # Between +Rise Hour angle and 0 are after sunrise before noon. 0 noon,
        # between 0 and -Set Hour Angle is afternoon,
        # between -Set Hour Angle and -180 is after sunset.
        
        # Once the current Hour Angle is determined, we now know the actual angle (in degrees)
        # between the position of the star and the +rise hour angle and the -set hour angle.
        HourAngle = (CurrentRotation-(Longitude360-Meridian)%360)%360
        if HourAngle > 180:
            HourAngle = HourAngle - 360
        
        
        # Determine the planet Angular Rotation Rate.
        # Angular Rotation Rate is simply the Planet Rotation Rate converted from Hours into degrees per minute.
        # The Planet Rotation Rate is datamined from the game files.
        try :
            AngularRotationRate = 6/rotation_speed # OK
        except ZeroDivisionError :
            AngularRotationRate = 0
        
        
        if AngularRotationRate != 0 :
            midnight = (HourAngle + 180) / AngularRotationRate
            
            morning = (HourAngle - (RiseSetHourAngle+12)) / AngularRotationRate
            if HourAngle <= RiseSetHourAngle+12:
                morning = morning + LengthOfDay*24*60
            
            sunrise = (HourAngle - RiseSetHourAngle) / AngularRotationRate
            if HourAngle <= RiseSetHourAngle:
                sunrise = sunrise + LengthOfDay*24*60
            
            noon = (HourAngle - 0) / AngularRotationRate
            if HourAngle <= 0:
                noon = noon + LengthOfDay*24*60
            
            sunset = (HourAngle - -1*RiseSetHourAngle) / AngularRotationRate
            if HourAngle <= -1*RiseSetHourAngle:
                sunset = sunset + LengthOfDay*24*60
            
            evening = (HourAngle - (-1*RiseSetHourAngle-12)) / AngularRotationRate
            if HourAngle <= -1*(RiseSetHourAngle-12):
                evening = evening + LengthOfDay*24*60
        else :
            midnight = 0
            morning = 0
            sunrise = 0
            noon = 0
            sunset = 0
            evening = 0
        
        
        
        
        if 180 >= HourAngle > RiseSetHourAngle+12:
            state_of_the_day = "After midnight"
            next_event = "Sunrise"
            next_event_time = sunrise
        elif RiseSetHourAngle+12 >= HourAngle > RiseSetHourAngle:
            state_of_the_day = "Morning Twilight"
            next_event = "Sunrise"
            next_event_time = sunrise
        elif RiseSetHourAngle >= HourAngle > 0:
            state_of_the_day = "Morning"
            next_event = "Sunset"
            next_event_time = sunset
        elif 0 >= HourAngle > -1*RiseSetHourAngle:
            state_of_the_day = "Afternoon"
            next_event = "Sunset"
            next_event_time = sunset
        elif -1*RiseSetHourAngle >= HourAngle > -1*RiseSetHourAngle-12:
            state_of_the_day = "Evening Twilight"
            next_event = "Sunrise"
            next_event_time = sunrise
        elif -1*RiseSetHourAngle-12 >= HourAngle >= -180:
            state_of_the_day = "Before midnight"
            next_event = "Sunrise"
            next_event_time = sunrise
        
        if AngularRotationRate == 0 :
            next_event = "N/A"
        
        return [state_of_the_day, next_event, next_event_time]
    
    except Exception as e:
        print(f"Error in sunrise/sunset calculations: \n{e}\nValues were:\n-X : {X}\n-Y : {Y}\n-Z : {Z}\n-Latitude : {Latitude}\n-Longitude : {Longitude}\n-Height : {Height}\n-Container : {Container['Name']}\n-Star : {Star['Name']}")
        sys.stdout.flush()
        return ["Unknown", "Unknown", 0]
    
def create_overlay(X : float, Y : float, Z : float, last_X : float, last_Y : float, last_Z : float, Container : dict):
    # x,y,z: current player location inside OC
    # todo: QT markers from outside OC
    # check vectors for known QT Targets
    # limit vectors to visible QT Targets
    # draw QT Targets for algnement

    drawCandidates = []
    x_array = []
    y_array = []
    z_array = []
    plt.box(False)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.set_frame_on(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    #calculate direction vector:
    direction_Vector = {
        "X": abs(X - last_X),
        "Y": abs(Y - last_Y),
        "Z": abs(Z - last_Z)
    }

    for POI in Container["POI"]:
        if Container["POI"][POI]["QTMarker"] == "TRUE":
            Vector_POI = {
               "X": abs(Container["POI"][POI]["X"] - X),
               "Y": abs(Container["POI"][POI]["Y"] - Y),
               "Z": abs(Container["POI"][POI]["Z"] - Z)
            }
            plt.plot(Container["POI"][POI]["X"], Container["POI"][POI]["Y"], Container["POI"][POI]["Z"], marker="o", markersize=20, markeredgecolor="red", markerfacecolor="green")
    
            #check if in viewport:

            #add to draw-candidates:
            x_array.append(Vector_POI["X"])
            y_array.append(Vector_POI["Y"])
            z_array.append(Vector_POI["Z"])
            
            drawCandidates.append({"Name" : POI, "X" : Vector_POI["X"], "Y" : Vector_POI["Y"], "Z" : Vector_POI["Z"]})

        #Distance_POI = vector_norm(Vector_POI)
        #Distances_to_POIs.append({"Name" : POI, "Distance" : Distance_POI})


    #plt.ylim((25,250)) ?
    plt.plot(X, Y, Z, marker="o", markersize=20, markeredgecolor="red", markerfacecolor="blue")
    
    plt.show()
    #Target_to_POIs_Distances_Sorted = sorted(Distances_to_POIs, key=lambda k: k['Distance'])








#Sets some variables
Reference_time_UTC = datetime.datetime(2020, 1, 1)
Epoch = datetime.datetime(1970, 1, 1)
Reference_time = (Reference_time_UTC - Epoch).total_seconds()




Old_player_Global_coordinates = {}
for i in ["X", "Y", "Z"]:
    Old_player_Global_coordinates[i] = 0.0

Old_player_local_rotated_coordinates = {}
for i in ["X", "Y", "Z"]:
    Old_player_local_rotated_coordinates[i] = 0.0

Old_Distance_to_POI = {}
for i in ["X", "Y", "Z"]:
    Old_Distance_to_POI[i] = 0.0

Old_container = {
    "Name": "None",
    "X": 0,
    "Y": 0,
    "Z": 0,
    "Rotation Speed": 0,
    "Rotation Adjust": 0,
    "OM Radius": 0,
    "Body Radius": 0,
    "POI": {}
}


Old_time = time.time()


def readClipboard():
    global Old_clipboard,Target, Old_time, Actual_Container, player_Longitude, player_Latitude, New_player_local_rotated_coordinates, Time_passed_since_reference_in_seconds
    #Get the new clipboard content
    new_clipboard = pyperclip.paste()


    #If clipboard content hasn't changed
    if new_clipboard == Old_clipboard and new_clipboard != "":

        #Wait some time
        #time.sleep(1/5)
        print("no update on clipboard")


    #If clipboard content has changed
    else :

        #update the memory with the new content
        Old_clipboard = new_clipboard
        #response = c.request('uk.pool.ntp.org', version=3)
        #server_time = response.tx_time
        #local_time = time.time()
        #time_difference = server_time - local_time
        #print(round(time_difference,5))
        #correction_value=time_difference
        #TPClient.stateUpdate ("correction", str(round(correction_value,5) ))

        New_time = time.time() + correction_value
        
        #If it contains some coordinates
        if new_clipboard.startswith("Coordinates:"):


            #split the clipboard in sections
            new_clipboard_splitted = new_clipboard.replace(":", " ").split(" ")


            #get the 3 new XYZ coordinates
            New_Player_Global_coordinates = {}
            New_Player_Global_coordinates['X'] = float(new_clipboard_splitted[3])/1000
            New_Player_Global_coordinates['Y'] = float(new_clipboard_splitted[5])/1000
            New_Player_Global_coordinates['Z'] = float(new_clipboard_splitted[7])/1000



            #-----------------------------------------------------Planetary Navigation--------------------------------------------------------------
            # If the target is within the attraction of a planet
            if Mode == "Planetary Navigation":



                #---------------------------------------------------Actual Container----------------------------------------------------------------
                #search in the Databse to see if the player is ina Container
                #Actual_Container = {
                #    "Name": "None",
                #    "X": 0,
                #    "Y": 0,
                #    "Z": 0,
                #    "Rotation Speed": 0,
                #    "Rotation Adjust": 0,
                #    "OM Radius": 0,
                #    "Body Radius": 0,
                #    "POI": {}
                #}
                #for i in Database["Containers"] :
                #    Player_Container_vector = {"X" : Database["Containers"][i]["X"] - New_Player_Global_coordinates["X"], "Y" : Database["Containers"][i]["Y"] - New_Player_Global_coordinates["Y"], "Z" : Database["Containers"][i]["Z"] - New_Player_Global_coordinates["Z"]}
                #    if vector_norm(Player_Container_vector) <= 2 * Database["Containers"][i]["OM Radius"]:
                #        Actual_Container = Database["Containers"][i]
                Actual_Container = get_current_container(New_Player_Global_coordinates["X"], New_Player_Global_coordinates["Y"], New_Player_Global_coordinates["Z"])



                #---------------------------------------------------New player local coordinates----------------------------------------------------
                #Time passed since the start of game simulation
                Time_passed_since_reference_in_seconds = New_time - Reference_time

                #Grab the rotation speed of the container in the Database and convert it in degrees/s
                #player_Rotation_speed_in_hours_per_rotation = Actual_Container["Rotation Speed"]
                #try:
                #    player_Rotation_speed_in_degrees_per_second = 0.1 * (1/player_Rotation_speed_in_hours_per_rotation)
                #except ZeroDivisionError:
                #    player_Rotation_speed_in_degrees_per_second = 0
                    
                
                
                #Get the actual rotation state in degrees using the rotation speed of the container, the actual time and a rotational adjustment value
                #player_Rotation_state_in_degrees = ((player_Rotation_speed_in_degrees_per_second * Time_passed_since_reference_in_seconds) + Actual_Container["Rotation Adjust"]) % 360

                #get the new player unrotated coordinates
                #New_player_local_unrotated_coordinates = {}
                #for i in ['X', 'Y', 'Z']:
                #    New_player_local_unrotated_coordinates[i] = New_Player_Global_coordinates[i] - Actual_Container[i]

                #get the new player rotated coordinates
                #New_player_local_rotated_coordinates = rotate_point_2D(New_player_local_unrotated_coordinates, radians(-1*player_Rotation_state_in_degrees))
                New_player_local_rotated_coordinates = get_local_rotated_coordinates(Time_passed_since_reference_in_seconds, New_Player_Global_coordinates["X"], New_Player_Global_coordinates["Y"], New_Player_Global_coordinates["Z"], Actual_Container)
                



                #---------------------------------------------------New player local coordinates----------------------------------------------------

                #Grab the rotation speed of the container in the Database and convert it in degrees/s
                target_Rotation_speed_in_hours_per_rotation = Database["Containers"][Target["Container"]]["Rotation Speed"]
                try:
                    target_Rotation_speed_in_degrees_per_second = 0.1 * (1/int(target_Rotation_speed_in_hours_per_rotation))
                except ZeroDivisionError:
                    target_Rotation_speed_in_degrees_per_second = 0
                    
                
                
                #Get the actual rotation state in degrees using the rotation speed of the container, the actual time and a rotational adjustment value
                target_Rotation_state_in_degrees = ((target_Rotation_speed_in_degrees_per_second * Time_passed_since_reference_in_seconds) + Database["Containers"][Target["Container"]]["Rotation Adjust"]) % 360

                #get the new player rotated coordinates
                target_rotated_coordinates = rotate_point_2D(Target, radians(target_Rotation_state_in_degrees))




                #-------------------------------------------------player local Long Lat Height--------------------------------------------------
                
                if Actual_Container['Name'] != "None":
                    
                    #Cartesian Coordinates
                    #x = New_player_local_rotated_coordinates["X"]
                    #y = New_player_local_rotated_coordinates["Y"]
                    #z = New_player_local_rotated_coordinates["Z"]

                    #Radius of the container
                    #player_Radius = Actual_Container["Body Radius"]

                    #Radial_Distance
                    #player_Radial_Distance = sqrt(x**2 + y**2 + z**2)

                    #Height
                    #player_Height = player_Radial_Distance - player_Radius
                    
                    #Longitude
                    #try :
                    #    player_Longitude = -1*degrees(atan2(x, y))
                    #except Exception as err:
                    #    print(f'Error in Longitude : {err} \nx = {x}, y = {y} \nPlease report this to Valalol#1790 for me to try to solve this issue')
                    #    sys.stdout.flush()
                    #    player_Longitude = 0

                    #Latitude
                    #try :
                    #    player_Latitude = degrees(asin(z/player_Radial_Distance))
                    #except Exception as err:
                    #    print(f'Error in Latitude : {err} \nz = {z}, radius = {player_Radial_Distance} \nPlease report this at Valalol#1790 for me to try to solve this issue')
                    #    sys.stdout.flush()
                    #    player_Latitude = 0

                    player_Latitude, player_Longitude, player_Height = get_lat_long_height(New_player_local_rotated_coordinates["X"], New_player_local_rotated_coordinates["Y"], New_player_local_rotated_coordinates["Z"], Actual_Container)

                
                
                #-------------------------------------------------target local Long Lat Height--------------------------------------------------

                #Cartesian Coordinates
                #x = Target["X"]
                #y = Target["Y"]
                #z = Target["Z"]

                #Radius of the container
                #target_Radius = Database["Containers"][Target["Container"]]["Body Radius"]

                #Radial_Distance
                #target_Radial_Distance = sqrt(x**2 + y**2 + z**2)

                #Height
                #target_Height = target_Radial_Distance - target_Radius
                
                #Longitude
                #try :
                #    target_Longitude = -1*degrees(atan2(x, y))
                #except Exception as err:
                #    print(f'Error in Longitude : {err} \nx = {x}, y = {y} \nPlease report this to Valalol#1790 for me to try to solve this issue')
                #    sys.stdout.flush()
                #    target_Longitude = 0

                #Latitude
                #try :
                #    target_Latitude = degrees(asin(z/target_Radial_Distance))
                #except Exception as err:
                #    print(f'Error in Latitude : {err} \nz = {z}, radius = {target_Radial_Distance} \nPlease report this at Valalol#1790 for me to try to solve this issue')
                #    sys.stdout.flush()
                #    target_Latitude = 0

                target_Latitude, target_Longitude, target_Height = get_lat_long_height(Target["X"], Target["Y"], Target["Z"], Database["Containers"][Target["Container"]])




                #---------------------------------------------------Distance to POI-----------------------------------------------------------------
                New_Distance_to_POI = {}
                
                if Actual_Container == Target["Container"]:
                    for i in ["X", "Y", "Z"]:
                        New_Distance_to_POI[i] = abs(Target[i] - New_player_local_rotated_coordinates[i])
                
                
                else:
                    for i in ["X", "Y", "Z"]:
                        New_Distance_to_POI[i] = abs((target_rotated_coordinates[i] + Database["Containers"][Target["Container"]][i]) - New_Player_Global_coordinates[i])

                #get the real new distance between the player and the target
                New_Distance_to_POI_Total = vector_norm(New_Distance_to_POI)

                if New_Distance_to_POI_Total <= 100:
                    New_Distance_to_POI_Total_color = "#00ff00"
                elif New_Distance_to_POI_Total <= 1000:
                    New_Distance_to_POI_Total_color = "#ffd000"
                else :
                    New_Distance_to_POI_Total_color = "#ff3700"


                #---------------------------------------------------Delta Distance to POI-----------------------------------------------------------
                #get the real old distance between the player and the target
                Old_Distance_to_POI_Total = vector_norm(Old_Distance_to_POI)




                #get the 3 XYZ distance travelled since last update
                Delta_Distance_to_POI = {}
                for i in ["X", "Y", "Z"]:
                    Delta_Distance_to_POI[i] = New_Distance_to_POI[i] - Old_Distance_to_POI[i]

                #get the real distance travelled since last update
                Delta_Distance_to_POI_Total = New_Distance_to_POI_Total - Old_Distance_to_POI_Total

                if Delta_Distance_to_POI_Total <= 0:
                    Delta_distance_to_poi_color = "#00ff00"
                else:
                    Delta_distance_to_poi_color = "#ff3700"



                #---------------------------------------------------Estimated time of arrival to POI------------------------------------------------
                #get the time between the last update and this update
                Delta_time = New_time - Old_time


                #get the time it would take to reach destination using the same speed
                try :
                    Estimated_time_of_arrival = (Delta_time*New_Distance_to_POI_Total)/abs(Delta_Distance_to_POI_Total)
                except ZeroDivisionError:
                    Estimated_time_of_arrival = 0.00



                #----------------------------------------------------Closest Quantumable POI--------------------------------------------------------
                #Target_to_POIs_Distances = []
                if Target["QTMarker"] == "FALSE":
                    #for POI in Database["Containers"][Target["Container"]]["POI"]:
                    #    if Database["Containers"][Target["Container"]]["POI"][POI]["QTMarker"] == "TRUE":#

                    #        Vector_POI_Target = {}
                    #        for i in ["X", "Y", "Z"]:
                    #            Vector_POI_Target[i] = abs(Target[i] - Database["Containers"][Target["Container"]]["POI"][POI][i])

                    #        Distance_POI_Target = vector_norm(Vector_POI_Target)

                    #        Target_to_POIs_Distances.append({"Name" : POI, "Distance" : Distance_POI_Target})

                    #Target_to_POIs_Distances_Sorted = sorted(Target_to_POIs_Distances, key=lambda k: k['Distance'])
                    Target_to_POIs_Distances_Sorted = get_closest_POI(Target["X"], Target["Y"], Target["Z"], Database["Containers"][Target["Container"]], True)

                else :
                    Target_to_POIs_Distances_Sorted = [{
                        "Name" : "POI itself",
                        "Distance" : 0
                    }]




                #----------------------------------------------------Player Closest POI--------------------------------------------------------
                #Player_to_POIs_Distances = []
                #for POI in Actual_Container["POI"]:
                
                #    Vector_POI_Player = {}
                #    for i in ["X", "Y", "Z"]:
                #        Vector_POI_Player[i] = abs(New_player_local_rotated_coordinates[i] - Actual_Container["POI"][POI][i])

                #    Distance_POI_Player = vector_norm(Vector_POI_Player)

                #    Player_to_POIs_Distances.append({"Name" : POI, "Distance" : Distance_POI_Player})

                #Player_to_POIs_Distances_Sorted = sorted(Player_to_POIs_Distances, key=lambda k: k['Distance'])
                Player_to_POIs_Distances_Sorted = get_closest_POI(New_player_local_rotated_coordinates["X"], New_player_local_rotated_coordinates["Y"], New_player_local_rotated_coordinates["Z"], Actual_Container, False)






                #-------------------------------------------------------3 Closest OMs to player---------------------------------------------------------------
                #player_Closest_OM = {}
                
                #if New_player_local_rotated_coordinates["X"] >= 0:
                #    player_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-5"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Z"]})}
                #else:
                #    player_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-6"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Z"]})}
                #if New_player_local_rotated_coordinates["Y"] >= 0:
                #    player_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-3"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Z"]})}
                #else:
                #    player_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-4"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Z"]})}
                #if New_player_local_rotated_coordinates["Z"] >= 0:
                #    player_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-1"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Z"]})}
                #else:
                #    player_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-2"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Z"]})}

                player_Closest_OM = get_closest_oms(New_player_local_rotated_coordinates["X"], New_player_local_rotated_coordinates["Y"], New_player_local_rotated_coordinates["Z"], Actual_Container)



                #-------------------------------------------------------3 Closest OMs to target---------------------------------------------------------------
                #target_Closest_OM = {}
                
                #if Target["X"] >= 0:
                #    target_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-5"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Z"]})}
                #else:
                #    target_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-6"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Z"]})}
                #if Target["Y"] >= 0:
                #    target_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-3"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Z"]})}
                #else:
                #    target_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-4"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Z"]})}
                #if Target["Z"] >= 0:
                #    target_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-1"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Z"]})}
                #else:
                #    target_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-2"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Z"]})}
                target_Closest_OM = get_closest_oms(Target["X"], Target["Y"], Target["Z"], Database["Containers"][Target["Container"]])




                #----------------------------------------------------Course Deviation to POI--------------------------------------------------------
                #get the vector between current_pos and previous_pos
                Previous_current_pos_vector = {}
                for i in ['X', 'Y', 'Z']:
                    Previous_current_pos_vector[i] = New_player_local_rotated_coordinates[i] - Old_player_local_rotated_coordinates[i]


                #get the vector between current_pos and target_pos
                Current_target_pos_vector = {}
                for i in ['X', 'Y', 'Z']:
                    Current_target_pos_vector[i] = Target[i] - New_player_local_rotated_coordinates[i]


                #get the angle between the current-target_pos vector and the previous-current_pos vector
                Total_deviation_from_target = angle_between_vectors(Previous_current_pos_vector, Current_target_pos_vector)


                if Total_deviation_from_target <= 10:
                    Total_deviation_from_target_color = "#00ff00"
                elif Total_deviation_from_target <= 20:
                    Total_deviation_from_target_color = "#ffd000"
                else:
                    Total_deviation_from_target_color = "#ff3700"


                #----------------------------------------------------------Flat_angle--------------------------------------------------------------
                previous = Old_player_local_rotated_coordinates
                current = New_player_local_rotated_coordinates


                #Vector AB (Previous -> Current)
                previous_to_current = {}
                for i in ["X", "Y", "Z"]:
                    previous_to_current[i] = current[i] - previous[i]

                #Vector AC (C = center of the planet, Previous -> Center)
                previous_to_center = {}
                for i in ["X", "Y", "Z"]:
                    previous_to_center[i] = 0 - previous[i]

                #Vector BD (Current -> Target)
                current_to_target = {}
                for i in ["X", "Y", "Z"]:
                    current_to_target[i] = Target[i] - current[i]

                    #Vector BC (C = center of the planet, Current -> Center)
                current_to_center = {}
                for i in ["X", "Y", "Z"]:
                    current_to_center[i] = 0 - current[i]



                #Normal vector of a plane:
                #abc : Previous/Current/Center
                n1 = {}
                n1["X"] = previous_to_current["Y"] * previous_to_center["Z"] - previous_to_current["Z"] * previous_to_center["Y"]
                n1["Y"] = previous_to_current["Z"] * previous_to_center["X"] - previous_to_current["X"] * previous_to_center["Z"]
                n1["Z"] = previous_to_current["X"] * previous_to_center["Y"] - previous_to_current["Y"] * previous_to_center["X"]

                #acd : Previous/Center/Target
                n2 = {}
                n2["X"] = current_to_target["Y"] * current_to_center["Z"] - current_to_target["Z"] * current_to_center["Y"]
                n2["Y"] = current_to_target["Z"] * current_to_center["X"] - current_to_target["X"] * current_to_center["Z"]
                n2["Z"] = current_to_target["X"] * current_to_center["Y"] - current_to_target["Y"] * current_to_center["X"]

                Flat_angle = angle_between_vectors(n1, n2)


                if Flat_angle <= 10:
                    Flat_angle_color = "#00ff00"
                elif Flat_angle <= 20:
                    Flat_angle_color = "#ffd000"
                else:
                    Flat_angle_color = "#ff3700"
                
                #-------------------------------------------------Sunrise Sunset Calculation----------------------------------------------------
                player_state_of_the_day, player_next_event, player_next_event_time = get_sunset_sunrise_predictions(
                    New_player_local_rotated_coordinates["X"], 
                    New_player_local_rotated_coordinates["Y"], 
                    New_player_local_rotated_coordinates["Z"], 
                    player_Latitude, 
                    player_Longitude, 
                    player_Height, 
                    Actual_Container, 
                    Database["Containers"]["Stanton"]
                )
                
                target_state_of_the_day, target_next_event, target_next_event_time = get_sunset_sunrise_predictions(
                    Target["X"], 
                    Target["Y"], 
                    Target["Z"], 
                    target_Latitude, 
                    target_Longitude, 
                    target_Height, 
                    Database["Containers"][Target["Container"]], 
                    Database["Containers"]["Stanton"]
                )
                
                
                #----------------------------------------------------------Heading--------------------------------------------------------------
                
                bearingX = cos(radians(target_Latitude)) * sin(radians(target_Longitude) - radians(player_Longitude))
                bearingY = cos(radians(player_Latitude)) * sin(radians(target_Latitude)) - sin(radians(player_Latitude)) * cos(radians(target_Latitude)) * cos(radians(target_Longitude) - radians(player_Longitude))

                Bearing = (degrees(atan2(bearingX, bearingY)) + 360) % 360


                #------------------------------------------------------------Backend to Frontend------------------------------------------------------------
                new_data = {
                    "updated" : f"{time.strftime('%H:%M:%S', time.localtime(time.time()))}",
                    "target" : Target['Name'],
                    "player_actual_container" : Actual_Container['Name'],
                    "target_container" : Target['Container'],
                    "player_x" : round(New_player_local_rotated_coordinates['X'], 3),
                    "player_y" : round(New_player_local_rotated_coordinates['Y'], 3),
                    "player_z" : round(New_player_local_rotated_coordinates['Z'], 3),
                    "player_long" : f"{round(player_Longitude, 2)}°",
                    "player_lat" : f"{round(player_Latitude, 2)}°",
                    "player_height" : f"{round(player_Height, 1)} km",
                    "player_OM1" : f"{player_Closest_OM['Z']['OM']['Name']} : {round(player_Closest_OM['Z']['Distance'], 3)} km",
                    "player_OM2" : f"{player_Closest_OM['Y']['OM']['Name']} : {round(player_Closest_OM['Y']['Distance'], 3)} km",
                    "player_OM3" : f"{player_Closest_OM['X']['OM']['Name']} : {round(player_Closest_OM['X']['Distance'], 3)} km",
                    "player_closest_poi" : f"{Player_to_POIs_Distances_Sorted[0]['Name']} : {round(Player_to_POIs_Distances_Sorted[0]['Distance'], 3)} km",
                    "target_x" : Target["X"],
                    "target_y" : Target["Y"],
                    "target_z" : Target["Z"],
                    "target_long" : f"{round(target_Longitude, 2)}°",
                    "target_lat" : f"{round(target_Latitude, 2)}°",
                    "target_height" : f"{round(target_Height, 1)} km",
                    "target_OM1" : f"{target_Closest_OM['Z']['OM']['Name']} : {round(target_Closest_OM['Z']['Distance'], 3)} km",
                    "target_OM2" : f"{target_Closest_OM['Y']['OM']['Name']} : {round(target_Closest_OM['Y']['Distance'], 3)} km",
                    "target_OM3" : f"{target_Closest_OM['X']['OM']['Name']} : {round(target_Closest_OM['X']['Distance'], 3)} km",
                    "target_closest_QT_beacon" : f"{Target_to_POIs_Distances_Sorted[0]['Name']} : {round(Target_to_POIs_Distances_Sorted[0]['Distance'], 3)} km",
                    "distance_to_poi" : f"{round(New_Distance_to_POI_Total, 3)} km",
                    "distance_to_poi_color" : New_Distance_to_POI_Total_color,
                    "delta_distance_to_poi" : f"{round(abs(Delta_Distance_to_POI_Total), 3)} km",
                    "delta_distance_to_poi_color" : Delta_distance_to_poi_color,
                    "total_deviation" : f"{round(Total_deviation_from_target, 1)}°",
                    "total_deviation_color" : Total_deviation_from_target_color,
                    "horizontal_deviation" : f"{round(Flat_angle, 1)}°",
                    "horizontal_deviation_color" : Flat_angle_color,
                    "heading" : f"{round(Bearing, 1)}°",
                    "ETA" : f"{str(datetime.timedelta(seconds=round(Estimated_time_of_arrival, 0)))}"
                }
                print("New data :", json.dumps(new_data))
                sys.stdout.flush()
                
                #bomb drop off calculations
                horizontal_distance = sqrt(pow(New_Distance_to_POI_Total,2) - pow((player_Height - target_Height),2))
                
                TPClient.stateUpdate("currentDstName", Target['Name'] )
                TPClient.stateUpdate("DistanceToDst", f"{round(New_Distance_to_POI_Total, 1)} km (Hor: {round(horizontal_distance, 1)} km" )
                TPClient.stateUpdate("Bearing", f"{round(Bearing, 0)}°" )
                TPClient.stateUpdate("nearestQTMarkerNameDistance", f"{Target_to_POIs_Distances_Sorted[0]['Name']} : {round(Target_to_POIs_Distances_Sorted[0]['Distance'], 1)} km" )
                where_am_i = "Current: " , Actual_Container['Name'] , ", x:", round(New_player_local_rotated_coordinates['X'], 3), " y:", round(New_player_local_rotated_coordinates['Y'], 3), " z:", round(New_player_local_rotated_coordinates['Z'], 3)
                print(where_am_i)
                TPClient.stateUpdate("currentLocationPlayer", str(where_am_i) )
                
                #point = (Target["X"], Target["Y"], Target["Z"])
                #rot_x = asin(New_player_local_rotated_coordinates['Z']/sqrt(pow(New_player_local_rotated_coordinates['Y'],2)+pow(New_player_local_rotated_coordinates['Z',2])))
                #rot_y = 0
                #rot_z = asin(New_player_local_rotated_coordinates['Y']/sqrt(pow(New_player_local_rotated_coordinates['X'],2)+pow(New_player_local_rotated_coordinates['Y',2])))
                #rotation = (rot_x, rot_y, rot_z)
                #translation = (-New_player_local_rotated_coordinates['X'], -New_player_local_rotated_coordinates['Y'], -New_player_local_rotated_coordinates['Z'])
                #matrix = matrix(rotation, translation)
                #print (transform(point, matrix))
                
                
                #horizontal_distance = sqrt(pow(New_Distance_to_POI_Total,2) - pow((player_Height - target_Height),2))
                #TPClient.stateUpdate("Horizontal_Distance", f"{round(horizontal_distance, 1)}km" )
                print("Player Height: " + str(player_Height) + " - Target Height: " + str(target_Height) + " Horizontal Distance: " + str(horizontal_distance))

                # player_state_of_the_day, player_next_event, player_next_event_time
                # target_state_of_the_day, target_next_event, target_next_event_time
                #Sunset_Info
                player_next_event_time = f"{time.strftime('%H:%M:%S', time.localtime(New_time + player_next_event_time*60))}"
                target_next_event_time = f"{time.strftime('%H:%M:%S', time.localtime(New_time + target_next_event_time*60))}"
                
                print("Sunset_Info", "Dst: " +  str(target_state_of_the_day) + ", " + str(target_next_event) + " at " +  str(target_next_event_time) + " Player: " + str(player_next_event) + " at " + str(player_next_event_time))
                TPClient.stateUpdate("Sunset_Info", "Dst: " +  str(target_state_of_the_day) + ", " + str(target_next_event) + " at " +  str(target_next_event_time) + " Player: " + str(player_next_event) + " at " + str(player_next_event_time))

                #create_overlay(New_Player_Global_coordinates["X"], New_Player_Global_coordinates["Y"], New_Player_Global_coordinates["Z"])
                #create_overlay(New_player_local_rotated_coordinates['X'],New_player_local_rotated_coordinates['Y'],New_player_local_rotated_coordinates['Z'],Old_player_local_rotated_coordinates['X'],Old_player_local_rotated_coordinates['Y'],Old_player_local_rotated_coordinates['Z'],Database["Containers"][Target["Container"]])


                #---------------------------------------------------Update coordinates for the next update------------------------------------------
                for i in ["X", "Y", "Z"]:
                    Old_player_Global_coordinates[i] = New_Player_Global_coordinates[i]

                for i in ["X", "Y", "Z"]:
                    Old_player_local_rotated_coordinates[i] = New_player_local_rotated_coordinates[i]

                for i in ["X", "Y", "Z"]:
                    Old_Distance_to_POI[i] = New_Distance_to_POI[i]

                Old_time = New_time

                #-------------------------------------------------------------------------------------------------------------------------------------------

def add_char(newChar):
    global custom_x,custom_y,custom_z,edit_coordinate
    if edit_coordinate == "none":
            print("no coordinate selected")
    elif edit_coordinate == "x":
            custom_x = custom_x + newChar
            TPClient.stateUpdate("custom_x", "X: " + custom_x)
    elif edit_coordinate == "y":
            custom_y = custom_y + newChar
            TPClient.stateUpdate("custom_y", "Y: "+ custom_y) 
    elif edit_coordinate == "z":
            custom_z = custom_z + newChar
            TPClient.stateUpdate("custom_z", "Z: "+ custom_z)         


@TPClient.on(TP.TYPES.onConnectorChange)
def connectorManager(data):
    global correction_value
    if data['connectorId'] == "correctionvalueslider" :
        correction_value=data['value'] * 0.5 - 25
        print(correction_value)
        TPClient.stateUpdate ("correction", str(correction_value) )


# This event handler will run once when the client connects to Touch Portal
@TPClient.on(TP.TYPES.onConnect) # Or replace TYPES.onConnect with 'info'
def onStart(data):
    global planetsListPointer,Container_list,Planetary_POI_list
    print("Connected!", data)
    # Update a state value in TouchPortal
    TPClient.stateUpdate("SCNavState", "Connected!")
    TPClient.stateUpdate ("selectedPlanet", Container_list[0])
    TPClient.stateUpdate("selectedPOI", Planetary_POI_list[Container_list[planetsListPointer]][0] )
    TPClient.stateUpdate ("correction", str(round(correction_value,5)))

# Action handlers, called when user activates one of this plugin's actions in Touch Portal.
@TPClient.on(TP.TYPES.onAction) # Or 'action'

def onAction(data):
    global planetsListPointer,poiListPointer,Container_list, Planetary_POI_list, Target, Actual_Container, toggle_qt_marker_switch,custom_x,custom_y,custom_z,edit_coordinate
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
      Target = Database["Containers"][Container_list[planetsListPointer]]["POI"][f'{Planetary_POI_list[Container_list[planetsListPointer]][poiListPointer]}']
      TPClient.stateUpdate("currentDstName", Target['Name'] )
      TPClient.stateUpdate("DistanceToDst", "? km" )
      TPClient.stateUpdate("Bearing", "-- °" )
      TPClient.stateUpdate("nearestQTMarkerNameDistance", "--" )
                
      readClipboard()
      print(Target)
    
      
    if data['actionId'] == "startNav2Coordinates":
      # get the value from the action data (a string the user specified)
      print("startNav for ", Container_list[planetsListPointer], ", ", custom_x, ", ", custom_y, ", ", custom_z)
      Target = {'Name': 'Custom POI', 'Container': f'{Container_list[planetsListPointer]}', 'X': float(custom_x), 'Y': float(custom_y), 'Z': float(custom_z), "QTMarker": "FALSE"}
      TPClient.stateUpdate("DistanceToDst", "? km" )
      TPClient.stateUpdate("Bearing", "-- °" )
      TPClient.stateUpdate("nearestQTMarkerNameDistance", "--" )
      
      readClipboard()
      print(Target)
    
    if data['actionId'] == "enter_x":
      # get the value from the action data (a string the user specified)
      edit_coordinate = "x"
      TPClient.stateUpdate("custom_x", "X: ?")
      custom_x = ""

    if data['actionId'] == "enter_y":
      # get the value from the action data (a string the user specified)
      edit_coordinate = "y"
      TPClient.stateUpdate("custom_y", "Y: ?")
      custom_y = ""

    if data['actionId'] == "enter_z":
      # get the value from the action data (a string the user specified)
      edit_coordinate = "z"
      TPClient.stateUpdate("custom_z", "Z: ?")   
      custom_z = "" 
    
    if data['actionId'] == "takeover_custom_coordinates":
      # get the value from the action data (a string the user specified)
       custom_xyz = custom_x + ", " + custom_y + ", " + custom_z
       print("Custom xzy: " + custom_xyz)
       TPClient.stateUpdate("custom_xyz", custom_xyz)
       edit_coordinate = "none"
    
    if data['actionId'] == "decimal":
      # get the value from the action data (a string the user specified)
      add_char(".") 

    if data['actionId'] == "0":
        add_char("0")        
    if data['actionId'] == "1":
        add_char("1")  
    if data['actionId'] == "2":
        add_char("2")
    if data['actionId'] == "3":
        add_char("3") 
    if data['actionId'] == "4":
        add_char("4") 
    if data['actionId'] == "5":
        add_char("5")
    if data['actionId'] == "6":
        add_char("6")
    if data['actionId'] == "7":
        add_char("7") 
    if data['actionId'] == "8":
        add_char("8")
    if data['actionId'] == "9":
        add_char("9")

    if data['actionId'] == "plus_minus":
        add_char("-")      

    if data['actionId'] == "del":
        if edit_coordinate == "none":
            print("no coordinate selected")
        elif edit_coordinate == "x":
            custom_x = custom_x[:-1]
            TPClient.stateUpdate("custom_x", "X: " + custom_x)
        elif edit_coordinate == "y":
            custom_y = custom_y[:-1]
            TPClient.stateUpdate("custom_y", "Y: "+ custom_y) 
        elif edit_coordinate == "z":
            custom_z = custom_z[:-1]
            TPClient.stateUpdate("custom_z", "Z: "+ custom_z) 


    if data['actionId'] == "toggle_wo_qtmarker":
      # get the value from the action data (a string the user specified)
      if toggle_qt_marker_switch == 0: toggle_qt_marker_switch = 1
      elif toggle_qt_marker_switch == 1: toggle_qt_marker_switch = 2
      elif toggle_qt_marker_switch == 2: toggle_qt_marker_switch = 0
      else: 
        print("Something wrong with Toggle switch... should not happen")
      
      print("Toggle wo qt marker to ", toggle_qt_marker_switch)
      poiListPointer = 0
      planetsListPointer = 0
      loadPOIList()
      
      
          
    if data['actionId'] == "saveLocation":
      # get the value from the action data (a string the user specified)
      print("saveLocation:")
      print(Actual_Container['Name'])
      print("player_x " , round(New_player_local_rotated_coordinates['X'], 3))
      print("player_y " , round(New_player_local_rotated_coordinates['Y'], 3))
      print("player_z " , round(New_player_local_rotated_coordinates['Z'], 3))
      
      poi_name="Test1"
      save_dic = {Actual_Container['Name']:{"Name":poi_name,"Container":Actual_Container['Name'],"X":round(New_player_local_rotated_coordinates['X'], 3),"Y":round(New_player_local_rotated_coordinates['Y'], 3),"Z":round(New_player_local_rotated_coordinates['Z'], 3),"QTMarker": "FALSE"}}
      #save_data = ",{",Actual_Container['Name'],":{Name:",Actual_Container['Name'],"Container:",Actual_Container['Name'],",x: ",round(New_player_local_rotated_coordinates['X'], 3),"y: ",round(New_player_local_rotated_coordinates['Y'], 3),",z: ",round(New_player_local_rotated_coordinates['Z'], 3),"QTMarker: FALSE}\n"
      with open("saved_pois.json", "a") as myfile:
            myfile.write(json.dumps(save_dic))
            print(json.dumps(save_dic))

      #"ArcCorp Mining Area 141": {
      #              "Name": "ArcCorp Mining Area 141",
      #              "Container": "Daymar",
      #              "X": -18.167,
      #              "Y": 180.362,
      #              "Z": -232.76,
      #              "qw": -0.22158949,
      #              "qx": 0.71121597,
      #              "qy": -0.62341905,
      #              "qz": -0.23752604,
      #              "QTMarker": "TRUE"
      
    if data['actionId'] == "updateLocation":
      # get the value from the action data (a string the user specified)
      print("updateLocation")
      
      readClipboard()

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

