# Ambiente de laboratório

## Topologia

| Máquina | Papel    | Sistema                                                 | IP (rede do laboratório)                       |
| ------- | -------- | ------------------------------------------------------- | ---------------------------------------------- |
| A       | Cliente  | Windows 11 (notebook físico)                            | 192.168.56.1 (adaptador "Ethernet 2")          |
| B       | Servidor | Windows Server 2025 Standard Evaluation (VM VirtualBox) | 192.168.56.10 (fixo, adaptador "HostOnly-Lab") |

```
 Máquina A (notebook)                     Máquina B (VM)
 192.168.56.1  ◀──── Rede Host-Only ────▶ 192.168.56.10
                     192.168.56.0/24
                     (isolada, sem internet)
```

## Máquina virtual B

| Item                   | Valor                                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| Hipervisor             | Oracle VirtualBox 7.2                                                                           |
| Nome da VM             | `B-Servidor-Firewall` (tipo no VirtualBox: Windows 2022 64-bit; sistema instalado: Server 2025) |
| Memória / CPUs / Disco | 4 GB / 2 vCPUs / 50 GB (dinâmico)                                                               |
| Edição                 | Windows Server 2025 Standard Evaluation (Desktop Experience)                                    |
| Fuso horário           | Brasília, UTC−3 (`E. South America Standard Time`), igual ao da máquina A, para comparar logs   |
| Adaptador 1            | NAT (`NAT-Internet`, 10.0.2.15): só para instalação e `git pull`; desconectado na demonstração  |
| Adaptador 2            | Host-Only (`HostOnly-Lab`): IP fixo 192.168.56.10/24, **sem gateway**                           |

## Software

| Máquina | Python                       | Git                                         |
| ------- | ---------------------------- | ------------------------------------------- |
| A       | 3.13.9                       | Git for Windows (Git Bash)                  |
| B       | 3.13.9 (python.org, no PATH) | 2.56.0 (somente clone e pull, nunca commit) |

Na máquina B, o repositório fica em `C:\projetos\projeto-firewall-remoto`, na branch `develop`.

## Regras de permissão (grupo `LaboratorioBase`)

Criadas manualmente na máquina B (PowerShell como Administrador):

```powershell
New-NetFirewallRule -DisplayName "LAB - Permitir controle TCP 5000" -Group "LaboratorioBase" -Direction Inbound -Protocol TCP -LocalPort 5000 -RemoteAddress 192.168.56.0/24 -Action Allow -Profile Any
New-NetFirewallRule -DisplayName "LAB - Permitir HTTP teste TCP 8080" -Group "LaboratorioBase" -Direction Inbound -Protocol TCP -LocalPort 8080 -RemoteAddress 192.168.56.0/24 -Action Allow -Profile Any
```

- Aceitam conexões **somente** da rede 192.168.56.0/24.
- Ficam em um grupo diferente do grupo do projeto (`ProjetoFirewallRemoto`), portanto a limpeza do projeto nunca as remove.
- A regra de bloqueio criada pelo projeto tem precedência sobre elas. É isso que a demonstração comprova.

## Verificação de conectividade

Na máquina B:

```powershell
python -m http.server 8080 --bind 192.168.56.10
```

Na máquina A (PowerShell):

```powershell
Test-NetConnection 192.168.56.10 -Port 8080   # com servidor: TcpTestSucceeded : True
                                              # sem servidor: TcpTestSucceeded : False (contraprova)
```

> O ping (ICMP) é bloqueado por padrão no Windows e **não** é usado como teste de conectividade.

## Snapshots

| Nome               | Conteúdo                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `instalacao-limpa` | Windows instalado + Guest Additions                                                                                 |
| `base-limpa`       | Rede, fuso horário, Python, Git, regras de permissão e repositório clonado. **Ponto de restauração do laboratório** |

Os snapshots foram criados com a VM **desligada**, para restaurar um sistema limpo, sem programas em execução.

## Privilégios

O servidor de controle deve ser executado em um PowerShell **como Administrador** na máquina B, porque criar e remover regras de firewall exige privilégio administrativo. O cliente, na máquina A, roda como usuário comum.
