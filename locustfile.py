import random
import time
import uuid
from locust import HttpUser, task, between

# endpoint que receberá os webhooks da Meta
WEBHOOK_ENDPOINT = "/webhook" 

class WhatsAppUser(HttpUser):
    # tempo que uma pessoa geralmente leva digitando (entre 1 e 5 segundos)
    wait_time = between(1, 5)

    def on_start(self):
        # Cada usuário simulado terá um número de telefone fixo durante a sessão
        self.phone_number = f"554198888{random.randint(100, 999)}"
        self.user_name = f"Paciente {random.randint(1, 1000)}"

    def _send_webhook(self, message_type, message_content):
        """payload padrão da Meta e envia POST"""
        
        # JSON da Meta
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "109238475",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {
                            "display_phone_number": "15550252222",
                            "phone_number_id": "1029384756"
                        },
                        "contacts": [{
                            "profile": {"name": self.user_name},
                            "wa_id": self.phone_number
                        }],
                        "messages": [{
                            "from": self.phone_number,
                            "id": f"wamid.{uuid.uuid4()}",
                            "timestamp": str(int(time.time())),
                            "type": message_type,
                            message_type: message_content
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

        # enviando o POST
        self.client.post(WEBHOOK_ENDPOINT, json=payload, headers={"User-Agent": "Facebook-Webhook"})

    @task(10) # Peso 10: Mensagens de texto são mais frequentes
    def send_text(self):
        textos = [
            "Olá, gostaria de marcar consulta",
            "Qual o valor da cirurgia?",
            "Estou com dúvidas sobre o pré-operatório",
            "O doutor atende Unimed?",
            "Bom dia!"
        ]
        content = {"body": random.choice(textos)}
        self._send_webhook("text", content)

    @task(2) # Peso 2: Imagens
    def send_image(self):
        content = {
            "mime_type": "image/jpeg",
            "sha256": "fake_hash_123",
            "id": "media_id_123",
            "caption": "Foto do exame"
        }
        self._send_webhook("image", content)

    @task(1) # Peso 1: Áudio (raro)
    def send_audio(self):
        content = {
            "mime_type": "audio/ogg; codecs=opus",
            "sha256": "fake_hash_audio",
            "id": "audio_id_456",
            "voice": True
        }
        self._send_webhook("audio", content)

    @task(1) # Peso 1: Documento/PDF
    def send_document(self):
        content = {
            "mime_type": "application/pdf",
            "sha256": "fake_hash_pdf",
            "id": "doc_id_789",
            "filename": "resultado_exame.pdf"
        }
        self._send_webhook("document", content)