# Laboratorio — Causas de mortalidad mundial 2017

Aplicación desarrollada en **Python + Streamlit + Pandas + Plotly** para limpiar,
preparar, analizar y visualizar el dataset de causas de fallecimiento.

## 1. Estructura del proyecto

```text
causas_mortalidad_streamlit/
├── app.py
├── dataset_final_causas_GBD2017.xlsx
├── requirements.txt
└── README.md
```

## 2. Ejecución local

Crear un entorno virtual:

```bash
python -m venv .venv
```

Activarlo en Windows:

```powershell
.venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar:

```bash
streamlit run app.py
```

La aplicación se abrirá en el navegador.

## 3. Comportamiento automático del dataset

La aplicación **no depende de que el encabezado esté en la primera fila física
del Excel**.

Busca automáticamente la primera fila que contiene `id_causa`, la utiliza como
encabezado y procesa todas las filas posteriores que tengan identificador.

Por tanto, si el archivo cambia a:

- 169 registros
- 200 registros
- 500 registros
- encabezado en la fila 1, 2, 3, etc.

la aplicación se adapta sin modificar el código, siempre que conserve las
columnas requeridas.

También se puede cargar un XLSX, XLS o CSV desde la barra lateral.

## 4. Proceso de preparación

El código realiza:

1. Detección automática de encabezados.
2. Normalización de nombres de columnas.
3. Eliminación de columnas completamente vacías.
4. Eliminación de filas sin `id_causa`.
5. Conversión de variables numéricas.
6. Limpieza de campos de texto.
7. Cálculo de:
   - `participacion_pct`
   - `variacion_pp`
   - `abs_variacion_pp`
   - `ranking_calculado`
8. Validación de columnas obligatorias.
9. Aplicación de filtros interactivos.
10. Exportación del dataset procesado.

## 5. Visualizaciones

### Visualización 1 — Top de causas

Gráfico de barras horizontal. Permite identificar rápidamente cuáles son las
causas con mayor participación en la mortalidad de 2017.

### Visualización 2 — Magnitud vs. evolución

Gráfico de dispersión.

- Eje X: variación 2010–2017.
- Eje Y: participación de muertes en 2017.
- Tamaño: participación.
- Color: grupo GBD.

Es la visualización más importante para responder conjuntamente a las dos
preguntas del laboratorio: **qué causas tienen mayor peso y si aumentan o
disminuyen**.

### Visualización 3 — Grupos GBD

Compara la participación acumulada de:

- Enfermedades no transmisibles.
- Enfermedades transmisibles, maternas, neonatales y nutricionales.
- Lesiones.

### Visualización 4 — Tendencia

Compara las causas clasificadas como aumento y descenso.

### Tablas de apoyo

Se muestran las 10 causas con mayores aumentos y las 10 con mayores descensos.

## 6. Enriquecimiento de datos

El dataset incorpora clasificación y trazabilidad de GBD/OMS. La aplicación
documenta además fuentes externas de la OMS para contextualizar la metodología.

Para cumplir de forma más estricta una exigencia de **cruce numérico** con otra
base, se recomienda incorporar una segunda fuente con una clave compatible.
Por ejemplo:

- población mundial/regional por año;
- datos de mortalidad de OMS;
- tasas de mortalidad;
- indicadores socioeconómicos por país, si la base principal también contiene
  una dimensión geográfica.

No se deben realizar cruces artificiales si las dos bases no comparten una
clave válida.

## 7. Publicación en Streamlit Community Cloud

1. Crear un repositorio en GitHub.
2. Subir:
   - `app.py`
   - `requirements.txt`
   - `dataset_final_causas_GBD2017.xlsx`
3. Entrar a Streamlit Community Cloud.
4. Crear una nueva aplicación.
5. Seleccionar el repositorio.
6. Seleccionar `app.py` como archivo principal.
7. Desplegar.

El enlace generado será público y podrá incluirse en el PDF de la actividad.

## 8. Fuentes

OMS — Global Health Estimates:
https://www.who.int/data/global-health-estimates/

OMS — WHO Mortality Database:
https://platform.who.int/mortality/about/about-the-who-mortality-database

OMS — Cause of death:
https://www.who.int/standards/classifications/classification-of-diseases/cause-of-death

IHME — Global Burden of Disease:
https://www.healthdata.org/research-analysis/gbd
