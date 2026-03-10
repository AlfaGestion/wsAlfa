# Manual operativo de arquitectura para `wsAlfa`

## 1. Objetivo

Este documento baja a tierra cómo organizar `wsAlfa` sin romper lo existente, tomando como criterio principal separar:

- lo legacy que ya está en producción
- lo nuevo que pertenece a Alfa Gestión Web
- la lógica reusable fuera de las rutas

## 2. Definición práctica de legacy

En este proyecto, `legacy` significa:

- rutas o contratos ya consumidos por clientes reales
- partes que usa ALFA Go o la web actual
- código que no conviene rediseñar agresivamente porque puede romper compatibilidad

No significa “malo”. Significa “hay que tocarlo con cuidado”.

## 3. Regla principal de decisión

Antes de crear algo nuevo, responder:

1. ¿Esto lo consume la app móvil, la web o ambos?
2. ¿Es una extensión chica de algo existente o un módulo nuevo?
3. ¿Necesita compatibilidad con contratos actuales?
4. ¿Puede nacer con diseño limpio?

## 4. Qué queda dónde

## `routes/v1`
- mantenimiento
- compatibilidad vieja
- sin módulos nuevos grandes

## `routes/v2`
- contratos existentes usados por móvil o web actual
- fixes y ampliaciones chicas
- no usar como destino de módulos nuevos grandes

## `routes/v3`
- solo si realmente es una nueva versión del mismo contrato
- no usar como “cajón” de funcionalidades nuevas

## `routes/AGW/V1`
- todo módulo nuevo propio de Alfa Gestión Web
- conciliación de tarjetas
- importación bancaria
- dashboards nuevos de web
- flujos asistidos por IA
- integraciones de web que no necesitan heredar deuda de `v2`

## 5. Estructura recomendada de crecimiento

```text
wsAlfa/
  routes/
    v1/
    v2/
    v3/
    AGW/
      V1/
        router.py
        cliente_id_bp.py
        card_reconciliation.py

  services/
    card_reconciliation_service.py
    card_pdf_service.py
    bank_rules_service.py

  repositories/
    card_reconciliation_repository.py
    mv_asientos_repository.py
    conciliacion_aux_repository.py

  parsers/
    bank_liquidations/
      base_parser.py
      visa_parser.py
      mastercard_parser.py
      amex_parser.py

  functions/
    ... legado compartido actual ...
```

## 6. Qué va en cada capa

## `routes`
Solo:
- request
- validación de parámetros
- llamada al servicio
- armado de response

No debería contener:
- SQL complejo
- matching
- parsing de PDF grande
- lógica de conciliación

## `services`
Acá vive la lógica de negocio.

Ejemplos:
- crear conciliación
- analizar PDFs
- inferir banco/adquirente
- decidir períodos
- correr matching
- preparar sugerencias

## `repositories`
Acá vive el acceso a datos.

Ejemplos:
- leer `MV_ASIENTOS`
- grabar `MV_CONCILIACION`
- grabar `MV_CONCILIACION_AUX`
- confirmar `MV_CONCILIACION_Cpte_AUX`
- actualizar `MV_ASIENTOS`

## `parsers`
Acá vive la lectura específica de PDFs.

Ejemplos:
- parser Visa
- parser Mastercard
- parser Amex
- parser genérico

## 7. Aplicación concreta a conciliación de tarjetas

## Ruta recomendada
- `routes/AGW/V1/card_reconciliation.py`

## Servicios sugeridos
- `services/card_reconciliation_service.py`
- `services/card_pdf_service.py`

## Repositorios sugeridos
- `repositories/card_reconciliation_repository.py`
- `repositories/card_reconciliation_aux_repository.py`
- `repositories/mv_asientos_repository.py`

## Parsers sugeridos
- `parsers/bank_liquidations/base_parser.py`
- `parsers/bank_liquidations/visa_parser.py`
- `parsers/bank_liquidations/mastercard_parser.py`

## 8. Endpoints sugeridos para conciliación

Bajo `AGW/V1`:

- `POST /AGW/V1/card-reconciliation/analyze-pdfs`
- `POST /AGW/V1/card-reconciliation/create`
- `POST /AGW/V1/card-reconciliation/{id}/load-system`
- `POST /AGW/V1/card-reconciliation/{id}/import-bank-movements`
- `POST /AGW/V1/card-reconciliation/{id}/match`
- `POST /AGW/V1/card-reconciliation/{id}/confirm`
- `GET /AGW/V1/card-reconciliation/{id}`

## 9. Política de migración sin romper nada

No mover masivamente lo legacy.

La estrategia recomendada es:

1. dejar `v1/v2/v3` como están para compatibilidad
2. todo módulo nuevo nace en `AGW/V1`
3. cuando haga falta reutilizar lógica legacy, encapsularla en servicios o repositorios
4. evitar seguir metiendo dominios nuevos en `v2`

## 10. Regla práctica para el día a día

## Si el endpoint ya existe o es una mejora chica
- tocar `v2` o `v3`

## Si es un dominio nuevo de web
- crear en `AGW/V1`

## Si la lógica se puede reutilizar
- extraer a `services` o `repositories`

## Si el cambio es solo para compatibilidad
- dejarlo dentro del espacio legacy correspondiente

## 11. Ejemplo concreto de decisión

## Caso: conciliación de tarjetas
- no pertenece a ALFA Go
- es un dominio nuevo
- es propio de web
- necesita crecer con parsers, matching y reglas por banco

Conclusión:
- debe vivir en `AGW/V1`
- no conviene seguir desarrollándolo dentro de `v2`

## 12. Resumen ejecutivo

La regla de trabajo es esta:

- `v1/v2/v3` = compatibilidad y mantenimiento
- `AGW/V1` = crecimiento nuevo de Alfa Gestión Web
- `services/repositories/parsers` = base profesional para crecer sin mezclar responsabilidades