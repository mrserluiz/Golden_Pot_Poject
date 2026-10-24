# Arquitetura e desenvolvimento

## Fluxo atual

`GoldenPotGen.onLoad()` prepara fontes e saídas e assina eventos Geyser. `onEnable()` registra eventos Paper e identidade PDC. `BedrockBridge` registra pack, bloco e item; `Resources` monta arquivos de recursos; `ResourceTest` valida o compilador sem iniciar servidor.

| Camada | Implementação atual |
|---|---|
| Identidade | Constante `goldenpot:ambrosio_ore`; ainda sem registro extensível por YAML |
| Item Java | Note block com PDC `content_id`, `item_model` e CustomModelData 720001 |
| Bloco Java | Estado vanilla reservado com modelo `cube_all` |
| Persistência | ID no PDC do chunk, chave por coordenadas locais e altura relativa ao mínimo do mundo |
| Bedrock | `GeyserDefineCustomBlocksEvent`, `GeyserDefineCustomItemsEvent` API v2 e `GeyserDefineResourcePacksEvent` |
| Recursos | Dois packs-base incorporados e duas saídas independentes |

O PNG oficial é compartilhado entre as representações geradas de Ambrósio. A geometria deste protótipo é um cubo; não existe conversão genérica de modelos Java para Bedrock.

## Compilador de recursos

Preserva entradas Java e recursos Bedrock, estendendo atlas e atualizando versão do manifesto Bedrock. Rejeita colisões de recursos diferentes, duplicatas e caminhos ZIP inseguros. Limites: 32 MiB por entrada e 256 MiB descompactados por pack. Escreve por arquivo temporário e tenta movimentação atômica, com alternativa quando indisponível. Não há mesclagem dos mappings Rainbow nesta preview.

## Compilar a partir do código

Requisitos: JDK 21, bibliotecas oficiais compatíveis com as utilizadas nesta preview. Não são distribuídos JARs de Paper, Geyser ou outros plugins no repositório. Obtenha os arquivos oficiais e mantenha em `lib/`: `paper-api.jar`, `Geyser-Spigot.jar`, `gson.jar`, `adventure-api.jar`, `adventure-key.jar`, `bungee-chat.jar` e as dependências adicionais exigidas pela API escolhida.

No diretório `goldenpotgen`, em shell POSIX:

```sh
mkdir -p build/classes build/test-classes
javac --release 21 -cp 'lib/*' -d build/classes src/main/java/br/com/ethercraft/goldenpot/*.java
cp -R src/main/resources/. build/classes/
javac --release 21 -cp 'lib/*:build/classes' -d build/test-classes src/test/java/br/com/ethercraft/goldenpot/ResourceTest.java
java -cp 'lib/*:build/classes:build/test-classes' br.com.ethercraft.goldenpot.ResourceTest src/main
jar --create --file build/GoldenPotGen-0.2.0-preview.jar -C build/classes .
```

A geração por esse procedimento não promete igualdade byte a byte do JAR distribuído, cujo empacotamento também inclui fontes. O teste recebe um diretório contendo `resources/` e cria `test-output/` nele. Em Windows, adapte separadores de classpath e comandos de cópia.

## Validação

O teste cobre preservação de fontes, entradas anteriores dos atlas, igualdade do PNG entre edições, reconstrução determinística do ZIP Java, rejeição de conflitos, proteção contra travessia ZIP e sintaxe JSON. Não testa ciclo Paper/Geyser, persistência real ou renderização. Esses testes dependem do roteiro do manual.

## Referências e ativos

CraftEngine e Oraxen são referências de mecanismos de estados vanilla; os eventos Geyser fundamentam a ponte. A implementação enviada é própria e não incorpora classes desses gerenciadores. Os ZIPs EtherTexture v0.0.9.1 são os ativos fornecidos pelo proprietário do servidor. A inclusão neste repositório não atribui automaticamente uma licença de redistribuição a código ou artes de terceiros; preserve os créditos e licenças aplicáveis.

- https://docs.oraxen.com/developers/api
- https://xiao-momi.github.io/craft-engine-wiki/configuration/block/
- https://geysermc.org/wiki/geyser/custom-blocks/
- https://geysermc.org/wiki/geyser/custom-items/
