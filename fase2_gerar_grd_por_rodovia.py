import os
import re
import csv
import unicodedata
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.drawing.image import Image as XLImage

# Pasta de entrega à Certificadora (uma subpasta por rodovia). Variável de ambiente ou ./entrega
BASE_DIR = os.environ.get("REMESSA_BASE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "entrega"))

DRY_RUN = False

EMPRESA = "Parceiro"

DATA_HOJE = datetime.today().strftime("%Y.%m.%d")
DATA_HOJE_BR = datetime.today().strftime("%d/%m/%Y")
DATA_HORA = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")

RODOVIAS = ["RD-101", "RD-102A", "RD-103", "RD-104"]

RENOMEAR_RAIZ_DA_RODOVIA = False

MAX_NIVEL_RENOMEAR_COM_DATA = 2
MAX_NIVEL_RENOMEAR_ARQUIVOS_COM_DATA = 1
MAX_NIVEL_GRD = 1

SOBRESCREVER_GRD_SE_EXISTIR = False

MARCAR_TIPO_NA_DESCRICAO = False

PASTAS_IGNORAR_PREFIXOS = (
    "_INDICE",
    "_BACKUP",
    "_TEMP",
    "_OLD",
    "__PY",
)

ARQUIVOS_IGNORAR = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
}

EXTENSOES_IGNORAR = {
    ".tmp",
    ".bak",
    ".lnk",
    ".ini",
    ".db",
}

LOGO_POSSIVEIS_NOMES = [
    "logo-parceiro.png",
    "logo-parceiro.jpg",
    "logo-parceiro.jpeg",
    "logo-parceiro.svg",
]

COR_VERDE_ESCURO = "015346"
COR_VERDE_HEADER = "029441"
COR_BRANCO = "FFFFFF"
COR_BORDA = "BFBFBF"


def caminho_longo(path):
    path_abs = os.path.abspath(path)
    if os.name == "nt" and not path_abs.startswith("\\\\?\\"):
        return "\\\\?\\" + path_abs
    return path_abs


def remover_acentos(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))


def limpar_nome(texto, maiusculo=True):
    texto = remover_acentos(str(texto))
    if maiusculo:
        texto = texto.upper()
    texto = re.sub(r'[<>:"/\\|?*]', " ", texto)
    texto = re.sub(r"[^A-Za-z0-9 ._\-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    texto = texto.rstrip(" .")
    return texto


def remover_data_inicial(nome):
    nome = str(nome).strip()
    nome = re.sub(r"^\d{4}\.\d{2}\.\d{2}\s*-\s*", "", nome).strip()
    nome = re.sub(r"^\d{4}-\d{2}-\d{2}\s*-\s*", "", nome).strip()
    return nome


def aplicar_data_nome_pasta(nome):
    base = limpar_nome(remover_data_inicial(nome), maiusculo=True)
    if not base:
        base = "PASTA"
    return f"{DATA_HOJE} - {base}"


def aplicar_data_nome_arquivo(nome):
    base, ext = os.path.splitext(nome)
    base = remover_data_inicial(base)
    base = limpar_nome(base, maiusculo=False)
    ext = limpar_nome(ext, maiusculo=False).replace(" ", "")
    if not base:
        base = "ARQUIVO"
    return f"{DATA_HOJE} - {base}{ext}"


def limpar_arquivo_sem_data(nome):
    base, ext = os.path.splitext(nome)
    base = remover_data_inicial(base)
    base = limpar_nome(base, maiusculo=False)
    ext = limpar_nome(ext, maiusculo=False).replace(" ", "")
    if not base:
        base = "ARQUIVO"
    return f"{base}{ext}"


def limpar_pasta_sem_data(nome):
    base = remover_data_inicial(nome)
    base = limpar_nome(base, maiusculo=True)
    if not base:
        base = "PASTA"
    return base


def deve_ignorar_pasta(nome):
    nome_upper = limpar_nome(nome, maiusculo=True)
    return any(nome_upper.startswith(prefixo) for prefixo in PASTAS_IGNORAR_PREFIXOS)


def deve_ignorar_arquivo(nome):
    if nome.startswith("~$"):
        return True

    if nome.lower() in ARQUIVOS_IGNORAR:
        return True

    ext = os.path.splitext(nome)[1].lower()
    if ext in EXTENSOES_IGNORAR:
        return True

    return False


def normalizar_rodovia_para_busca(texto):
    return limpar_nome(texto, maiusculo=True).replace("-", "").replace(" ", "")


def localizar_pasta_rodovia(rodovia):
    alvo = normalizar_rodovia_para_busca(rodovia)

    if not os.path.isdir(caminho_longo(BASE_DIR)):
        return os.path.join(BASE_DIR, rodovia)

    candidatos = []

    for item in os.listdir(caminho_longo(BASE_DIR)):
        caminho = os.path.join(BASE_DIR, item)

        if not os.path.isdir(caminho_longo(caminho)):
            continue

        if deve_ignorar_pasta(item):
            continue

        nome_busca = normalizar_rodovia_para_busca(item)

        if alvo in nome_busca:
            candidatos.append(caminho)

    if candidatos:
        candidatos.sort(
            key=lambda x: (
                0 if "PROJETOS" in limpar_nome(os.path.basename(x), maiusculo=True) else 1,
                len(os.path.basename(x))
            )
        )
        return candidatos[0]

    return os.path.join(BASE_DIR, rodovia)


def nome_projeto_rodovia(rodovia):
    return f"{DATA_HOJE} - PROJETOS {rodovia}"


def nome_raiz_exibicao(pasta_raiz, rodovia):
    nome_atual = os.path.basename(pasta_raiz)

    if normalizar_rodovia_para_busca(rodovia) in normalizar_rodovia_para_busca(nome_atual):
        return nome_atual

    return nome_projeto_rodovia(rodovia)


def caminho_relativo_grd(caminho, pasta_raiz):
    pasta_mae = os.path.dirname(pasta_raiz)
    return os.path.relpath(caminho, pasta_mae)


def profundidade_relativa(pasta, pasta_raiz):
    if os.path.abspath(pasta) == os.path.abspath(pasta_raiz):
        return 0

    rel = os.path.relpath(pasta, pasta_raiz)
    return len(rel.split(os.sep))


def nome_unico_pasta(destino):
    if not os.path.exists(caminho_longo(destino)):
        return destino

    pasta_pai = os.path.dirname(destino)
    nome = os.path.basename(destino)

    contador = 2
    while True:
        novo = os.path.join(pasta_pai, f"{nome} - DUPLICADO {contador}")
        if not os.path.exists(caminho_longo(novo)):
            return novo
        contador += 1


def nome_unico_arquivo(destino):
    if not os.path.exists(caminho_longo(destino)):
        return destino

    pasta = os.path.dirname(destino)
    base, ext = os.path.splitext(os.path.basename(destino))

    contador = 2
    while True:
        novo = os.path.join(pasta, f"{base} - DUPLICADO {contador}{ext}")
        if not os.path.exists(caminho_longo(novo)):
            return novo
        contador += 1


def renomear_pasta(origem, destino):
    if os.path.abspath(origem) == os.path.abspath(destino):
        return origem, "MANTIDA"

    destino_final = nome_unico_pasta(destino)

    if DRY_RUN:
        print(f"[TESTE] Renomearia pasta: {origem} -> {destino_final}")
    else:
        os.rename(caminho_longo(origem), caminho_longo(destino_final))
        print(f"[OK] Pasta renomeada: {origem} -> {destino_final}")

    return destino_final, "RENOMEADA"


def renomear_arquivo(origem, destino):
    if os.path.abspath(origem) == os.path.abspath(destino):
        return origem, "MANTIDO"

    destino_final = nome_unico_arquivo(destino)

    if DRY_RUN:
        print(f"[TESTE] Renomearia arquivo: {origem} -> {destino_final}")
    else:
        os.rename(caminho_longo(origem), caminho_longo(destino_final))
        print(f"[OK] Arquivo renomeado: {origem} -> {destino_final}")

    return destino_final, "RENOMEADO"


def preparar_raiz_rodovia(rodovia):
    pasta_atual = localizar_pasta_rodovia(rodovia)

    if not os.path.isdir(caminho_longo(pasta_atual)):
        if DRY_RUN:
            print(f"[TESTE] Criaria pasta da rodovia: {pasta_atual}")
        else:
            os.makedirs(caminho_longo(pasta_atual), exist_ok=True)
            print(f"[OK] Pasta da rodovia criada/verificada: {pasta_atual}")

    if RENOMEAR_RAIZ_DA_RODOVIA:
        nome_correto = nome_projeto_rodovia(rodovia)
        destino = os.path.join(os.path.dirname(pasta_atual), nome_correto)
        pasta_final, acao = renomear_pasta(pasta_atual, destino)
        return pasta_final, acao

    return pasta_atual, "MANTIDA"


def preparar_nomes_pastas_e_arquivos(pasta_raiz, rodovia):
    logs = []

    for raiz, dirs, arquivos in os.walk(caminho_longo(pasta_raiz), topdown=True):
        raiz = raiz.replace("\\\\?\\", "")
        nivel_raiz = profundidade_relativa(raiz, pasta_raiz)

        dirs[:] = [d for d in dirs if not deve_ignorar_pasta(d)]

        for i, nome_dir in enumerate(list(dirs)):
            origem = os.path.join(raiz, nome_dir)
            nivel_dir = nivel_raiz + 1

            if not os.path.isdir(caminho_longo(origem)):
                continue

            if nivel_dir <= MAX_NIVEL_RENOMEAR_COM_DATA:
                novo_nome = aplicar_data_nome_pasta(nome_dir)
            else:
                novo_nome = limpar_pasta_sem_data(nome_dir)

            destino = os.path.join(raiz, novo_nome)
            destino_final, acao = renomear_pasta(origem, destino)

            dirs[i] = os.path.basename(destino_final)

            logs.append({
                "rodovia": rodovia,
                "tipo": "PASTA",
                "origem": origem,
                "destino": destino_final,
                "acao": acao,
            })

        for nome_arq in list(arquivos):
            if deve_ignorar_arquivo(nome_arq):
                continue

            origem = os.path.join(raiz, nome_arq)

            if not os.path.isfile(caminho_longo(origem)):
                continue

            if nivel_raiz <= MAX_NIVEL_RENOMEAR_ARQUIVOS_COM_DATA:
                novo_nome = aplicar_data_nome_arquivo(nome_arq)
            else:
                novo_nome = limpar_arquivo_sem_data(nome_arq)

            destino = os.path.join(raiz, novo_nome)
            destino_final, acao = renomear_arquivo(origem, destino)

            logs.append({
                "rodovia": rodovia,
                "tipo": "ARQUIVO",
                "origem": origem,
                "destino": destino_final,
                "acao": acao,
            })

    return logs


def formatar_item_descricao(nome, eh_pasta):
    if MARCAR_TIPO_NA_DESCRICAO:
        prefixo = "[PASTA]" if eh_pasta else "[ARQUIVO]"
        return f"{prefixo} {nome}"
    return nome


def listar_conteudo_direto(pasta, nome_grd_previsto=None):
    itens = []

    try:
        nomes = os.listdir(caminho_longo(pasta))
    except Exception:
        return itens

    for nome in nomes:
        caminho = os.path.join(pasta, nome)

        if os.path.isdir(caminho_longo(caminho)):
            if deve_ignorar_pasta(nome):
                continue

            itens.append(formatar_item_descricao(nome, True))

        elif os.path.isfile(caminho_longo(caminho)):
            if deve_ignorar_arquivo(nome):
                continue

            itens.append(formatar_item_descricao(nome, False))

    if nome_grd_previsto:
        ja_existe = any(
            limpar_nome(x, maiusculo=True) == limpar_nome(nome_grd_previsto, maiusculo=True)
            for x in itens
        )
        if not ja_existe:
            itens.append(formatar_item_descricao(nome_grd_previsto, False))

    itens.sort(key=lambda x: remover_acentos(x).upper())

    return itens


def montar_linhas_grd(rodovia, pasta_raiz, nome_grd_previsto):
    linhas = []

    raiz_exibicao = nome_raiz_exibicao(pasta_raiz, rodovia)

    conteudo_raiz = listar_conteudo_direto(
        pasta_raiz,
        nome_grd_previsto=nome_grd_previsto
    )

    linhas.append({
        "data": DATA_HOJE_BR,
        "revisao": "-",
        "nivel": 0,
        "identificador_geral": raiz_exibicao,
        "id_past": "-",
        "descricao": "\n".join(conteudo_raiz) if conteudo_raiz else "-",
        "total": len(conteudo_raiz),
        "caminho": caminho_relativo_grd(pasta_raiz, pasta_raiz),
    })

    try:
        itens_raiz = os.listdir(caminho_longo(pasta_raiz))
    except Exception:
        itens_raiz = []

    pastas_primeiro_nivel = []

    for nome in itens_raiz:
        caminho = os.path.join(pasta_raiz, nome)

        if not os.path.isdir(caminho_longo(caminho)):
            continue

        if deve_ignorar_pasta(nome):
            continue

        pastas_primeiro_nivel.append(caminho)

    pastas_primeiro_nivel.sort(
        key=lambda p: remover_acentos(os.path.basename(p)).upper()
    )

    for pasta in pastas_primeiro_nivel:
        nome_pasta = os.path.basename(pasta)
        conteudo = listar_conteudo_direto(pasta)

        linhas.append({
            "data": DATA_HOJE_BR,
            "revisao": "-",
            "nivel": 1,
            "identificador_geral": nome_pasta,
            "id_past": "-",
            "descricao": "\n".join(conteudo) if conteudo else "-",
            "total": len(conteudo),
            "caminho": caminho_relativo_grd(pasta, pasta_raiz),
        })

    return linhas


def localizar_logo():
    possiveis_pastas = [
        os.getcwd(),
        BASE_DIR,
        os.path.dirname(os.path.abspath(__file__)),
    ]

    for pasta in possiveis_pastas:
        for nome in LOGO_POSSIVEIS_NOMES:
            caminho = os.path.join(pasta, nome)
            if os.path.isfile(caminho_longo(caminho)):
                return caminho

    return None


def converter_svg_para_png(caminho_svg):
    caminho_png = os.path.splitext(caminho_svg)[0] + "_convertida.png"

    if os.path.isfile(caminho_longo(caminho_png)):
        return caminho_png

    try:
        import cairosvg
        cairosvg.svg2png(url=caminho_svg, write_to=caminho_png, output_width=520)
        return caminho_png
    except Exception as e:
        print("[AVISO] Nao consegui converter SVG para PNG automaticamente.")
        print("Para inserir a logo, salve a logo como logo-parceiro.png na mesma pasta do script.")
        print(f"Motivo: {e}")
        return None


def inserir_logo(ws):
    caminho_logo = localizar_logo()

    if not caminho_logo:
        print("[AVISO] Logo nao encontrada. Coloque logo-parceiro.png ou logo-parceiro.svg na pasta do script.")
        return

    ext = os.path.splitext(caminho_logo)[1].lower()

    if ext == ".svg":
        caminho_logo = converter_svg_para_png(caminho_logo)
        if not caminho_logo:
            return

    try:
        img = XLImage(caminho_logo)
        img.width = 242
        img.height = 80
        ws.add_image(img, "B2")
    except Exception as e:
        print("[AVISO] Nao foi possivel inserir a logo no Excel.")
        print(f"Motivo: {e}")


def borda_fina():
    side = Side(style="thin", color=COR_BORDA)
    return Border(left=side, right=side, top=side, bottom=side)


def aplicar_bordas(ws, intervalo):
    b = borda_fina()
    for row in ws[intervalo]:
        for cell in row:
            cell.border = b


def ajustar_altura(ws, linha, texto):
    qtd = max(1, len(str(texto).splitlines()))
    altura = min(max(22, qtd * 13), 180)
    ws.row_dimensions[linha].height = altura


def formatar_area_topo(ws):
    fill_topo = PatternFill("solid", fgColor=COR_VERDE_ESCURO)
    fonte_topo = Font(name="Arial", size=10, bold=True, color=COR_BRANCO)

    for row in ws["B2:I4"]:
        for cell in row:
            cell.fill = fill_topo
            cell.font = fonte_topo
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = borda_fina()

    ws["F2"].font = Font(name="Arial", size=14, bold=True, color=COR_BRANCO)
    ws["F2"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    for celula in ["I2", "I3", "I4"]:
        ws[celula].font = Font(name="Arial", size=10, bold=True, color=COR_BRANCO)
        ws[celula].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def formatar_header_tabela(ws):
    fill_header = PatternFill("solid", fgColor=COR_VERDE_HEADER)
    fonte_header = Font(name="Arial", size=10, bold=True, color=COR_BRANCO)

    for cell in ws["B5:I5"][0]:
        cell.fill = fill_header
        cell.font = fonte_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = borda_fina()


def formatar_linha_body(ws, linha_excel, nivel):
    for col in range(2, 10):
        cell = ws.cell(row=linha_excel, column=col)
        cell.fill = PatternFill("solid", fgColor=COR_BRANCO)
        cell.font = Font(name="Arial", size=9, color="000000")
        cell.border = borda_fina()
        cell.alignment = Alignment(vertical="top", wrap_text=True)

    for col in [2, 3, 4, 6, 8]:
        ws.cell(row=linha_excel, column=col).alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )

    for col in [5, 7, 9]:
        ws.cell(row=linha_excel, column=col).alignment = Alignment(
            horizontal="left",
            vertical="top",
            wrap_text=True
        )


def configurar_layout_planilha(ws):
    ws.sheet_view.showGridLines = False

    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 11
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 39
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 57
    ws.column_dimensions["H"].width = 25
    ws.column_dimensions["I"].width = 24

    ws.row_dimensions[1].height = 7.95
    ws.row_dimensions[2].height = 24
    ws.row_dimensions[3].height = 24
    ws.row_dimensions[4].height = 24
    ws.row_dimensions[5].height = 25.95

    ws.freeze_panes = "B6"

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws.page_margins.left = 0.25
    ws.page_margins.right = 0.25
    ws.page_margins.top = 0.5
    ws.page_margins.bottom = 0.5


def criar_grd_excel(rodovia, pasta_raiz):
    nome_grd = f"GRD {DATA_HOJE} - PROJETOS {rodovia}.xlsx"
    caminho_saida = os.path.join(pasta_raiz, nome_grd)

    if os.path.exists(caminho_longo(caminho_saida)) and not SOBRESCREVER_GRD_SE_EXISTIR:
        caminho_saida = nome_unico_arquivo(caminho_saida)
        nome_grd = os.path.basename(caminho_saida)

    linhas = montar_linhas_grd(
        rodovia=rodovia,
        pasta_raiz=pasta_raiz,
        nome_grd_previsto=nome_grd
    )

    wb = Workbook()
    ws = wb.active
    ws.title = f"GRD {rodovia}"

    configurar_layout_planilha(ws)

    ws.merge_cells("B2:D4")
    ws.merge_cells("E2:E4")
    ws.merge_cells("F2:H4")

    inserir_logo(ws)

    ws["F2"] = f"GUIA DE REMESSA DE DOCUMENTOS - {EMPRESA}\n{nome_raiz_exibicao(pasta_raiz, rodovia)}"
    ws["I2"] = f"Data: {DATA_HOJE_BR}"
    ws["I3"] = EMPRESA
    ws["I4"] = rodovia

    headers = [
        "DATA",
        "REVISÃO",
        "NÍVEL",
        "IDENTIFICADOR_GERAL",
        "ID_PAST",
        "DESCRIÇÃO",
        "TOTAL DE REGISTROS",
        "CAMINHO",
    ]

    for col, header in enumerate(headers, start=2):
        ws.cell(row=5, column=col).value = header

    formatar_area_topo(ws)
    formatar_header_tabela(ws)

    inicio = 6

    for i, linha in enumerate(linhas, start=inicio):
        valores = [
            linha["data"],
            linha["revisao"],
            linha["nivel"],
            linha["identificador_geral"],
            linha["id_past"],
            linha["descricao"],
            linha["total"],
            linha["caminho"],
        ]

        for col, valor in enumerate(valores, start=2):
            ws.cell(row=i, column=col).value = valor

        formatar_linha_body(ws, i, linha["nivel"])
        ajustar_altura(ws, i, linha["descricao"])

    final = inicio + len(linhas) - 1

    aplicar_bordas(ws, f"B2:I4")
    aplicar_bordas(ws, f"B5:I{max(final, 6)}")

    ws.auto_filter.ref = f"B5:I{max(final, 6)}"

    if DRY_RUN:
        print(f"[TESTE] Criaria GRD: {caminho_saida}")
    else:
        wb.save(caminho_longo(caminho_saida))
        print(f"[OK] GRD criada: {caminho_saida}")

    return caminho_saida, len(linhas)


def salvar_log(logs, resumo):
    caminho_log = os.path.join(BASE_DIR, f"LOG_FASE2_GRD_FINAL_{DATA_HORA}.csv")

    if DRY_RUN:
        print(f"[TESTE] Criaria log: {caminho_log}")
        return caminho_log

    with open(caminho_longo(caminho_log), "w", newline="", encoding="utf-8-sig") as f:
        campos = ["rodovia", "tipo", "origem", "destino", "acao"]
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        writer.writerows(logs)

        f.write("\n")
        f.write("RESUMO\n")
        for item in resumo:
            f.write(";".join(map(str, item)) + "\n")

    return caminho_log


def main():
    print("=" * 90)
    print("FASE 2 FINAL - GRD FORMATADO + RENOMEACAO CONTROLADA")
    print(f"Data usada: {DATA_HOJE}")
    print(f"Empresa: {EMPRESA}")
    print("Nao move arquivos. Nao exclui arquivos.")
    print("Renomeia arquivos considerados no GRD com data antes.")
    print("Remove data das pastas/arquivos internos que nao entram no GRD.")
    print("Aplica layout verde do Parceiro com bordas, alinhamento, largura e cabecalho.")
    print("=" * 90)

    logs = []
    saidas = []
    resumo = []

    for rodovia in RODOVIAS:
        pasta_raiz, acao_raiz = preparar_raiz_rodovia(rodovia)

        logs.append({
            "rodovia": rodovia,
            "tipo": "RAIZ_RODOVIA",
            "origem": "",
            "destino": pasta_raiz,
            "acao": acao_raiz,
        })

        logs.extend(preparar_nomes_pastas_e_arquivos(pasta_raiz, rodovia))

        caminho_grd, qtd_linhas = criar_grd_excel(rodovia, pasta_raiz)

        saidas.append((rodovia, caminho_grd, qtd_linhas))

        resumo.append((rodovia, "PASTA_RAIZ", pasta_raiz))
        resumo.append((rodovia, "LINHAS_GRD", qtd_linhas))
        resumo.append((rodovia, "ARQUIVO_GRD", caminho_grd))

    caminho_log = salvar_log(logs, resumo)

    print("")
    print("=" * 90)
    print("[FINALIZADO - FASE 2 FINAL]" if not DRY_RUN else "[FINALIZADO EM MODO TESTE]")
    print(f"Pastas/arquivos verificados ou renomeados: {len(logs)}")
    print("")
    print("GRDs geradas:")
    for rodovia, caminho, qtd in saidas:
        print(f"- {rodovia}: {qtd} linhas -> {caminho}")
    print("")
    print(f"Log: {caminho_log}")
    print("=" * 90)

    if DRY_RUN:
        print("")
        print("ATENCAO: DRY_RUN = True.")
        print("Nada foi renomeado e nenhum Excel foi salvo.")
        print("Para executar de verdade, mude DRY_RUN = False.")


if __name__ == "__main__":
    main()