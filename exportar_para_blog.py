"""
Exportador de Notebook -> Post Jekyll Chirpy
---------------------------------------------
Roda a partir de dentro da própria pasta de notebooks (ex: notebooks/),
busca um .ipynb recursivamente nas subpastas, converte para Markdown e
organiza o resultado no site Jekyll (tema Chirpy) em:

    _posts/<AAAA>/AAAA-MM-DD-nome-do-notebook.md
    assets/img/posts/<AAAA>/<AAAA-MM-DD-nome-do-notebook>/<imagens...>

O ano usado é sempre o ano corrente no momento em que o script roda; a
pasta do ano é criada automaticamente se ainda não existir. O nome do
arquivo .md continua seguindo o padrão AAAA-MM-DD-titulo.md exigido
pelo Jekyll, só que agora dentro de uma subpasta por ano. As imagens
ficam em assets/img/posts/, organizadas por ano e por post. O front
matter usa "img: / path:" (aninhado) apontando para essa pasta, e as
referências de imagem dentro do corpo do markdown levam o caminho
completo do arquivo (não dependem de nenhum atalho do Chirpy).
"""

import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------
DIR_NOTEBOOKS = Path('.')  # roda a partir da própria pasta de notebooks
CAMINHO_JEKYLL = Path('..') / 'alxpas.github.io'  # ajuste se o repo do Chirpy for outro
DIR_POSTS = CAMINHO_JEKYLL / '_posts'
DIR_IMAGENS_BASE = CAMINHO_JEKYLL / 'assets' / 'img' / 'posts'


def slugificar(texto: str) -> str:
    """Remove acentos e caracteres especiais, retornando um slug em minúsculas."""
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '-', sem_acento.lower()).strip('-')


def escolher_notebook() -> Path:
    """Busca notebooks (.ipynb) recursivamente a partir da pasta atual e permite escolher um."""
    notebooks = sorted(
        p for p in DIR_NOTEBOOKS.rglob('*.ipynb')
        if '.ipynb_checkpoints' not in p.parts
    )
    if not notebooks:
        print(f"Nenhum notebook (.ipynb) encontrado a partir de '{DIR_NOTEBOOKS.resolve()}'.")
        raise SystemExit(1)

    print("\nNotebooks disponíveis:")
    for i, nb in enumerate(notebooks, start=1):
        print(f"  [{i}] {nb}")

    while True:
        escolha = input("\nDigite o número ou o caminho do notebook: ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(notebooks):
            return notebooks[int(escolha) - 1]
        candidato = escolha if escolha.endswith('.ipynb') else f"{escolha}.ipynb"
        caminho = Path(candidato)
        if caminho.exists():
            return caminho
        print("Notebook não encontrado, tente novamente.")


def exportar_notebook():
    caminho_nb = escolher_notebook()

    while True:
        titulo = input("Digite o título que aparecerá no Blog: ").strip()
        confirmacao = input(f"Confirma o título \"{titulo}\"? Sim (s) ou (n): ").strip().lower()
        if confirmacao == 's':
            break

    categorias_in = input("Categorias (separadas por vírgula, opcional): ").strip()
    tags_in = input("Tags (separadas por vírgula, opcional): ").strip()
    categorias = [c.strip() for c in categorias_in.split(',') if c.strip()]
    tags = [t.strip() for t in tags_in.split(',') if t.strip()]

    nome_base = slugificar(caminho_nb.stem)  # nome do notebook, usado no nome do post
    agora = datetime.now()
    data_str = agora.strftime("%Y-%m-%d")
    ano_dir = agora.strftime("%Y")  # pasta do ano, verificada/criada na hora da execução
    nome_post = f"{data_str}-{nome_base}"

    pasta_posts_ano = DIR_POSTS / ano_dir
    pasta_posts_ano.mkdir(parents=True, exist_ok=True)

    # Jekyll não usa "page bundles" como o Hugo, então convertemos em uma
    # pasta temporária e depois movemos só o .md final para _posts/<ano>/.
    pasta_temp = DIR_POSTS / f"__tmp_{nome_post}"
    pasta_temp.mkdir(parents=True, exist_ok=True)

    print(f"\nConvertendo notebook...")
    # Usa "python -m nbconvert" (via sys.executable) em vez de chamar o
    # executável "jupyter" diretamente: o python.exe costuma estar liberado
    # por políticas de Application Control (WDAC/AppLocker) do Windows,
    # enquanto executáveis gerados à parte (jupyter.exe, jupyter-nbconvert.exe)
    # às vezes são bloqueados (WinError 4551).
    subprocess.run([
        sys.executable, "-m", "nbconvert",
        "--to", "markdown",
        str(caminho_nb),
        "--output-dir", str(pasta_temp)
    ], check=True)

    md_gerado = pasta_temp / f"{caminho_nb.stem}.md"
    pasta_imagens_nb = pasta_temp / f"{caminho_nb.stem}_files"

    conteudo = md_gerado.read_text(encoding='utf-8')

    # Imagens organizadas em assets/img/posts/<AAAA>/<AAAA-MM-DD-nome>/
    pasta_imagens_destino = DIR_IMAGENS_BASE / ano_dir / nome_post
    pasta_imagens_destino.mkdir(parents=True, exist_ok=True)

    img_path_web = f"/assets/img/posts/{ano_dir}/{nome_post}/"

    if pasta_imagens_nb.exists():
        for imagem in pasta_imagens_nb.iterdir():
            shutil.move(str(imagem), str(pasta_imagens_destino / imagem.name))
        pasta_imagens_nb.rmdir()
        # troca o prefixo de pasta gerado pelo nbconvert pelo caminho
        # completo da imagem (sem depender de img_path no front matter)
        conteudo = conteudo.replace(f"{caminho_nb.stem}_files/", img_path_web)

    md_gerado.unlink()
    pasta_temp.rmdir()

    data_atual = agora.strftime("%Y-%m-%d %H:%M:%S -0300")

    linhas_front_matter = [
        "---",
        f'title: "{titulo}"',
        f"date: {data_atual}",
        "draft: true",
    ]
    if categorias:
        linhas_front_matter.append("categories: [" + ", ".join(categorias) + "]")
    if tags:
        linhas_front_matter.append("tags: [" + ", ".join(tags) + "]")
    linhas_front_matter.append("img:")
    linhas_front_matter.append(f"  path: {img_path_web}")
    linhas_front_matter.append("---\n")

    front_matter = "\n".join(linhas_front_matter)

    arquivo_md_final = pasta_posts_ano / f"{nome_post}.md"
    arquivo_md_final.write_text(front_matter + conteudo, encoding='utf-8')

    print("\n" + "=" * 50)
    print("EXPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f"Post:     {arquivo_md_final}")
    print(f"Imagens:  {pasta_imagens_destino}")
    print("=" * 50)


if __name__ == '__main__':
    exportar_notebook()