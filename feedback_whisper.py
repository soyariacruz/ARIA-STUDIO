"""Transcribe un audio en español con Whisper en este ordenador (Apple Silicon). Lo usa feedback_informe.py.
Se ejecuta con /usr/bin/python3, que es el que tiene mlx_whisper instalado.  Uso: /usr/bin/python3 feedback_whisper.py AUDIO"""
import sys
import mlx_whisper

r = mlx_whisper.transcribe(sys.argv[1], path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language='es')
print((r.get('text') or '').strip())
