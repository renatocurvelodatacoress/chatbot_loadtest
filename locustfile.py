import random
import time
import uuid
import os
import io
import json
from locust import HttpUser, task, between

# endpoint que receberá os webhooks da Meta
WEBHOOK_ENDPOINT = "/webhook"

# --------------------
# Ajustes de frequência (valores inteiros usados pelos decoradores @task)
TEXT_WEIGHT = 10
IMAGE_WEIGHT = 2
AUDIO_WEIGHT = 1
DOCUMENT_WEIGHT = 1

# --------------------
# Simulação de mídia: modo e probabilidades
# UPLOAD_MODE: "none" -> apenas metadados (padrão leve)
#              "server_fetch" -> inclui media_url para o servidor baixar (testa I/O do servidor)
#              "multipart" -> envia multipart/form-data com binário gerado (testa rede/CPU do receptor)
UPLOAD_MODE = "multipart"  # escolha: "none", "server_fetch", "multipart"
SIMULATE_UPLOAD_FILES = True  # habilita comportamento de mídia pesada

# probabilidade, dentro de cada task de mídia, de enviar/gerar o binário (0.0 - 1.0)
IMAGE_UPLOAD_PROB = 0.8
AUDIO_UPLOAD_PROB = 0.5
DOCUMENT_UPLOAD_PROB = 0.8

# URLs públicas para "server_fetch" (se usar esse modo, o backend deverá buscar esses URLs)
MEDIA_PUBLIC_URLS = {
    "image": [
        "https://example.com/test-media/image-100kb.jpg",
        "https://example.com/test-media/image-300kb.jpg"
    ],
    "audio": [
        "https://example.com/test-media/audio-200kb.ogg",
        "https://example.com/test-media/audio-800kb.ogg"
    ],
    "document": [
        "https://example.com/test-media/doc-50kb.pdf",
        "https://example.com/test-media/doc-250kb.pdf"
    ]
}

# --------------------
# Tamanhos (bytes) variáveis para geração local (multipart)
IMAGE_MIN_BYTES = 10_000     # 10 KB
IMAGE_MAX_BYTES = 500_000    # 500 KB
AUDIO_MIN_BYTES = 20_000     # 20 KB
AUDIO_MAX_BYTES = 1_200_000  # 1.2 MB
DOCUMENT_MIN_BYTES = 10_000  # 10 KB
DOCUMENT_MAX_BYTES = 800_000 # 800 KB

class WhatsAppUser(HttpUser):
    # tempo que uma pessoa geralmente leva digitando (entre 1 e 5 segundos)
    wait_time = between(1, 5)

    def on_start(self):
        # Cada usuário simulado terá um número de telefone fixo durante a sessão
        self.phone_number = f"554198888{random.randint(100, 999)}"
        self.user_name = f"Paciente {random.randint(1, 1000)}"

    def _post_payload(self, payload, files=None):
        """Envia POST: se files fornecido, envia multipart/form-data incluindo o campo 'payload'."""
        headers = {"User-Agent": "Facebook-Webhook"}
        if files is not None:
            # inclui payload JSON como campo form-data
            multipart = {"payload": (None, json.dumps(payload), "application/json")}
            multipart.update(files)
            self.client.post(WEBHOOK_ENDPOINT, files=multipart, headers=headers)
        else:
            self.client.post(WEBHOOK_ENDPOINT, json=payload, headers=headers)

    def _build_base_payload(self, message_type, message_content):
        """Gera o JSON base conforme estrutura da Meta."""
        return {
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

    @task(TEXT_WEIGHT)
    def send_text(self):
        textos = [
            "Olá, gostaria de marcar consulta",
            "Qual o valor da cirurgia?",
            "Estou com dúvidas sobre o pré-operatório",
            "O doutor atende Unimed?",
            "Bom dia!"
        ]
        content = {"body": random.choice(textos)}
        payload = self._build_base_payload("text", content)
        self._post_payload(payload)

    @task(IMAGE_WEIGHT)
    def send_image(self):
        content = {
            "mime_type": "image/jpeg",
            "sha256": "fake_hash_123",
            "id": f"media_id_img_{random.randint(1,9999)}",
            "caption": "Foto do exame"
        }

        payload = self._build_base_payload("image", content)

        if SIMULATE_UPLOAD_FILES and UPLOAD_MODE == "server_fetch" and random.random() < IMAGE_UPLOAD_PROB:
            # instrui backend a baixar a imagem
            content["media_url"] = random.choice(MEDIA_PUBLIC_URLS["image"])
            payload = self._build_base_payload("image", content)
            self._post_payload(payload)
            return

        if SIMULATE_UPLOAD_FILES and UPLOAD_MODE == "multipart" and random.random() < IMAGE_UPLOAD_PROB:
            size = random.randint(IMAGE_MIN_BYTES, IMAGE_MAX_BYTES)
            img_bytes = os.urandom(size)
            img_file = io.BytesIO(img_bytes)
            img_file.seek(0)
            files = {
                "file": (f"image_{size}.jpg", img_file, "image/jpeg")
            }
            self._post_payload(payload, files=files)
            return

        # default: metadados leves
        self._post_payload(payload)

    @task(AUDIO_WEIGHT)
    def send_audio(self):
        content = {
            "mime_type": "audio/ogg; codecs=opus",
            "sha256": "fake_hash_audio",
            "id": f"media_id_aud_{random.randint(1,9999)}",
            "voice": True
        }

        payload = self._build_base_payload("audio", content)

        if SIMULATE_UPLOAD_FILES and UPLOAD_MODE == "server_fetch" and random.random() < AUDIO_UPLOAD_PROB:
            content["media_url"] = random.choice(MEDIA_PUBLIC_URLS["audio"])
            payload = self._build_base_payload("audio", content)
            self._post_payload(payload)
            return

        if SIMULATE_UPLOAD_FILES and UPLOAD_MODE == "multipart" and random.random() < AUDIO_UPLOAD_PROB:
            size = random.randint(AUDIO_MIN_BYTES, AUDIO_MAX_BYTES)
            aud_bytes = os.urandom(size)
            aud_file = io.BytesIO(aud_bytes)
            aud_file.seek(0)
            files = {
                "file": (f"audio_{size}.ogg", aud_file, "audio/ogg")
            }
            self._post_payload(payload, files=files)
            return

        self._post_payload(payload)

    @task(DOCUMENT_WEIGHT)
    def send_document(self):
        content = {
            "mime_type": "application/pdf",
            "sha256": "fake_hash_pdf",
            "id": f"doc_id_{random.randint(1,9999)}",
            "filename": "resultado_exame.pdf"
        }

        payload = self._build_base_payload("document", content)

        if SIMULATE_UPLOAD_FILES and UPLOAD_MODE == "server_fetch" and random.random() < DOCUMENT_UPLOAD_PROB:
            content["media_url"] = random.choice(MEDIA_PUBLIC_URLS["document"])
            payload = self._build_base_payload("document", content)
            self._post_payload(payload)
            return

        if SIMULATE_UPLOAD_FILES and UPLOAD_MODE == "multipart" and random.random() < DOCUMENT_UPLOAD_PROB:
            size = random.randint(DOCUMENT_MIN_BYTES, DOCUMENT_MAX_BYTES)
            # monta um "PDF" simples: header + bytes aleatórios
            header = b"%PDF-1.4\n%FakePDF\n"
            body_size = max(0, size - len(header))
            pdf_bytes = header + os.urandom(body_size)
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_file.seek(0)
            files = {
                "file": ("resultado_exame.pdf", pdf_file, "application/pdf")
            }
            self._post_payload(payload, files=files)
            return

        self._post_payload(payload)