# GoldenPotGen — EtherCraft

Motor de conteúdo para Paper com uma identidade comum para Java e Bedrock, distribuído em **um único GoldenPotGen.jar**. Gera dois pacotes separados e conecta a representação Bedrock pela API pública do Geyser.

**Versão atual: 0.2.1-preview, experimental.** Compilada contra APIs reais; ainda sem validação em servidor Paper e clientes Minecraft. Não substitui integralmente CraftEngine, Oraxen, MeowFurniture ou RecipeCrafter.

- [Manual do administrador](docs/MANUAL.md)
- [Arquitetura e desenvolvimento](docs/ARQUITETURA.md)
- [Plano de evolução](docs/ROADMAP.md)
- [Validação detalhada e limitações](docs/VALIDACAO-E-LIMITACOES.txt)
- [Baixar JAR da preview](dist/GoldenPotGen-0.2.1-preview.jar?raw=true)

## Implementado

Um item/bloco `goldenpot:ambrosio_ore`, com textura oficial de Ambrósio do EtherTexture v0.0.9.1. Identidade do item em PDC, identidade de posição no PDC do chunk, colocação, quebra e drop próprio. Usa estado de note block, sem entidades auxiliares. Registra bloco, item e pack pela API Geyser, e prepara o pack Java para instalação manual ou distribuição por URL.

As outras imagens e modelos dos packs-base são preservados, mas não ganham automaticamente mecânicas, receitas ou registro no servidor.

## Estrutura

`src/main/java`: implementação própria. `src/main/resources`: configuração e dois packs-base oficiais. `src/test/java`: teste do compilador de recursos. `dist`: JAR já compilado. `docs`: documentação em português.

O Golden Pot original em Python permanece na raiz do repositório como ferramenta existente. O plugin Paper não executa nem incorpora automaticamente seu mesclador semântico.

## Atualização 0.2.1

Mappings Geyser incorporados e exportados na inicialização, com prioridade para seletores existentes, relatório de conflitos e preservação de edições manuais. Uma textura oficial recuperada; 65 referências de ícones ainda precisam dos recursos correspondentes. [Detalhes dos mappings](docs/MAPPINGS.md).
