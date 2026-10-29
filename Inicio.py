import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import uuid
from pathlib import Path

# Configuración de la página
st.set_page_config(
    page_title="Lector de Sensor MQTT",
    page_icon="📡",
    layout="centered"
)

# Variables de estado
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = None


def get_mqtt_message(broker, port, topic, client_id, wait_seconds=10):
    """Se conecta al broker, se suscribe al tópico y espera un mensaje."""
    message_received = {"received": False, "payload": None}

    def on_message(client, userdata, message):
        try:
            message_received["payload"] = json.loads(message.payload.decode())
        except Exception:
            # Si no es JSON, guardar como texto
            message_received["payload"] = message.payload.decode()
        message_received["received"] = True

    try:
        # Compatible con paho-mqtt 1.x y 2.x
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
        except AttributeError:
            client = mqtt.Client(client_id=client_id)

        client.on_message = on_message
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()

        # Esperar hasta wait_seconds a que llegue un mensaje
        timeout = time.time() + wait_seconds
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.1)

        client.loop_stop()
        client.disconnect()

        if not message_received["received"]:
            return {
                "error": f"No llegó ningún mensaje en {wait_seconds} s. "
                         "¿Está corriendo la simulación en Wokwi y el tópico coincide?"
            }

        return message_received["payload"]

    except Exception as e:
        return {"error": str(e)}


# Sidebar - Configuración
with st.sidebar:
    st.subheader('⚙️ Configuración de Conexión')

    broker = st.text_input(
        'Broker MQTT',
        value='broker.hivemq.com',
        help='Dirección del broker MQTT'
    )

    port = st.number_input(
        'Puerto',
        value=1883,
        min_value=1,
        max_value=65535,
        help='Puerto del broker (generalmente 1883)'
    )

    topic = st.text_input(
        'Tópico',
        value='Sensor/THP2/nicolemejia',
        help='Debe ser exactamente el mismo tópico que usa el ESP32'
    )

    client_id = st.text_input(
        'ID del Cliente',
        value=f'streamlit_{uuid.uuid4().hex[:8]}',
        help='Identificador único para este cliente'
    )

# Título
st.title('📡 Lector de Sensor MQTT')

# Imagen debajo del título
img_path = Path(__file__).parent / 'gatomqtt.jpg'
if img_path.exists():
    st.image(str(img_path), use_container_width=True)
else:
    st.warning('⚠️ No se encontró la imagen gatomqtt.jpg en el repositorio.')

# Información al inicio
with st.expander('ℹ️ Información', expanded=False):
    st.markdown("""
    ### Cómo usar esta aplicación:

    1. **Broker MQTT**: Ingresa la dirección del servidor MQTT en el sidebar
    2. **Puerto**: Generalmente es 1883 para conexiones no seguras
    3. **Tópico**: El canal al que deseas suscribirte (igual al del ESP32)
    4. **ID del Cliente**: Un identificador único para esta conexión
    5. Haz clic en **Obtener Datos** para recibir el mensaje más reciente

    ### Brokers públicos para pruebas:
    - broker.hivemq.com
    - test.mosquitto.org
    - broker.mqttdashboard.com
    """)

st.divider()

# Botón para obtener datos
if st.button('🔄 Obtener Datos del Sensor', use_container_width=True):
    with st.spinner('Conectando al broker y esperando datos...'):
        sensor_data = get_mqtt_message(broker, int(port), topic, client_id)
        st.session_state.sensor_data = sensor_data

# Mostrar resultados
if st.session_state.sensor_data is not None:
    st.divider()
    st.subheader('📊 Datos Recibidos')

    data = st.session_state.sensor_data

    # Verificar si hay error
    if isinstance(data, dict) and 'error' in data:
        st.error(f"❌ {data['error']}")
    else:
        st.success('✅ Datos recibidos correctamente')

        if isinstance(data, dict) and len(data) > 0:
            # Mostrar cada campo en una métrica
            cols = st.columns(len(data))
            for i, (key, value) in enumerate(data.items()):
                with cols[i]:
                    if isinstance(value, float):
                        value = round(value, 1)
                    st.metric(label=key, value=value)

            # Mostrar JSON completo
            with st.expander('Ver JSON completo'):
                st.json(data)
        else:
            # Si no es dict, mostrar como texto
            st.code(data)
