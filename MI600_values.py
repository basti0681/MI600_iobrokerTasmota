# -*- coding: utf-8 -*-
import requests
from requests.exceptions import Timeout
import os
from paho.mqtt import client as mqtt
import time, json, sys, math, datetime, re
from datetime import datetime
import subprocess
import platform


################################
# MQTT CONFIG
################################
mqtt_ip = '192.168.xx.xx'
mqtt_port = 1883
client_id = "DVES_MI600"
mqtt_username = 'xx'
mqtt_password = 'xx'


################################
# MI600 Login
################################
htaccess_user = 'xx'
htaccess_pw = 'xx'
bosswerkIP = '192.168.xx.xx'
ping_try_count = 10     #multiplied with 3 seconds sleep between each loop => 10*3 = 30 seconds try to connect the inverter then kill the script
webinterface_url = 'http://192.168.xx.xx/status.html'




def connectMQTT(ip, port):
 client = mqtt.Client(client_id)
 client.username_pw_set(mqtt_username, mqtt_password)
 client.on_connect = on_connect
 client.on_message = on_message
 client.connect(ip , port, 60)
 return client

def sendData(client, webdata_now_p, webdata_today_e, webdata_total_e):
    client.publish("tasmota_MI600/BM280/Power",webdata_now_p)
    client.publish("tasmota_MI600/BM280/Today",webdata_today_e)
    client.publish("tasmota_MI600/BM280/Total",webdata_total_e)
    client.disconnect()

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+":"+str(msg.payload))  



def ping_ip(current_ip_address):
        #source: https://dmitrygolovach.com/python-ping-ip-address/
        try:
            output = subprocess.check_output("ping -{} 1 {}".format('n' if platform.system().lower(
            ) == "windows" else 'c', current_ip_address ), shell=True, universal_newlines=True)
            if 'unreachable' in output:
                return False
            else:
                return True
        except Exception:
                return False


def find_target_value(target, hp_source):
  find_target = hp_source.find(target)
  #print("target: {}" .format(find_target))
  get_target_back = "-1"
  if find_target > 0:
    find_value_start = hp_source.find("\"", find_target)
    #print("start: {}" .format(find_value_start))
    find_value_end = hp_source.find("\"", find_value_start+1)
    #print("end: {}" .format(find_value_end))
          
  get_target_back = hp_source[find_value_start+1:find_value_end]
  return(get_target_back)



def get_Solar_values():
    try:
        r = requests.get(webinterface_url, verify=False, auth=(htaccess_user, htaccess_pw), timeout=2)
    except Timeout:
        print('I waited far too long')
    else:
        print('The request got executed')
        if r.status_code == 200:
            hp_source = str(r.text)
            #print(hp_source)
            error = re.search("ERROR:404 Not Found:", hp_source)


            if(hp_source.find('ERROR:404 Not Found') == True):
                print(error)
            else:
                ret0 = find_target_value("var webdata_now_p =", hp_source)
                #print(find_target_value("var webdata_now_p =", hp_source))
                if not (re.search('---',ret0) == True):
                    power = ret0
                    print('Power: '+ret0+'W')
                ret1 = find_target_value("var webdata_today_e =", hp_source)
                #print(find_target_value("var webdata_today_e =", hp_source))
                if not (re.search('---',ret1) == True):
                    today = ret1
                    print('Energy: '+ret1+'kWh')
                ret2 = find_target_value("var webdata_total_e =", hp_source)
                #print(find_target_value("var webdata_total_e =", hp_source))
                if not (re.search('---',ret2) == True):
                    total = ret2
                    print('Total: '+ret2+'kWh')
                if ret1 is not None:
                    client = connectMQTT(mqtt_ip, mqtt_port)
                    sendData(client, power, today, total)
            
        else:
            print(r.status_code)

        #close connection
        r.close()
        print("Connection Closed")




if __name__=='__main__':
    getDataCountPing = 0
    while getDataCountPing < ping_try_count:
        #print(getDataCountPing)
        if ping_ip(bosswerkIP) == True:
            get_Solar_values()
            break
        else:
          getDataCountPing = getDataCountPing + 1
          time.sleep(3)
          if getDataCountPing == ping_try_count:
            startmsg = json.dumps({"device": {"status": {"clientname":'MI600', "status":"Offline", "power":0.0, "lastDateUpdate":datetime.today().strftime('%Y-%m-%d %H:%M:%S')}}}, skipkeys = True, allow_nan = False);
            client = connectMQTT(mqtt_ip, mqtt_port)
            client.publish(topic, startmsg, qos=0, retain=False)
            client.disconnect()
          
