from functions.general_customer import get_customer_response, exec_customer_sql
from functions.responses import set_response
from .master import MasterView
from flask_classful import route
from flask import request
from functions.Log import Log

class IngresosView(MasterView):
    def get(self):
        sql = """
        SELECT *
        FROM MV_INGRESOS
        WHERE format(Ingreso, 'yyyy-MM-dd') = format(getdate(),'yyyy-MM-dd')
        """
        
        # return set_response([], 200, sql)
        
        result, error = get_customer_response(sql, f" al obtener los ingresos del día.", True, self.token_global)

        response = set_response(result, 200 if not error else 404, "" if not error else result[0]['message'])
        
        if error:
            self.log({result}, "ERROR")
        
        return response
    

    def post(self):
        data = request.get_json()

        # Log.create(data, 'ERROR') # Dejo comentado el log original si no es necesario para el flujo normal

        apellido_nombre = data.get('apellido_nombre', '')
        ingreso = data.get('ingreso', '')
        egreso = data.get('egreso', '')
        observaciones = data.get('observaciones', '')
        adultos = data.get('adultos', '')
        menores = data.get('menores', '')
        jubilados = data.get('jubilados', '')
        parcela = data.get('parcela', '')
        dni = data.get('dni', '')
        nacionalidad = data.get('nacionalidad', '')
        direccion = data.get('direccion', '')
        modelo_vehiculo = data.get('modelo_vehiculo', '')
        ciudad = data.get('ciudad', '')
        patente = data.get('patente', '')
        bajada_lancha = data.get('bajada_lancha', '')
        amarre = data.get('amarre', '')
        trekking = data.get('trekking', '')
        kayak = data.get('kayak', '')
        embarcado = data.get('embarcado', '')
        subtotal = data.get('subtotal', 0)
        total = data.get('total', 0)
        
        # Campo nuevo
        egresar = data.get('egresar', False) # Asumo que puede ser un booleano o un valor que se evalúa como tal

        # Conversión de booleanos a 1 o 0
        bajada_lancha = 1 if bajada_lancha == True else 0
        amarre = 1 if amarre == True else 0
        trekking = 1 if trekking == True else 0
        kayak = 1 if kayak == True else 0
        embarcado = 1 if embarcado == True else 0
        
        # Obtener el timestamp actual para EgresoReal si se egresa
        import datetime
        egreso_real_actual = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # --- Lógica de SQL modificada ---
        
        # 1. Bloque de actualización/inserción de datos del cliente (MV_INGRESOS_CLIENTES)
        sql_cliente = f"""
            IF NOT EXISTS(SELECT 1 FROM MV_INGRESOS_CLIENTES WHERE dni='{dni}')
                BEGIN
                    INSERT INTO MV_INGRESOS_CLIENTES (ApellidoNombre, Dni, Nacionalidad, Direccion, ModeloVehiculo, Ciudad, Patente)
                    VALUES
                    ('{apellido_nombre}', '{dni}', '{nacionalidad}', '{direccion}', '{modelo_vehiculo}', '{ciudad}', '{patente}')
                END
            ELSE
                BEGIN
                    UPDATE MV_INGRESOS_CLIENTES SET 
                        ApellidoNombre = '{apellido_nombre}', 
                        Nacionalidad = '{nacionalidad}', 
                        Direccion = '{direccion}', 
                        ModeloVehiculo = '{modelo_vehiculo}', 
                        Ciudad = '{ciudad}', 
                        Patente = '{patente}' 
                    WHERE dni = '{dni}'
                END
        """

        # 2. Bloque de lógica de Ingreso/Egreso (MV_INGRESOS)
        if egresar:
            # Escenario 2: egresar es true -> Actualizar EgresoReal con fecha y hora actual
            sql_ingreso = f"""
                UPDATE MV_INGRESOS SET EgresoReal = '{egreso_real_actual}'
                WHERE Patente = '{patente}' 
                AND Dni = '{dni}' 
                AND Ingreso = '{ingreso}' 
                AND Parcela = {parcela} 
                AND EgresoReal IS NULL;
                
                SELECT 'Egreso actualizado.' AS Resultado;
            """
            mensaje_exito = "Egreso grabado con éxito."
        else:
            # Escenarios 1 y 3: egresar es false/0
            sql_ingreso = f"""
                -- Verificar si ya existe un registro activo (sin EgresoReal)
                IF NOT EXISTS(
                    SELECT 1 FROM MV_INGRESOS 
                    WHERE Patente = '{patente}' 
                    AND Dni = '{dni}' 
                    AND Ingreso = '{ingreso}' 
                    AND Parcela = {parcela} 
                    AND EgresoReal IS NULL
                )
                BEGIN
                    -- Escenario 3: No existe un registro activo, crear nuevo ingreso
                    INSERT INTO MV_INGRESOS (
                        ApellidoNombre, Ingreso, Egreso, Observaciones, Adultos, Menores, Jubilados,
                        Parcela, Dni, Nacionalidad, Direccion, ModeloVehiculo, Ciudad, Patente,
                        BajadaLancha, Amarre, Trekking, Kayak, Embarcado, SubTotal, Total
                    )
                    VALUES
                    (
                        '{apellido_nombre}', '{ingreso}', '{egreso}', '{observaciones}', {adultos}, {menores}, {jubilados},
                        {parcela}, '{dni}', '{nacionalidad}', '{direccion}', '{modelo_vehiculo}', '{ciudad}', '{patente}',
                        {bajada_lancha}, {amarre}, {trekking}, {kayak}, {embarcado}, {subtotal}, {total}
                    );
                    SELECT 'Ingreso creado.' AS Resultado;
                END
                ELSE
                BEGIN
                    -- Escenario 1: Ya existe un registro activo, evitar duplicado
                    SELECT 'Registro activo ya existe. No se creó un nuevo ingreso.' AS Resultado;
                END
            """
            mensaje_exito = "Ingreso grabado con éxito."
            
        # Combina los SQL para asegurar la actualización del cliente y luego la gestión de ingreso/egreso
        sql = sql_cliente + sql_ingreso

        # return set_response([], 200, sql) # Útil para depurar el SQL
        
        result, error = exec_customer_sql(sql, "al grabar el movimiento", self.token_global)

        if error:
            self.log({result}, "ERROR")
            return set_response(None, 404, f"Ocurrió un error al grabar el movimiento: \n{result}.")
        
        # Devuelve el mensaje de éxito basado en la operación realizada (ingreso o egreso)
        return set_response(result, 200, mensaje_exito)
    
    @route('/clientes', methods=['POST'])
    def upload_cliente(self):
        data = request.get_json()
    
        apellido_nombre = data.get('apellido_nombre', '')
        dni = data.get('dni', '')
        nacionalidad = data.get('nacionalidad', '')
        direccion = data.get('direccion', '')
        modelo_vehiculo = data.get('modelo_vehiculo', '')
        ciudad = data.get('ciudad', '')
        patente = data.get('patente', '')
        
        sql = f"""
        INSERT INTO MV_INGRESOS_CLIENTES (ApellidoNombre, Dni, Nacionalidad, Direccion, ModeloVehiculo, Ciudad, Patente)
        VALUES
        ('{apellido_nombre}', '{dni}', '{nacionalidad}', '{direccion}', '{modelo_vehiculo}', '{ciudad}', '{patente}')
        """

        # sql = "DELETE FROM MV_INGRESOS_CLIENTES"

        print(sql)
        # return set_response([], 200, "Cliente grabado con éxito.")
        
        result, error = exec_customer_sql(sql, "al grabar el cliente", self.token_global)

        if error:
            self.log({result}, "ERROR")
            return set_response(None, 404, f"Ocurrió un error al grabar el cliente: \n{result}.")
          
        return set_response(result, 200, "Cliente grabado con éxito.")
    
    @route('/clientes', methods=['GET'])
    def get_cliente_por_dni(self):
        dni = request.args.get('dni', '').strip()

        if not dni:
            return set_response([], 200, "")

        sql = f"""
        IF COL_LENGTH('MV_Ingresos_Clientes', 'Telefono') IS NULL
        BEGIN
            SELECT TOP (1) [Id]
                ,[ApellidoNombre]
                ,[Dni]
                ,[Nacionalidad]
                ,[Direccion]
                ,[ModeloVehiculo]
                ,[Ciudad]
                ,[Patente]
            FROM MV_Ingresos_Clientes
            WHERE Dni = '{dni}'
        END
        ELSE
        BEGIN
            SELECT TOP (1) [Id]
                ,[ApellidoNombre]
                ,[Dni]
                ,[Nacionalidad]
                ,[Direccion]
                ,[ModeloVehiculo]
                ,[Ciudad]
                ,[Patente]
                ,[Telefono]
            FROM MV_Ingresos_Clientes
            WHERE Dni = '{dni}'
        END
        """

        result, error = get_customer_response(sql, "al obtener cliente.", True, self.token_global)
        response = set_response(result, 200 if not error else 404, "" if not error else result[0]['message'])

        if error:
            self.log({result}, "ERROR")

        return response

    @route('/precios', methods=['GET'])
    def get_precios(self):
                    
        sql = f"""
        SELECT CLAVE, VALOR
        FROM TA_CONFIGURACION
        WHERE CLAVE LIKE 'ING_%'
        """
                                                                    
        # sql = f"""
		# SELECT CLAVE, VALOR
        # FROM TA_CONFIGURACION
        # WHERE CLAVE = 'ING_BAJADALANCHA'
        # OR CLAVE = 'ING_MAYOR'
        # OR CLAVE = 'ING_MENOR'
        # OR CLAVE = 'ING_JUBILADO'
        # """


        # return set_response([], 200, sql)
        
        result, error = get_customer_response(sql, f" al obtener los precios .", True, self.token_global)
        response = set_response(result, 200 if not error else 404, "" if not error else result[0]['message'])
        
        if error:
            self.log({result}, "ERROR")
        
        return response
        
