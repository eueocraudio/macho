#!/usr/bin/env bash

set -e

echo "==> Instalando dependências do sistema..."
apt-get update -qq
apt-get install -y ffmpeg librubberband-dev python3 python3-pip

echo "==> Instalando dependências Python..."
runuser user -c "pip3 install --break-system-packages rich python-dotenv faster-whisper nltk spacy anthropic"

echo "==> Baixando modelos spaCy..."
runuser user -c "python3 -m spacy download pt_core_news_sm --break-system-packages"
runuser user -c "python3 -m spacy download en_core_web_sm --break-system-packages"

echo "==> Baixando dados NLTK..."
runuser user -c "python3 -c \"import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')\""

echo "==> Criando diretórios de vídeo..."
mkdir -p /home/user/Videos/gravado
mkdir -p /home/user/Videos/final
mkdir -p /home/user/Videos/processado

echo "==> Instalação concluída."
