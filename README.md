# GeoCentro - Monitor de Eventos Geológicos para Centroamérica

Este proyecto es un monitor de eventos geológicos y climáticos para Centroamérica. Actualmente, se enfoca en la recopilación y visualización de datos sísmicos de INETER (Instituto Nicaragüense de Estudios Territoriales).

## Arquitectura

El proyecto está compuesto por tres componentes principales:

1.  **Agente de Adquisición de Datos (`agent.py`):** Un script de Python que orquesta la descarga y el procesamiento de los datos.
2.  **Tareas (`tasks/`):** Módulos de Python que realizan tareas específicas:
    *   `download_sismos_html.py`: Descarga los datos de sismos de la página de INETER utilizando Selenium.
    *   `parse_sismos_file.py`: Procesa el HTML descargado, extrae la información de los sismos y la almacena en una base de datos SQLite (`sismos.db`).
3.  **Servidor Web (`web_server.py`):** Una aplicación Flask que sirve una API para consultar los datos de sismos y una interfaz web para visualizarlos en un mapa interactivo.

## Cómo Ejecutar el Proyecto

### Prerrequisitos

*   Python 3.x
*   PIP (manejador de paquetes de Python)

### Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL-del-repositorio>
    cd <nombre-del-repositorio>
    ```

2.  **Instalar las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    El archivo `requirements.txt` contiene todas las librerías de Python necesarias para ejecutar el proyecto (Flask, Selenium, BeautifulSoup, etc.).

### Ejecución

1.  **Ejecutar el agente para obtener los datos:**
    ```bash
    python3 agent.py
    ```
    Este comando ejecutará las tareas de descarga y procesamiento de datos, poblando la base de datos `sismos.db`.

2.  **Iniciar el servidor web:**
    ```bash
    python3 web_server.py
    ```
    Esto iniciará un servidor de desarrollo de Flask.

3.  **Abrir la aplicación en el navegador:**
    Abre tu navegador y ve a `http://127.0.0.1:5000` para ver el mapa de sismos.

## Decisiones de Diseño

*   **Modularidad:** El proyecto está dividido en módulos cohesivos y poco acoplados (agente, tareas, servidor web). Esto facilita el mantenimiento, la depuración y la adición de nuevas funcionalidades.
*   **Base de Datos SQLite:** Se eligió SQLite por su simplicidad y porque no requiere un servidor de base de datos separado. Es ideal para un proyecto de esta escala.
*   **Selenium y `webdriver-manager`:** Se utiliza Selenium para el web scraping porque la página de INETER carga los datos de forma dinámica. `webdriver-manager` se encarga de la gestión automática del `chromedriver`, lo que simplifica la configuración del entorno.
*   **API REST:** El servidor web expone una API REST para desacoplar el backend del frontend. Esto permite que el frontend (o cualquier otro cliente) consuma los datos de manera estructurada.
*   **Interfaz Interactiva:** Se utiliza Leaflet.js para crear un mapa interactivo que permite a los usuarios visualizar y filtrar los datos de sismos de manera intuitiva.
