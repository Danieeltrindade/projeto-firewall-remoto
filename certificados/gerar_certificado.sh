#!/usr/bin/env bash
# Gera o certificado TLS autoassinado do servidor de controle.
# Executar NA MÁQUINA B, no Git Bash, a partir da raiz do projeto:
#     bash certificados/gerar_certificado.sh
# A chave privada (servidor.key) nunca deve sair da máquina B.

set -e                      # interrompe o script no primeiro erro
export MSYS_NO_PATHCONV=1   # impede o Git Bash de converter "/CN=..." em caminho do Windows

IP_SERVIDOR="192.168.56.10"
PASTA="certificados"

openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$PASTA/servidor.key" \
    -out "$PASTA/servidor.crt" \
    -days 365 \
    -subj "/CN=servidor-firewall-lab" \
    -addext "subjectAltName=IP:$IP_SERVIDOR"

echo "Certificado gerado em $PASTA/servidor.crt (válido por 365 dias)."
echo "Chave privada em $PASTA/servidor.key: NÃO copie este arquivo para outra máquina."