# Manual do administrador — 0.2.1-preview

## Requisitos e instalação

A compilação utilizou Paper API 1.21.11-R0.1 build 91 e o Geyser-Spigot 2.11.3-SNAPSHOT fornecido pelo servidor. Use o Java exigido pelo Paper (21 ou superior conforme a versão do servidor). Não foi validada compatibilidade com outras APIs Geyser, Paper 26.x ou Folia.

1. Prepare um servidor de teste separado, sem CraftEngine, Oraxen ou Nexo disputando estados de blocos. Não remova gerenciadores de um mundo existente para testar: esta preview não migra seus registros.
2. Coloque `GoldenPotGen-0.2.1-preview.jar` em `plugins/`. Mantenha Geyser-Spigot e a infraestrutura Floodgate usada no servidor. Eles são externos ao JAR.
3. Habilite conteúdo personalizado na configuração da versão instalada do Geyser.
4. Reinicie completamente. Não utilize PlugMan nem reload: os registros Geyser dependem da inicialização.
5. Execute `/gpg status`, aceite os packs e use `/gpg give` no jogo.

## Comandos e permissão

| Comando | Comportamento |
|---|---|
| `/gpg` ou `/gpg status` | Informa geração dos packs, bloco experimental e registros Geyser |
| `/gpg give` | Entrega uma unidade do minério ao próprio jogador; requer bloco habilitado |
| `/gpg pack` | Solicita o pack Java por URL; no console informa a pasta de saída |

Todos exigem `goldenpotgen.admin`, concedida por padrão a operadores. `scan`, `validate` e `reload` não são comandos desta preview.

## Arquivos e configuração

Na primeira inicialização, o plugin copia os dois ZIPs internos para `plugins/GoldenPotGen/sources/`, sem sobrescrever fontes existentes. Produz:

- `generated/EtherTexture-Java-GoldenPotGen.zip`
- `generated/EtherTexture-Bedrock-GoldenPotGen.mcpack`
- `registry.json`: relatório gerado, não configuração editável de conteúdo.

Configuração em `plugins/GoldenPotGen/config.yml`:

```yaml
experimental-blocks: true
java-pack:
  url: ''
  send-on-join: false
```

`experimental-blocks` controla o bloco de teste. A detecção de CraftEngine/Oraxen/Nexo também desativa o experimento. Reinicie após alterações. A substituição manual das fontes exige backup e nova validação de conflitos; não existe importador genérico nesta versão.

## Java

Instale o ZIP gerado manualmente no cliente ou hospede esse arquivo exato em uma URL pública de download direto. Configure `java-pack.url` e reinicie. `/gpg pack` envia a solicitação com SHA-1 do arquivo local gerado. `send-on-join: true` solicita o pack na entrada. O plugin não oferece hospedagem HTTP e o jogador precisa aceitar os recursos.

## Bedrock/Geyser

O plugin registra o MCPACK pelo evento público do Geyser, substituindo somente o mesmo UUID na lista de execução. Não apaga packs de origem. Não copie outra instância desse pack para a pasta de packs do Geyser. A ponte registra também bloco e item: enviar somente o MCPACK não implementa o conteúdo.

Em `/gpg status`, os indicadores `blocos`, `itens` e `pack` confirmam execução do registro, não comprovam renderização no cliente. Compare no jogo Java e Bedrock após aceitar os recursos.

## Testes no servidor

Compare inventário, mão, item dropado e bloco colocado nas duas edições. Coloque o bloco, descarregue/recarregue o chunk, reinicie e quebre em sobrevivência. Confirme ausência de drop no criativo. Verifique cancelamento por proteção de terreno, inventário cheio, pistões, explosões e interações.

Tempo de mineração é vanilla. Pistões e explosões são bloqueados para o bloco experimental. O estado `minecraft:note_block[instrument=flute,note=24,powered=false]` fica reservado; um bloco vanilla nesse estado também recebe o visual do pack. Alterações externas por WorldEdit ou outros meios sem eventos podem deixar registros obsoletos.

## Diagnóstico

- **Bloco desativado:** confira a configuração e presença de outros gerenciadores.
- **Geyser ausente/indicadores falsos:** confira versão, conteúdo personalizado habilitado e erros no console; reinicie por completo.
- **Java sem textura:** use o ZIP gerado correto e confira URL, download e aceite.
- **Bedrock sem textura:** confira aceite, registro do pack, duplicação de UUID e compatibilidade da API instalada.
- **Falha de geração:** examine o console; o compilador rejeita recursos conflitantes, entradas ZIP duplicadas/inseguras e limites de tamanho.

Esta versão não tem atualização automática nem migração reversa. Antes de desinstalar, remova os blocos de teste e guarde backup do mundo e da pasta do plugin.

## Mappings herdados

A versão 0.2.1 exporta os mappings enviados antes da habilitação do Geyser e preserva arquivos existentes. Consulte [Mappings, conflitos e recursos ausentes](MAPPINGS.md). Reinicie por completo; caso o Geyser já tenha carregado os registros nessa versão, reinicie novamente. Não instale uma segunda cópia manual.
