import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
DEVICE_ID = "upet-001"

TOPIC = f"upet/devices/{DEVICE_ID}/status"

collar = {
    "online": False,
    "latitude": 0.0,
    "longitude": 0.0,
    "temperature": 0.0,
    "humidity": 0.0,
    "pulse": 0,
    "last_seen": None
}

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def on_connect(client, userdata, flags, rc):
    log("Conectando con el broker MQTT...")
    if rc == 0:
        log("Conectado al broker MQTT")
        
        client.subscribe(TOPIC)
        log(f"Suscrito a: {TOPIC}")
        
    else:
        log(f"Error conectando al MQTT: {rc}", "ERROR")

def on_message(client, userdata, msg):
    global collar
    
    try:
        topic = msg.topic
        data = json.loads(msg.payload.decode())
        if topic == TOPIC:
            collar.update({
                "online": True,
                "latitude": data.get("latitude", 0.0),
                "longitude": data.get("longitude", 0.0),
                "temperature": data.get("temperature", 0.0),
                "humidity": data.get("humidity", 0.0),
                "pulse": data.get("pulse", 0.0),
                "last_seen": datetime.now()
            })      
    except Exception as e:
        log(f"Error procesando mensaje: {e}", "ERROR")


def show_device_status():
    print("\n" + "="*50)
    print("ESTADO DEL COLLAR")
    print("="*50)
    print(f"Dispositivo: {collar.get('device_id', DEVICE_ID)}")
    print(f"Online: {'SÍ' if collar['online'] else 'NO'}")
    print(f"Temperatura: {collar.get('temperature', 0.0)} %")
    print(f"Humedad: {collar.get('humidity', 0.0)} %")
    print(f"Longitud: {collar.get('longitude', 0.0)}°")
    print(f"Latitud: {collar.get('latitude', 0.0)}°")
    print(f"Pulso: {collar.get('pulse', 0)}")
    
    if collar['last_seen']:
        print(f"Última vez visto: {collar['last_seen'].strftime('%H:%M:%S')}")
    
    print("="*50)

def interactive_menu():
    while True:
        print("\nBIENVENIDO A LA APP EDGE UPET:")
        print("1.Ver Estado")
        print("2.Salir")
        
        try:
            choice = input("\nSelecciona una opción (1-2): ").strip()
            if choice == "1":
                show_device_status()

            elif choice == "2":
                log("Cerrando aplicación...")
                break
            else:
                print("Opción inválida")
                
        except KeyboardInterrupt:
            log("\nCerrando aplicación...")
            break
        except Exception as e:
            log(f"Error: {e}", "ERROR")

def main():
    global client
    
    log("Iniciando la aplicación Edge de UPet")
    log(f"Conectando a MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    
    # Configurar cliente MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        log("Espere unos segundos...")
        time.sleep(5)
        interactive_menu()
        
    except Exception as e:
        log(f"Error fatal: {e}", "ERROR")
        
    finally:
        client.loop_stop()
        client.disconnect()
        log("Aplicación cerrada")

if __name__ == "__main__":
    main()