import paho.mqtt.client as mqtt
import json
import time
import requests
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
import os
from pydantic import parse_obj_as
from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Float

MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
DEVICE_ID = "upet-001"
api_link = "http://localhost:8000/api/v1/"
URL_DATABASE = os.getenv('URL_DATABASE', "mysql+pymysql://root:root@localhost:3306/edge")
engine = create_engine(URL_DATABASE)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



def get_db() :
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    Base.metadata.create_all(bind=engine)


TOPIC = "upet/devices/status"

collar = {
    "id":"upet-001",
    "online": False,
    "latitude": 0.0,
    "longitude": 0.0,
    "temperature": 0.0,
    "lpm": 0.0,
    "last_seen": None,
    "pet_id": 0
}

class SmartCollar(Base):
    __tablename__= 'smartcollars'
    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String(255), unique=True, nullable=False)
    temperature = Column(Float, nullable=True)
    lpm = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    pet_id = Column(Integer, nullable=True, default=None)

def saveCollar(collar1):
    with Session(engine) as session:
        col = session.query(SmartCollar).filter(SmartCollar.serial_number == collar1.serial_number).first()
        if not col:
            col = SmartCollar(
                serial_number=collar1.serial_number,
                temperature=collar1.temperature,
                lpm=collar1.lpm,
                latitude=collar1.latitude,
                longitude=collar1.longitude,
                pet_id=collar1.pet_id
            )
            session.add(col)
            session.commit()
            session.refresh(col)
        else:
            col.serial_number=collar1.serial_number
            col.temperature=collar1.temperature
            col.lpm=collar1.lpm
            col.latitude=collar1.latitude
            col.longitude=collar1.longitude
            col.pet_id=collar1.pet_id
        session.commit()
    


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
    try:
        topic = msg.topic
        data = json.loads(msg.payload.decode())
        p_id = data.get("id").split("-")[1]
        if topic == TOPIC:
            col = SmartCollar(
                serial_number=data.get("id","upet-001"),
                temperature=data.get("temperature",0.0),
                lpm=data.get("pulse",0.0),
                latitude=data.get("latitude", 0.0),
                longitude=data.get("longitude", 0.0),
                pet_id=int(p_id)
                )
        saveCollar(col)
        print("¡Collar actualizado!")
    except Exception as e:
        log(f"Error procesando mensaje: {e}", "ERROR")


def show_device_status(pid):
    global collar
    with Session(engine) as session:
        col = session.query(SmartCollar).filter(SmartCollar.pet_id==pid).first()
        if col:
            collar.update({
                        "online": True,
                        "latitude": col.latitude,
                        "longitude": col.longitude,
                        "temperature": col.temperature,
                        "lpm": col.lpm,
                        "last_seen": datetime.now(),
                        "pet_id":col.pet_id
                    })
        print("\n" + "="*50)
        print("ESTADO DEL COLLAR")
        print("="*50)
        print(f"Dispositivo: {collar.get('id', DEVICE_ID)}")
        print(f"Online: {'SÍ' if collar['online'] else 'NO'}")
        print(f"Temperatura: {collar.get('temperature', 0.0)}")
        print(f"Longitud: {collar.get('longitude', 0.0)}°")
        print(f"Latitud: {collar.get('latitude', 0.0)}°")
        print(f"Pulso: {collar.get('lpm', 0.0)}")
        
        if collar['last_seen']:
            print(f"Última vez visto: {collar['last_seen'].strftime('%H:%M:%S')}")
        print(f"Pet Id: {collar.get('pet_id', 0)}")
        print("="*50)

def interactive_menu():
    with Session(engine) as session:
        while True:
            print("\nBIENVENIDO A LA APP EDGE UPET:")
            print("1.Ver Estado")
            print("2.Subir")
            print("3.Salir")
            
            try:
                choice = input("\nSelecciona una opción (1-3): ").strip()
                if choice == "1":
                    pid = int(input("\nIndique el id en número entero del animal.").strip())
                    show_device_status(pid)
                elif choice =="2":
                    collars =session.query(SmartCollar).all()
                    if collars:
                        for x in collars:
                            try:
                                payload ={
                                    'temperature':x.temperature,
                                    'lpm':x.lpm,
                                    'battery':100.0,
                                    'location':{
                                        'latitude':x.latitude,
                                        'longitude':x.longitude
                                    }
                                }
                                headers = {"content-type": "application/json"}
                                print(payload)
                                requests.put(api_link+"smart-collars/"+str(x.pet_id),data=json.dumps(payload),headers=headers)
                                print("Collar subido al backend.")
                            except Exception as e:
                                log(f"Error fatal: {e}", "ERROR")
                                print("No existe la mascota.")
                                continue
                    else:
                        print("No hay.")

                elif choice == "3":
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
    create_all_tables()
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