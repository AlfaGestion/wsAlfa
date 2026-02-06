from datetime import datetime
from flask import request
from functions.general_customer import exec_customer_sql, get_customer_response
from functions.responses import set_response
from flask_classful import route
from routes.v2.master import MasterView
from rich import print


class ViewOrder(MasterView):
    def _normalize_datetime(self, value) -> str:
        if not value:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")

        s = str(value).strip()
        for fmt in [
            "%d/%m/%Y %H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y%m%d%H%M%S",
            "%Y%m%d",
        ]:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        for fmt in ["%d/%m/%Y", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime("%Y-%m-%d 00:00:00")
            except ValueError:
                pass

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _normalize_marker(self, marker: str, max_len: int = 20) -> str:
        if not marker:
            return ""
        return marker[:max_len]

    def _order_exists(self, marker: str, tc: str, account: str) -> bool:
        if not marker:
            return False

        safe_marker = marker.replace("'", "''")
        safe_tc = (tc or "NP").strip().upper()
        safe_account = (account or "").replace("'", "''")
        sql = f"SELECT TOP 1 ID FROM V_MV_CPTE WHERE TC='{safe_tc}' AND CUENTA='{safe_account}' AND TRANSPORTE_NOMBRE='{safe_marker}'"
        result, error = get_customer_response(sql, "validar pedido duplicado", True, self.token_global)
        return (not error) and len(result) > 0

    def post(self):
        orders = request.get_json()
        result = []

        for order in orders:

            account = order.get('account', '')
            date_raw = order.get('date', datetime.now().strftime('%d/%m/%Y'))
            date = self._normalize_datetime(date_raw)
            seller = order.get('seller', '')
            lat = order.get('lat', '0')
            lng = order.get('lng', '0')
            tc_invoice = order.get('type', '')
            obs = order.get('obs', '')
            sale_condition = order.get('condition', '')
            tc = order.get('tc', 'NP')
            tc = (tc or 'NP').strip().upper()
            external_id = order.get('externalId', '') or order.get('external_id', '') or order.get('id', '')
            transporte_nombre = order.get('TRANSPORTE_NOMBRE', '') or order.get('transporte_nombre', '') or order.get('transporteNombre', '')
            seller_name = order.get('sellerName', '') or ''
            device_model = order.get('deviceModel', '') or ''

            marker = ""
            if transporte_nombre:
                marker = transporte_nombre
            elif external_id:
                seller_tag = seller.strip() if seller else ""
                if seller_tag and not str(external_id).startswith(f"{seller_tag}-"):
                    marker = f"{seller_tag}-{external_id}"
                else:
                    marker = f"{external_id}"

            marker = self._normalize_marker(marker)

            if marker and self._order_exists(marker, tc, account):
                self.log(f"Pedido duplicado omitido. Marker: {marker}")
                continue

            safe_obs = (obs or "").replace("'", "''")
            if len(safe_obs) > 250:
                safe_obs = safe_obs[:250]

            sql = f"""
            DECLARE @pRes INT
            DECLARE @pMensaje NVARCHAR(250)
            DECLARE @pIdCpte INT

            set nocount on; EXEC sp_web_V_MV_CPTE '{account}','{seller}','{date}','{safe_obs}','{lat}','{lng}','{tc}',@pRes OUTPUT, @pMensaje OUTPUT,@pIdCpte OUTPUT

            SELECT @pRes as pRes, @pMensaje as pMensaje, @pIdCpte pIdCpte
            """

            try:
                result, error = exec_customer_sql(sql, " al grabar los pedidos", self.token_global, True)
            except Exception as r:
                error = True

            if error:
                self.log(str(result[0]['message']) + "\nSENTENCIA : " + sql)
                return set_response(None, 404, "OcurriÃ³ un error al grabar el pedido.")

            result_code = result[0][0]
            if result_code != 11:
                self.log(str(result[0][1]) + "\nSENTENCIA : " + sql)
                return set_response(None, 404, result[0][1])

            result_id_invoice = result[0][2]
            if marker:
                safe_marker = marker.replace("'", "''")
                sql_transporte = f"UPDATE V_MV_CPTE SET TRANSPORTE_NOMBRE='{safe_marker}' WHERE ID={result_id_invoice}"
                exec_customer_sql(sql_transporte, " al actualizar transporte del pedido", self.token_global, False)

            try:
                safe_seller = (seller or '').strip()
                safe_name = (seller_name or '').strip()
                if not safe_name and safe_seller:
                    sql_vdor = f"SELECT LTRIM(nombre) FROM V_TA_VENDEDORES WHERE LTRIM(idvendedor)='{safe_seller}'"
                    vdor_rows, vdor_err = exec_customer_sql(sql_vdor, " al obtener el nombre del vendedor", self.token_global, True)
                    if not vdor_err and vdor_rows:
                        safe_name = (vdor_rows[0][0] or "").strip()
                usuario = f"{safe_seller} - {safe_name}".strip(" -")
                usuario = usuario[:255]
                pc = (device_model or '').strip()[:255]

                sql_cp = f"SELECT IDCOMPROBANTE, FECHAHORA_GRABACION FROM V_MV_CPTE WHERE ID = {result_id_invoice}"
                cpte_rows, cpte_err = exec_customer_sql(sql_cp, " al obtener idcomprobante", self.token_global, True)
                idcomprobante = cpte_rows[0][0] if not cpte_err and cpte_rows else result_id_invoice
                fecha_grabacion = cpte_rows[0][1] if not cpte_err and cpte_rows else None
                safe_fecha = (date or "").replace("'", "''")
                safe_fecha_grab = str(fecha_grabacion).replace("'", "''") if fecha_grabacion else ""
                fecha_sql = (
                    f"CASE "
                    f"WHEN ISDATE('{safe_fecha_grab}') = 1 THEN CONVERT(DATETIME,'{safe_fecha_grab}',121) "
                    f"WHEN ISDATE('{safe_fecha}') = 1 THEN CONVERT(DATETIME,'{safe_fecha}',103) "
                    f"ELSE GETDATE() END"
                )
                fecha_cp_sql = (
                    f"CASE WHEN ISDATE('{safe_fecha}') = 1 THEN CONVERT(DATETIME,'{safe_fecha}',103) "
                    f"ELSE GETDATE() END"
                )
                safe_cuenta = (account or '').replace("'", "''")
                raw_lat = str(lat).strip()
                raw_lng = str(lng).strip()
                has_coords = raw_lat not in ['', '0', '0.0'] and raw_lng not in ['', '0', '0.0']
                safe_lat = raw_lat.replace("'", "''") if has_coords else "SIN_PERMISO"
                safe_lng = raw_lng.replace("'", "''") if has_coords else ""

                sql_accion = f"""
                INSERT INTO V_MV_CPTEACCIONES
                (TC, IDCOMPROBANTE, IDCOMPLEMENTO, TIPO_ACCION, FECHAHORA, USUARIO, PC, SYSTEMUSER, CUENTA, PROCESO, PROCESOLOTE, FECHA)
                VALUES
                ('{tc}', '{idcomprobante}', 0, 'UB', {fecha_sql}, '{usuario}', '{pc}', 'APP AlfaGo - Ubicacion actual', '{safe_cuenta}', '{safe_lat}', '{safe_lng}', {fecha_cp_sql})
                """
                exec_customer_sql(sql_accion, " al grabar la ubicacion del comprobante", self.token_global, False)
            except Exception as _err:
                self.log(_err)

            if lat != '0' and lng != '0':
                sql_coords = f"UPDATE MA_CUENTASADIC SET X='{lat}', Y='{lng}' WHERE CODIGO='{account}'"
                # Usamos False en el último parámetro para que no espere un SELECT de vuelta
                exec_customer_sql(sql_coords, " al actualizar coordenadas del cliente", self.token_global, False)

            # Actualizo la condicion de venta y el tipo de comprobante a generar
            if tc_invoice or sale_condition:
                if sale_condition == 'contado':
                    sale_condition = '   1'
                if sale_condition == 'ctacte':
                    sale_condition = '  10'

                if tc_invoice == 'fp':
                    tc_invoice = 'Proforma'
                if tc_invoice == 'fc':
                    tc_invoice = 'Factura'

                if sale_condition:
                    sql = f"UPDATE V_MV_CPTE SET IDCOND_CPRA_VTA='{sale_condition}',comentarios='{tc_invoice}' WHERE ID={result_id_invoice}"
                else:
                    sql = f"UPDATE V_MV_CPTE SET comentarios='{tc_invoice}' WHERE ID={result_id_invoice}"

                result, error = exec_customer_sql(sql, " al actualizar los datos de condicion de venta y tipo de comprobante", self.token_global, False)

            # Actualizo la condicion de venta y el tipo de comprobante a generar
            if tc_invoice or sale_condition:
                if sale_condition == 'contado':
                    sale_condition = '   1'
                if sale_condition == 'ctacte':
                    sale_condition = '  10'

                if tc_invoice == 'fp':
                    tc_invoice = 'Proforma'
                if tc_invoice == 'fc':
                    tc_invoice = 'Factura'

                if sale_condition:
                    sql = f"UPDATE V_MV_CPTE SET IDCOND_CPRA_VTA='{sale_condition}',comentarios='{tc_invoice}' WHERE ID={result_id_invoice}"
                else:
                    sql = f"UPDATE V_MV_CPTE SET comentarios='{tc_invoice}' WHERE ID={result_id_invoice}"

                result, error = exec_customer_sql(sql, " al actualizar los datos de condicion de venta y tipo de comprobante", self.token_global, False)

            for item in order.get('items', []):
                product = item.get('product', '')
                quantity = item.get('quantity', 0)
                amount = item.get('amount', 0)
                dto = item.get('dto', 0)
                bultos = item.get('bultos', 0)
                if bultos == 'None' or bultos is None:
                    bultos = 0

                if dto == 'None' or dto is None:
                    dto = 0

                sql = f"""
                DECLARE @pRes INT
                DECLARE @pMensaje NVARCHAR(250)
                DECLARE @pIdCpte INT
                EXEC sp_web_CpteInsumosV2 {result_id_invoice},'{product}',{quantity},{bultos},{amount},{dto},@pRes OUTPUT, @pMensaje OUTPUT,@pIdCpte OUTPUT
                SELECT @pRes as pRes, @pMensaje as pMensaje, @pIdCpte pIdCpte
                """

                try:
                    result, error = exec_customer_sql(sql, f" al grabar el detalle del pedido", self.token_global)
                except Exception as f:
                    error = True

                if error:
                    self.log(str(result[0]['message']) + "\nSENTENCIA : " + sql)
                    self.__delete_order_on_error(result_id_invoice, tc)
                    return set_response(None, 404, "OcurriÃ³ un error al grabar el detalle del pedido. Intente nuevamente.")

        response = set_response([], 200, "Pedidos grabados correctamente.")
        return response

    @route('/detail/<string:tc>/<string:invoice>', methods=['GET'])
    def get_detail_order(self, tc: str, invoice: str):

        sql = f"""
        SELECT convert(varchar,convert(decimal(15,2),isnull(a.importe,0))) as total_comprobante,CONVERT(NVARCHAR(10),a.fecha,103) as fecha,a.cuenta,a.nombre,a.tc,a.idcomprobante,ltrim(b.idarticulo) as idarticulo,b.descripcion,
        convert(varchar,convert(decimal(15,2),isnull(b.cantidad,0))) as cantidad,
        convert(varchar,convert(decimal(15,2),isnull(b.importe,0))) as importe,
        convert(varchar,convert(decimal(15,2),isnull(b.total,0))) as total
        FROM V_MV_CPTE a LEFT JOIN V_MV_CPTEINSUMOS b on a.tc = b.tc and a.idcomprobante = b.idcomprobante 
        WHERE a.tc='{tc}' and a.idcomprobante='{invoice}'
        """

        result, error = get_customer_response(sql, f" al obtener el detalle del pedido {invoice}", True, self.token_global)
        response = set_response(result, 200 if not error else 404, "" if not error else result[0]['message'])

        return response

    @route('/search', methods=['POST'])
    def search_payments(self):
        data = request.get_json()

        seller = data.get('seller', '')
        fhd = data.get('dateFrom', datetime.now().strftime('%Y%m%d'))
        fhh = data.get('dateUntil', datetime.now().strftime('%Y%m%d'))

        fecha_desde = datetime.strptime(fhd, '%Y%m%d').strftime('%d/%m/%Y')
        fecha_hasta = datetime.strptime(fhh, '%Y%m%d').strftime('%d/%m/%Y')

        sql = f"sp_web_getComprobantes 'NP','{seller}','{fecha_desde}','{fecha_hasta}','',0"

        result, error = get_customer_response(sql, f" al obtener los pedidos", True, self.token_global)

        response = set_response(result, 200 if not error else 404, "" if not error else result[0]['message'])
        return response

    def __delete_order_on_error(self, cpte_id: str, tc: str):
        safe_tc = (tc or 'NP').strip().upper()
        query = f"""
        DELETE FROM V_MV_CPTEINSUMOS WHERE TC = '{safe_tc}' AND IDCOMPROBANTE = '{cpte_id}';
        DELETE FROM V_MV_CPTE WHERE ID = {cpte_id};
        """

        response = self.get_response(query, f"Ocurri? un error al eliminar el comprobante", False, True)
