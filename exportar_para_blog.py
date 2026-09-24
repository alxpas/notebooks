import os
import re
import shutil
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path

CAMINHO_HUGO = Path('..') / 'alxpas.github.io'

def exportar_notebook():
    arquivo_nb = input("Qual o nome do notebook para exportar (ex: analise.ipynb)? ")
    if not arquivo_nb.endswith('.ipynb'):
        arquivo_nb += '.ipynb'
        
    caminho_nb = Path(arquivo_nb)
    if not caminho_nb.exists():
        print(f"Erro: Arquivo '{arquivo_nb}' não encontrado nesta pasta.")
        return

    while True:
        titulo = input("Digite o título que aparecerá no Blog: ")
        confirmacao = input(f"Confirma o título \"{titulo}\"? Sim (s) ou (n): ").strip().lower()
        if confirmacao == 's':
            break

    nfkd = unicodedata.normalize('NFKD', titulo)
    sem_acento = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    slug = re.sub(r'[^a-z0-9]+', '-', sem_acento.lower()).strip('-')
    
    ano = datetime.now().year
    
    pasta_destino_hugo = CAMINHO_HUGO / 'content' / 'posts' / str(ano) / slug
    pasta_destino_hugo.mkdir(parents=True, exist_ok=True)
    
    print(f"\nConvertendo e enviando para {pasta_destino_hugo.name}...")
    subprocess.run([
        "jupyter", "nbconvert", 
        "--to", "markdown", 
        str(caminho_nb), 
        "--output-dir", str(pasta_destino_hugo)
    ])
    
    nome_base = caminho_nb.stem 
    md_gerado = pasta_destino_hugo / f"{nome_base}.md"
    index_md = pasta_destino_hugo / "index.md"
    pasta_imagens_nb = pasta_destino_hugo / f"{nome_base}_files"
    
    conteudo = md_gerado.read_text(encoding='utf-8')

    if pasta_imagens_nb.exists():
        for imagem in pasta_imagens_nb.iterdir():
            shutil.move(str(imagem), str(pasta_destino_hugo / imagem.name))
        pasta_imagens_nb.rmdir()
        
        conteudo = conteudo.replace(f"{nome_base}_files/", "")

    data_atual = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    front_matter = f"""---
title: "{titulo}"
date: {data_atual}
draft: true
description: ""
tags: []
---

"""
    index_md.write_text(front_matter + conteudo, encoding='utf-8')
        
    md_gerado.unlink()

    print("\n" + "="*50)
    print("EXPORTACAO CONCLUIDA COM SUCESSO!")
    print(f"O post esta no seu Hugo em: {pasta_destino_hugo}")
    print("="*50)

if __name__ == '__main__':
    exportar_notebook()