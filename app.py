from flask import Blueprint, Flask, jsonify

from flask_cors import CORS
from flask_mail import Mail
from datetime import datetime

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


app = Flask(__name__)

app.config.from_object(AppConfig)


mail = Mail(app)

api_cors_config = {
    "origins": "*",
    "methods": ["OPTIONS", "GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Authorization", "Content-Type"]
}

CORS(app, resources={"/api/*": api_cors_config},
     supports_credentials=True)


API_PREFIX_V3 = '/api/v3/'
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
# ViewProduct.register(app, route_base=f'{API_PREFIX_V3}/product')
# ViewCustomer.register(app, route_base=f'{API_PREFIX_V3}/customer')
# ViewAccount.register(app, route_base=f'{API_PREFIX_V3}/account')
# ViewProducts.register(app, route_base=f'{API_PREFIX_V3}/products')
# ViewAuth.register(app, route_base=f'{API_PREFIX_V3}/auth')
# ViewRegister.register(app, route_base=f'{API_PREFIX_V3}/register')
# ViewSession.register(app, route_base=f'{API_PREFIX_V3}/session')
# ViewSeller.register(app, route_base=f'{API_PREFIX_V3}/seller')
# ViewBrand.register(app, route_base=f'{API_PREFIX_V3}/brand')
# ViewCategory.register(app, route_base=f'{API_PREFIX_V3}/category')
# ViewUnit.register(app, route_base=f'{API_PREFIX_V3}/unit')
# ViewStock.register(app, route_base=f'{API_PREFIX_V3}/stock')
# ViewFamily.register(app, route_base=f'{API_PREFIX_V3}/family')
# ViewChromeExtension.register(app, route_base=f'{API_PREFIX_V3}/extension')
# ViewConfiguration.register(app, route_base=f'{API_PREFIX_V3}/configuration')
# ViewMenu.register(app, route_base=f'{API_PREFIX_V3}/menu')
ViewTransmisionCodigosZonas.register(app,route_base=f'{API_PREFIX_V3}/transmision_codigos')
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
#     Esta función es vital para que funcione con Fetch de JS.
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
