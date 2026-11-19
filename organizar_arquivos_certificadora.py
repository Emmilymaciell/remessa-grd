import os
import re
import csv
import shutil
import unicodedata
from datetime import datetime

# ============================================================
# CONFIGURACAO
# ============================================================

# Pasta de entrega à Certificadora (uma subpasta por rodovia). Variável de ambiente ou ./entrega
BASE_DIR = os.environ.get("REMESSA_BASE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "entrega"))

# Primeiro rode com True para testar sem alterar nada.
# Depois de conferir, mude para False.
DRY_RUN = False

# Se True, arquivos dentro de subpastas serao movidos para a raiz da pasta da disciplina.
# Nao exclui arquivos.
ACHATAR_SUBPASTAS = True

# Se False, subpastas vazias ficam no lugar.
# Recomendo manter False.
REMOVER_SUBPASTAS_VAZIAS = False

DATA_HOJE = datetime.today().strftime("%Y.%m.%d")
DATA_HORA = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")

EXTENSOES_IGNORAR = {
    ".tmp", ".bak", ".lnk", ".ini", ".db", ".ds_store"
}

PROXIMAS_GRDS = {
    "RD-101": "001/2026",
    "RD-102A": "001/2026",
    "RD-103": "001/2026",
    "RD-104": "001/2026",
}

DISCIPLINAS = {
    "RELATORIO DE ATIVIDADES PRELIMINARES": {
        "sigla": "RAP",
        "esperados": ["RT", "CR", "DC"]
    },
    "ESTUDOS DE TRAFEGO": {
        "sigla": "TRA",
        "esperados": ["RT", "CR", "DC"]
    },
    "ESTUDOS TOPOGRAFICOS": {
        "sigla": "TOP",
        "esperados": ["RT", "CR", "DC"]
    },
    "ESTUDOS GEOLOGICOS": {
        "sigla": "GEO",
        "esperados": ["RT", "CR", "DC"]
    },
    "DIAGNOSTICO AMBIENTAL PREVIO DAP": {
        "sigla": "DAP",
        "esperados": ["RT", "CR", "DC"]
    },
    "DOCUMENTACAO PARA DECLARACAO DE UTILIDADE PUBLICA DUP": {
        "sigla": "DUP",
        "esperados": ["RT", "CR", "DC"]
    },
    "ESTUDOS HIDROLOGICOS": {
        "sigla": "HID",
        "esperados": ["RT", "CR", "DC"]
    },
}

TIPOS_VALIDOS = {
    "RT": "RELATORIO TECNICO",
    "CR": "CARTA / COMUNICACAO / CONTROLE",
    "DC": "DOCUMENTOS COMPLEMENTARES / DESENHOS / EDITAVEIS",
    "MC": "MEMORIAL DE CALCULO",
    "MD": "MEMORIAL DESCRITIVO",
    "PL": "PLANILHA",
    "PE": "PROJETO EXECUTIVO",
    "GRD": "GUIA DE REMESSA DE DOCUMENTOS",
}

# ============================================================
# FUNCOES BASICAS
# ============================================================

def caminho_longo_windows(path: str) -> str:
    path_abs = os.path.abspath(path)
    if os.name == "nt":
        if path_abs.startswith("\\\\?\\"):
            return path_abs
        return "\\\\?\\" + path_abs
    return path_abs


def remover_acentos(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def normalizar_texto(texto: str) -> str:
    texto = remover_acentos(texto)
    texto = texto.upper()
    texto = re.sub(r"[^A-Z0-9 ._\-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def limpar_nome_arquivo(nome: str) -> str:
    nome = remover_acentos(nome)
    nome = nome.upper()

    # Caracteres proibidos no Windows: < > : " / \ | ? *
    nome = re.sub(r'[<>:"/\\|?*]', "_", nome)

    # Limpa espacos duplicados
    nome = re.sub(r"\s+", " ", nome).strip()

    # Evita pontos/espacos no final
    nome = nome.rstrip(" .")

    return nome


def garantir_nome_unico(caminho_destino: str) -> str:
    if not os.path.exists(caminho_longo_windows(caminho_destino)):
        return caminho_destino

    pasta = os.path.dirname(caminho_destino)
    nome = os.path.basename(caminho_destino)
    base, ext = os.path.splitext(nome)

    contador = 2
    while True:
        novo = os.path.join(pasta, f"{base}__DUPLICADO_{contador}{ext}")
        if not os.path.exists(caminho_longo_windows(novo)):
            return novo
        contador += 1


def acao_mover(origem: str, destino: str):
    destino = garantir_nome_unico(destino)

    if DRY_RUN:
        print(f"[TESTE] Moveria: {origem} -> {destino}")
    else:
        shutil.move(caminho_longo_windows(origem), caminho_longo_windows(destino))
        print(f"[OK] Movido: {origem} -> {destino}")

    return destino


def acao_renomear(origem: str, destino: str):
    destino = garantir_nome_unico(destino)

    if origem == destino:
        return destino

    if DRY_RUN:
        print(f"[TESTE] Renomearia: {origem} -> {destino}")
    else:
        os.rename(caminho_longo_windows(origem), caminho_longo_windows(destino))
        print(f"[OK] Renomeado: {origem} -> {destino}")

    return destino


# ============================================================
# IDENTIFICACAO
# ============================================================

def obter_rodovia_por_pasta(path: str):
    partes = os.path.normpath(path).split(os.sep)
    for parte in partes:
        parte_norm = parte.upper().replace(" ", "")
        if parte_norm in PROXIMAS_GRDS:
            return parte_norm
    return None


def rodovia_sem_hifen(rodovia: str) -> str:
    return rodovia.replace("-", "")


def obter_disciplina_por_nome_pasta(nome_pasta: str):
    nome_norm = normalizar_texto(nome_pasta)

    # Remove data inicial AAAA.MM.DD -
    nome_norm = re.sub(r"^\d{4}\.\d{2}\.\d{2}\s*-\s*", "", nome_norm).strip()

    for disciplina in DISCIPLINAS:
        if disciplina in nome_norm:
            return disciplina

    return None


def detectar_tipo_documento(nome_base: str):
    nome = normalizar_texto(nome_base)

    # Busca padroes tipo _RT. ou .RT. ou _RT_
    for tipo in TIPOS_VALIDOS:
        if re.search(rf"(^|[._\-\s]){tipo}([._\-\s]|$)", nome):
            return tipo

    # Heuristicas por nome
    if "GRD" in nome:
        return "GRD"
    if "RELATORIO" in nome or "_RT" in nome:
        return "RT"
    if "CARTA" in nome or "_CR" in nome:
        return "CR"
    if "DESENHO" in nome or "EDITAVEL" in nome or "_DC" in nome:
        return "DC"

    return "OUTROS"


def detectar_revisao(nome_base: str):
    nome = normalizar_texto(nome_base)

    # Exemplos: _03.2 / REV 03 / R03 / REV03
    padroes = [
        r"REV\s*([0-9]{1,2}(?:\.[0-9])?)",
        r"R\s*([0-9]{1,2}(?:\.[0-9])?)",
        r"_([0-9]{1,2}\.[0-9])$",
        r"\.([0-9]{1,2}\.[0-9])$",
    ]

    for padrao in padroes:
        m = re.search(padrao, nome)
        if m:
            return m.group(1).zfill(2) if "." not in m.group(1) else m.group(1)

    return "00"


def detectar_codigo_documento(nome_base: str):
    """
    Tenta preservar o codigo tipo 022.077, se existir.
    """
    nome = normalizar_texto(nome_base)
    m = re.search(r"([0-9]{3}\.[0-9]{3})", nome)
    if m:
        return m.group(1)

    m = re.search(r"([0-9]{2,3}\.[0-9]{2,3})", nome)
    if m:
        return m.group(1)

    return "SEM-CODIGO"


def nome_final_para_arquivo(arquivo: str, rodovia: str, disciplina: str, sequencial: int):
    nome_original, ext = os.path.splitext(arquivo)
    ext = ext.lower()

    sigla_disciplina = DISCIPLINAS[disciplina]["sigla"]
    rodovia_codigo = rodovia_sem_hifen(rodovia)

    nome_norm = normalizar_texto(nome_original)
    tipo = detectar_tipo_documento(nome_original)
    revisao = detectar_revisao(nome_original)
    codigo = detectar_codigo_documento(nome_original)

    # GRD recebe nome especial, conforme diretriz: GRD - numeracao unica
    if tipo == "GRD":
        grd = PROXIMAS_GRDS.get(rodovia, "000/2026")
        grd_num, grd_ano = grd.split("/")
        return limpar_nome_arquivo(f"GRD-{grd_num}-{grd_ano}{ext}")

    # Se for arquivo sem codigo, cria nome controlado por sequencial
    if codigo == "SEM-CODIGO":
        nome_final = f"{rodovia_codigo}_{sigla_disciplina}_{tipo}_{sequencial:03d}_REV_{revisao}{ext}"
        return limpar_nome_arquivo(nome_final)

    # Padrao principal preservando codigo original
    nome_final = f"{rodovia_codigo}_{codigo}_{tipo}.EST.{sigla_disciplina}_{revisao}{ext}"
    return limpar_nome_arquivo(nome_final)


def arquivo_deve_ser_ignorado(nome: str):
    ext = os.path.splitext(nome)[1].lower()
    if ext in EXTENSOES_IGNORAR:
        return True
    if nome.startswith("~$"):
        return True
    return False


# ============================================================
# ACHATAR SUBPASTAS
# ============================================================

def puxar_arquivos_de_subpastas(pasta_disciplina: str, registros: list, alertas: list):
    if not ACHATAR_SUBPASTAS:
        return

    for raiz, dirs, arquivos in os.walk(caminho_longo_windows(pasta_disciplina), topdown=False):
        raiz_limpa = raiz.replace("\\\\?\\", "")

        if os.path.abspath(raiz_limpa) == os.path.abspath(pasta_disciplina):
            continue

        for arquivo in arquivos:
            origem = os.path.join(raiz_limpa, arquivo)

            if arquivo_deve_ser_ignorado(arquivo):
                alertas.append({
                    "tipo": "IGNORADO",
                    "arquivo": origem,
                    "motivo": "Arquivo temporario/sistema ignorado."
                })
                continue

            destino = os.path.join(pasta_disciplina, arquivo)
            destino_final = acao_mover(origem, destino)

            registros.append({
                "acao": "MOVIDO_DA_SUBPASTA",
                "origem": origem,
                "destino": destino_final,
                "observacao": "Arquivo puxado para a raiz da pasta da disciplina."
            })

        if REMOVER_SUBPASTAS_VAZIAS:
            try:
                if not os.listdir(caminho_longo_windows(raiz_limpa)):
                    if DRY_RUN:
                        print(f"[TESTE] Removeria subpasta vazia: {raiz_limpa}")
                    else:
                        os.rmdir(caminho_longo_windows(raiz_limpa))
                        print(f"[OK] Subpasta vazia removida: {raiz_limpa}")
            except Exception as e:
                alertas.append({
                    "tipo": "SUBPASTA_NAO_REMOVIDA",
                    "arquivo": raiz_limpa,
                    "motivo": str(e)
                })


# ============================================================
# PROCESSAMENTO
# ============================================================

def processar_pasta_disciplina(pasta_disciplina: str, rodovia: str, disciplina: str, registros: list, alertas: list):
    puxar_arquivos_de_subpastas(pasta_disciplina, registros, alertas)

    arquivos = [
        f for f in os.listdir(caminho_longo_windows(pasta_disciplina))
        if os.path.isfile(caminho_longo_windows(os.path.join(pasta_disciplina, f)))
    ]

    sequencial = 1

    for arquivo in arquivos:
        if arquivo_deve_ser_ignorado(arquivo):
            alertas.append({
                "tipo": "IGNORADO",
                "arquivo": os.path.join(pasta_disciplina, arquivo),
                "motivo": "Arquivo temporario/sistema ignorado."
            })
            continue

        origem = os.path.join(pasta_disciplina, arquivo)
        nome_final = nome_final_para_arquivo(arquivo, rodovia, disciplina, sequencial)
        destino = os.path.join(pasta_disciplina, nome_final)

        tipo = detectar_tipo_documento(os.path.splitext(arquivo)[0])
        ext = os.path.splitext(arquivo)[1].lower()

        if tipo == "OUTROS":
            alertas.append({
                "tipo": "FORA_DO_ESPERADO",
                "arquivo": origem,
                "motivo": "Nao foi possivel identificar tipo documental RT/CR/DC/GRD/etc. Conferir manualmente."
            })

        if ext == "":
            alertas.append({
                "tipo": "SEM_EXTENSAO",
                "arquivo": origem,
                "motivo": "Arquivo sem extensao. Conferir manualmente."
            })

        destino_final = acao_renomear(origem, destino)

        registros.append({
            "acao": "RENOMEADO",
            "rodovia": rodovia,
            "disciplina": disciplina,
            "tipo": tipo,
            "origem": origem,
            "destino": destino_final,
            "arquivo_final": os.path.basename(destino_final),
            "observacao": ""
        })

        sequencial += 1

    verificar_conteudo_minimo(pasta_disciplina, rodovia, disciplina, alertas)


def verificar_conteudo_minimo(pasta_disciplina: str, rodovia: str, disciplina: str, alertas: list):
    arquivos = [
        f for f in os.listdir(caminho_longo_windows(pasta_disciplina))
        if os.path.isfile(caminho_longo_windows(os.path.join(pasta_disciplina, f)))
    ]

    tem_pdf = any(os.path.splitext(f)[1].lower() == ".pdf" for f in arquivos)
    tem_grd_pdf = any("GRD" in f.upper() and f.lower().endswith(".pdf") for f in arquivos)
    tem_grd_excel = any("GRD" in f.upper() and f.lower().endswith((".xlsx", ".xlsm", ".xls")) for f in arquivos)

    if not tem_pdf:
        alertas.append({
            "tipo": "POSSIVEL_PENDENCIA",
            "arquivo": pasta_disciplina,
            "motivo": "Nao foi encontrado PDF na pasta da disciplina."
        })

    if not tem_grd_pdf:
        alertas.append({
            "tipo": "PENDENCIA_GRD",
            "arquivo": pasta_disciplina,
            "motivo": "Nao foi encontrada GRD em PDF. A diretriz pede GRD em PDF."
        })

    if not tem_grd_excel:
        alertas.append({
            "tipo": "PENDENCIA_GRD",
            "arquivo": pasta_disciplina,
            "motivo": "Nao foi encontrada GRD em Excel. A diretriz pede GRD em Excel editavel."
        })


def processar_tudo():
    registros = []
    alertas = []

    for rodovia in PROXIMAS_GRDS:
        pasta_rodovia = os.path.join(BASE_DIR, rodovia)

        if not os.path.exists(caminho_longo_windows(pasta_rodovia)):
            alertas.append({
                "tipo": "RODOVIA_NAO_ENCONTRADA",
                "arquivo": pasta_rodovia,
                "motivo": "Pasta da rodovia nao encontrada."
            })
            continue

        for item in os.listdir(caminho_longo_windows(pasta_rodovia)):
            pasta_disciplina = os.path.join(pasta_rodovia, item)

            if not os.path.isdir(caminho_longo_windows(pasta_disciplina)):
                continue

            disciplina = obter_disciplina_por_nome_pasta(item)

            if not disciplina:
                alertas.append({
                    "tipo": "DISCIPLINA_NAO_IDENTIFICADA",
                    "arquivo": pasta_disciplina,
                    "motivo": "Nome da pasta nao corresponde a uma disciplina esperada."
                })
                continue

            processar_pasta_disciplina(
                pasta_disciplina=pasta_disciplina,
                rodovia=rodovia,
                disciplina=disciplina,
                registros=registros,
                alertas=alertas
            )

    gerar_indices(registros, alertas)


# ============================================================
# SAIDAS / INDICES
# ============================================================

def gerar_indices(registros: list, alertas: list):
    pasta_saida = os.path.join(BASE_DIR, f"_INDICE_FINAL_PROG_{DATA_HORA}")

    if DRY_RUN:
        print(f"[TESTE] Criaria pasta de saida: {pasta_saida}")
    else:
        os.makedirs(caminho_longo_windows(pasta_saida), exist_ok=True)

    csv_indice = os.path.join(pasta_saida, "INDICE_COMPLETO_ARQUIVOS.csv")
    csv_alertas = os.path.join(pasta_saida, "ARQUIVOS_FORA_DO_ESPERADO.csv")
    txt_relatorio = os.path.join(pasta_saida, "RELATORIO_FINAL_ORGANIZACAO.txt")
    xlsx_indice = os.path.join(pasta_saida, "INDICE_COMPLETO_ARQUIVOS.xlsx")

    if not DRY_RUN:
        with open(caminho_longo_windows(csv_indice), "w", newline="", encoding="utf-8-sig") as f:
            campos = ["acao", "rodovia", "disciplina", "tipo", "arquivo_final", "origem", "destino", "observacao"]
            writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", delimiter=";")
            writer.writeheader()
            writer.writerows(registros)

        with open(caminho_longo_windows(csv_alertas), "w", newline="", encoding="utf-8-sig") as f:
            campos = ["tipo", "arquivo", "motivo"]
            writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore", delimiter=";")
            writer.writeheader()
            writer.writerows(alertas)

        with open(caminho_longo_windows(txt_relatorio), "w", encoding="utf-8") as f:
            f.write("RELATORIO FINAL DE ORGANIZACAO - Programa / CERTIFICADORA ENTREGA\n")
            f.write("=" * 80 + "\n")
            f.write(f"Data/hora: {datetime.today().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Pasta base: {BASE_DIR}\n")
            f.write(f"Total de arquivos processados: {len(registros)}\n")
            f.write(f"Total de alertas/pendencias: {len(alertas)}\n")
            f.write("\n")
            f.write("PROXIMAS GRDS USADAS COMO REFERENCIA:\n")
            for rodovia, grd in PROXIMAS_GRDS.items():
                f.write(f"- {rodovia}: {grd}\n")
            f.write("\n")
            f.write("ARQUIVOS PROCESSADOS:\n")
            f.write("-" * 80 + "\n")
            for r in registros:
                f.write(f"{r.get('rodovia', '')} | {r.get('disciplina', '')} | {r.get('tipo', '')} | {r.get('arquivo_final', '')}\n")
            f.write("\n")
            f.write("FORA DO ESPERADO / VERIFICAR:\n")
            f.write("-" * 80 + "\n")
            for a in alertas:
                f.write(f"{a.get('tipo', '')} | {a.get('arquivo', '')} | {a.get('motivo', '')}\n")

        tentar_gerar_excel(xlsx_indice, registros, alertas)

    print("")
    print("=" * 80)
    print("[FINALIZADO EM MODO TESTE]" if DRY_RUN else "[FINALIZADO]")
    print(f"Arquivos processados: {len(registros)}")
    print(f"Alertas/pendencias: {len(alertas)}")
    print("")
    print("Saidas:")
    print(f"- {csv_indice}")
    print(f"- {csv_alertas}")
    print(f"- {txt_relatorio}")
    print(f"- {xlsx_indice}")
    print("=" * 80)

    if DRY_RUN:
        print("")
        print("ATENCAO: DRY_RUN esta como True.")
        print("Nada foi movido ou renomeado.")
        print("Depois de conferir o teste, mude DRY_RUN = False e rode novamente.")


def tentar_gerar_excel(xlsx_path: str, registros: list, alertas: list):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        wb = Workbook()

        ws = wb.active
        ws.title = "Indice Completo"

        headers = ["Rodovia", "Disciplina", "Tipo", "Arquivo final", "Origem", "Destino", "Acao", "Observacao"]
        ws.append(headers)

        for r in registros:
            ws.append([
                r.get("rodovia", ""),
                r.get("disciplina", ""),
                r.get("tipo", ""),
                r.get("arquivo_final", ""),
                r.get("origem", ""),
                r.get("destino", ""),
                r.get("acao", ""),
                r.get("observacao", ""),
            ])

        ws2 = wb.create_sheet("Fora do Esperado")
        ws2.append(["Tipo", "Arquivo/Pasta", "Motivo"])

        for a in alertas:
            ws2.append([
                a.get("tipo", ""),
                a.get("arquivo", ""),
                a.get("motivo", ""),
            ])

        ws3 = wb.create_sheet("Resumo GRDs")
        ws3.append(["Rodovia", "GRD sugerida"])
        for rodovia, grd in PROXIMAS_GRDS.items():
            ws3.append([rodovia, grd])

        for aba in [ws, ws2, ws3]:
            for cell in aba[1]:
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="D9EAF7")
                cell.alignment = Alignment(horizontal="center")

            for col in aba.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    value = str(cell.value) if cell.value is not None else ""
                    max_len = max(max_len, len(value))
                aba.column_dimensions[col_letter].width = min(max_len + 2, 70)

            aba.freeze_panes = "A2"

        wb.save(caminho_longo_windows(xlsx_path))

    except Exception as e:
        print("[AVISO] Nao foi possivel gerar Excel .xlsx.")
        print("O CSV e TXT foram gerados normalmente.")
        print(f"Motivo: {e}")


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":
    processar_tudo()