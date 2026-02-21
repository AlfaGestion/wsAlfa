# Login / Auth

# NO

Para la autenticación del usuario, vamos a tener una tabla con la siguiente estructura:

### Tabla: web_auth

- email - es el nombre que identifica al usuario
- cuenta - es el codigo de cliente asociado al usuario
- password - es la clave del usuario
- dbname - es la base de datos que utilizar
- server - es el servidor de la base de datos

# Por el momento se usa TA_USUARIOS

### Se agregan los siguientes campos :

- claveweb nvarchar (50) - clave que el usuario va a utilizar para loguearse

### Como campo usuario se utiliza el siguiente campo:

- email_usuario


https://auth.mercadolibre.com.ar/authorization?response_type=code&client_id=6147429509226251&redirect_uri=https://www.google.com/

test_seller = {
    "id": 1429334698,
    "email": "test_user_149595167@testuser.com",
    "nickname": "TESTUSER149595167",
    "site_status": "active",
    "password": "Kk76MlM0kP"
}

test_buyer = {
    "id": 1428364087,
    "email": "test_user_2024903831@testuser.com",
    "nickname": "TESTUSER2024903831",
    "site_status": "active",
    "password": "H3sRyXZIVt"
}

Tarjetas de prueba = {
    "entidad" : "Mastercard",
    "numero" : 5031 7557 3453 0604,
    "codigo" : 123,
    "vencimiento" : "11/25"
}

{
    "entidad" : "Visa",
    "numero" : 4509 9535 6623 3704,
    "codigo" : 123,
    "vencimiento" : "11/25"
}

{
    "entidad" : "American Express",
    "numero" : 3711 803032 57522,
    "codigo" : 1234,
    "vencimiento" : "11/25"
}

Para probar diferentes resultados de pago, completa el estado deseado en el nombre del titular de la tarjeta. Por ejemplo, si deseas que el pago sea aprobado, debes ingresar "APRO APRO":

Estado de pago	    Descripción	                                            Documento de identidad

APRO	            Pago aprobado	                                        (DNI) 12345678
OTHE	            Rechazado por error general	                            (DNI) 12345678
CONT	            Pendiente de pago	                                    -
CALL	            Rechazado con validación para autorizar	                -
FUND	            Rechazado por importe insuficiente	                    -
SECU	            Rechazado por código de seguridad inválido	            -
EXPI	            Rechazado debido a un problema de fecha de vencimiento	-
FORM	            Rechazado debido a un error de formulario	            -


# wsAlfa
## IA Backend OpenAI

Script backend movido desde `IA_ProcesarDocumentos`:
- `ia_backend\ia_backend_proxy_server.py`

Variables requeridas en `.env`:
```env
OPENAI_API_KEY=tu_api_key_openai
IA_CLIENTS_JSON={"cliente_oliva":"secreto_largo_unico"}
IA_BACKEND_HOST=0.0.0.0
IA_BACKEND_PORT=8787
IA_MAX_SKEW_SECONDS=300
```

Ejecutar:
```powershell
cd e:\Dev\wsAlfa
python .\ia_backend\ia_backend_proxy_server.py
```

