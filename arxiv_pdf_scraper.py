import os
import csv
import requests
from tqdm import tqdm  # Importar tqdm para la barra de progreso
from playwright.sync_api import sync_playwright

# ===========================
# CONFIGURACIÓN Y UTILIDADES
# ===========================

DATA_DIR = "data"
CSV_FILE = "articles_arxiv.csv"

os.makedirs(DATA_DIR, exist_ok=True)


def descargar_pdf(file_url: str, output_dir: str) -> str | None:
    """
    Descarga un archivo PDF desde arXiv utilizando la URL de la página de resumen.

    :param file_url: URL de la página de resumen del artículo en arXiv.
    :param output_dir: Carpeta donde se guardará el archivo.
    :return: Ruta del archivo descargado o None si falla.
    """
    # Extraer solo el identificador del archivo desde la URL
    file_id = file_url.split("/")[-1]   # Extrae, digamos, '2301.04567'
                                        # desde, por ejemplo, 'https://arxiv.org/pdf/2301.04567'

    # Construir la URL del PDF
    pdf_url = f"https://arxiv.org/pdf/{file_id}.pdf"

    user_agent = {
        "user-agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/134.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(pdf_url, stream=True, timeout=10, headers=user_agent)
        if response.status_code == 200:
            file_path = os.path.join(output_dir, f"{file_id}.pdf")
            with open(file_path, "wb") as f, tqdm(
                    desc=f"Descargando {file_id}.pdf",
                    total=int(response.headers.get("content-length", 0)),
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
            ) as bar:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
                    bar.update(len(chunk))
            print(f"Archivo descargado: {file_path}")
            return file_path
        else:
            print(f"Error al descargar {pdf_url}: Código {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error en la descarga de {pdf_url}: {e}")
        return None


def guardar_en_csv(links: list, file_path: str):
    """
    Guarda una lista de enlaces en un archivo CSV.

    :param links: Lista de URLs de los PDFs
    :param file_path: Ruta del archivo CSV
    """
    try:
        with open(file_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            for link in links:
                writer.writerow([link])
        print(f"{len(links)} enlaces guardados en {file_path}")
    except Exception as e:
        print(f"Error al escribir en CSV: {e}")


# ===========================
# SCRAPING CON PLAYWRIGHT
# ===========================

def scrape_arxiv(search_term: str):
    """
    Realiza scraping en arXiv.org para buscar artículos en PDF y descargarlos.

    :param search_term: Término de búsqueda en arXiv
    """
    with sync_playwright() as pw:
        # Inicia el navegador Firefox en modo no headless (visible)
        browser = pw.firefox.launch(headless=False, slow_mo=2000)
        page = browser.new_page()

        print(f"Buscando artículos con el término: {search_term}")

        # Navega a la página de búsqueda de arXiv
        page.goto("https://arxiv.org/search/")

        # Rellena el campo de búsqueda con el término especificado
        page.get_by_placeholder("Search term...").fill(search_term)

        # Encuentra y hace clic en el botón de búsqueda
        page.get_by_role("button").nth(1).click()

        # Espera hasta que los enlaces de PDFs sean visibles antes de continuar
        page.wait_for_selector("xpath=//span/a[contains(@href, 'arxiv.org/pdf')]", timeout=5000)

        # Localiza todos los enlaces a archivos PDF
        links = page.locator("xpath=//span/a[contains(@href, 'arxiv.org/pdf')]")
        count = links.count()
        pdf_links = []

        print(f"Se encontraron {count} PDFs para descargar.")

        # Recorre los enlaces encontrados y los almacena en la lista pdf_links
        for i in range(count):
            link_element = links.nth(i)
            href = link_element.get_attribute("href")
            if href:
                pdf_links.append(href)

                # Descarga el PDF y lo almacena en el directorio "data"
                descargar_pdf(href, DATA_DIR)

        # Guarda los enlaces de los PDFs en un archivo CSV
        guardar_en_csv(pdf_links, CSV_FILE)

        # Toma una captura de pantalla de la página final para verificar la ejecución
        page.screenshot(path="example.png")

        print(f"Página cargada: {page.title()}")

        # Cierra el navegador una vez completado el proceso
        browser.close()



# ===========================
# EJECUCIÓN DEL SCRAPER
# ===========================

if __name__ == "__main__":
    search_term = "learning"
    scrape_arxiv(search_term)
