"""Catálogo base de una empresa de seguridad electrónica: los artículos que se usan a diario en cámaras, alarmas,
cerco eléctrico, domótica, control de acceso, redes, incendio, material eléctrico y ferretería, con su categoría,
unidad y palabras para que la IA los encuentre. SIN precios: cada empresa pone los suyos (entran marcados «sin
precio» para que se note cuáles faltan).

Se usa de dos formas: como plantillas descargables por tipo (Catálogo → Importar) y para cargar todo de una vez
(«Cargar catálogo base»), que solo CREA lo que falta: un artículo que ya existe con ese nombre no se toca.
"""

import re
import unicodedata
from typing import Any

from sqlalchemy.orm import Session

from app.models.category import Category

# (nombre, unidad, etiquetas, sinónimos). La categoría va en el grupo.
Item = tuple[str, str, str, str]

# Primer nivel nuevo -> prefijo del código de sus productos (ALM-000001…). Los que ya existen en la taxonomía de
# fábrica (CCTV, Redes, Control de Acceso…) conservan el suyo.
NEW_ROOTS = {
    "Alarmas": "ALM",
    "Cerco Eléctrico": "CER",
    "Domótica": "DOM",
    "Detección de Incendio": "INC",
    "Material Eléctrico": "ELE",
    "Ferretería": "FER",
    "Servicios": "SRV",
}

KITS: dict[str, tuple[str, str, dict[str, list[Item]]]] = {
    "cctv": (
        "Cámaras (CCTV)",
        "plantilla_camaras_cctv",
        {
            "CCTV > Cámaras Domo": [
                ("Cámara IP domo 2 MP", "unidad", "camara;ip;domo;2mp", "camara domo;camara de techo"),
                ("Cámara IP domo 4 MP", "unidad", "camara;ip;domo;4mp", "camara domo"),
                ("Cámara IP domo 8 MP (4K)", "unidad", "camara;ip;domo;8mp;4k", ""),
                ("Cámara analógica domo 2 MP (1080p)", "unidad", "camara;analogica;domo;turbo hd", "camara hd"),
                ("Cámara analógica domo 5 MP", "unidad", "camara;analogica;domo;5mp", ""),
            ],
            "CCTV > Cámaras Bullet": [
                ("Cámara IP bala 2 MP", "unidad", "camara;ip;bullet;2mp", "camara bala;camara exterior"),
                ("Cámara IP bala 4 MP", "unidad", "camara;ip;bullet;4mp", "camara bala"),
                ("Cámara IP bala 4 MP a color nocturno", "unidad", "camara;ip;bullet;colorvu;full color", "camara a color de noche"),
                ("Cámara IP bala 8 MP (4K)", "unidad", "camara;ip;bullet;8mp;4k", ""),
                ("Cámara analógica bala 2 MP (1080p)", "unidad", "camara;analogica;bullet", "camara bala hd"),
                ("Cámara analógica bala 5 MP", "unidad", "camara;analogica;bullet;5mp", ""),
            ],
            "CCTV > Cámaras PTZ": [
                ("Cámara PTZ IP 4 MP zoom 25x", "unidad", "camara;ptz;zoom;ip", "camara robotica;speed dome"),
                ("Cámara mini PTZ IP 4 MP", "unidad", "camara;ptz;mini", ""),
            ],
            "CCTV > Cámaras IP": [
                ("Cámara IP Wi-Fi interior 2 MP", "unidad", "camara;wifi;interior", "camara inalambrica"),
                ("Cámara IP Wi-Fi exterior 4 MP", "unidad", "camara;wifi;exterior", "camara inalambrica"),
                ("Cámara IP ojo de pez 360° 6 MP", "unidad", "camara;fisheye;360", "camara panoramica"),
                ("Cámara IP con audio bidireccional 4 MP", "unidad", "camara;ip;audio", ""),
            ],
            "CCTV > NVR": [
                ("NVR 4 canales PoE", "unidad", "nvr;grabador;poe;4 canales", "grabador ip"),
                ("NVR 8 canales PoE", "unidad", "nvr;grabador;poe;8 canales", "grabador ip"),
                ("NVR 16 canales PoE", "unidad", "nvr;grabador;poe;16 canales", "grabador ip"),
                ("NVR 32 canales", "unidad", "nvr;grabador;32 canales", ""),
            ],
            "CCTV > DVR": [
                ("DVR 4 canales 1080p", "unidad", "dvr;grabador;4 canales", "grabador analogico"),
                ("DVR 8 canales 1080p", "unidad", "dvr;grabador;8 canales", "grabador analogico"),
                ("DVR 16 canales 1080p", "unidad", "dvr;grabador;16 canales", "grabador analogico"),
                ("DVR 8 canales 5 MP", "unidad", "dvr;grabador;5mp", ""),
            ],
            "CCTV > Discos Duros": [
                ("Disco duro de videovigilancia 1 TB", "unidad", "disco;hdd;almacenamiento;1tb", "disco purple;disco skyhawk"),
                ("Disco duro de videovigilancia 2 TB", "unidad", "disco;hdd;almacenamiento;2tb", "disco purple"),
                ("Disco duro de videovigilancia 4 TB", "unidad", "disco;hdd;almacenamiento;4tb", "disco purple"),
                ("Disco duro de videovigilancia 6 TB", "unidad", "disco;hdd;almacenamiento;6tb", ""),
                ("Memoria microSD 128 GB para cámara", "unidad", "memoria;microsd;sd", "tarjeta de memoria"),
            ],
            "CCTV > Monitores": [
                ("Monitor 22\" para CCTV", "unidad", "monitor;pantalla", ""),
                ("Monitor 32\" para CCTV", "unidad", "monitor;pantalla;tv", "televisor"),
            ],
            "CCTV > Fuentes de Alimentación": [
                ("Fuente 12 V 1 A para cámara", "unidad", "fuente;adaptador;12v", "eliminador;transformador"),
                ("Fuente 12 V 2 A para cámara", "unidad", "fuente;adaptador;12v", "eliminador"),
                ("Fuente centralizada 12 V 10 A 9 salidas (gabinete)", "unidad", "fuente;centralizada;12v", "fuente de caja"),
                ("Fuente centralizada 12 V 20 A 18 salidas", "unidad", "fuente;centralizada;12v", ""),
            ],
            "CCTV > Accesorios": [
                ("Caja de conexiones para cámara (junction box)", "unidad", "caja;base;camara", "base de camara"),
                ("Brazo de pared para cámara", "unidad", "brazo;soporte;camara", "soporte de pared"),
                ("Soporte de poste para cámara", "unidad", "soporte;poste;camara", ""),
                ("Video balun pasivo (par)", "par", "balun;utp;analogica", "transceptor"),
                ("Protector de sobretensión para cámara", "unidad", "protector;surge;camara", ""),
                ("Micrófono para cámara", "unidad", "microfono;audio;camara", ""),
            ],
        },
    ),
    "alarma": (
        "Alarmas",
        "plantilla_materiales_alarma",
        {
            "Alarmas > Paneles": [
                ("Panel de alarma 8 zonas", "unidad", "alarma;panel", "central de alarma"),
                ("Panel de alarma 16 zonas", "unidad", "alarma;panel", "central de alarma"),
                ("Panel de alarma inalámbrico con Wi-Fi / GSM", "unidad", "alarma;panel;inalambrico;wifi", "alarma inalambrica"),
            ],
            "Alarmas > Teclados": [
                ("Teclado LCD para panel de alarma", "unidad", "alarma;teclado", ""),
                ("Teclado LED para panel de alarma", "unidad", "alarma;teclado", ""),
                ("Teclado inalámbrico para alarma", "unidad", "alarma;teclado;inalambrico", ""),
            ],
            "Alarmas > Sensores": [
                ("Sensor de movimiento PIR", "unidad", "alarma;sensor;pir", "detector de movimiento"),
                ("Sensor de movimiento PIR inmune a mascotas", "unidad", "alarma;sensor;pir;mascotas", ""),
                ("Sensor de movimiento PIR inalámbrico", "unidad", "alarma;sensor;pir;inalambrico", ""),
                ("Sensor de movimiento exterior doble tecnología", "unidad", "alarma;sensor;exterior;dual", ""),
                ("Contacto magnético para puerta", "unidad", "alarma;contacto magnetico", "magnetico de puerta"),
                ("Contacto magnético inalámbrico", "unidad", "alarma;contacto magnetico;inalambrico", ""),
                ("Contacto magnético de alto tráfico (portón)", "unidad", "alarma;contacto magnetico;porton", ""),
                ("Detector de rotura de vidrio", "unidad", "alarma;vidrio", ""),
                ("Barrera infrarroja exterior (par)", "par", "alarma;barrera;infrarroja;perimetral", "fotocelda de alarma"),
                ("Detector de inundación", "unidad", "alarma;agua;inundacion", ""),
            ],
            "Alarmas > Sirenas": [
                ("Sirena exterior con estrobo", "unidad", "alarma;sirena;exterior", ""),
                ("Sirena interior 30 W", "unidad", "alarma;sirena;interior", ""),
                ("Sirena inalámbrica", "unidad", "alarma;sirena;inalambrica", ""),
                ("Corneta 15 W", "unidad", "alarma;corneta;bocina", "bocina"),
            ],
            "Alarmas > Comunicadores": [
                ("Comunicador GSM / 4G para alarma", "unidad", "alarma;comunicador;gsm", ""),
                ("Módulo de comunicación IP para alarma", "unidad", "alarma;comunicador;ip", ""),
                ("Módulo expansor de 8 zonas", "unidad", "alarma;expansor;zonas", ""),
                ("Receptor inalámbrico para panel", "unidad", "alarma;receptor;inalambrico", ""),
            ],
            "Alarmas > Baterías": [
                ("Batería 12 V 4 Ah", "unidad", "bateria;12v", "bateria de respaldo"),
                ("Batería 12 V 7 Ah", "unidad", "bateria;12v", "bateria de respaldo"),
                ("Batería 12 V 18 Ah", "unidad", "bateria;12v", ""),
            ],
            "Alarmas > Accesorios": [
                ("Botón de pánico", "unidad", "alarma;panico", ""),
                ("Botón de pánico inalámbrico (colgante)", "unidad", "alarma;panico;inalambrico", ""),
                ("Control remoto (llavero) para alarma", "unidad", "alarma;control remoto", ""),
                ("Transformador 16.5 V para panel", "unidad", "alarma;transformador", ""),
                ("Gabinete metálico para panel", "unidad", "alarma;gabinete", ""),
                ("Resistencia de fin de línea (bolsa 100)", "bolsa", "alarma;resistencia;eol", ""),
            ],
            "Alarmas > Cableado": [
                ("Cable de alarma 4 hilos 22 AWG (rollo 305 m)", "rollo", "alarma;cable;4 hilos", "cable de alarma"),
                ("Cable de alarma 2 hilos 22 AWG (rollo 305 m)", "rollo", "alarma;cable;2 hilos", ""),
                ("Cable de alarma 4 hilos 22 AWG (metro)", "metro", "alarma;cable;4 hilos", ""),
            ],
        },
    ),
    "cerco": (
        "Cerco eléctrico",
        "plantilla_cerco_electrico",
        {
            "Cerco Eléctrico > Energizadores": [
                ("Energizador de cerco eléctrico 5000 m", "unidad", "cerco;energizador;electrificador", "pulsador;impulsor de cerco"),
                ("Energizador de cerco eléctrico 10000 m", "unidad", "cerco;energizador;electrificador", "pulsador"),
                ("Energizador de cerco con Wi-Fi / app", "unidad", "cerco;energizador;wifi", ""),
                ("Teclado para energizador de cerco", "unidad", "cerco;teclado", ""),
            ],
            "Cerco Eléctrico > Alambre y cable": [
                ("Alambre de acero inoxidable para cerco (rollo 1000 m)", "rollo", "cerco;alambre;inoxidable", "alambre de cerco"),
                ("Alambre de aluminio para cerco (rollo)", "rollo", "cerco;alambre;aluminio", ""),
                ("Cable de alta tensión para cerco (metro)", "metro", "cerco;cable;alta tension", "cable bujia"),
                ("Cable de alta tensión para cerco (rollo 50 m)", "rollo", "cerco;cable;alta tension", ""),
            ],
            "Cerco Eléctrico > Postes y soportes": [
                ("Poste para cerco eléctrico 4 líneas", "unidad", "cerco;poste;4 lineas", "barra de cerco"),
                ("Poste para cerco eléctrico 6 líneas", "unidad", "cerco;poste;6 lineas", "barra de cerco"),
                ("Poste esquinero para cerco", "unidad", "cerco;poste;esquina", ""),
                ("Soporte en L para muro", "unidad", "cerco;soporte;muro", ""),
            ],
            "Cerco Eléctrico > Aisladores": [
                ("Aislador de paso para cerco", "unidad", "cerco;aislador", ""),
                ("Aislador de esquina (tensor) para cerco", "unidad", "cerco;aislador;esquina", ""),
                ("Aislador tipo carrete", "unidad", "cerco;aislador", ""),
            ],
            "Cerco Eléctrico > Accesorios": [
                ("Tensor para alambre de cerco", "unidad", "cerco;tensor", ""),
                ("Kit de aterrizaje (varilla de tierra 6 pies + conector)", "unidad", "cerco;tierra;varilla", "varilla de cobre;puesta a tierra"),
                ("Pararrayos para cerco eléctrico", "unidad", "cerco;pararrayos", ""),
                ("Placa de advertencia «Cerco eléctrico»", "unidad", "cerco;letrero;advertencia", "letrero de peligro"),
                ("Interruptor de corte para cerco", "unidad", "cerco;interruptor", ""),
                ("Sirena para cerco eléctrico", "unidad", "cerco;sirena", ""),
                ("Batería 12 V 7 Ah para energizador", "unidad", "cerco;bateria;12v", ""),
            ],
        },
    ),
    "domotica": (
        "Domótica",
        "plantilla_domotica",
        {
            "Domótica > Controladores": [
                ("Hub / controlador domótico Zigbee", "unidad", "domotica;hub;zigbee", "puente inteligente"),
                ("Control remoto infrarrojo inteligente (aires y TV)", "unidad", "domotica;infrarrojo;wifi", "control universal"),
                ("Asistente de voz / pantalla inteligente", "unidad", "domotica;asistente;voz", "alexa;google home"),
            ],
            "Domótica > Interruptores y enchufes": [
                ("Interruptor inteligente Wi-Fi 1 vía", "unidad", "domotica;interruptor;wifi", "suiche inteligente"),
                ("Interruptor inteligente Wi-Fi 2 vías", "unidad", "domotica;interruptor;wifi", "suiche inteligente"),
                ("Interruptor inteligente Wi-Fi 3 vías", "unidad", "domotica;interruptor;wifi", ""),
                ("Módulo relé inteligente para interruptor existente", "unidad", "domotica;rele;modulo", ""),
                ("Enchufe inteligente Wi-Fi", "unidad", "domotica;enchufe;wifi", "tomacorriente inteligente"),
                ("Dimmer inteligente Wi-Fi", "unidad", "domotica;dimmer;wifi", ""),
                ("Interruptor inteligente para cortinas", "unidad", "domotica;cortinas;interruptor", ""),
            ],
            "Domótica > Iluminación": [
                ("Bombillo LED inteligente RGB", "unidad", "domotica;bombillo;led;rgb", "foco inteligente"),
                ("Tira LED inteligente 5 m", "unidad", "domotica;tira led", ""),
            ],
            "Domótica > Sensores": [
                ("Sensor de puerta inteligente Zigbee", "unidad", "domotica;sensor;puerta", ""),
                ("Sensor de movimiento inteligente Zigbee", "unidad", "domotica;sensor;movimiento", ""),
                ("Sensor de temperatura y humedad", "unidad", "domotica;sensor;temperatura", ""),
                ("Detector de humo inteligente Wi-Fi", "unidad", "domotica;humo;wifi", ""),
            ],
            "Domótica > Cerraduras y portones": [
                ("Cerradura inteligente con huella y clave", "unidad", "domotica;cerradura;huella", "cerradura digital"),
                ("Módulo Wi-Fi para motor de portón", "unidad", "domotica;porton;wifi", "abre porton por app"),
                ("Motor para cortina inteligente", "unidad", "domotica;cortina;motor", ""),
            ],
        },
    ),
    "acceso": (
        "Control de acceso y videoporteros",
        "plantilla_control_acceso",
        {
            "Control de Acceso > Lectores Biométricos": [
                ("Control de acceso biométrico huella y tarjeta", "unidad", "acceso;biometrico;huella", "ponchador"),
                ("Control de acceso con reconocimiento facial", "unidad", "acceso;facial", "lector facial"),
                ("Reloj de asistencia biométrico", "unidad", "asistencia;biometrico", "reloj ponchador"),
            ],
            "Control de Acceso > Lectores RFID": [
                ("Lector de proximidad RFID 125 kHz", "unidad", "acceso;rfid;lector", ""),
                ("Teclado de acceso con tarjeta y clave", "unidad", "acceso;teclado;rfid", ""),
            ],
            "Control de Acceso > Tarjetas": [
                ("Tarjeta de proximidad RFID", "unidad", "acceso;tarjeta;rfid", ""),
                ("Llavero de proximidad RFID", "unidad", "acceso;llavero;tag", "tag"),
            ],
            "Control de Acceso > Cerraduras Magnéticas": [
                ("Cerradura electromagnética 600 lb", "unidad", "acceso;cerradura;magnetica", "electroiman"),
                ("Cerradura electromagnética 1200 lb", "unidad", "acceso;cerradura;magnetica", "electroiman"),
                ("Soporte L y Z para cerradura magnética", "unidad", "acceso;soporte;cerradura", ""),
            ],
            "Control de Acceso > Cerraduras Eléctricas": [
                ("Contrachapa eléctrica", "unidad", "acceso;contrachapa;cerradura", "chapa electrica"),
                ("Cerradura eléctrica de sobreponer", "unidad", "acceso;cerradura;electrica", ""),
            ],
            "Control de Acceso > Botones de Salida": [
                ("Botón de salida", "unidad", "acceso;boton;salida", "push de salida"),
                ("Botón de salida sin contacto (infrarrojo)", "unidad", "acceso;boton;sin contacto", ""),
                ("Botón de emergencia (rompa el vidrio)", "unidad", "acceso;emergencia", ""),
            ],
            "Control de Acceso > Fuentes": [
                ("Fuente 12 V 5 A para control de acceso con respaldo", "unidad", "acceso;fuente;12v", ""),
            ],
            "Control de Acceso > Controladoras": [
                ("Controladora de acceso 1 puerta", "unidad", "acceso;controladora", ""),
                ("Controladora de acceso 2 puertas", "unidad", "acceso;controladora", ""),
                ("Controladora de acceso 4 puertas", "unidad", "acceso;controladora", ""),
                ("Cierrapuertas hidráulico", "unidad", "acceso;cierrapuertas", "brazo hidraulico"),
            ],
            "Videoporteros > Monitores": [
                ("Monitor de videoportero 7\"", "unidad", "videoportero;monitor", "intercom"),
                ("Monitor de videoportero IP / Wi-Fi 7\"", "unidad", "videoportero;monitor;wifi", ""),
            ],
            "Videoporteros > Estaciones Exteriores": [
                ("Frente de calle de videoportero 1 botón", "unidad", "videoportero;exterior;timbre", "timbre con camara"),
                ("Frente de calle de videoportero multiapartamento", "unidad", "videoportero;exterior;edificio", ""),
                ("Timbre con cámara Wi-Fi", "unidad", "videoportero;timbre;wifi", "doorbell"),
            ],
            "Videoporteros > Accesorios": [
                ("Kit de videoportero (monitor + frente de calle)", "kit", "videoportero;kit", ""),
                ("Intercomunicador de audio (portero eléctrico)", "unidad", "intercom;audio;portero", "citofono"),
            ],
        },
    ),
    "redes": (
        "Redes, cableado y canalización",
        "plantilla_redes_cableado",
        {
            "Redes > Switch PoE": [
                ("Switch PoE 4 puertos + 2 uplink", "unidad", "switch;poe;4 puertos", ""),
                ("Switch PoE 8 puertos + 2 uplink", "unidad", "switch;poe;8 puertos", ""),
                ("Switch PoE 16 puertos", "unidad", "switch;poe;16 puertos", ""),
                ("Switch PoE 24 puertos", "unidad", "switch;poe;24 puertos", ""),
            ],
            "Redes > Switch Administrable": [
                ("Switch Gigabit 8 puertos (no PoE)", "unidad", "switch;gigabit", ""),
                ("Switch administrable 24 puertos Gigabit", "unidad", "switch;administrable", ""),
            ],
            "Redes > Router": [("Router Wi-Fi doble banda", "unidad", "router;wifi", "enrutador")],
            "Redes > Access Point": [
                ("Access point Wi-Fi de techo", "unidad", "access point;wifi;ap", "antena wifi"),
                ("Antena punto a punto 5 GHz (par)", "par", "enlace;punto a punto;antena", "radioenlace"),
            ],
            "Redes > Inyectores PoE": [("Inyector PoE", "unidad", "poe;inyector", ""), ("Extensor PoE", "unidad", "poe;extensor", "")],
            "Redes > Rack": [
                ("Gabinete de pared 6U", "unidad", "rack;gabinete;6u", "rack de pared"),
                ("Gabinete de pared 9U", "unidad", "rack;gabinete;9u", "rack de pared"),
                ("Bandeja para rack", "unidad", "rack;bandeja", ""),
                ("Regleta de energía para rack", "unidad", "rack;regleta;pdu", "multitoma"),
            ],
            "Redes > Patch Panel": [("Patch panel 24 puertos Cat6", "unidad", "patch panel;cat6", "")],
            "Redes > Organizadores": [("Organizador horizontal de cables", "unidad", "organizador;rack", "")],
            "Redes > UPS": [
                ("UPS 1000 VA", "unidad", "ups;respaldo", "no break"),
                ("UPS 1500 VA", "unidad", "ups;respaldo", "no break"),
                ("Regulador de voltaje", "unidad", "regulador;voltaje", "estabilizador"),
            ],
            "Cableado > UTP Categoría 5e": [("Cable UTP Cat5e (caja 305 m)", "caja", "cable;utp;cat5e", "cable de red"), ("Cable UTP Cat5e exterior (caja 305 m)", "caja", "cable;utp;cat5e;exterior", "")],
            "Cableado > UTP Categoría 6": [("Cable UTP Cat6 (caja 305 m)", "caja", "cable;utp;cat6", "cable de red"), ("Cable UTP Cat6 exterior (caja 305 m)", "caja", "cable;utp;cat6;exterior", ""), ("Cable UTP Cat6 (metro)", "metro", "cable;utp;cat6", "")],
            "Cableado > Cable Siamés": [("Cable siamés RG59 + energía (rollo 305 m)", "rollo", "cable;siames;rg59", "cable coaxial con energia")],
            "Cableado > Cable Coaxial RG6": [("Cable coaxial RG6 (rollo 305 m)", "rollo", "cable;coaxial;rg6", "")],
            "Cableado > Cable para Alimentación": [("Cable dúplex 18 AWG (rollo 100 m)", "rollo", "cable;duplex;energia", "cable de corriente")],
            "Cableado > Patch Cord": [("Patch cord Cat6 1 m", "unidad", "patch cord;cat6", "cable de parcheo"), ("Patch cord Cat6 3 m", "unidad", "patch cord;cat6", "")],
            "Cableado > Cable HDMI": [("Cable HDMI 1.8 m", "unidad", "hdmi;cable", ""), ("Cable HDMI 10 m", "unidad", "hdmi;cable", "")],
            "Conectores > RJ45 Cat5e": [("Conector RJ45 Cat5e (bolsa 100)", "bolsa", "rj45;conector;cat5e", "pin de red")],
            "Conectores > RJ45 Cat6": [("Conector RJ45 Cat6 (bolsa 100)", "bolsa", "rj45;conector;cat6", "pin de red"), ("Bota para RJ45 (bolsa 100)", "bolsa", "bota;rj45", "capuchon")],
            "Conectores > Keystone RJ45": [("Jack keystone Cat6", "unidad", "keystone;jack;cat6", ""), ("Face plate 1 puerto", "unidad", "faceplate;tapa", "tapa de red"), ("Face plate 2 puertos", "unidad", "faceplate;tapa", "")],
            "Conectores > BNC": [("Conector BNC de presión", "unidad", "bnc;conector", ""), ("Conector BNC de rosca", "unidad", "bnc;conector", "")],
            "Conectores > Conector DC": [("Conector DC macho con bornera", "unidad", "conector;dc;plug", "plug de energia"), ("Conector DC hembra con bornera", "unidad", "conector;dc;jack", ""), ("Pulpo de energía 1 a 4", "unidad", "pulpo;splitter;dc", "divisor de corriente")],
            "Canalizaciones > Tubería EMT": [("Tubo EMT 1/2\" (10 pies)", "unidad", "tubo;emt;1/2", "tuberia metalica"), ("Tubo EMT 3/4\" (10 pies)", "unidad", "tubo;emt;3/4", "tuberia metalica")],
            "Canalizaciones > PVC Eléctrico": [("Tubo PVC eléctrico 1/2\" (10 pies)", "unidad", "tubo;pvc;1/2", ""), ("Tubo PVC eléctrico 3/4\" (10 pies)", "unidad", "tubo;pvc;3/4", ""), ("Codo PVC 3/4\"", "unidad", "codo;pvc", "")],
            "Canalizaciones > Tubería Flexible": [("Tubo flexible (BX) 1/2\" (metro)", "metro", "tubo;flexible", "coraza"), ("Manguera corrugada 3/4\" (rollo 50 m)", "rollo", "manguera;corrugada", "tubo corrugado")],
            "Canalizaciones > Canaleta Plástica": [("Canaleta plástica 20 x 10 mm (2 m)", "unidad", "canaleta;plastica", "moldura"), ("Canaleta plástica 40 x 25 mm (2 m)", "unidad", "canaleta;plastica", "moldura"), ("Canaleta de piso", "unidad", "canaleta;piso", "")],
            "Canalizaciones > Cajas de Paso": [("Caja de paso plástica exterior 10 x 10 cm", "unidad", "caja;paso;exterior", "caja de registro"), ("Caja de paso plástica exterior 15 x 15 cm", "unidad", "caja;paso;exterior", "")],
            "Fibra Óptica > Splitters": [("Splitter óptico 1x8", "unidad", "fibra;splitter", "")],
            "Fibra Óptica > Pigtails": [("Pigtail SC/APC", "unidad", "fibra;pigtail", "")],
            "Cableado > Cable de Fibra Óptica Monomodo": [("Cable de fibra óptica drop 1 hilo (metro)", "metro", "fibra;drop;monomodo", "fibra")],
            "Fibra Óptica > ODF": [("Caja de terminación óptica (ODF) 12 puertos", "unidad", "fibra;odf", "")],
            "Fibra Óptica > Patch Cord": [("Patch cord de fibra SC/APC 3 m", "unidad", "fibra;patch cord", "jumper de fibra")],
            "Fibra Óptica > Conversores": [("Media converter (conversor de fibra a red)", "unidad", "fibra;media converter", "conversor")],
        },
    ),
    "incendio": (
        "Detección de incendio",
        "plantilla_deteccion_incendio",
        {
            "Detección de Incendio > Paneles": [("Panel de detección de incendio 4 zonas", "unidad", "incendio;panel", "central de incendio"), ("Panel de detección de incendio 8 zonas", "unidad", "incendio;panel", "")],
            "Detección de Incendio > Detectores": [
                ("Detector de humo fotoeléctrico convencional", "unidad", "incendio;humo;detector", "detector de humo"),
                ("Detector de temperatura (térmico)", "unidad", "incendio;temperatura;detector", ""),
                ("Detector de humo autónomo con batería", "unidad", "incendio;humo;autonomo", ""),
                ("Detector de monóxido de carbono", "unidad", "incendio;co;monoxido", ""),
                ("Detector de gas", "unidad", "incendio;gas", ""),
            ],
            "Detección de Incendio > Notificación": [("Estación manual de incendio (pull station)", "unidad", "incendio;estacion manual", "palanca de incendio"), ("Sirena con luz estroboscópica para incendio", "unidad", "incendio;sirena;estrobo", "luz estrobo")],
            "Detección de Incendio > Cableado": [("Cable de incendio 2 x 18 AWG (rollo 305 m)", "rollo", "incendio;cable;fplr", "cable rojo")],
            "Detección de Incendio > Extintores": [("Extintor ABC 10 lb", "unidad", "extintor;abc", ""), ("Extintor CO2 10 lb", "unidad", "extintor;co2", ""), ("Señal de salida de emergencia", "unidad", "senal;salida;emergencia", "letrero de salida"), ("Lámpara de emergencia", "unidad", "lampara;emergencia", "")],
        },
    ),
    "electrico": (
        "Material eléctrico",
        "plantilla_material_electrico",
        {
            "Material Eléctrico > Cables": [
                ("Cable THHN #12 (rollo 100 m)", "rollo", "cable;thhn;12", "alambre electrico"),
                ("Cable THHN #14 (rollo 100 m)", "rollo", "cable;thhn;14", "alambre electrico"),
                ("Cable THHN #12 (metro)", "metro", "cable;thhn;12", ""),
                ("Cable dúplex 2 x 14 AWG (metro)", "metro", "cable;duplex;14", "cordon"),
                ("Cable de tierra desnudo #10 (metro)", "metro", "cable;tierra;cobre", ""),
            ],
            "Material Eléctrico > Breakers y protección": [
                ("Breaker 1 polo 15 A", "unidad", "breaker;15a", "disyuntor;cuchilla"),
                ("Breaker 1 polo 20 A", "unidad", "breaker;20a", "disyuntor"),
                ("Breaker 2 polos 30 A", "unidad", "breaker;30a", ""),
                ("Panel de breakers 4 circuitos", "unidad", "panel;breaker;caja", "caja de breakers"),
                ("Protector de voltaje para equipos", "unidad", "protector;voltaje", "supresor de picos"),
                ("Varilla de tierra de cobre 6 pies", "unidad", "tierra;varilla;cobre", "barra de tierra"),
            ],
            "Material Eléctrico > Tomacorrientes e interruptores": [
                ("Tomacorriente doble", "unidad", "tomacorriente;enchufe", "toma"),
                ("Tomacorriente doble exterior con tapa", "unidad", "tomacorriente;exterior", ""),
                ("Interruptor sencillo", "unidad", "interruptor;suiche", "suiche"),
                ("Extensión eléctrica (multitoma) 6 salidas", "unidad", "extension;multitoma;regleta", "regleta"),
            ],
            "Material Eléctrico > Iluminación": [("Reflector LED 50 W", "unidad", "reflector;led;exterior", "foco led"), ("Reflector LED con sensor de movimiento", "unidad", "reflector;led;sensor", "")],
            "Material Eléctrico > Energía de respaldo": [("Inversor de corriente 1000 W", "unidad", "inversor;respaldo", ""), ("Batería de ciclo profundo 12 V 100 Ah", "unidad", "bateria;ciclo profundo", ""), ("Panel solar 100 W", "unidad", "solar;panel", "placa solar"), ("Controlador de carga solar 20 A", "unidad", "solar;controlador", "")],
        },
    ),
    "ferreteria": (
        "Ferretería",
        "plantilla_materiales_ferreteria",
        {
            "Ferretería > Tornillería": [
                ("Tornillo autorroscante 8 x 1\" (caja 100)", "caja", "tornillo;ferreteria", ""),
                ("Tornillo para concreto 1/4 x 1-1/4\"", "unidad", "tornillo;concreto;ferreteria", "tapcon"),
                ("Tornillo para madera 8 x 1-1/2\" (caja 100)", "caja", "tornillo;madera", ""),
                ("Tornillo de seguridad antivandálico (bolsa 50)", "bolsa", "tornillo;seguridad", ""),
            ],
            "Ferretería > Anclajes": [
                ("Taco plástico (fisher) 1/4\" (bolsa 100)", "bolsa", "taco;anclaje;ferreteria", "tarugo;fisher"),
                ("Taco plástico (fisher) 5/16\" (bolsa 100)", "bolsa", "taco;anclaje", "tarugo;fisher"),
                ("Ancla de expansión 3/8\"", "unidad", "ancla;anclaje;ferreteria", ""),
                ("Taco para tablayeso (mariposa)", "unidad", "taco;drywall;mariposa", "anclaje de sheetrock"),
            ],
            "Ferretería > Abrazaderas y grapas": [
                ("Abrazadera EMT 1/2\"", "unidad", "abrazadera;emt", "grapa"),
                ("Abrazadera EMT 3/4\"", "unidad", "abrazadera;emt;ferreteria", "grapa"),
                ("Grapa para cable con clavo (bolsa 100)", "bolsa", "grapa;cable;ferreteria", ""),
                ("Grapa para cable UTP (bolsa 100)", "bolsa", "grapa;utp", ""),
            ],
            "Ferretería > Amarres y cintas": [
                ("Amarre plástico 8\" (bolsa 100)", "bolsa", "amarre;tie wrap;ferreteria", "tie wrap;cincho"),
                ("Amarre plástico 12\" negro UV (bolsa 100)", "bolsa", "amarre;tie wrap;exterior", "tie wrap"),
                ("Cinta aislante negra", "unidad", "cinta;aislante;ferreteria", "tape"),
                ("Cinta doble cara", "unidad", "cinta;doble cara;ferreteria", ""),
                ("Cinta autofundente", "unidad", "cinta;autofundente", ""),
                ("Termoencogible surtido (kit)", "kit", "termoencogible;aislante", "termo"),
            ],
            "Ferretería > Selladores": [("Silicón transparente (tubo)", "unidad", "silicon;sellador;ferreteria", "silicona"), ("Espuma expansiva", "unidad", "espuma;sellador", "")],
            "Ferretería > Brocas": [
                ("Broca para concreto 1/4\"", "unidad", "broca;concreto;ferreteria", "mecha"),
                ("Broca para concreto 5/16\"", "unidad", "broca;concreto", "mecha"),
                ("Broca para concreto larga 1/2\" x 12\"", "unidad", "broca;concreto;larga", "mecha larga"),
                ("Broca para metal 1/8\"", "unidad", "broca;metal;ferreteria", "mecha"),
                ("Sierra de copa 3/4\"", "unidad", "sierra de copa;broca", ""),
            ],
            "Ferretería > Cajas y tapas": [
                ("Caja eléctrica rectangular 2 x 4", "unidad", "caja;electrica;ferreteria", "caja 2x4"),
                ("Caja octagonal", "unidad", "caja;octagonal", ""),
                ("Caja de registro exterior IP65", "unidad", "caja;registro;exterior;ferreteria", ""),
                ("Tapa ciega 2 x 4", "unidad", "tapa;ferreteria", ""),
            ],
            "Ferretería > Conectores y uniones": [
                ("Conector EMT 1/2\"", "unidad", "conector;emt", ""),
                ("Conector EMT 3/4\"", "unidad", "conector;emt;ferreteria", ""),
                ("Unión EMT 3/4\"", "unidad", "union;emt;ferreteria", ""),
                ("Conector de presión (wire nut) (bolsa 100)", "bolsa", "conector;wire nut", "capuchon electrico"),
                ("Conector de gel para empalmes (bolsa 100)", "bolsa", "conector;gel;empalme", "conector 3m"),
                ("Terminal de ojo (bolsa 100)", "bolsa", "terminal;ojo", ""),
            ],
            "Ferretería > Herramientas y consumibles": [
                ("Disco de corte para metal 4-1/2\"", "unidad", "disco;corte;ferreteria", ""),
                ("Guía pasacables (metro)", "metro", "guia;pasacables", "cinta pescadora;sonda"),
                ("Lubricante para halar cable", "unidad", "lubricante;cable", ""),
                ("Pintura en aerosol", "unidad", "pintura;spray", "spray"),
                ("Escalera de tijera 6 pies (alquiler)", "servicio", "escalera;alquiler", ""),
            ],
        },
    ),
    "servicios": (
        "Servicios / mano de obra",
        "plantilla_servicios",
        {
            "Servicios > Instalación": [
                ("Instalación de cámara (por punto)", "servicio", "servicio;instalacion;camara", "mano de obra camara"),
                ("Instalación y configuración de DVR / NVR", "servicio", "servicio;instalacion;nvr;dvr", ""),
                ("Instalación de sensor de alarma (por punto)", "servicio", "servicio;instalacion;alarma", ""),
                ("Instalación y programación de panel de alarma", "servicio", "servicio;instalacion;alarma;panel", ""),
                ("Instalación de cerco eléctrico (metro lineal)", "metro", "servicio;instalacion;cerco", "mano de obra cerco"),
                ("Instalación de control de acceso (por puerta)", "servicio", "servicio;instalacion;acceso", ""),
                ("Instalación de videoportero", "servicio", "servicio;instalacion;videoportero", ""),
                ("Instalación de dispositivo domótico (por punto)", "servicio", "servicio;instalacion;domotica", ""),
                ("Punto de red (cableado y certificación)", "servicio", "servicio;punto de red;cableado", "punto de data"),
                ("Canalización (metro lineal)", "metro", "servicio;canalizacion", ""),
            ],
            "Servicios > Configuración y soporte": [
                ("Configuración de acceso remoto en celular", "servicio", "servicio;configuracion;app", "ver camaras en el celular"),
                ("Visita técnica / diagnóstico", "servicio", "servicio;visita;diagnostico", "chequeo"),
                ("Mantenimiento preventivo de CCTV", "servicio", "servicio;mantenimiento;cctv", ""),
                ("Mantenimiento preventivo de alarma", "servicio", "servicio;mantenimiento;alarma", ""),
                ("Mantenimiento de cerco eléctrico", "servicio", "servicio;mantenimiento;cerco", ""),
                ("Monitoreo de alarma (mensual)", "mes", "servicio;monitoreo;alarma", "monitoreo 24 horas"),
            ],
        },
    ),
}

KIT_ORDER = list(KITS.keys())


def kit_rows(kind: str) -> list[list[str]]:
    """Filas con las columnas de la plantilla (Nombre, Categoria, Unidad, Precio, Costo, Marca, Modelo, Descripcion,
    Etiquetas, Sinonimos, Codigo). Precio y costo vacíos."""
    _label, _file, groups = KITS[kind]
    return [
        [name, category, unit, "", "", "", "", "", tags, synonyms, ""]
        for category, items in groups.items()
        for name, unit, tags, synonyms in items
    ]


def all_rows() -> list[list[str]]:
    return [row for kind in KIT_ORDER for row in kit_rows(kind)]


def _fold(text: str) -> str:
    stripped = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def ensure_roots(db: Session) -> list[str]:
    """Crea los primeros niveles nuevos con su prefijo de código (y le pone el prefijo a uno que ya exista sin él).
    Devuelve los nombres creados."""
    roots = {_fold(c.name): c for c in db.query(Category).filter(Category.parent_id.is_(None)).all()}
    slugs = {s for (s,) in db.query(Category.slug).all()}
    created: list[str] = []
    for name, prefix in NEW_ROOTS.items():
        found = roots.get(_fold(name))
        if found is None:
            base = re.sub(r"[^a-z0-9]+", "-", _fold(name)).strip("-")
            slug, n = base, 2
            while slug in slugs:
                slug, n = f"{base}-{n}", n + 1
            slugs.add(slug)
            db.add(Category(name=name, slug=slug, code_prefix=prefix))
            created.append(name)
        elif not found.code_prefix:
            found.code_prefix = prefix
    db.flush()
    return created


def kit_summary() -> list[dict[str, Any]]:
    return [{"kind": k, "label": KITS[k][0], "file": KITS[k][1], "items": len(kit_rows(k))} for k in KIT_ORDER]
