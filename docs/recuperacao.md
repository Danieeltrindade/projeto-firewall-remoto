# Recuperação e limpeza das regras

Este documento explica como restaurar o tráfego na máquina B quando uma regra
de bloqueio do projeto ficou ativa e a comunicação com o servidor de controle
caiu (servidor desligado, travado, rede fora do ar).

Tudo aqui é feito **na própria máquina B**, em um PowerShell aberto **como
Administrador**, na pasta `C:\projetos\projeto-firewall-remoto`.

## 1. Script de recuperação (caminho normal)

```powershell
python -m servidor.recuperacao          # lista as regras e pede confirmação
python -m servidor.recuperacao --sim    # remove sem perguntar
```

O script:

1. confere se está rodando como Administrador;
2. lista as regras do grupo `ProjetoFirewallRemoto`;
3. pede confirmação (`s` para remover);
4. remove **apenas** as regras desse grupo;
5. consulta de novo e avisa se alguma regra sobrou.

Ele não usa a rede, então funciona mesmo com o servidor de controle desligado.
As regras de permissão do grupo `LaboratorioBase` (portas 5000 e 8080) não são
tocadas.

## 2. Comando manual equivalente

Se o Python não estiver disponível, os comandos abaixo fazem o mesmo:

```powershell
# Ver as regras do projeto
Get-NetFirewallRule -Group 'ProjetoFirewallRemoto' | Format-Table Name, Enabled, Action

# Remover todas as regras do projeto (e só elas)
Remove-NetFirewallRule -Group 'ProjetoFirewallRemoto'

# Conferir que as regras de permissão do laboratório continuam lá
Get-NetFirewallRule -Group 'LaboratorioBase' | Format-Table DisplayName, Enabled, Action
```

Nunca use `Remove-NetFirewallRule` sem `-Group` ou `-Name`: sem filtro, o
comando apagaria regras do próprio Windows.

## 3. Decisão: não remover as regras automaticamente ao encerrar o servidor

Avaliamos remover as regras do projeto sempre que o servidor fosse encerrado
(Ctrl+C) e decidimos **não** fazer isso:

- **O bloqueio é o estado pedido pelo operador.** Se o servidor for reiniciado
  (atualização, troca de configuração), a porta deve continuar bloqueada; uma
  limpeza automática liberaria o tráfego sem ninguém pedir.
- **Não cobriria os casos reais de falha.** Se o processo travar, for morto pelo
  Gerenciador de Tarefas ou a máquina desligar, o código de limpeza nem roda.
  A recuperação precisa existir de qualquer forma.
- **Ações explícitas são mais fáceis de auditar.** Toda remoção acontece por um
  pedido do cliente (registrado no `servidor.log`) ou por um operador local
  rodando a recuperação.

## 4. Último recurso: snapshot `base-limpa`

Se nada acima funcionar (firewall em estado desconhecido, máquina sem acesso),
restaure a VM para o snapshot `base-limpa` no VirtualBox:

1. Desligue a VM (Máquina → Fechar → Desligar).
2. Na lista de snapshots, selecione `base-limpa` e clique em **Restaurar**.
3. Ligue a VM. O firewall volta ao estado da preparação do ambiente
   (regras do `LaboratorioBase` criadas, nenhuma regra do projeto).

Atenção: tudo o que foi feito na VM depois do snapshot é perdido. Depois de
restaurar, faça `git pull` na pasta do projeto. O `config.json` e os
certificados não ficam no Git: se o snapshot for anterior a eles, gere ou
copie esses arquivos de novo.