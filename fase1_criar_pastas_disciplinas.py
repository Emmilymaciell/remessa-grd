import os
import re
import unicodedata
from datetime import datetime

# Pasta de entrega à Certificadora (uma subpasta por rodovia). Variável de ambiente ou ./entrega
BASE_DIR = os.environ.get("REMESSA_BASE_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "entrega"))

# True = só testa / False = cria e renomeia de verdade
DRY_RUN = False

# Data de hoje no padrão AAAA.MM.DD
DATA_HOJE = datetime.today().strftime("%Y.%m.%d")

DADOS = {
    "RD-102A": [
        "Relatório de Atividades Preliminares",
        "Estudos de Tráfego",
        "Estudos Topográficos",
        "Estudos Geológicos",
        "Diagnóstico Ambiental Prévio DAP",
        "Documentação para Declaração de Utilidade Pública DUP",
        "Estudos Hidrológicos",
    ],
    "RD-101": [
        "Relatório de Atividades Preliminares",
        "Estudos de Tráfego",
        "Estudos Topográficos",
        "Estudos Hidrológicos",
    ],
    "RD-104": [
        "Relatório de Atividades Preliminares",
        "Estudos de Tráfego",
        "Estudos Topográficos",
        "Estudos Geológicos",
        "Diagnóstico Ambiental Prévio DAP",
        "Estudos Hidrológicos",
    ],
    "RD-103": [
        "Relatório de Atividades Preliminares",
        "Estudos de Tráfego",
        "Estudos Topográficos",
        "Estudos Geológicos",
        "Diagnóstico Ambiental Prévio DAP",
    ],
}


def caminho_longo(path: str) -> str:
    path_abs = os.path.abspath(path)
    if os.name == "nt" and not path_abs.startswith("\\\\?\\"):
        return "\\\\?\\" + path_abs
    return path_abs


def remover_acentos(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def limpar_nome(texto: str) -> str:
    texto = remover_acentos(texto).upper()
    texto = re.sub(r"[^A-Z0-9 \-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def criar_pasta(path: str):
    if DRY_RUN:
        print(f"[TESTE] Criaria/verificaria: {path}")
    else:
        os.makedirs(caminho_longo(path), exist_ok=True)
        print(f"[OK] Pasta criada/verificada: {path}")


def disciplina_sem_data(nome_pasta: str) -> str:
    nome = limpar_nome(nome_pasta)
    nome = re.sub(r"^\d{4}\.\d{2}\.\d{2}\s*-\s*", "", nome).strip()
    return nome


def main():
    relatorio = []
    total = 0

    relatorio.append("FASE 1 - ESTRUTURA DE PASTAS DAS DISCIPLINAS")
    relatorio.append("=" * 80)
    relatorio.append(f"Pasta base: {BASE_DIR}")
    relatorio.append(f"Data usada nas pastas: {DATA_HOJE}")
    relatorio.append("")

    for rodovia, disciplinas in DADOS.items():
        pasta_rodovia = os.path.join(BASE_DIR, rodovia)
        criar_pasta(pasta_rodovia)

        relatorio.append(rodovia)

        for disciplina in disciplinas:
            nome_disciplina = limpar_nome(disciplina)
            nome_correto = f"{DATA_HOJE} - {nome_disciplina}"
            caminho_correto = os.path.join(pasta_rodovia, nome_correto)

            # Procura se já existe a disciplina com outra data/nome parecido
            encontrada = None
            if os.path.isdir(caminho_longo(pasta_rodovia)):
                for item in os.listdir(caminho_longo(pasta_rodovia)):
                    caminho_item = os.path.join(pasta_rodovia, item)
                    if not os.path.isdir(caminho_longo(caminho_item)):
                        continue

                    if item.startswith("_INDICE"):
                        continue

                    if disciplina_sem_data(item) == nome_disciplina:
                        encontrada = caminho_item
                        break

            if encontrada and os.path.abspath(encontrada) != os.path.abspath(caminho_correto):
                if DRY_RUN:
                    print(f"[TESTE] Renomearia: {encontrada} -> {caminho_correto}")
                else:
                    if os.path.exists(caminho_longo(caminho_correto)):
                        print(f"[AVISO] Ja existe, mantido: {caminho_correto}")
                    else:
                        os.rename(caminho_longo(encontrada), caminho_longo(caminho_correto))
                        print(f"[OK] Pasta renomeada: {encontrada} -> {caminho_correto}")
            else:
                criar_pasta(caminho_correto)

            relatorio.append(f"  - {nome_correto}")
            total += 1

        relatorio.append("")

    relatorio.append("=" * 80)
    relatorio.append(f"Total de pastas criadas/verificadas: {total}")
    relatorio.append("Observacao: esta fase NAO mexe em arquivos e NAO cria GRD.")

    relatorio_path = os.path.join(BASE_DIR, "FASE1_ESTRUTURA_PASTAS_DISCIPLINAS.txt")

    if DRY_RUN:
        print("")
        print("\n".join(relatorio))
    else:
        with open(caminho_longo(relatorio_path), "w", encoding="utf-8") as f:
            f.write("\n".join(relatorio))

        print("")
        print("=" * 80)
        print("[FINALIZADO - FASE 1]")
        print(f"Relatorio criado em: {relatorio_path}")
        print(f"Total de pastas: {total}")
        print("=" * 80)


if __name__ == "__main__":
    main()