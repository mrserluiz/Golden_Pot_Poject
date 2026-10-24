# Mappings Geyser — 0.2.1-preview

## Conteúdo importado

Os quatro JSONs enviados são preservados byte a byte nos recursos do JAR e em `sources/mappings/` na primeira execução. O arquivo `.md` contém só 115 entradas e não é fonte do importador.

- Itens: formato 2, 46 materiais Java, 1.793 entradas superiores. Incluindo os grupos: 1.839 definições de itens e 232 ícones distintos.
- Blocos: formato 1, `minecraft:light` para cultivos Aeternum com 16 estados. Texturas e geometria dos cultivos já estão no pack Bedrock.
- Skulls e estilos de waypoint: formato 1, vazios no material fornecido.

A fonte Java `assets/ether/textures/item/custom.png` é copiada sem alterações para o Bedrock e associada ao ícone ausente `ether.item_custom`. As 251 entradas do atlas original são preservadas. O pack gerado inclui também Ambrósio quando o experimento está ativo.

A contagem inicial de 18 ícones ausentes só contemplava entradas superiores. A auditoria recursiva encontrou 66; após recuperar a picareta celeste, restam 65, incluindo armaduras de topázio e seus trims. Os packs fornecidos não contêm os recursos suficientes para corrigir essas referências fielmente. Não são removidas nem substituídas por artes genéricas.

## Instalação automática

No carregamento do GoldenPotGen, o instalador usa o diretório público `Geyser-Spigot/custom_mappings/`, antes da habilitação dos plugins. As identidades do Ambrósio continuam registradas pela API. Nenhuma classe interna do Geyser é usada.

Arquivos gerados: `goldenpotgen_item.json`, `goldenpotgen_block.json`, `goldenpotgen_skull.json` e `goldenpotgen_waypoint_style.json`. Não copie manualmente os JSONs do kit para esse diretório: eles são fontes de referência e o plugin faz a exportação.

Reinicie completamente; nunca PlugMan/reload. A integração do ciclo de inicialização ainda requer teste no Paper com a versão instalada do Geyser. Se o Geyser já tiver lido o diretório nessa versão, os arquivos estarão prontos para o próximo reinício. O status mostra **exportação**, não confirmação de que os itens antigos foram registrados.

## Preservação e conflitos

O instalador inspeciona os JSONs existentes no diretório e suas subpastas. Para itens, compara material Java e seletor (tipo, model, CustomModelData e predicados). Se já existe um seletor, a definição existente prevalece. Os demais seletores são exportados; a sequência original é mantida. Grupos são tratados como unidades, preservando as definições e predicados internos. Para blocos/skulls/waypoints, uma chave raiz já existente prevalece integralmente: não se arrisca mesclar parcialmente estados de cultivos.

Os arquivos de outros plugins não são alterados. Uma cópia dos últimos bytes escritos é armazenada em `mapping-receipts/`; se um administrador editar o arquivo gerenciado, o plugin preserva a edição e interrompe atualizações daquele arquivo. Uma fonte em `sources/mappings/` já existente também não é substituída por uma nova build. Faça backup antes de qualquer migração manual.

Não é uma migração de mecânicas: esses mappings permitem ao Geyser associar aparências a itens existentes; não criam receitas, efeitos, móveis, cultivos ou drops que pertenciam aos outros plugins. Conflitos complexos entre seletores diferentes que se sobrepõem precisam de revisão pelo administrador.

## Relatórios

- `reports/mapping-install.json`: quantidades exportadas/ignoradas, conflitos e arquivos preservados.
- `reports/mapping-assets.json`: ícones ausentes no atlas, incluindo referências dentro dos grupos.

A saída de uma instalação limpa contém 1.793 entradas superiores de itens e a definição de bloco com os 16 estados. Se já existem os mesmos mappings, o arquivo gerenciado só recebe o conteúdo ainda não coberto.

## Testes executados

Compilação contra Paper/Geyser reais. Testes locais de preservação de packs e atlas, mesma textura entre edições, exportação repetida, supressão de duplicatas existentes, arquivos alheios intactos, proteção de edição manual, 16 estados de cultivos e auditoria recursiva. Ainda sem execução em servidor ou clientes Minecraft.
