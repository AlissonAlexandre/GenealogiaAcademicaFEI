from playwright.sync_api import sync_playwright
import urllib.parse
import time
import re
from pesquisador import Pesquisador

def handle_route_block_script(route, request):
    if request.resource_type == "script":
        route.abort()
    else:
        route.continue_()

def handle_route_block_nothing(route, request):
    route.continue_()


def checaDataParam(elementos):
    pattern = re.compile(r".*nivelCurso=D.*")
    for elemento in elementos:
        if pattern.match(elemento.get_attribute('data-param')):
            return elemento
    return None

with sync_playwright() as p:
    # Configurar as opções do Chrome (caso deseje que a janela do navegador fique oculta)
    browser = p.chromium.launch(headless=False, args=["--enable-automation"])
    context = browser.new_context()
    # Inicializar o WebDriver
    page = context.new_page()
    
    # Abrir uma página web
    page.goto("http://lattes.cnpq.br/5676806579817092")
    lid10 = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id'][0]
    
    URL = "http://buscatextual.cnpq.br/buscatextual/preview.do?metodo=apresentar&id="
    print(lid10)
    
    page.goto(URL + lid10) 
    timeout = 5000  # Timeout in milliseconds
    try:
        page.locator(".name").wait_for(timeout=timeout)
    except:
        print("Erro ao esperar pela pagina de middleware entre Captcha e Curriculo Lattes")
    context.route("**/*", handle_route_block_script)

    cmd_open_cv = 'abreCV()'
    with context.expect_page() as new_page:
        page.evaluate(cmd_open_cv)
    pages = new_page.value.context.pages
    pattern = re.compile(r".*visualizacv.*")
    for new_page in pages:
        new_page.wait_for_load_state()
        if pattern.match(new_page.url):
            page = new_page

    #page.route("**buscatextual/js/v2*", handle_route)
    print("Carregou pagina lattes do curriculo: ")
    # Exibir o título da página
    with open("teste.html", "w") as file:
        file.write(page.content())
    context.route("**/*", handle_route_block_nothing)

    elementosAcademicos = page.locator(".ajaxCAPES").all()
    objetoParamDoutorado = checaDataParam(elementosAcademicos).locator("..").inner_html()

    #elemento = page.locator("[data-param]~='nivelCurso=D").locator("..")

    time.sleep(1000)
    
    # Fechar o navegador
    browser.close()