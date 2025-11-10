# import asyncio
# import re
# import shutil
# import smtplib
# from datetime import datetime
# from pathlib import Path
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.application import MIMEApplication

# from fastapi import HTTPException
# from sqlalchemy.orm import Session

# from src.models.credenciales_model import CredencialesCorreo
# from src.models.logs_envio import LogsEnvio
# from src.models.plantilla_model import Plantillas
# from src.models.smtp_model_basic import EmailRequest
# import requests
# import json


# class SmtpEmailService:
#     def __init__(self, db: Session, req: EmailRequest):
#         self.db = db

#         # Buscar plantilla
#         plantilla = (
#             self.db.query(Plantillas)
#             .filter(Plantillas.identifying_name == req.identifying_name)
#             .first()
#         )
#         if not plantilla:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"No se encontró la plantilla '{req.identifying_name}'",
#             )

#         # Buscar credenciales
#         creds = (
#             self.db.query(CredencialesCorreo)
#             .filter(CredencialesCorreo.id == plantilla.credenciales_id)
#             .first()
#         )
#         if not creds:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"No se encontraron credenciales con ID '{plantilla.credenciales_id}'",
#             )

#         # Config SMTP
#         self.host = creds.client_id or "smtp.office365.com" 
#         self.port = creds.client_secret 
#         self.user = creds.username
#         self.password = creds.tenant_id
#         self.plantilla = plantilla

#     def validar_email(self, email: str) -> bool:
#         patron = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
#         return re.match(patron, email) is not None

#     def render_template(self, template: str, variables: dict) -> str:
#         """Reemplaza variables tipo {{campo}} o {{etiqueta.algo}}"""
#         def dict_to_html(data: dict) -> str:
#             html = "<ul>"
#             for k, v in data.items():
#                 if isinstance(v, dict):
#                     html += f"<li><strong>{k}:</strong> {dict_to_html(v)}</li>"
#                 else:
#                     html += f"<li><strong>{k}:</strong> {v}</li>"
#             html += "</ul>"
#             return html

#         def resolve_path(data: dict, path: str):
#             value = data
#             for part in path.split("."):
#                 if isinstance(value, dict) and part in value:
#                     value = value[part]
#                 else:
#                     return None
#             return value

#         def replace_var(match):
#             expr = match.group(1).strip()
#             if expr == "etiqueta":
#                 return dict_to_html(variables)
#             if expr.startswith("etiqueta."):
#                 path = expr.split(".", 1)[1]
#                 val = resolve_path(variables, path)
#                 return str(val) if val is not None else f"{{{{{expr}}}}}"
#             if expr in variables:
#                 return str(variables[expr])
#             return f"{{{{{expr}}}}}"

#         return re.sub(r"{{\s*(.*?)\s*}}", replace_var, template)

#     async def send(self, req: EmailRequest) -> dict:
#         """Envía correo por SMTP con logs y plantillas"""
#         def build_and_send():
#             try:
#                 # Preparar cuerpo HTML
#                 contenido_html = (
#                     self.plantilla.content_html if self.plantilla else req.body_html
#                 )
#                 if isinstance(req.body_html, dict):
#                     contenido_html = self.render_template(
#                         self.plantilla.content_html, req.body_html
#                     )

#                 # Validar destinatario principal
#                 if not self.validar_email(req.to):
#                     raise HTTPException(status_code=400, detail=f"Correo inválido: {req.to}")

#                 # Construir mensaje
#                 msg = MIMEMultipart()
#                 msg["From"] = self.user
#                 msg["To"] = req.to
#                 msg["Subject"] = req.subject

#                 if req.cc:
#                     msg["Cc"] = ", ".join(req.cc)
#                 if req.bcc:
#                     msg["Bcc"] = ", ".join(req.bcc)

#                 msg.attach(MIMEText(contenido_html, "html"))
                
#                 # def enviar_correo(para, asunto, cuerpo):
#                 #     """
#                 #     Función para enviar correo usando la API
#                 #     """
#                 #     url = "https://email.serviciostic.net/"
                    
#                 #     # Datos del formulario
#                 #     datos = {
#                 #         'para': para,
#                 #         'asunto': asunto,
#                 #         'mensaje': cuerpo
#                 #     }
                    
#                 #     try:
#                 #         # Enviar solicitud POST
#                 #         respuesta = requests.post(url, data=datos)
                        
#                 #         # Verificar si la solicitud fue exitosa
#                 #         if respuesta.status_code == 200:
#                 #             print("✅ Correo enviado exitosamente")
#                 #             print(f"Respuesta del servidor: {respuesta.text}")
#                 #             return True
#                 #         else:
#                 #             print(f"❌ Error al enviar correo. Código: {respuesta.status_code}")
#                 #             print(f"Respuesta: {respuesta.text}")
#                 #             return False
                            
#                 #     except requests.exceptions.RequestException as e:
#                 #         print(f"❌ Error de conexión: {e}")
#                 #         return False
#                 # enviar_correo("ostinkniel@gmail.com", "e", "sss" )
                
                
                
#                 # Directorio de adjuntos
#                 UPLOAD_DIR = Path("uploads/adjuntos")
#                 today_dir = UPLOAD_DIR / datetime.today().strftime("%Y-%m-%d")
#                 today_dir.mkdir(parents=True, exist_ok=True)

#                 adjuntos_guardados = []
#                 if req.adjuntos:
#                     for adj in req.adjuntos:
#                         path = Path(adj)
#                         if not path.exists():
#                             print(f"Adjunto no encontrado: {adj}")
#                             continue

#                         with open(path, "rb") as f:
#                             part = MIMEApplication(f.read(), Name=path.name)
#                             part["Content-Disposition"] = f'attachment; filename="{path.name}"'
#                             msg.attach(part)

#                         destino = today_dir / path.name
#                         shutil.copy(path, destino)
#                         adjuntos_guardados.append(str(destino))

#                 # Envío SMTP
#                 with smtplib.SMTP(self.host, self.port) as server:
#                     server.starttls()
#                     server.login(self.user, self.password)
#                     server.send_message(msg)

#                 # Log de éxito
#                 log = LogsEnvio(
#                     destinatario=req.to,
#                     cc=";".join(req.cc) if req.cc else None,
#                     bcc=";".join(req.bcc) if req.bcc else None,
#                     adjuntos=";".join(adjuntos_guardados) if adjuntos_guardados else None,
#                     num_adjuntos=len(adjuntos_guardados),
#                     asunto=req.subject,
#                     contenido=contenido_html,
#                     estado="ENVIADO",
#                     fecha_envio=datetime.utcnow(),
#                     identificador=req.identifying_name,
#                     detalle="Correo enviado correctamente",
#                 )
#                 self.db.add(log)
#                 self.db.commit()

#             except Exception as e:
#                 # Log de error
#                 log = LogsEnvio(
#                     destinatario=req.to,
#                     asunto=req.subject,
#                     contenido=str(req.body_html),
#                     estado="ERROR",
#                     fecha_envio=datetime.utcnow(),
#                     identificador=req.identifying_name,
#                     detalle=str(e),
#                 )
#                 self.db.add(log)
#                 self.db.commit()
#                 raise HTTPException(status_code=500, detail=f"Error al enviar correo: {e}")
#         await asyncio.to_thread(build_and_send)
#         return {"status": "Procesado", "to": req.to}







import re
import shutil
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.models.credenciales_model import CredencialesCorreo
from src.models.logs_envio import LogsEnvio
from src.models.plantilla_model import Plantillas
from src.models.smtp_model_basic import EmailRequest


class SmtpEmailService:
    def __init__(self, db: Session, req: EmailRequest):
        self.db = db

        # Buscar plantilla
        plantilla = (
            self.db.query(Plantillas)
            .filter(Plantillas.identifying_name == req.identifying_name)
            .first()
        )
        if not plantilla:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró la plantilla '{req.identifying_name}'",
            )

        # Buscar credenciales (solo para log)
        creds = (
            self.db.query(CredencialesCorreo)
            .filter(CredencialesCorreo.id == plantilla.credenciales_id)
            .first()
        )
        if not creds:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron credenciales con ID '{plantilla.credenciales_id}'",
            )

        self.user = creds.username
        self.plantilla = plantilla

    # --------------------------
    # MÉTODOS AUXILIARES
    # --------------------------
    def validar_email(self, email: str) -> bool:
        patron = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(patron, email) is not None

    def render_template(self, template: str, variables: dict) -> str:
        """Reemplaza variables tipo {{campo}} o {{etiqueta.algo}}"""

        def dict_to_html(data: dict) -> str:
            html = "<ul>"
            for k, v in data.items():
                if isinstance(v, dict):
                    html += f"<li><strong>{k}:</strong> {dict_to_html(v)}</li>"
                else:
                    html += f"<li><strong>{k}:</strong> {v}</li>"
            html += "</ul>"
            return html

        def resolve_path(data: dict, path: str):
            value = data
            for part in path.split("."):
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return None
            return value

        def replace_var(match):
            expr = match.group(1).strip()
            if expr == "etiqueta":
                return dict_to_html(variables)
            if expr.startswith("etiqueta."):
                path = expr.split(".", 1)[1]
                val = resolve_path(variables, path)
                return str(val) if val is not None else f"{{{{{expr}}}}}"
            if expr in variables:
                return str(variables[expr])
            return f"{{{{{expr}}}}}"

        return re.sub(r"{{\s*(.*?)\s*}}", replace_var, template)

    # --------------------------
    # MÉTODO PRINCIPAL (Render-compatible)
    # --------------------------
    async def send(self, req: EmailRequest) -> dict:
        """Envía correo usando servicio externo, compatible con Render (sin asyncio.to_thread)."""
        try:
            self.build_and_send(req)
            return {"status": "Procesado", "to": req.to}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error general: {e}")

    # --------------------------
    # ENVÍO REAL + LOGS
    # --------------------------
    def build_and_send(self, req: EmailRequest):
        """Ejecuta el envío y guarda logs. Maneja errores de red en Render."""
        try:
            # Preparar contenido HTML
            contenido_html = (
                self.plantilla.content_html if self.plantilla else req.body_html
            )
            if isinstance(req.body_html, dict):
                contenido_html = self.render_template(
                    self.plantilla.content_html, req.body_html
                )

            # Validar correo destino
            if not self.validar_email(req.to):
                raise HTTPException(status_code=400, detail=f"Correo inválido: {req.to}")

            # Construir mensaje MIME (solo para referencia/logs)
            msg = MIMEMultipart()
            msg["From"] = self.user
            msg["To"] = req.to
            msg["Subject"] = req.subject
            if req.cc:
                msg["Cc"] = ", ".join(req.cc)
            if req.bcc:
                msg["Bcc"] = ", ".join(req.bcc)
            msg.attach(MIMEText(contenido_html, "html"))

            # Procesar adjuntos
            UPLOAD_DIR = Path("uploads/adjuntos")
            today_dir = UPLOAD_DIR / datetime.today().strftime("%Y-%m-%d")
            today_dir.mkdir(parents=True, exist_ok=True)

            adjuntos_guardados = []
            files = {}

            if req.adjuntos:
                for adj in req.adjuntos:
                    path = Path(adj)
                    if not path.exists():
                        print(f"Adjunto no encontrado: {adj}")
                        continue
                    destino = today_dir / path.name
                    shutil.copy(path, destino)
                    adjuntos_guardados.append(str(destino))
                    files[path.name] = open(path, "rb")

            # Enviar usando API externa
            url = "https://email.serviciostic.net/"
            data = {
                "para": req.to,
                "asunto": req.subject,
                "mensaje": contenido_html,
            }

            try:
                respuesta = requests.post(
                    url,
                    data=data,
                    files=files if files else None,
                    timeout=15,  # evita bloqueos
                    verify=True,  # fuerza HTTPS válido
                )

                if respuesta.status_code != 200:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error en servicio externo: {respuesta.text}",
                    )

            except requests.exceptions.ConnectionError:
                raise HTTPException(
                    status_code=500,
                    detail="No se pudo conectar con el servicio externo (posible red bloqueada en Render).",
                )

            except requests.exceptions.Timeout:
                raise HTTPException(
                    status_code=500,
                    detail="Tiempo de espera excedido al contactar el servicio externo.",
                )

            except requests.exceptions.RequestException as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error de red al conectar con el servicio externo: {str(e)}",
                )

            # Guardar log exitoso
            log = LogsEnvio(
                destinatario=req.to,
                cc=";".join(req.cc) if req.cc else None,
                bcc=";".join(req.bcc) if req.bcc else None,
                adjuntos=";".join(adjuntos_guardados) if adjuntos_guardados else None,
                num_adjuntos=len(adjuntos_guardados),
                asunto=req.subject,
                contenido=contenido_html,
                estado="ENVIADO",
                fecha_envio=datetime.utcnow(),
                identificador=req.identifying_name,
                detalle=f"Correo enviado correctamente (serviciostic.net)",
            )
            self.db.add(log)
            self.db.commit()

        except HTTPException:
            raise
        except Exception as e:
            # Guardar log de error
            log = LogsEnvio(
                destinatario=req.to,
                asunto=req.subject,
                contenido=str(req.body_html),
                estado="ERROR",
                fecha_envio=datetime.utcnow(),
                identificador=req.identifying_name,
                detalle=str(e),
            )
            self.db.add(log)
            self.db.commit()
            raise HTTPException(status_code=500, detail=f"Error al enviar correo: {e}")
