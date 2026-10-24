# Evolução planejada

Entregue em 0.2.1-preview: instalação dos JSONs Geyser enviados, preservação de definições existentes e auditoria recursiva de ícones. A migração completa de mecânicas continua pendente.

Objetivo: um único plugin gerenciando blocos, itens, móveis, receitas e representações Java/Bedrock, substituindo gradualmente os gerenciadores atuais. Os marcos abaixo são planos, sem promessa de versão ou prazo.

| Marco | Critério de conclusão |
|---|---|
| Validar a preview | Colocação, quebra, proteção, reinicialização e visual nas duas edições em servidor real |
| Registro extensível | IDs configuráveis, validação de referências e reserva persistente de estados sem conflitos |
| Compilador incremental | Origem e hashes, importação Rainbow e mesclagem semântica que preserve edições manuais |
| Blocos e itens completos | Ferramentas, dureza, atributos, drops e estados condicionais |
| Receitas | Ingredientes pela identidade real, receitas configuráveis e validação de duplicação |
| Móveis | Posicionamento, colisão, persistência e representações por edição |
| Migração | Inventário e importação dos dados CraftEngine/Oraxen/MeowFurniture/RecipeCrafter com backup e verificação |
| Integração Terra2 | Minérios e conteúdo dimensionais com registros estáveis |

Os registros futuros `GP_Items`, `GP_Blocks` e `GP_Entities` ainda não são arquivos de configuração funcionais desta preview. Modelos e IA de criaturas pertencem ao outro ramal e não estão implementados aqui.

A substituição de um gerenciador só deve ocorrer após cobertura dos recursos efetivamente usados pelo servidor e validação dos mundos existentes.
