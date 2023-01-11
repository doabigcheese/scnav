#Made by Valalol#1790
#First release 16/04/2021

#Imports
from math import sqrt, degrees, radians, cos, acos, sin, asin, atan2
import pyperclip
import time
import datetime

import json
import os
import csv
import sys



os.system("")


Program_mode_list = ["Planetary Navigation", "Space Navigation", "Companion"] #, "Racing Tool"

with open('Database.json') as f:
    Database = json.load(f)


Container_list = []
for i in Database["Containers"]:
    Container_list.append(Database["Containers"][i]["Name"])

Space_POI_list = []
for poi in Database["Space_POI"]:
    Space_POI_list.append(poi)

Planetary_POI_list = {}
for container_name in Database["Containers"]:
    Planetary_POI_list[container_name] = []
    for poi in Database["Containers"][container_name]["POI"]:
        if "OM-" not in poi and "Comm Array" not in poi:
           Planetary_POI_list[container_name].append(poi)



Target = ""
Mode = "Planetary Navigation"

Target = Database["Containers"][Container_Selection_Combobox.get()]["POI"][f'{Planetary_POI_Selection_Combobox.get()}']

#Target = {'Name': 'Custom POI', 'Container': f'{Container_Selection_Combobox.get()}', 'X': float(Planetary_X_Custom_POI_Entry.get()), 'Y': float(Planetary_Y_Custom_POI_Entry.get()), 'Z': float(Planetary_Z_Custom_POI_Entry.get()), "QTMarker": "FALSE"}




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


#Sets some variables
Reference_time_UTC = datetime.datetime(2020, 1, 1)
Epoch = datetime.datetime(1970, 1, 1)
Reference_time = (Reference_time_UTC - Epoch).total_seconds()





Old_clipboard = ""

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


#Reset the clipboard content
pyperclip.copy("")


def readClipboard():

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

        New_time = time.time()

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
                    Player_Container_vector = {"X" : Database["Containers"][i]["X"] - New_Player_Global_coordinates["X"], "Y" : Database["Containers"][i]["Y"] - New_Player_Global_coordinates["Y"], "Z" : Database["Containers"][i]["Z"] - New_Player_Global_coordinates["Z"]}
                    if vector_norm(Player_Container_vector) <= 2 * Database["Containers"][i]["OM Radius"]:
                        Actual_Container = Database["Containers"][i]



                #---------------------------------------------------New player local coordinates----------------------------------------------------
                #Time passed since the start of game simulation
                Time_passed_since_reference_in_seconds = New_time - Reference_time

                #Grab the rotation speed of the container in the Database and convert it in degrees/s
                player_Rotation_speed_in_hours_per_rotation = Actual_Container["Rotation Speed"]
                try:
                    player_Rotation_speed_in_degrees_per_second = 0.1 * (1/player_Rotation_speed_in_hours_per_rotation)
                except ZeroDivisionError:
                    player_Rotation_speed_in_degrees_per_second = 0
                    
                
                
                #Get the actual rotation state in degrees using the rotation speed of the container, the actual time and a rotational adjustment value
                player_Rotation_state_in_degrees = ((player_Rotation_speed_in_degrees_per_second * Time_passed_since_reference_in_seconds) + Actual_Container["Rotation Adjust"]) % 360

                #get the new player unrotated coordinates
                New_player_local_unrotated_coordinates = {}
                for i in ['X', 'Y', 'Z']:
                    New_player_local_unrotated_coordinates[i] = New_Player_Global_coordinates[i] - Actual_Container[i]

                #get the new player rotated coordinates
                New_player_local_rotated_coordinates = rotate_point_2D(New_player_local_unrotated_coordinates, radians(-1*player_Rotation_state_in_degrees))




                #---------------------------------------------------New player local coordinates----------------------------------------------------

                #Grab the rotation speed of the container in the Database and convert it in degrees/s
                target_Rotation_speed_in_hours_per_rotation = Database["Containers"][Target["Container"]]["Rotation Speed"]
                try:
                    target_Rotation_speed_in_degrees_per_second = 0.1 * (1/target_Rotation_speed_in_hours_per_rotation)
                except ZeroDivisionError:
                    target_Rotation_speed_in_degrees_per_second = 0
                    
                
                
                #Get the actual rotation state in degrees using the rotation speed of the container, the actual time and a rotational adjustment value
                target_Rotation_state_in_degrees = ((target_Rotation_speed_in_degrees_per_second * Time_passed_since_reference_in_seconds) + Database["Containers"][Target["Container"]]["Rotation Adjust"]) % 360

                #get the new player rotated coordinates
                target_rotated_coordinates = rotate_point_2D(Target, radians(target_Rotation_state_in_degrees))




                #-------------------------------------------------player local Long Lat Height--------------------------------------------------
                
                if Actual_Container['Name'] != "None":
                    
                    #Cartesian Coordinates
                    x = New_player_local_rotated_coordinates["X"]
                    y = New_player_local_rotated_coordinates["Y"]
                    z = New_player_local_rotated_coordinates["Z"]

                    #Radius of the container
                    player_Radius = Actual_Container["Body Radius"]

                    #Radial_Distance
                    player_Radial_Distance = sqrt(x**2 + y**2 + z**2)

                    #Height
                    player_Height = player_Radial_Distance - player_Radius
                    
                    #Longitude
                    try :
                        player_Longitude = -1*degrees(atan2(x, y))
                    except Exception as err:
                        print(f'Error in Longitude : {err} \nx = {x}, y = {y} \nPlease report this to Valalol#1790 for me to try to solve this issue')
                        sys.stdout.flush()
                        player_Longitude = 0

                    #Latitude
                    try :
                        player_Latitude = degrees(asin(z/player_Radial_Distance))
                    except Exception as err:
                        print(f'Error in Latitude : {err} \nz = {z}, radius = {player_Radial_Distance} \nPlease report this at Valalol#1790 for me to try to solve this issue')
                        sys.stdout.flush()
                        player_Latitude = 0

                
                
                #-------------------------------------------------target local Long Lat Height--------------------------------------------------

                #Cartesian Coordinates
                x = Target["X"]
                y = Target["Y"]
                z = Target["Z"]

                #Radius of the container
                target_Radius = Database["Containers"][Target["Container"]]["Body Radius"]

                #Radial_Distance
                target_Radial_Distance = sqrt(x**2 + y**2 + z**2)

                #Height
                target_Height = target_Radial_Distance - target_Radius
                
                #Longitude
                try :
                    target_Longitude = -1*degrees(atan2(x, y))
                except Exception as err:
                    print(f'Error in Longitude : {err} \nx = {x}, y = {y} \nPlease report this to Valalol#1790 for me to try to solve this issue')
                    sys.stdout.flush()
                    target_Longitude = 0

                #Latitude
                try :
                    target_Latitude = degrees(asin(z/target_Radial_Distance))
                except Exception as err:
                    print(f'Error in Latitude : {err} \nz = {z}, radius = {target_Radial_Distance} \nPlease report this at Valalol#1790 for me to try to solve this issue')
                    sys.stdout.flush()
                    target_Latitude = 0





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
                Target_to_POIs_Distances = []
                if Target["QTMarker"] == "FALSE":
                    for POI in Database["Containers"][Target["Container"]]["POI"]:
                        if Database["Containers"][Target["Container"]]["POI"][POI]["QTMarker"] == "TRUE":

                            Vector_POI_Target = {}
                            for i in ["X", "Y", "Z"]:
                                Vector_POI_Target[i] = abs(Target[i] - Database["Containers"][Target["Container"]]["POI"][POI][i])

                            Distance_POI_Target = vector_norm(Vector_POI_Target)

                            Target_to_POIs_Distances.append({"Name" : POI, "Distance" : Distance_POI_Target})

                    Target_to_POIs_Distances_Sorted = sorted(Target_to_POIs_Distances, key=lambda k: k['Distance'])
                
                else :
                    Target_to_POIs_Distances_Sorted = [{
                        "Name" : "POI itself",
                        "Distance" : 0
                    }]




                #----------------------------------------------------Player Closest POI--------------------------------------------------------
                Player_to_POIs_Distances = []
                for POI in Actual_Container["POI"]:
                
                    Vector_POI_Player = {}
                    for i in ["X", "Y", "Z"]:
                        Vector_POI_Player[i] = abs(New_player_local_rotated_coordinates[i] - Actual_Container["POI"][POI][i])

                    Distance_POI_Player = vector_norm(Vector_POI_Player)

                    Player_to_POIs_Distances.append({"Name" : POI, "Distance" : Distance_POI_Player})

                Player_to_POIs_Distances_Sorted = sorted(Player_to_POIs_Distances, key=lambda k: k['Distance'])





                #-------------------------------------------------------3 Closest OMs to player---------------------------------------------------------------
                player_Closest_OM = {}
                
                if New_player_local_rotated_coordinates["X"] >= 0:
                    player_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-5"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Z"]})}
                else:
                    player_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-6"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Z"]})}
                if New_player_local_rotated_coordinates["Y"] >= 0:
                    player_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-3"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Z"]})}
                else:
                    player_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-4"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Z"]})}
                if New_player_local_rotated_coordinates["Z"] >= 0:
                    player_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-1"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Z"]})}
                else:
                    player_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-2"], "Distance" : vector_norm({"X" : New_player_local_rotated_coordinates["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["X"], "Y" : New_player_local_rotated_coordinates["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Y"], "Z" : New_player_local_rotated_coordinates["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Z"]})}




                #-------------------------------------------------------3 Closest OMs to target---------------------------------------------------------------
                target_Closest_OM = {}
                
                if Target["X"] >= 0:
                    target_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-5"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-5"]["Z"]})}
                else:
                    target_Closest_OM["X"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-6"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-6"]["Z"]})}
                if Target["Y"] >= 0:
                    target_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-3"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-3"]["Z"]})}
                else:
                    target_Closest_OM["Y"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-4"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-4"]["Z"]})}
                if Target["Z"] >= 0:
                    target_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-1"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-1"]["Z"]})}
                else:
                    target_Closest_OM["Z"] = {"OM" : Database["Containers"][Target["Container"]]["POI"]["OM-2"], "Distance" : vector_norm({"X" : Target["X"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["X"], "Y" : Target["Y"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Y"], "Z" : Target["Z"] - Database["Containers"][Target["Container"]]["POI"]["OM-2"]["Z"]})}




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
                



               


                #---------------------------------------------------Update coordinates for the next update------------------------------------------
                for i in ["X", "Y", "Z"]:
                    Old_player_Global_coordinates[i] = New_Player_Global_coordinates[i]

                for i in ["X", "Y", "Z"]:
                    Old_player_local_rotated_coordinates[i] = New_player_local_rotated_coordinates[i]

                for i in ["X", "Y", "Z"]:
                    Old_Distance_to_POI[i] = New_Distance_to_POI[i]

                Old_time = New_time

                #-------------------------------------------------------------------------------------------------------------------------------------------













# Hurston : Coordinates: x:12850457093 y:0 z:0
# Microtech : Coordinates: x:22462016306.0103 y:37185625645.8346 z:0
# Daymar : Coordinates: x:-18930439540 y:-2610058765 z:0