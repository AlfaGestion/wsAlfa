from flask import Blueprint, Flask, jsonify, request, Response

from flask_cors import CORS
from flask_mail import Mail
from datetime import datetime
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

from auth import validate_api_key

from routes.v2.admin import admin

from routes.v2.account import AccountView
from routes.v2.auth import AuthView
from routes.v2.budget import BudgetView
from routes.v2.cashbox import CashBoxView
from routes.v2.customer import CustomerView
from routes.v2.family import FamilyView
from routes.v2.helpdesk import HelpDeskView
from routes.v2.management import ManagementView
from routes.v2.order import OrderView
from routes.v2.order_c import OrderCView
from routes.v2.payment import PaymentView
from routes.v2.product import ProductView
from routes.v2.products import ProductsView
from routes.v2.sales import SalesView
from routes.v2.seller import SellerView
from routes.v2.service import ServiceView
from routes.v2.session import SessionView
from routes.v2.stock import StockView
from routes.v2.sync import SyncView
from routes.v2.category import CategoryView
from routes.v2.brand import BrandView
from routes.v2.unit import UnitView
from routes.v2.task import TaskView
from routes.v2.chart import ChartView
# from routes.v2.database import DatabaseView
from routes.v2.contract import ContractView
from routes.v2.transport.customer import CustomerTransportView
from routes.v2.register import RegisterView
from routes.v2.cart import CartView
from routes.v2.configuration import ConfigurationView
from routes.v2.mercadolibre import MercadoLibreView
from routes.v2.ingresos import IngresosView
from routes.v2.Inventario import InventarioView

# Transport
from routes.v2.transport.remittances import RemittancesTransportView

# Alfa (Se conectan a la base de datos de alfa tareas)
# from routes.v2.alfa.task import AlfaTaskView
from routes.v2.user import UserView
from routes.v2.user_contact import UserContactView
from routes.v2.utils import UtilsView
from routes.v2.tables import TablesView
from routes.v2.report import ReportView

from routes.v2.alfa.sharedb import AlfaShareDBView

from config import AppConfig


from routes.v2.chrome_extension import ChromeExtensionView

from routes.v3.consultas import ViewConsultas
from routes.v3.report import ViewReport
from routes.v3.product import ViewProduct
from routes.v3.customer import ViewCustomer
from routes.v3.account import ViewAccount
from routes.v3.products import ViewProducts
from routes.v3.auth import ViewAuth
from routes.v3.register import ViewRegister
from routes.v3.session import ViewSession
from routes.v3.category import ViewCategory
from routes.v3.brand import ViewBrand
from routes.v3.unit import ViewUnit
from routes.v3.seller import ViewSeller
from routes.v3.stock import ViewStock
from routes.v3.family import ViewFamily
from routes.v3.chrome_extension import ViewChromeExtension
from routes.v3.configuration import ViewConfiguration
from routes.v3.transmision_codigos_zonas import ViewTransmisionCodigosZonas
from routes.v3.menu import ViewMenu

from routes.v3.ingresos import IngresosView
from routes.v3.cashbox import ViewCashBox
from routes.v3.service import ViewService
from routes.v3.task import ViewTask
from routes.v3.order import ViewOrder
from routes.v3.payment import ViewPayment
from routes.v3.sales import ViewSales
from routes.v3.utils import ViewUtils


app = Flask(__name__)

# Carga variables desde wsAlfa/.env al iniciar app.py
_env_path = Path(__file__).resolve().parent / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=str(_env_path), override=True)
else:
    load_dotenv(override=True)


NONCE_TTL_SECONDS = 600
_IA_SEEN_NONCES: Dict[str, float] = {}
_IA_CLIENTS: Optional[Dict[str, str]] = None
_IA_OPENAI_CLIENT: Optional[OpenAI] = None


def _cleanup_nonces(now: float) -> None:
    expired = [k for k, ts in _IA_SEEN_NONCES.items() if (now - ts) > NONCE_TTL_SECONDS]
    for k in expired:
        _IA_SEEN_NONCES.pop(k, None)


def _build_signature(secret: str, timestamp: str, nonce: str, body: str) -> str:
    msg = f"{timestamp}.{nonce}.{body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _extract_output_text(resp: Any) -> str:
    out_text = (getattr(resp, "output_text", None) or "").strip()
    if out_text:
        return out_text

    parts = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            t = getattr(c, "text", None)
            if t:
                parts.append(t)
    return "\n".join(parts).strip()


def _load_ia_clients() -> Dict[str, str]:
    raw = (os.getenv("IA_CLIENTS_JSON") or "").strip()
    if not raw:
        raise RuntimeError("Falta IA_CLIENTS_JSON")

    try:
        data = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"IA_CLIENTS_JSON invalido: {e}") from e

    if not isinstance(data, dict) or not data:
        raise RuntimeError("IA_CLIENTS_JSON debe ser un objeto con al menos un cliente")

    out: Dict[str, str] = {}
    for k, v in data.items():
        key = str(k).strip()
        val = str(v).strip()
        if key and val:
            out[key] = val

    if not out:
        raise RuntimeError("IA_CLIENTS_JSON sin clientes validos")
    return out


def _get_ia_clients() -> Dict[str, str]:
    global _IA_CLIENTS
    if _IA_CLIENTS is None:
        _IA_CLIENTS = _load_ia_clients()
    return _IA_CLIENTS


def _get_ia_openai_client() -> OpenAI:
    global _IA_OPENAI_CLIENT
    if _IA_OPENAI_CLIENT is None:
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise RuntimeError("Falta OPENAI_API_KEY")
        _IA_OPENAI_CLIENT = OpenAI(api_key=api_key)
    return _IA_OPENAI_CLIENT


def _sql_conn_str() -> str:
    user = (os.getenv("SQL_USER") or "").strip()
    pwd = (os.getenv("SQL_PASSWORD") or "").strip()
    server = (os.getenv("SQL_SERVER") or "").strip()
    db = (os.getenv("SQL_DATABASE") or "").strip()
    driver = (os.getenv("SQL_DRIVER") or "").strip()
    if not all([user, pwd, server, db, driver]):
        return ""
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={pwd};"
        "TrustServerCertificate=yes;"
    )


def _save_audit(idcliente_raw: Any, opcion: str, archivo: str, ok: bool, err: str, duracion_ms: int) -> Optional[str]:
    if idcliente_raw is None or str(idcliente_raw).strip() == "":
        return None

    try:
        idcliente = int(str(idcliente_raw).strip())
    except Exception:
        return "idcliente invalido"

    conn_str = _sql_conn_str()
    if not conn_str:
        return "faltan variables SQL_*"

    try:
        import pyodbc  # type: ignore
    except Exception:
        return "falta pyodbc"

    variants = [
        (
            "INSERT INTO dbo.IA_ConsultasGPT (idcliente, opcion, archivo, ok, error, duracion_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (idcliente, opcion, archivo, 1 if ok else 0, err, int(duracion_ms)),
        ),
        (
            "INSERT INTO dbo.IA_ConsultasGPT (idcliente, opcion, archivo_nombre, ok, error, duracion_ms) VALUES (?, ?, ?, ?, ?, ?)",
            (idcliente, opcion, archivo, 1 if ok else 0, err, int(duracion_ms)),
        ),
        (
            "INSERT INTO dbo.IA_ConsultasGPT (idcliente, opcion, archivo) VALUES (?, ?, ?)",
            (idcliente, opcion, archivo),
        ),
        (
            "INSERT INTO dbo.IA_ConsultasGPT (idcliente, opcion, archivo_nombre) VALUES (?, ?, ?)",
            (idcliente, opcion, archivo),
        ),
    ]

    last_err = ""
    for sql, params in variants:
        try:
            import pyodbc  # type: ignore
            with pyodbc.connect(conn_str, timeout=5) as conn:
                cur = conn.cursor()
                cur.execute(sql, params)
                conn.commit()
                return None
        except Exception as e:
            last_err = str(e)

    return f"sql_insert_error: {last_err}"


def _append_audit_fallback(
    *,
    idcliente: Any,
    opcion: str,
    archivo: str,
    ok: bool,
    error: str,
    duracion_ms: int,
    sql_error: str,
) -> None:
    """Persistencia local cuando SQL no está disponible."""
    try:
        log_dir = Path(__file__).resolve().parent / "LOG"
        log_dir.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": int(time.time()),
            "idcliente": idcliente,
            "opcion": opcion,
            "archivo_nombre": archivo,
            "ok": 1 if ok else 0,
            "error": error or "",
            "duracion_ms": int(duracion_ms),
            "sql_error": sql_error or "",
        }
        with (log_dir / "ia_audit_fallback.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        # Nunca cortar la respuesta de API por error de fallback.
        return


app.config.from_object(AppConfig)


mail = Mail(app)

api_cors_config = {
    "origins": "*",
    "methods": ["OPTIONS", "GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Authorization", "Content-Type"]
}

CORS(app, resources={"/api/*": api_cors_config},
     supports_credentials=True)


API_PREFIX_V3 = '/api/v3'
API_PREFIX = '/api/v2'
TRANSPORT_PREFIX = '/transport'

# Utilizado para lo administrativo
apiv2_bp = Blueprint('apiv2_bp', __name__,
                     template_folder='templates',
                     static_folder='static', static_url_path='assets')

apiv2_bp.register_blueprint(admin)
app.register_blueprint(apiv2_bp, url_prefix=f'{API_PREFIX}')

# Endpoints generales
AuthView.register(app, route_base=f'{API_PREFIX}')
ProductsView.register(app, route_base=f'{API_PREFIX}/products')
AccountView.register(app, route_base=f'{API_PREFIX}/account')
SalesView.register(app, route_base=f'{API_PREFIX}/sales')
ManagementView.register(app, route_base=f'{API_PREFIX}/management')
CashBoxView.register(app, route_base=f'{API_PREFIX}/cashbox')
StockView.register(app, route_base=f'{API_PREFIX}/stock')
SessionView.register(app, route_base=f'{API_PREFIX}/session')
UserContactView.register(app, route_base=f'{API_PREFIX}/contact')
UserView.register(app, route_base=f'{API_PREFIX}/user')
ContractView.register(app, route_base=f'{API_PREFIX}/contract')
BudgetView.register(app, route_base=f'{API_PREFIX}/budget')
UtilsView.register(app, route_base=f'{API_PREFIX}/utils')
AlfaShareDBView.register(app, route_base=f'{API_PREFIX}/share')
# DatabaseView.register(app, route_base=f'{API_PREFIX}/database')
# RegisterView.register(app, route_base=f'{API_PREFIX}/register')
ChromeExtensionView.register(app, route_base=f'{API_PREFIX}/extension')
TablesView.register(app, route_base=f'{API_PREFIX}/tables')
ChartView.register(app, route_base=f'{API_PREFIX}/charts')
CartView.register(app, route_base=f'{API_PREFIX}/cart')
ConfigurationView.register(app, route_base=f'{API_PREFIX}/configuration')
ReportView.register(app, route_base=f'{API_PREFIX}/report')
MercadoLibreView.register(app, route_base=f'{API_PREFIX}/ml')
IngresosView.register(app, route_base=f'{API_PREFIX}/ingresos')
InventarioView.register(app, route_base=f'{API_PREFIX}/inventario')




# Movil
SyncView.register(app, route_base=f'{API_PREFIX}/sync')
CategoryView.register(app, route_base=f'{API_PREFIX}/category')
SellerView.register(app, route_base=f'{API_PREFIX}/seller')
ServiceView.register(app, route_base=f'{API_PREFIX}/service')
TaskView.register(app, route_base=f'{API_PREFIX}/task')
FamilyView.register(app, route_base=f'{API_PREFIX}/family')
CustomerView.register(app, route_base=f'{API_PREFIX}/customer')
ProductView.register(app, route_base=f'{API_PREFIX}/product')
PaymentView.register(app, route_base=f'{API_PREFIX}/payment')
OrderView.register(app, route_base=f'{API_PREFIX}/order')
OrderCView.register(app, route_base=f'{API_PREFIX}/order_c')
BrandView.register(app, route_base=f'{API_PREFIX}/brand')
UnitView.register(app, route_base=f'{API_PREFIX}/unit')

# Transporte

RemittancesTransportView.register(app, route_base=f'{API_PREFIX}{TRANSPORT_PREFIX}/remittances')
CustomerTransportView.register(app, route_base=f'{API_PREFIX}{TRANSPORT_PREFIX}/customer')

# Alfa
HelpDeskView.register(app, route_base=f'{API_PREFIX}/helpdesk')
# AlfaTaskView.register(app, route_base=f'{API_PREFIX}/alfa/task')


"""
Endpoints V3
"""
# ViewConsultas.register(app, route_base=f'{API_PREFIX_V3}/consultas')
# ViewReport.register(app, route_base=f'{API_PREFIX_V3}/report')
ViewProduct.register(app, route_base=f'{API_PREFIX_V3}/product')
ViewCustomer.register(app, route_base=f'{API_PREFIX_V3}/customer')
ViewAccount.register(app, route_base=f'{API_PREFIX_V3}/account')
ViewProducts.register(app, route_base=f'{API_PREFIX_V3}/products')
ViewAuth.register(app, route_base=f'{API_PREFIX_V3}')
# ViewRegister.register(app, route_base=f'{API_PREFIX_V3}/register')
ViewSession.register(app, route_base=f'{API_PREFIX_V3}/session')
ViewSeller.register(app, route_base=f'{API_PREFIX_V3}/seller')
ViewBrand.register(app, route_base=f'{API_PREFIX_V3}/brand')
ViewCategory.register(app, route_base=f'{API_PREFIX_V3}/category')
ViewUnit.register(app, route_base=f'{API_PREFIX_V3}/unit')
ViewStock.register(app, route_base=f'{API_PREFIX_V3}/stock')
ViewFamily.register(app, route_base=f'{API_PREFIX_V3}/family')
ViewCashBox.register(app, route_base=f'{API_PREFIX_V3}/cashbox')
ViewService.register(app, route_base=f'{API_PREFIX_V3}/service')
ViewTask.register(app, route_base=f'{API_PREFIX_V3}/task')
ViewOrder.register(app, route_base=f'{API_PREFIX_V3}/order')
ViewPayment.register(app, route_base=f'{API_PREFIX_V3}/payment')
ViewSales.register(app, route_base=f'{API_PREFIX_V3}/sales')
ViewUtils.register(app, route_base=f'{API_PREFIX_V3}/utils')
# ViewChromeExtension.register(app, route_base=f'{API_PREFIX_V3}/extension')
# ViewConfiguration.register(app, route_base=f'{API_PREFIX_V3}/configuration')
# ViewMenu.register(app, route_base=f'{API_PREFIX_V3}/menu')
ViewTransmisionCodigosZonas.register(app, route_base=f'{API_PREFIX_V3}/transmision_codigos')
# IngresosView.register(app, route_base=f'{API_PREFIX_V3}/ingresos')
# ViewWarehouse.register(app, route_base=f'{API_PREFIX_V3}/warehouse')
# ViewProducts.register(app, route_base=f'{API_PREFIX_V3}/products')
# ViewStock.register(app, route_base=f'{API_PREFIX_V3}/stock')
# ViewCustomer.register(app, route_base=f'{API_PREFIX_V3}/customers')
# ViewSales.register(app, route_base=f'{API_PREFIX_V3}/sales')
# ViewSeller.register(app, route_base=f'{API_PREFIX_V3}/sellers')
# ViewAuth.register(app, route_base=f'{API_PREFIX_V3}/auth')
# ViewSession.register(app, route_base=f'{API_PREFIX_V3}/session')
# TODO agregar logs en todos los puntos de la api

@app.route('/v1/process', methods=['POST', 'OPTIONS'])
def ia_process_proxy():
    if request.method == 'OPTIONS':
        return ('', 204)

    raw_body_bytes = request.get_data() or b''
    raw_body = raw_body_bytes.decode('utf-8', errors='replace')

    client_id = (request.headers.get('X-IA-Client-Id') or '').strip()
    ts_raw = (request.headers.get('X-IA-Timestamp') or '').strip()
    nonce = (request.headers.get('X-IA-Nonce') or '').strip()
    sig = (request.headers.get('X-IA-Signature') or '').strip().lower()
    if not client_id or not ts_raw or not nonce or not sig:
        return jsonify({'ok': False, 'error': 'missing_auth_headers'}), 401

    try:
        ts = int(ts_raw)
    except Exception:
        return jsonify({'ok': False, 'error': 'bad_timestamp'}), 401

    max_skew = int(os.getenv('IA_MAX_SKEW_SECONDS', '300') or '300')
    now_i = int(time.time())
    if abs(now_i - ts) > max_skew:
        return jsonify({'ok': False, 'error': 'timestamp_out_of_range'}), 401

    try:
        clients = _get_ia_clients()
    except Exception as e:
        return jsonify({'ok': False, 'error': f'ia_config_error: {e}'}), 500

    secret = clients.get(client_id)
    if not secret:
        return jsonify({'ok': False, 'error': 'unknown_client'}), 403

    nonce_key = f'{client_id}:{nonce}'
    now_f = time.time()
    _cleanup_nonces(now_f)
    if nonce_key in _IA_SEEN_NONCES:
        return jsonify({'ok': False, 'error': 'replay_detected'}), 409

    expected = _build_signature(secret, ts_raw, nonce, raw_body)
    if not hmac.compare_digest(expected, sig):
        return jsonify({'ok': False, 'error': 'invalid_signature'}), 403
    _IA_SEEN_NONCES[nonce_key] = now_f

    try:
        payload = json.loads(raw_body)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_json_body'}), 400

    model = str(payload.get('model') or '').strip()
    max_output_tokens = int(payload.get('max_output_tokens') or 4000)
    input_payload = payload.get('input')
    text_payload = payload.get('text')

    metadata = payload.get('metadata') if isinstance(payload.get('metadata'), dict) else {}
    idcliente = payload.get('idcliente') if payload.get('idcliente') is not None else metadata.get('idcliente')
    opcion = (str(payload.get('opcion') or payload.get('task') or metadata.get('opcion') or metadata.get('task') or 'FACTURAS').strip() or 'FACTURAS').upper()
    archivo = str(
        payload.get('archivo_nombre')
        or payload.get('source_filename')
        or payload.get('filename')
        or payload.get('archivoNombre')
        or payload.get('file_name')
        or payload.get('archivo')
        or metadata.get('archivo_nombre')
        or metadata.get('source_filename')
        or metadata.get('filename')
        or metadata.get('archivoNombre')
        or metadata.get('file_name')
        or metadata.get('archivo')
        or request.headers.get('X-IA-Archivo-Nombre')
        or request.headers.get('X-IA-Source-Filename')
        or request.headers.get('X-IA-Filename')
        or request.headers.get('X-IA-File-Name')
        or ''
    ).strip()

    if not model:
        return jsonify({'ok': False, 'error': 'model_required'}), 400
    if not isinstance(input_payload, list):
        return jsonify({'ok': False, 'error': 'input_required'}), 400

    t0 = time.time()
    try:
        client = _get_ia_openai_client()
        req: Dict[str, Any] = {
            'model': model,
            'max_output_tokens': max_output_tokens,
            'input': input_payload,
        }
        if text_payload is not None:
            req['text'] = text_payload

        resp = client.responses.create(**req)
        output_text = _extract_output_text(resp)
    except Exception as e:
        dur_ms = max(0, int((time.time() - t0) * 1000))
        sql_err = _save_audit(idcliente, opcion, archivo, False, str(e), dur_ms)
        if sql_err:
            print(f'[AUDIT] {sql_err}')
            _append_audit_fallback(
                idcliente=idcliente,
                opcion=opcion,
                archivo=archivo,
                ok=False,
                error=str(e),
                duracion_ms=dur_ms,
                sql_error=sql_err,
            )
        return jsonify({'ok': False, 'error': f'openai_error: {e}'}), 500

    if not output_text:
        dur_ms = max(0, int((time.time() - t0) * 1000))
        sql_err = _save_audit(idcliente, opcion, archivo, False, 'empty_model_response', dur_ms)
        if sql_err:
            print(f'[AUDIT] {sql_err}')
            _append_audit_fallback(
                idcliente=idcliente,
                opcion=opcion,
                archivo=archivo,
                ok=False,
                error='empty_model_response',
                duracion_ms=dur_ms,
                sql_error=sql_err,
            )
        return jsonify({'ok': False, 'error': 'empty_model_response'}), 502

    dur_ms = max(0, int((time.time() - t0) * 1000))
    sql_err = _save_audit(idcliente, opcion, archivo, True, '', dur_ms)
    if sql_err:
        print(f'[AUDIT] {sql_err}')
        _append_audit_fallback(
            idcliente=idcliente,
            opcion=opcion,
            archivo=archivo,
            ok=True,
            error='',
            duracion_ms=dur_ms,
            sql_error=sql_err,
        )

    return jsonify({'ok': True, 'model': model, 'output_text': output_text}), 200


@app.route('/api/ping')
def ping():
    return jsonify({
        'status': 'success',
        'message': 'pong',
        'time': datetime.now().isoformat(),
        'error': False
    })


@app.route('/api/test')
def test():
    return 'Servidor funcionando!'


@app.route('/api/serie/<string:codigo>')
@validate_api_key
def serie(codigo):
    """
    Devuelve un numero de serie valido para claves de registro alfa
    """
    nro_serie = ""
    for num in codigo[:: -1]:
        nro_serie += str(int(ord(num)) + codigo.__len__()).zfill(3)

    return jsonify({'serie': "0-" + nro_serie + "-0"})


# Filtros Jinja personalizados
@app.template_filter()
def f_str_to_date(value):
    return datetime.strptime(value, '%d/%m/%Y').strftime('%Y-%m-%d')


# @app.after_request
# def after_request(response):
#     """
#     Esta funciÃƒÆ’Ã‚Â³n es vital para que funcione con Fetch de JS.
#     Valida la peticion Options
#     """
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     response.headers.add('Access-Control-Allow-Headers',
#                          'Content-Type, Authorization')
#     response.headers.add('Access-Control-Allow-Methods',
#                          'GET, PUT, POST, DELETE,OPTIONS ')
#     response.status_code = 200
#     return response


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

