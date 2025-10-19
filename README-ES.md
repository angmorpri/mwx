# MWX
Herramienta QoL para la aplicación "MiBilletera" de Android.

Proporciona un modelo de datos para manipular toda la información de la app desde scripts y programas en Python.



## Modelo de datos

Todos los datos de MiBilletera son representados mediante 3 entidades principales (`Account`, `Category`, `Entry`) y 2 auxiliares (`Counterpart`, `Note`).

### Clase base

Todas las entidades heredan de la clase base `_MWXBaseModel`. Ésta define:

* **Identificador de MiBilletera**, `mwid`. Es el identificador numérico de la entidad en la app. En caso de una nueva entidad no registrada aun en MiBilletera, su valor será `-1`. En caso de entidades que no usan ID de MiBilletera, su valor será `0`.
* **Comparación** (`__eq__` y `__lt__`).
* **Representación** (`__repr__`).

Y requiere definir en las subclases:

* **Identificador unívoco**, `id`. Debe ser un identificador textual unívoco de la entidad en **todo** el modelo de datos. Será usado para los métodos de comparación y representación.

### `Account`

Representa una cuenta contable, almacén físico o lógico de dinero.

* **`id`** se forma mediante `order` y `name`.
* **`name`**, nombre de la cuenta. **NO** puede contener espacios en blanco, y la primera letra debe ser mayúscula.
* **`order`**, indicador numérico del orden de representación en la interfaz de MiBilletera.
* **`color`**, color asociado a la cuenta, debe tener formato `##RRGGBB`.
* **`is_visible`**, indica si aparece visible (`True`) u oculta (`False`) en la interfaz de MiBilletera.
* **`is_legacy`**, indica si es una cuenta _legado_, es decir, que ya no está en uso, pero sigue habiendo entradas que la utilizan.