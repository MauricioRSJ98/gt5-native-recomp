# GT5 Native Recomp

Projeto experimental de recompilação nativa do **Gran Turismo 5 de PS3 — BCUS98114, atualização 2.17**, para **Windows x86-64 com Vulkan**.

**Pré-alfa: ainda não desenha um quadro do jogo e não é jogável.** O objetivo imediato é chegar à primeira imagem real, depois ao menu e a uma corrida, mesmo com desempenho muito baixo.

[Documentação principal](README.md) · [Roteiro](https://github.com/MauricioRSJ98/gt5-native-recomp/issues/1) · [Compilação](docs/BUILDING.md) · [Estado atual](docs/STATUS.md) · [Como contribuir](CONTRIBUTING.md) · [Créditos](docs/CREDITS.md)

## Como funciona

O caminho pretendido converte código PPU e SPU antecipadamente em código nativo. Um runtime implementa serviços necessários do PS3 e traduz o processamento dos comandos RSX para Vulkan. Código de CPU ausente causa uma parada controlada para investigação/recompilação. O interpretador de instruções SPU é excluído do executável; DirectX 12 está desativado.

No checkpoint local de 29/10/2026, existem 43.525 entradas PPU e seis imagens ELF SPU mais 16 imagens SPU brutas compiladas/registradas. O Vulkan inicializa, o programa lê a ISO e os patches locais e alcança a configuração de buffers, áudio e controles XInput. **Ainda não observamos draw ou flip/frame do jogo.** Esses números não são porcentagens de conclusão nem validação de todas as funções.

## Quer ajudar?

Precisamos de investigação de PPU/SPU, SPURS, sincronização, RSX/Vulkan, serviços USB e melhoria da reprodução da compilação. As [issues](https://github.com/MauricioRSJ98/gt5-native-recomp/issues) identificam bloqueios concretos; use [Discussions](https://github.com/MauricioRSJ98/gt5-native-recomp/discussions) para dúvidas e planejamento. Contribuições pequenas com evidência são bem-vindas.

Não envie executáveis, ISOs, arquivos do jogo, firmware, SDKs, chaves, programas SPU capturados ou corpos de código recompilado extraídos do jogo. Cada colaborador fornece seus próprios dados locais. Este repositório publica ferramentas, integração, patches e metadados de endereços.

O checkpoint depende de artefatos privados gerados localmente. O processo de um clone limpo ainda precisa ser validado de ponta a ponta; não existe instalador pronto ou download jogável.

## Ferramentas e referências

Base principal: **ps3recomp**. Referências: **GT5 Prologue Recompiled**, **RPCS3** e **ShadowOfTheColossus-PC**. Análise estática: **Ghidra 12.2**, PyGhidra e Java. **REA 6.8.0** foi instalado e avaliado, mas sua integração Ghidra/PS3 ainda não funciona neste ambiente; a análise validada usou Ghidra diretamente.

Também usamos Python, Node.js, MinGW-w64 GCC, CMake/Ninja, SDL2, Vulkan-Headers, glslang e SPIRV-Tools/Headers. A preparação privada inicial utilizou PyCryptodome; essa ferramenta de extração e seus dados não são distribuídos aqui. O GitHub CLI é usado para publicação.

Desenvolvimento assistido por **OpenAI Codex, GPT-6.1 Sol com raciocínio médio**, conforme configuração informada pelo mantenedor. Código e conclusões precisam de revisão e evidência. Créditos, versões e limitações estão em [CREDITS](docs/CREDITS.md).

Projeto independente, sem vínculo ou endosso da Sony, Polyphony Digital, OpenAI ou autores das referências. Licença MIT para o código original de integração, preservando os avisos de terceiros.
