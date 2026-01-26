import os
from .master import MasterView
from flask_classful import route
from functions.responses import set_response
from functions.general_customer import exec_customer_sql, exec_update_db
# from rich import print


class DatabaseView(MasterView):
    BASE_DIR = os.path.dirname(os.path.abspath(__name__))

    @route('/update', methods=['POST'])
    def update_database(self):
        has_error = False
        path = os.path.join('sql', 'v2', 'Stores_alfaweb.sql')
        path_to_sql_file = os.path.join(self.BASE_DIR, path)

        try:
            with open(path_to_sql_file, 'r') as file:
                data = file.read()

            # data = data.replace('GO', '')
        except Exception as e:
            self.log(f"Error al actualizar la base de datos desde archivo sql: {e}")
            has_error = True

        if has_error:
            return set_response([], 500, 'Error al leer archivo de actualización de base de datos')

        if not data:
            return set_response([], 500, 'No hay datos en el archivo de actualización de base de datos')

        # print(data)
        try:
            result, has_error = exec_update_db(data, self.token_global)
        except Exception as r:
            has_error = True

        if has_error:
            self.log("Error al actualizar la base de datos" + str(result))
            return set_response(result, 500, "No se actualizar la base de datos.")
        # result = []
        return set_response(result, 404, "Base de datos actualizada.")
