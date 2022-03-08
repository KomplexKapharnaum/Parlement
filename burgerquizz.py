from sre_parse import State
import paho.mqtt.client as mqtt 
import time
from enum import Enum


class States(Enum):
    INIT    = 1
    CONN    = 2
    START   = 3
    READY   = 4
    BUZZED  = 5
    CHRONO  = 6


state = States.INIT
leader = 0

def setState(s):
    global state
    state = s
    print("- ", s)

######## MQTT

mqttBroker ="127.0.0.1"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker ", mqttBroker)
    client.subscribe("k32/event/#")
    global state
    setState(States.START)
    


def on_disconnect(client, userdata, rc):
    global state
    setState(States.CONN)
    print("- State", "CONN")
    print("Disconnected from MQTT broker.. retrying")
    client.reconnect_delay_set(1,30)

def on_publish(client, userdata, mid):
    # print("Published")
    pass

def on_message(client, userdata, message):
    print("Received message '" + str(message.payload) + "' on topic '" + message.topic + "' with QoS " + str(message.qos))
    
    # BUZZ
    if message.topic == "k32/event/buzz" and state == States.READY:
        
        # BUZZED    
        setState(States.BUZZED)
        leader = int(message.payload)
        client.publish("k32/l"+str(leader)+"/leds/mem", "1", qos=1)
        print("k32/l"+str(leader)+"/leds/mem", "1")
        
        for i in range(1,6):
            if i != leader:
                client.publish("k32/l"+str(i)+"/leds/mem", "0", qos=1)
                print("k32/l"+str(i)+"/leds/mem", "0")
        
        
    # END
    if message.topic.startswith("k32/event/sablier") and state == States.CHRONO:
        setState(States.READY)
        
        


######### MAIN LOOP

while True:
    if state == States.INIT:
        client = mqtt.Client("Controller")
        client.loop_start()
        client.on_message=on_message 
        client.on_connect=on_connect 
        client.on_publish=on_publish 
        client.on_disconnect=on_disconnect 
        client.connect_async(mqttBroker)  
        setState(States.CONN)
        
    elif state == States.CONN:
        time.sleep(.5)
        
    elif state == States.START:
        client.publish("k32/all/leds/mem", "0", qos=1)
        time.sleep(1)
        setState(States.READY)
    
    elif state == States.BUZZED:
        # CHRONO
        time.sleep(1)
        setState(States.CHRONO)
        client.publish("k32/c1/leds/mem", "2", qos=1)
        print("k32/c1/leds/mem", "2")
        
    else:
        time.sleep(.1)