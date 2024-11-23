import http.server
import socketserver
import threading
from dotenv import load_dotenv
from telethon import TelegramClient, events
import os
import asyncio

# Puerta por la que el servidor HTTP escuchará
PORT = int(os.getenv('PORT', 8000))

# Configurar un simple servidor HTTP para satisfacer los requerimientos de Render
class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_http_server():
    handler = SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"serving at port {PORT}")
        httpd.serve_forever()

# Iniciar el servidor HTTP en un hilo separado
http_thread = threading.Thread(target=start_http_server)
http_thread.daemon = True
http_thread.start()
# Lista de palabras clave a buscar en los mensajes
KEYWORDS = ["c4", "doxeo", "dni", "antecedentes", "titular", "arbol", "C4", "C4?", "c4?", "Doxeo?", "doxeo?", "DOXEO", "DNI?", "DNI", "Dni?", "dni?", "arbol?", "Arbol?"]

# Función para enviar un mensaje privado al usuario
async def sendPrivateMessage(client, user_id):
    try:
        # Enviar un mensaje privado
        await client.send_message(user_id, f"¡Hola! hago doxeos a un bajo precio, mira mis referencias aquí: https://t.me/doxingsreferencias. Soy 100% legal. Primero hago el trabajo y luego pagas")
        print(f"Enviado mensaje privado a {user_id}")
    except Exception as e:
        print(f"Error al enviar mensaje privado a {user_id}: {e}")

# Función para obtener la lista de grupos donde el bot está presente
async def getListOfGroups(client):
    try:
        dialogs = await client.get_dialogs()
        groups_info = []
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                entity = await client.get_entity(dialog.id)
                can_send_messages = entity.default_banned_rights is None or not entity.default_banned_rights.send_messages
                if can_send_messages:
                    group_info = {'group_id': dialog.id, 'group_name': dialog.title}
                    groups_info.append(group_info)
        return groups_info
    except Exception as e:
        print(f"Error getting list of groups: {e}")
        return []

# Función para obtener los últimos mensajes de un grupo
async def getMessagesFromGroup(client, group_id):
    try:
        all_messages = []
        async for message in client.iter_messages(group_id, limit=100):  # Lee los últimos 100 mensajes
            all_messages.append(message)
        return all_messages
    except Exception as e:
        print(f"Error getting messages from group {group_id}: {e}")
        return []


# Función para manejar el evento de nuevos mensajes
async def messageHandler(event, client):
    message_spam = event.message
    sender_id = message_spam.sender_id
    message_text = message_spam.text

    # Asegurarse de que el mensaje contenga texto y que no tenga menciones de @karmaOfc
    if message_text and '@KarmaOfc' not in message_text:
        print(f"Mensaje recibido: {message_text} - De {sender_id}")

    # Asegurarse de que el mensaje contenga texto y que no tenga menciones (usando el símbolo @)
    if message_text and '@' not in message_text:
        print(f"Mensaje recibido: {message_text} - De {sender_id}")

        # Verificar si el mensaje contiene alguna palabra clave
        if any(keyword.lower() in message_text.lower() for keyword in KEYWORDS):
            print(f"Mensaje con palabra clave encontrado: {message_text}")
            
            # Verificar que el mensaje tiene un sender_id válido
            if sender_id != (await client.get_me()).id and sender_id:
                # Enviar mensaje privado al usuario
                await sendPrivateMessage(client, sender_id)


# Función para manejar el envío y registro de logs
async def sendSpamAndLog(client, group_info, message_spam):
    try:
        # Si el mensaje contiene texto, enviarlo al grupo
        if message_spam.text:
            print(f"Enviando mensaje: {message_spam.text} - A grupo: {group_info['group_name']} ({group_info['group_id']})")
            if isinstance(group_info["group_id"], int):  # Si group_id es un número entero
                entity = await client.get_entity(group_info["group_id"])
                await client.send_message(entity, message_spam.text)
            
            # Log para el canal de spam
            log_message = f"Spam enviado exitosamente a: {group_info['group_name']} ({group_info['group_id']})"
            await client.send_message(os.getenv("LOGS_CHANNEL"), log_message)

        else:
            if isinstance(group_info["group_id"], int):
                entity = await client.get_entity(group_info["group_id"])
                await client.forward_messages(entity, message_spam.id)

        # Espera de 2 minutos entre los mensajes enviados a un grupo
        await asyncio.sleep(120)
    except Exception as error:
        print(f"Error procesando mensaje: {error}")

# Función principal que ejecuta el bot
async def logUserBot(client):
    load_dotenv()
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    phone_number = os.getenv("PHONENUMBER")
    session_name = "bot_spammer"

    # Conectar al cliente de Telegram si aún no está conectado
    if not client.is_connected():
        await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone_number)
        await client.sign_in(phone_number, input('Ingrese el código de verificación: '))
    else:
        print("Usuario ya autorizado")

    # Enviar mensaje inicial al canal de logs
    await client.send_message(os.getenv("LOGS_CHANNEL"), f'<b>Bot encendido</b>', parse_mode="HTML")
    spammer_group = int(os.getenv("SPAMMER_GROUP"))

    while True:
        try:
            # Obtener la lista de grupos donde el bot está presente
            groups_info = await getListOfGroups(client)
            messages_list = await getMessagesFromGroup(client, spammer_group)

            # Informar sobre la cantidad de mensajes obtenidos
            await client.send_message("@doxeoEconomicoOficial", f"<b>CANTIDAD DE MENSAJES CONSEGUIDOS PARA PUBLICAR</b> <code>{len(messages_list) - 1}</code>", parse_mode="HTML")

            # Procesar cada grupo donde el bot está presente
            for group_info in groups_info:
                # Ignorar grupos específicos
                if group_info['group_name'] not in ["Spam 2024", "DOXEO ECONOMICO"]:
                    print(f"Procesando grupo: {group_info['group_name']} ({group_info['group_id']})")
                    for message_spam in messages_list:
                        try:
                            # Verificar si el mensaje contiene alguna de las palabras clave
                            if message_spam.text and any(keyword.lower() in message_spam.text.lower() for keyword in KEYWORDS):
                                print(f"Mensaje encontrado: {message_spam.text} - De {message_spam.sender_id}")
                                
                                # Verificar que el mensaje tenga un sender_id y que no sea del propio bot
                                if message_spam.sender_id != (await client.get_me()).id and message_spam.sender_id:
                                    # Enviar mensaje privado al usuario
                                    await sendPrivateMessage(client, message_spam.sender_id)

                            # Enviar el mensaje y registrar el log
                            await sendSpamAndLog(client, group_info, message_spam)

                        except Exception as error:
                            print(f"Error procesando mensaje: {error}")
                    # Espera 2 minutos después de procesar todos los mensajes de un grupo
                    await asyncio.sleep(120)  # Espera 2 minutos entre el envío de mensajes a un grupo

            # Mensaje de log después de completar una ronda
            await client.send_message(os.getenv("LOGS_CHANNEL"), f'<b>Round finished</b>', parse_mode="HTML")
            await asyncio.sleep(300)  # Esperar 5 minutos antes de la siguiente ronda

        except Exception as e:
            print(f"Error en el bucle principal: {e}")

# Crear la instancia del cliente de Telegram
load_dotenv()
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
phone_number = os.getenv("PHONENUMBER")
session_name = "bot_spammer"
client = TelegramClient(session_name, api_id, api_hash)

# Decora la función de respuesta a mensajes después de crear la instancia de client
@client.on(events.NewMessage(incoming=True))
async def handler(event):
    await messageHandler(event, client)

# Ejecutar el bot
if __name__ == "__main__":
    # Ejecutar la función logUserBot con la instancia de client
    asyncio.run(logUserBot(client))

