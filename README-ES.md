# MWX
Herramienta QoL para la aplicación "MiBilletera" de Android.

Proporciona un modelo de datos para manipular toda la información de la app desde scripts y programas en Python.



## Modelo de datos

Todos los datos de MiBilletera son representados mediante 4 entidades: `Account`, `Counterpart`, `Category`, `Entry`.

#### Clase base

Todas las entidades heredan de la clase base `_MWXBaseModel`. Ésta define:

* **Identificador de MiBilletera**, `mwid`. Es el identificador numérico de la entidad en la app. En caso de una nueva entidad no registrada aun en MiBilletera, su valor será `-1`. En caso de entidades que no usan ID de MiBilletera, su valor será `0`.
* **Comparación** (`__eq__` y `__lt__`).
* **Representación** (`__repr__`).

Y requiere definir en las subclases:

* **Lave de comparación**, `sorting_key`. Debe ser una clave que permita comparar entidades del **todo** el modelo de datos (incluso entre entidades distintas).
* Métodos `to_dict()` y `to_mywallet()`, para representar en formato JSON y en formato MiBilletera, respectivamente.

### Entidades principales

#### `Account`

Representa una cuenta contable, almacén físico o lógico de dinero.

* **`sorting_key`**, se forma mediante `order` y `name`.
* **`name`**, nombre de la cuenta. **NO** puede contener espacios en blanco, y la primera letra debe ser mayúscula.
* **`@repr_name`**, nombre de la cuenta para su representación.
* **`order`**, indicador numérico del orden de representación en la interfaz de MiBilletera. Debe estar entre 1 y 999.
* **`color`**, color asociado a la cuenta, debe tener formato `#RRGGBB`. Las cuentas sin color tendrán el `#000000`.
* **`is_visible`**, indica si aparece visible (`True`) u oculta (`False`) en la interfaz de MiBilletera. Por defecto, serán visibles.
* **`is_legacy`**, indica si es una cuenta _legado_, es decir, que ya no está en uso, pero sigue habiendo entradas que la utilizan.

Define un atributo de clase, `_GLOBAL_ORDER`, para mantener cuál es el mayor índice de orden, en caso de que tenga que asignar uno nuevo por defecto.

#### `Counterpart`

Contraparte de un ingreso o un gasto, es decir, pagador, o pagado.

* **`sorting_key`**, se formará mediante la tupla (999, `name`).
* **`name`**, nombre de la contraparte.
* **`@repr_name`**, igual que `name`, definido para que sea compatible con `Account`.

#### `Category`

Representa una categoría contable, en la que se puede clasificar cada entrada.

* **`sorting_key`**, es equivalente a su código (`code`).
* **`code`**, es el código identificativo de la categoría. Se compone de una letra mayúscula seguida de dos dígitos.
* **`name`**, es el nombre de la categoría.
* **`@repr_name`**, nombre de la categoría para su representación. Toma la forma "`<code>. <name>`".
* **`type`**, indica el tipo de entrada al que representa: 0 = traslado; -1 = gasto; +1 = ingreso. Es **inmutable**.
* **`icon_id`**, identificador numérico del icono identificativo de la categoría en la interfaz de MiBilletera. Debe estar entre 0 y 99, siendo el 0 reservado para categorías sin icono.
* **`color`**, color asociado a la categoría, debe tener formato `#RRGGBB`. Las categorías sin color tendrán el `#000000`.
* **`is_legacy`**, indica si es una categoría *legado*, es decir, que ya no está en uso, pero sigue habiendo entradas que la utilizan.

#### `Entry`

Representa una entrada contable, una cantidad de dinero que en una fecha exacta entra, sale o se mueve entre cuentas y contrapartes, es categorizable, y posee un concepto claro.

* **`sorting_key`**, está compuesto de `date`, `mwid` y un valor aleatorio.
* **`amount`**, cantidad de dinero en movimiento. Siempre es un valor positivo que debe estar ajustado a dos decimales.
* **`date`**, fecha exacta en la que sucede el movimiento. Debe ser un `datetime` con año, mes y día.
* **`type`**, tipo de entrada, que puede ser: 0 = traslado, -1 = gasto; +1 = ingreso. Es **inmutable**.
* **`source`**, origen del movimiento. Si es una cuenta (`Account`), hablamos de un gasto o traslado; si es una contraparte (`Counterpart`), hablamos de un ingreso o traslado. Debe respetar el tipo de entrada. Nunca puede ser contraparte si el destino es contraparte. Nunca puede ser igual que `target`.
* **`target`**, destino del movimiento. Si es una cuenta (`Account`), hablamos de un ingreso o traslado; si es una contraparte (`Counterpart`), hablamos de un gasto o traslado. Debe respetar el tipo de entrada. Nunca puede ser contraparte si el origen es contraparte. Nunca puede ser igual que `source`.
* **`category`**, categoría asociada a la entrada. Debe ser tipo `Category`, siendo el tipo de ésta igual al de la entrada.
* **`item`**, concepto de la entrada, en forma de cadena de caracteres. Si fuera a ser nulo, debería sustituirse por "Sin concepto".
* **`details`**, detalles adicionales opcionales, en forma de cadena de caracteres.
* **`is_bill`**, indica si es una entrada que provino de una factura recurrente.

Define, además, los siguientes métodos:

* **`has_account(account)`**, devuelve `True` si la entrada tiene, como origen o destino, la cuenta `account`, que puede ser un objeto tipo `Account`, o el nombre de una cuenta.
* **`flow(account)`**, devuelve +1, 0 o -1, en función de hacia dónde viaja el flujo de dinero de la entrada respecto a la cuenta `account`. Si `account` no es una cuenta de esta entrada, se devuelve 0; en cualquier otro caso, siempre se devolverá -1 o +1.

## ETL

El proceso de ETL se divide en **lectura** (`read()`) y **escritura** (`write()`).

#### `read(path: str | Path) -> MWXNamespace`

Lee del archivo SQLite indicado por `path`, que debe tener formato de archivo de backup de MiBilletera. Devuelve un `MWXNamespace`, un espacio de nombres que contiene cuatro listas, una por entidad: `accounts`, `counterparts`, `categories` y `entries`.

#### `write(path: str | Path, data: MWXNamespace) -> None`

Sobrescribe el archivo SQLite indicado por `path`, que debe tener formato de archivo de backup de MiBilletera, con los datos en `data`, que deben tener formato `MWXNamespace`.

Automáticamente gestiona:

* **Nuevas entidades**, todas aquéllas que tengan `mwid` igual a `-1`.
* **Entidades a eliminar**, todas aquéllas que existan en su tabla respectiva, pero cuyo `mwid` no esté en el modelo.
* **Entidades erróneas**, todas aquéllas cuyo `mwid` no exista ya en su tabla respectiva, serán ignoradas y se informará al usuario.

